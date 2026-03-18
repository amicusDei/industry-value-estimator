"""
Industry and segment tagging module.

Every row in the processed layer MUST have:
- industry_tag: which industry this data belongs to (e.g., "ai")
- industry_segment: which segment within the industry (e.g., "ai_hardware")
- source: which data source produced this row (e.g., "world_bank")

Tags are derived from the industry config YAML, not hardcoded.
"""
import pandas as pd


def apply_industry_tags(
    df: pd.DataFrame,
    config: dict,
    source: str,
    segment: str = "macro",
) -> pd.DataFrame:
    """
    Add industry_tag, industry_segment, and source columns.

    Parameters
    ----------
    df : pd.DataFrame
        Data to tag.
    config : dict
        Industry config (from load_industry_config).
    source : str
        Data source name: "world_bank", "oecd", or "lseg".
    segment : str
        Industry segment. For macro data (World Bank), use "macro".
        For LSEG company data, use the segment from TRBC mapping.

    Returns
    -------
    pd.DataFrame with added tag columns.
    """
    result = df.copy()
    result["industry_tag"] = config["industry"]  # e.g., "ai"
    result["industry_segment"] = segment
    result["source"] = source
    return result


def tag_lseg_by_trbc(
    df: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    """
    Tag LSEG company data with industry segments based on TRBC code mapping.

    Uses the trbc_codes section of config to map each company's
    TRBCActivityCode to an industry segment.
    """
    result = df.copy()
    result["industry_tag"] = config["industry"]
    result["source"] = "lseg"

    # Build TRBC code -> segment mapping from config
    trbc_to_segment = {}
    for entry in config.get("lseg", {}).get("trbc_codes", []):
        trbc_to_segment[entry["code"]] = entry["segment"]

    # Map TRBC codes to segments
    trbc_col = "TR.TRBCActivityCode" if "TR.TRBCActivityCode" in result.columns else "trbc_code"
    if trbc_col in result.columns:
        result["industry_segment"] = result[trbc_col].astype(str).map(trbc_to_segment)
        result["industry_segment"] = result["industry_segment"].fillna("ai_software")  # default
    else:
        result["industry_segment"] = "ai_software"  # fallback

    return result
