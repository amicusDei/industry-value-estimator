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
from pathlib import Path

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


def _empty_attribution_df() -> pd.DataFrame:
    """Return empty earnings attribution DataFrame with correct schema."""
    return pd.DataFrame(columns=[
        "cik", "company_name", "fiscal_year", "fiscal_quarter",
        "total_revenue_usd", "ai_revenue_usd", "ai_ratio",
        "attribution_method", "confidence_score", "llm_validated",
        "vintage_date",
    ])


def run_earnings_attribution(industry_id: str = "ai") -> pd.DataFrame:
    """
    Run earnings-based AI revenue attribution for all companies in ai.yaml.

    For each company in edgar_companies:
    1. Attempts fetch_and_extract() for EDGAR filings
    2. Optionally runs LLM validation (if ANTHROPIC_API_KEY is set)
    3. Computes AI revenue ratio from regex extractions
    4. Falls back to static YAML ratios when no EDGAR data is available

    Output is written to data/processed/earnings_ai_attribution.parquet.

    Parameters
    ----------
    industry_id : str
        Industry config ID. Default "ai".

    Returns
    -------
    pd.DataFrame
        Earnings attribution results with schema: cik, company_name,
        fiscal_year, fiscal_quarter, total_revenue_usd, ai_revenue_usd,
        ai_ratio, attribution_method, confidence_score, llm_validated,
        vintage_date.
    """
    import yaml
    import pyarrow as pa
    import pyarrow.parquet as pq
    from datetime import datetime, timezone
    from config.settings import DATA_PROCESSED

    config_path = Path(__file__).resolve().parent.parent.parent / "config" / "industries" / f"{industry_id}.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    edgar_companies = config.get("edgar_companies", [])
    if not edgar_companies:
        logger.warning("No edgar_companies in %s.yaml", industry_id)
        return _empty_attribution_df()

    # Load existing YAML attribution as fallback
    from config.settings import DATA_RAW
    yaml_registry_path = DATA_RAW / "attribution" / f"{industry_id}_attribution_registry.yaml"
    yaml_fallback = {}
    if yaml_registry_path.exists():
        with open(yaml_registry_path) as f:
            yaml_data = yaml.safe_load(f)
        for entry in yaml_data.get("entries", []):
            yaml_fallback[entry["cik"]] = entry

    # Build company context for LLM validation
    company_contexts = {}
    for comp in edgar_companies:
        company_contexts[comp["cik"]] = {
            "company_name": comp["name"],
            "filing_type": "10-K",
        }

    rows = []
    for comp in edgar_companies:
        cik = comp["cik"]
        name = comp["name"]
        form_types = comp.get("form_types", ["10-K", "10-Q"])

        logger.info("Processing %s (CIK: %s)", name, cik)

        # Attempt EDGAR extraction
        extraction_df = pd.DataFrame()
        try:
            extraction_df = fetch_and_extract(cik, form_types=form_types, start_year=2022, end_year=2025)
        except Exception as e:
            logger.warning("EDGAR fetch failed for %s: %s", name, e)

        if not extraction_df.empty:
            # Pick highest-confidence extraction per (cik, period_end)
            best = _select_best_extractions(extraction_df)

            # Attempt LLM validation if available
            llm_validated_flag = None
            try:
                from src.ingestion.llm_validator import validate_batch
                validated = validate_batch(best.to_dict("records"), company_contexts)
                for v in validated:
                    fiscal_year, fiscal_quarter = _parse_fiscal_period(
                        v.get("llm_fiscal_period", v.get("period_end", ""))
                    )
                    rows.append({
                        "cik": cik,
                        "company_name": name,
                        "fiscal_year": fiscal_year,
                        "fiscal_quarter": fiscal_quarter,
                        "total_revenue_usd": None,
                        "ai_revenue_usd": v.get("llm_corrected_value_usd") or v["extracted_value_usd"],
                        "ai_ratio": None,
                        "attribution_method": "earnings_regex+llm",
                        "confidence_score": v.get("llm_confidence", 0.5),
                        "llm_validated": v.get("llm_validated"),
                        "vintage_date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
                    })
                continue
            except Exception as e:
                logger.info("LLM validation skipped for %s: %s", name, e)

            # Use regex-only extractions
            for _, row in best.iterrows():
                fiscal_year, fiscal_quarter = _parse_fiscal_period(str(row.get("period_end", "")))
                rows.append({
                    "cik": cik,
                    "company_name": name,
                    "fiscal_year": fiscal_year,
                    "fiscal_quarter": fiscal_quarter,
                    "total_revenue_usd": None,
                    "ai_revenue_usd": row["extracted_value_usd"],
                    "ai_ratio": None,
                    "attribution_method": "earnings_regex",
                    "confidence_score": _confidence_to_score(row["confidence"]),
                    "llm_validated": None,
                    "vintage_date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
                })
        else:
            # Fallback: use YAML static attribution
            if cik in yaml_fallback:
                entry = yaml_fallback[cik]
                rows.append({
                    "cik": cik,
                    "company_name": name,
                    "fiscal_year": entry.get("year", 2024),
                    "fiscal_quarter": None,
                    "total_revenue_usd": None,
                    "ai_revenue_usd": entry["ai_revenue_usd_billions"],
                    "ai_ratio": None,
                    "attribution_method": f"yaml_fallback/{entry['attribution_method']}",
                    "confidence_score": 0.3 if entry.get("estimated_flag") else 0.7,
                    "llm_validated": None,
                    "vintage_date": entry.get("vintage_date", ""),
                })
                logger.info("  %s: using YAML fallback ($%.1fB)", name, entry["ai_revenue_usd_billions"])
            else:
                logger.warning("  %s: no EDGAR data and no YAML fallback", name)

    if not rows:
        logger.warning("No earnings attribution results produced")
        result_df = _empty_attribution_df()
    else:
        result_df = pd.DataFrame(rows)

    # Write parquet
    output_path = DATA_PROCESSED / f"earnings_{industry_id}_attribution.parquet"
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(result_df, preserve_index=False)
    existing_meta = table.schema.metadata or {}
    custom_meta = {
        b"source": b"earnings_analysis",
        b"industry": industry_id.encode(),
        b"compiled_at": datetime.now(tz=timezone.utc).isoformat().encode(),
        b"n_companies": str(len(result_df["cik"].unique())).encode(),
    }
    table = table.replace_schema_metadata({**existing_meta, **custom_meta})
    pq.write_table(table, output_path, compression="snappy")

    logger.info("Wrote %d rows to %s", len(result_df), output_path)
    return result_df


