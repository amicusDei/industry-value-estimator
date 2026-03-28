"""
Regex-based AI revenue extraction from EDGAR filing text.

Scans 10-K and 10-Q filing text for AI-related revenue mentions using
company-specific and generic regex patterns. Produces structured extraction
results with confidence scores for downstream revenue attribution.

This module complements the XBRL extraction in edgar.py: XBRL provides
structured financial data (total revenue), while this module extracts
AI-specific segment revenue from management commentary and MD&A sections
where XBRL tags are absent.

Usage:
    # Extract from raw text:
    mentions = extract_ai_revenue_mentions(filing_text, cik="0001045810")

    # Full pipeline via edgartools:
    df = fetch_and_extract("0001045810", form_types=["10-K", "10-Q"])
"""

import logging
import re

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Company-specific regex patterns
# ---------------------------------------------------------------------------
# Each pattern targets the specific disclosure language used by that company.
# Patterns are ordered from most specific to most generic within each company.

COMPANY_PATTERNS: dict[str, list[dict]] = {
    # NVIDIA — "Data Center" segment is the primary AI revenue line
    "0001045810": [
        {
            "name": "nvidia_data_center",
            "pattern": re.compile(
                r"(?:Data Center|Compute & Networking)"
                r".*?(?:revenue|sales)"
                r".*?\$?([\d,.]+)\s*(billion|million|B|M)",
                re.IGNORECASE | re.DOTALL,
            ),
            "confidence": "high",
        },
    ],
    # Microsoft — Azure / Intelligent Cloud
    "0000789019": [
        {
            "name": "microsoft_azure_ai",
            "pattern": re.compile(
                r"(?:Azure|Intelligent Cloud|AI)"
                r".*?(?:revenue|grew|increased)"
                r".*?\$?([\d,.]+)\s*(billion|million|B|M)",
                re.IGNORECASE | re.DOTALL,
            ),
            "confidence": "medium",
        },
    ],
    # Alphabet — Google Cloud
    "0001652044": [
        {
            "name": "alphabet_google_cloud",
            "pattern": re.compile(
                r"(?:Google Cloud|Cloud segment)"
                r".*?(?:revenue|sales)"
                r".*?\$?([\d,.]+)\s*(billion|million|B|M)",
                re.IGNORECASE | re.DOTALL,
            ),
            "confidence": "medium",
        },
    ],
    # Amazon — AWS
    "0001018724": [
        {
            "name": "amazon_aws",
            "pattern": re.compile(
                r"(?:AWS|Amazon Web Services)"
                r".*?(?:revenue|sales|net sales)"
                r".*?\$?([\d,.]+)\s*(billion|million|B|M)",
                re.IGNORECASE | re.DOTALL,
            ),
            "confidence": "medium",
        },
    ],
    # Meta — AI investment / CapEx mentions
    # Two patterns: dollar-then-keyword and keyword-then-dollar
    "0001326801": [
        {
            "name": "meta_ai_investment",
            "pattern": re.compile(
                r"(?:AI|machine learning|infrastructure)"
                r".*?(?:invest|capex|spend)"
                r".*?\$?([\d,.]+)\s*(billion|million|B|M)",
                re.IGNORECASE | re.DOTALL,
            ),
            "confidence": "low",
        },
        {
            "name": "meta_ai_capex",
            "pattern": re.compile(
                r"\$?([\d,.]+)\s*(billion|million|B|M)"
                r".*?(?:invest|capex|spend).*?"
                r"(?:AI|artificial intelligence|infrastructure)",
                re.IGNORECASE | re.DOTALL,
            ),
            "confidence": "low",
        },
    ],
    # AMD — Data Center segment
    "0000002488": [
        {
            "name": "amd_data_center",
            "pattern": re.compile(
                r"(?:Data Center)"
                r".*?(?:revenue|sales|net revenue)"
                r".*?\$?([\d,.]+)\s*(billion|million|B|M)",
                re.IGNORECASE | re.DOTALL,
            ),
            "confidence": "medium",
        },
    ],
    # Palantir — AI Platform revenue (direct disclosure)
    "0001321655": [
        {
            "name": "palantir_aip",
            "pattern": re.compile(
                r"(?:AIP|Artificial Intelligence Platform|AI Platform)"
                r".*?(?:revenue|contribution)"
                r".*?\$?([\d,.]+)\s*(billion|million|B|M)",
                re.IGNORECASE | re.DOTALL,
            ),
            "confidence": "high",
        },
    ],
}

# Generic pattern applied to all companies as fallback
GENERIC_AI_PATTERN = {
    "name": "generic_ai_revenue",
    "pattern": re.compile(
        r"(?:artificial intelligence|AI|machine learning|ML)"
        r".*?(?:revenue|sales|contribution)"
        r".*?\$?([\d,.]+)\s*(billion|million|B|M)",
        re.IGNORECASE | re.DOTALL,
    ),
    "confidence": "low",
}

# Context window size (chars before and after match) for snippet extraction
CONTEXT_WINDOW = 200

# Maximum chars to search within a single regex match span to prevent
# catastrophic backtracking on very large documents
MAX_MATCH_SPAN = 500


def _normalize_value(raw_str: str, unit: str) -> float:
    """Convert extracted string + unit to USD billions.

    Parameters
    ----------
    raw_str : str
        Numeric string, possibly with commas (e.g., "47.5", "12,300").
    unit : str
        Unit indicator: "billion", "B", "million", or "M".

    Returns
    -------
    float
        Value in USD billions.
    """
    cleaned = raw_str.replace(",", "")
    value = float(cleaned)
    unit_lower = unit.lower()
    if unit_lower in ("million", "m"):
        return value / 1000.0
    return value


