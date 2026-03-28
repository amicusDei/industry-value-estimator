"""
Private market integration: adds private company ARR to public market anchors.

Private AI companies (OpenAI, Anthropic, Databricks, CoreWeave, etc.) are not
captured in the analyst consensus market anchors which track primarily public
company revenue. This module computes the private market contribution and adds
it to the segment-level market size estimates.

Confidence-weighted approach: HIGH-confidence ARR estimates (verified funding
rounds + revenue reports) get full weight; MEDIUM gets 0.7x; LOW gets 0.4x.
This reflects the decreasing reliability of private company revenue estimates.

Usage:
    contribution = compute_private_contribution()
    # Returns dict: {segment: {"arr_weighted": float, "low": float, "high": float}}
"""

import logging

import pandas as pd

from config.settings import DATA_PROCESSED

logger = logging.getLogger(__name__)

# Confidence tier weights
CONFIDENCE_WEIGHTS = {
    "HIGH": 1.0,
    "MEDIUM": 0.7,
    "LOW": 0.4,
}


def compute_private_contribution() -> dict[str, dict]:
    """
    Compute private company ARR contribution per segment.

    Reads private_valuations_ai.parquet, groups by segment, and applies
    confidence-weighted summation of estimated ARR.

    Returns
    -------
    dict[str, dict]
        Maps segment name to:
        {
            "arr_weighted": float — confidence-weighted ARR sum (USD billions)
            "low": float — sum of implied_ev_low / comparable_mid_multiple
            "high": float — sum of implied_ev_high / comparable_mid_multiple
            "n_companies": int — number of private companies in segment
        }
        Empty dict if private_valuations parquet not found.
    """
    path = DATA_PROCESSED / "private_valuations_ai.parquet"
    if not path.exists():
        logger.warning("private_valuations_ai.parquet not found — no private contribution")
        return {}

    pv = pd.read_parquet(path)
    if pv.empty:
        return {}

    # Compute ARR from EV/multiples as cross-check, prefer direct ARR column
    if "estimated_arr_usd_billions" in pv.columns:
        pv["arr"] = pv["estimated_arr_usd_billions"].astype(float)
    else:
        pv["arr"] = pv["implied_ev_mid"] / pv["comparable_mid_multiple"]

    # Confidence weighting
    pv["weight"] = pv["confidence_tier"].map(CONFIDENCE_WEIGHTS).fillna(0.4)
    pv["arr_weighted"] = pv["arr"] * pv["weight"]

    # Uncertainty bounds via EV low/high divided by mid multiple
    pv["arr_low"] = pv["implied_ev_low"] / pv["comparable_mid_multiple"]
    pv["arr_high"] = pv["implied_ev_high"] / pv["comparable_mid_multiple"]

    result = {}
    for segment, group in pv.groupby("segment"):
        result[segment] = {
            "arr_weighted": float(group["arr_weighted"].sum()),
            "low": float(group["arr_low"].sum()),
            "high": float(group["arr_high"].sum()),
            "n_companies": len(group),
        }

    logger.info(
        "Private market contribution: %s",
        {seg: f"${v['arr_weighted']:.1f}B ({v['n_companies']} cos)" for seg, v in result.items()},
    )
    return result