def _select_best_extractions(df: pd.DataFrame) -> pd.DataFrame:
    """Select highest-confidence extraction per (cik, period_end)."""
    confidence_order = {"high": 3, "medium": 2, "low": 1}
    df = df.copy()
    df["_conf_rank"] = df["confidence"].map(confidence_order).fillna(0)
    # Group by (cik, period_end) and take the highest confidence
    idx = df.groupby(["cik", "period_end"])["_conf_rank"].idxmax()
    return df.loc[idx].drop(columns=["_conf_rank"]).reset_index(drop=True)


def _confidence_to_score(confidence_str: str) -> float:
    """Convert confidence string to numeric score."""
    return {"high": 0.9, "medium": 0.6, "low": 0.3}.get(confidence_str, 0.3)


def _parse_fiscal_period(period_str: str) -> tuple[int, int | None]:
    """Parse a fiscal period string into (year, quarter).

    Handles formats: "FY2024", "Q3 2024", "2024-09-30", "2024".

    Returns
    -------
    tuple[int, int | None]
        (fiscal_year, fiscal_quarter). Quarter is None for annual periods.
    """
    import re as _re

    if not period_str:
        return (2024, None)

    # "Q3 2024" or "Q3FY2024" or "Q1 FY 2025" — check before bare FY
    m = _re.search(r"Q(\d)\s*(?:FY)?\s*(\d{4})", period_str, _re.IGNORECASE)
    if m:
        return (int(m.group(2)), int(m.group(1)))

    # "FY2024" or "FY 2024" (after quarter check)
    m = _re.search(r"FY\s*(\d{4})", period_str, _re.IGNORECASE)
    if m:
        return (int(m.group(1)), None)

    # "2024-09-30" (date format)
    m = _re.search(r"(\d{4})-(\d{2})-\d{2}", period_str)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        quarter = (month - 1) // 3 + 1
        return (year, quarter)

    # "2024" bare year
    m = _re.search(r"(\d{4})", period_str)
    if m:
        return (int(m.group(1)), None)

    return (2024, None)
