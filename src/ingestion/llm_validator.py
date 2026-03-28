"""
LLM validation layer for regex-based AI revenue extractions.

Uses Claude claude-sonnet-4-5 to validate whether regex-extracted revenue figures
are genuinely AI-specific, correctly parsed, and properly attributed to fiscal
periods. Designed as a second-pass filter over earnings_analysis.py output.

The validator checks:
1. Is the extracted figure actually AI-specific revenue (vs. total/other)?
2. Is the dollar amount correctly parsed from the text?
3. What fiscal period does the figure cover?
4. Overall confidence (0-1) in the extraction.

Usage:
    from src.ingestion.llm_validator import validate_extraction, validate_batch

    result = validate_extraction(
        extraction={"raw_snippet": "...", "extracted_value_usd": 47.5, ...},
        company_context={"company_name": "NVIDIA", "filing_type": "10-K"},
    )

    results = validate_batch(extractions, company_contexts)

Requires:
    ANTHROPIC_API_KEY environment variable (loaded via python-dotenv).
"""

import json
import logging
import os
import time

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env if present (no error if missing)
load_dotenv()

# Rate limiting: max requests per minute
MAX_REQUESTS_PER_MINUTE = 10
_MIN_INTERVAL = 60.0 / MAX_REQUESTS_PER_MINUTE  # 6 seconds between requests

# Model to use for validation
VALIDATION_MODEL = "claude-sonnet-4-5-20250514"

_VALIDATION_PROMPT_TEMPLATE = """\
You are a financial data validation assistant. Given a text snippet from a \
public company's SEC filing, validate a regex-extracted AI revenue figure.

Company: {company_name}
Filing type: {filing_type}
Extracted value: ${extracted_value_usd:.2f} billion
Pattern that matched: {pattern_name}

Text snippet:
\"\"\"{raw_snippet}\"\"\"

Answer these questions:
1. Is this actually AI-specific revenue (not total company revenue or a non-AI segment)?
2. Is the dollar amount ${extracted_value_usd:.2f}B correctly extracted from the text?
3. What fiscal period does this figure cover (e.g., "FY2024", "Q3 2024")?
4. Your confidence (0.0 to 1.0) that this extraction is valid AI-specific revenue.

Respond as JSON only, no other text:
{{"validated": true/false, "corrected_value_usd": null or number if different, \
"fiscal_period": "string", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}\
"""

# Unavailable fallback — returned when API is not reachable
_UNAVAILABLE_RESULT = {
    "validated": None,
    "corrected_value_usd": None,
    "fiscal_period": "",
    "confidence": 0.0,
    "reasoning": "LLM unavailable",
}


def _get_client():
    """Create Anthropic client, returning None if unavailable."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — LLM validation unavailable")
        return None

    try:
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    except Exception as e:
        logger.warning("Failed to create Anthropic client: %s", e)
        return None


def validate_extraction(
    extraction: dict,
    company_context: dict,
) -> dict:
    """
    Validate a single regex extraction using Claude claude-sonnet-4-5.

    Parameters
    ----------
    extraction : dict
        Output from extract_ai_revenue_mentions(). Must contain:
        raw_snippet, extracted_value_usd, pattern_name.
    company_context : dict
        Must contain: company_name, filing_type (e.g. "10-K", "10-Q").

    Returns
    -------
    dict
        {
            "validated": bool | None,
            "corrected_value_usd": float | None,
            "fiscal_period": str,
            "confidence": float,
            "reasoning": str,
        }
        Returns unavailable fallback if API key missing or call fails.
    """
    client = _get_client()
    if client is None:
        return dict(_UNAVAILABLE_RESULT)

    prompt = _VALIDATION_PROMPT_TEMPLATE.format(
        company_name=company_context.get("company_name", "Unknown"),
        filing_type=company_context.get("filing_type", "10-K"),
        extracted_value_usd=extraction.get("extracted_value_usd", 0.0),
        pattern_name=extraction.get("pattern_name", "unknown"),
        raw_snippet=extraction.get("raw_snippet", ""),
    )

    try:
        response = client.messages.create(
            model=VALIDATION_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text.strip()
        result = _parse_llm_response(raw_text)
        return result

    except Exception as e:
        logger.warning("LLM validation call failed: %s", e)
        return dict(_UNAVAILABLE_RESULT)


def _parse_llm_response(raw_text: str) -> dict:
    """Parse LLM JSON response, with fallback for malformed output."""
    # Strip markdown code fences if present
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last line (fences)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON response: %s", text[:200])
        return {
            "validated": None,
            "corrected_value_usd": None,
            "fiscal_period": "",
            "confidence": 0.0,
            "reasoning": f"Failed to parse LLM response: {text[:200]}",
        }

    return {
        "validated": parsed.get("validated"),
        "corrected_value_usd": parsed.get("corrected_value_usd"),
        "fiscal_period": str(parsed.get("fiscal_period", "")),
        "confidence": float(parsed.get("confidence", 0.0)),
        "reasoning": str(parsed.get("reasoning", "")),
    }


def validate_batch(
    extractions: list[dict],
    company_contexts: dict,
) -> list[dict]:
    """
    Validate a batch of extractions with rate limiting.

    Parameters
    ----------
    extractions : list[dict]
        List of extraction dicts from extract_ai_revenue_mentions().
        Each must contain at minimum: raw_snippet, extracted_value_usd,
        pattern_name, and a 'cik' key for context lookup.
    company_contexts : dict
        Mapping of CIK → company context dict. Each context must contain:
        company_name, filing_type.

    Returns
    -------
    list[dict]
        List of validation results, one per extraction. Each result is
        merged with the original extraction: all original keys plus
        llm_validated, llm_corrected_value_usd, llm_fiscal_period,
        llm_confidence, llm_reasoning.
    """
    results = []
    last_call_time = 0.0

    for extraction in extractions:
        cik = extraction.get("cik", "")
        context = company_contexts.get(cik, {
            "company_name": "Unknown",
            "filing_type": extraction.get("form_type", "10-K"),
        })
        # Override filing_type from extraction if available
        if "form_type" in extraction:
            context = {**context, "filing_type": extraction["form_type"]}

        # Rate limiting
        elapsed = time.time() - last_call_time
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)

        last_call_time = time.time()
        validation = validate_extraction(extraction, context)

        # Merge validation result with original extraction
        merged = dict(extraction)
        merged["llm_validated"] = validation["validated"]
        merged["llm_corrected_value_usd"] = validation["corrected_value_usd"]
        merged["llm_fiscal_period"] = validation["fiscal_period"]
        merged["llm_confidence"] = validation["confidence"]
        merged["llm_reasoning"] = validation["reasoning"]
        results.append(merged)

    return results