def extract_ai_revenue_mentions(
    filing_text: str,
    cik: str,
) -> list[dict]:
    """
    Extract AI revenue mentions from filing text using regex patterns.

    Applies company-specific patterns first (if available for the CIK),
    then the generic AI pattern as fallback. Each match produces a structured
    dict with the extracted value, confidence, and surrounding context.

    Parameters
    ----------
    filing_text : str
        Full text of a 10-K or 10-Q filing (or the MD&A section).
    cik : str
        SEC CIK number used to select company-specific patterns.

    Returns
    -------
    list[dict]
        Each dict contains:
        - raw_snippet: str — surrounding text context
        - extracted_value_usd: float — value in USD billions
        - unit: str — original unit (billion/million/B/M)
        - confidence: str — high/medium/low
        - pattern_name: str — which pattern matched
        - context_window: int — chars of context included
    """
    if not filing_text or not filing_text.strip():
        return []

    results = []
    seen_values = set()  # deduplicate by (pattern_name, value)

    # Build pattern list: company-specific first, then generic
    patterns_to_try = list(COMPANY_PATTERNS.get(cik, []))
    patterns_to_try.append(GENERIC_AI_PATTERN)

    for pat_config in patterns_to_try:
        pattern = pat_config["pattern"]
        pat_name = pat_config["name"]
        pat_confidence = pat_config["confidence"]

        # Search with limited span to prevent catastrophic backtracking
        for match in pattern.finditer(filing_text):
            # Skip matches that span too much text (likely false positives)
            if match.end() - match.start() > MAX_MATCH_SPAN:
                continue

            raw_value_str = match.group(1)
            unit = match.group(2)

            try:
                value_usd = _normalize_value(raw_value_str, unit)
            except (ValueError, TypeError) as e:
                logger.debug("Failed to parse value '%s %s': %s", raw_value_str, unit, e)
                continue

            # Sanity check: AI revenue should be between $0.01B and $500B
            if value_usd < 0.01 or value_usd > 500:
                continue

            # Deduplicate
            dedup_key = (pat_name, round(value_usd, 2))
            if dedup_key in seen_values:
                continue
            seen_values.add(dedup_key)

            # Extract context window
            start = max(0, match.start() - CONTEXT_WINDOW)
            end = min(len(filing_text), match.end() + CONTEXT_WINDOW)
            snippet = filing_text[start:end].strip()
            # Collapse whitespace in snippet
            snippet = re.sub(r"\s+", " ", snippet)

            results.append({
                "raw_snippet": snippet,
                "extracted_value_usd": value_usd,
                "unit": unit,
                "confidence": pat_confidence,
                "pattern_name": pat_name,
                "context_window": CONTEXT_WINDOW,
            })

    return results


def fetch_and_extract(
    cik: str,
    form_types: list[str] | None = None,
    start_year: int = 2020,
    end_year: int = 2025,
) -> pd.DataFrame:
    """
    Fetch EDGAR filings for a company and extract AI revenue mentions.

    Uses edgartools to retrieve filing text, then applies regex extraction.
    Requires set_edgar_identity() to have been called first.

    Parameters
    ----------
    cik : str
        SEC CIK number, e.g. "0001045810".
    form_types : list[str], optional
        Filing types to fetch. Default: ["10-K", "10-Q"].
    start_year : int
        First filing year (inclusive). Default 2020.
    end_year : int
        Last filing year (inclusive). Default 2025.

    Returns
    -------
    pd.DataFrame
        Columns: cik, period_end, form_type, pattern_name, extracted_value_usd,
        unit, confidence, raw_snippet.
        Empty DataFrame if no matches found or edgartools unavailable.
    """
    if form_types is None:
        form_types = ["10-K", "10-Q"]

    try:
        from edgar import Company
    except ImportError:
        logger.warning("edgartools not available — cannot fetch EDGAR filings")
        return _empty_result_df()

    rows = []
    company = Company(cik)
    date_filter = f"{start_year}-01-01:{end_year}-12-31"

    for form_type in form_types:
        try:
            filings = company.get_filings(form=form_type)
            filings = filings.filter(date=date_filter)
        except Exception as e:
            logger.warning("Failed to fetch %s filings for CIK %s: %s", form_type, cik, e)
            continue

        for filing in filings:
            try:
                # Get the filing text — edgartools provides .text() or .html()
                text = None
                try:
                    text = filing.text()
                except Exception:
                    pass
                if not text:
                    try:
                        text = filing.html()
                    except Exception:
                        pass
                if not text:
                    logger.debug("No text available for CIK %s filing %s", cik, filing.period_of_report)
                    continue

                mentions = extract_ai_revenue_mentions(text, cik)
                for mention in mentions:
                    rows.append({
                        "cik": cik,
                        "period_end": str(getattr(filing, "period_of_report", "")),
                        "form_type": form_type,
                        "pattern_name": mention["pattern_name"],
                        "extracted_value_usd": mention["extracted_value_usd"],
                        "unit": mention["unit"],
                        "confidence": mention["confidence"],
                        "raw_snippet": mention["raw_snippet"],
                    })

            except Exception as e:
                logger.warning("Failed to process filing for CIK %s: %s", cik, e)
                continue

    if not rows:
        logger.info("No AI revenue mentions found for CIK %s", cik)
        return _empty_result_df()

    return pd.DataFrame(rows)


def _empty_result_df() -> pd.DataFrame:
    """Return empty DataFrame with the correct schema."""
    return pd.DataFrame(columns=[
        "cik", "period_end", "form_type", "pattern_name",
        "extracted_value_usd", "unit", "confidence", "raw_snippet",
    ])
