"""AI Bubble Index API endpoints.

Serves the computed bubble index data, dotcom parallel comparison,
and data centre risk metrics.
"""

import logging
from pathlib import Path

import yaml
from fastapi import APIRouter

from api.data_loader import get_bubble_index

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["bubble-index"])

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "industries" / "ai.yaml"


def _load_config() -> dict:
    """Load bubble_index config from ai.yaml."""
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    return cfg.get("bubble_index", {})


@router.get("/bubble-index")
def bubble_index():
    """Return all semi-annual bubble index rows with composite score and subscores."""
    df = get_bubble_index()
    if df.empty:
        return []

    df = df.sort_values(["year", "half"])
    return df.to_dict(orient="records")


@router.get("/bubble-index/dotcom-parallel")
def dotcom_parallel():
    """Return AI bubble index alongside dotcom-era equivalent for comparison.

    Response: { ai: [...], dotcom: [...] }
    """
    df = get_bubble_index()
    bi_cfg = _load_config()
    dotcom_data = bi_cfg.get("dotcom_parallel", [])

    # AI timeline
    ai_rows = []
    if not df.empty:
        df = df.sort_values(["year", "half"])
        for _, row in df.iterrows():
            ai_rows.append({
                "year": int(row["year"]),
                "half": int(row["half"]),
                "composite_score": round(float(row["composite_score"]), 1),
                "classification": row["classification"],
            })

    # Dotcom timeline with composite-like score
    dotcom_rows = []
    for entry in sorted(dotcom_data, key=lambda x: x["year"]):
        # Compute a rough composite for dotcom using available metrics
        capex_r = entry.get("capex_intensity_ratio", 1.0)
        conc = entry.get("concentration_pct", 10.0)
        bond = entry.get("telecom_bond_issuance_usd_b", 0)
        fiber = entry.get("fiber_build_rate_yoy_pct", 0)
        it_capex_g = entry.get("it_capex_growth_pct", 0)
        prod_g = entry.get("productivity_growth_pct", 1.0)

        # Normalize similarly to AI scores
        capex_score = max(0, min(100, (capex_r - 1.0) / (5.0 - 1.0) * 100))
        conc_score = max(0, min(100, (conc - 10.0) / (40.0 - 10.0) * 100))
        build_score = max(0, min(100, fiber / 100.0 * 100))
        credit_score = max(0, min(100, bond / 200.0 * 100))
        prod_ratio = abs(it_capex_g) / max(abs(prod_g), 0.1)
        prod_score = max(0, min(100, (prod_ratio - 1.0) / (25.0 - 1.0) * 100))

        composite = (
            capex_score * 0.20 +
            conc_score * 0.15 +
            build_score * 0.20 +
            credit_score * 0.25 +
            prod_score * 0.20
        )
        composite = max(0, min(100, composite))

        dotcom_rows.append({
            "year": entry["year"],
            "composite_score": round(composite, 1),
            "capex_intensity_ratio": capex_r,
            "concentration_pct": conc,
            "telecom_bond_issuance_usd_b": bond,
        })

    return {"ai": ai_rows, "dotcom": dotcom_rows}


@router.get("/bubble-index/dc-risk")
def dc_risk():
    """Return data centre risk metrics: build rate, credit stack, refinancing calendar.

    Pulls from both computed bubble index and raw YAML config.
    """
    df = get_bubble_index()
    bi_cfg = _load_config()

    # Build rate from bubble index data
    build_rate = []
    if not df.empty:
        df_sorted = df.sort_values(["year", "half"])
        for _, row in df_sorted.iterrows():
            build_rate.append({
                "year": int(row["year"]),
                "half": int(row["half"]),
                "dc_yoy_growth_pct": round(float(row.get("dc_yoy_growth_pct", 0)), 1),
                "dc_build_score": round(float(row.get("dc_build_score", 0)), 1),
            })

    # Credit stack from bubble index
    credit_stack = []
    if not df.empty:
        for _, row in df_sorted.iterrows():
            credit_stack.append({
                "year": int(row["year"]),
                "half": int(row["half"]),
                "total_usd_b": round(float(row.get("credit_total_usd_b", 0)), 1),
                "credit_score": round(float(row.get("credit_score", 0)), 1),
                "bis_risk_rating": int(row.get("bis_risk_rating", 0)),
            })

    # Refinancing calendar and asset-life mismatch from YAML
    dc_risk_cfg = bi_cfg.get("dc_risk", {})
    refinancing = dc_risk_cfg.get("refinancing_calendar", [])
    mismatch = dc_risk_cfg.get("asset_life_mismatch", {})

    return {
        "build_rate": build_rate,
        "credit_stack": credit_stack,
        "refinancing_calendar": refinancing,
        "asset_life_mismatch": mismatch,
    }
