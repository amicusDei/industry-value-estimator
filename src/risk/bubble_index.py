"""
AI Bubble Index — Composite indicator measuring AI investment overheating.

Computes 8 sub-scores from YAML config data:
  INPUT (5):  capex_intensity, concentration, dc_build, credit, shadow
  OUTPUT (2): enterprise_roi, productivity_gap
  PARALLEL (1): dotcom_parallel

Composite = weighted average (Input 60%, Output 30%, Parallel 10%).
Classification: <30 Healthy, 30-50 Elevated, 50-70 Warning, >70 Critical.

Output: data/processed/bubble_index.parquet
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

# Weights for composite score (must sum to 1.0)
WEIGHTS = {
    "capex_intensity_score": 0.15,
    "concentration_score": 0.10,
    "dc_build_score": 0.10,
    "credit_score": 0.15,
    "shadow_score": 0.10,
    "enterprise_roi_score": 0.15,
    "productivity_gap_score": 0.15,
    "dotcom_parallel_score": 0.10,
}

CLASSIFICATION_THRESHOLDS = [
    (30, "Healthy Expansion"),
    (50, "Elevated Valuations"),
    (70, "Bubble Warning"),
    (float("inf"), "Critical Overheating"),
]


def _clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clip value to [lo, hi]."""
    return max(lo, min(hi, value))


def _normalize_linear(value: float, low: float, high: float) -> float:
    """Normalize value to 0-100 scale. value=low -> 0, value=high -> 100."""
    if high == low:
        return 50.0
    return _clip((value - low) / (high - low) * 100.0)


def _classify(score: float) -> str:
    """Classify composite score into risk category."""
    for threshold, label in CLASSIFICATION_THRESHOLDS:
        if score < threshold:
            return label
    return "Critical Overheating"


def _build_lookup(entries: list[dict], key_fields: tuple[str, ...] = ("year", "half")) -> dict:
    """Build a (year, half) -> entry lookup from a list of dicts."""
    return {tuple(e[k] for k in key_fields): e for e in entries}


def _compute_capex_intensity_score(entry: dict) -> float:
    """Capex intensity ratio normalized: 1.0 -> 0, 5.0 -> 100."""
    capex = entry.get("hyperscaler_ai_capex_usd_b", 0)
    revenue = entry.get("ai_revenue_usd_b", 1)
    ratio = capex / max(revenue, 0.1)
    return _normalize_linear(ratio, 1.0, 5.0)


def _compute_concentration_score(entry: dict) -> float:
    """AI-specific concentration via HHI. HHI 0.10 -> 0, HHI 0.40 -> 100."""
    hhi = entry.get("ai_revenue_hhi", 0.10)
    return _normalize_linear(hhi, 0.10, 0.40)


def _compute_dc_build_score(entry: dict) -> float:
    """DC build momentum: 0% YoY -> 0, 100% YoY -> 100."""
    yoy = entry.get("yoy_growth_pct", 0)
    return _normalize_linear(yoy, 0.0, 100.0)


def _compute_credit_score(entry: dict, total_ai_market_usd_b: float = 200.0) -> float:
    """Credit exposure: total credit / AI market normalized.

    Uses total_credit / total_ai_market ratio, normalized 0-100.
    Ratio 0.0 -> 0, ratio 5.0 -> 100.
    """
    bonds = entry.get("hyperscaler_bonds_usd_b", 0)
    private = entry.get("private_credit_ai_usd_b", 0)
    off_bs = entry.get("off_balance_sheet_est_usd_b", 0)
    total = bonds + private + off_bs
    ratio = total / max(total_ai_market_usd_b, 1.0)
    return _normalize_linear(ratio, 0.0, 5.0)


def _compute_shadow_score(entry: dict) -> float:
    """Shadow leverage composite: off-BS opacity + SPV proliferation + asset-life mismatch."""
    off_bs = entry.get("off_bs_ratio", 0.5)
    spv_count = entry.get("spv_jv_count", 0)
    mismatch = entry.get("asset_life_mismatch_ratio", 3.0)
    s1 = _normalize_linear(off_bs, 0.5, 3.0)
    s2 = _normalize_linear(spv_count, 5.0, 40.0)
    s3 = _normalize_linear(mismatch, 3.0, 15.0)
    return _clip(s1 * 0.40 + s2 * 0.30 + s3 * 0.30)


def _compute_enterprise_roi_score(entry: dict) -> float:
    """Enterprise ROI gap model — expectation vs realization.

    Three components:
    1. Expectation gap: spend_growth - impact (higher gap = more bubble)
    2. ROI hollowness: headcount-driven ROI relative to actual impact
    3. Margin burden: direct infrastructure cost erosion
    """
    spend_growth = entry.get("enterprise_ai_spend_growth_pct", 0)
    impact = entry.get("revenue_and_cost_impact_pct", 0)
    headcount = entry.get("roi_from_headcount_pct", 0)
    margin = entry.get("margin_erosion_from_ai_infra_pct", 0)

    expectation_gap = max(0, spend_growth - impact)
    roi_hollowness = min(100.0, (headcount / max(impact, 1.0)) * 10.0)
    margin_burden = margin

    raw = expectation_gap * 0.40 + roi_hollowness * 0.35 + margin_burden * 0.25
    return _normalize_linear(raw, 10.0, 80.0)


def _compute_productivity_gap_score(entry: dict) -> float:
    """Productivity gap (Solow Index): solow_gap_ratio normalized.

    solow_gap_ratio = capex_growth / productivity_growth
    Ratio 1x -> 0, ratio 25x -> 100.
    """
    capex_g = entry.get("ai_capex_growth_yoy_pct", 0)
    prod_g = entry.get("us_productivity_growth_pct", 0)

    # Avoid division by zero or negative; use absolute value of productivity
    if abs(prod_g) < 0.1:
        prod_g = 0.1

    ratio = abs(capex_g) / abs(prod_g)
    return _normalize_linear(ratio, 1.0, 25.0)


def _compute_dotcom_parallel_score(
    year: int,
    half: int,
    ai_capex_ratio: float,
    ai_concentration: float,
    ai_credit_total: float,
    ai_dc_growth: float,
    dotcom_data: list[dict],
) -> float:
    """Compute how closely current AI metrics parallel the dotcom cycle.

    Maps AI cycle years to dotcom equivalent:
    2020 -> 1996, 2021 -> 1997, ..., 2026 -> 2002
    But we cap at 2000 (peak) for comparison.

    Score based on how much AI exceeds dotcom at equivalent cycle point.
    """
    # Map AI year to dotcom equivalent year
    # AI cycle start: 2020, Dotcom cycle start: 1996
    cycle_offset = year - 2020
    dotcom_equiv_year = 1996 + cycle_offset

    # Clamp to available dotcom range
    dotcom_equiv_year = max(1996, min(2002, dotcom_equiv_year))

    dotcom_lookup = {e["year"]: e for e in dotcom_data}
    dotcom_entry = dotcom_lookup.get(dotcom_equiv_year)

    if dotcom_entry is None:
        return 0.0

    # Compare AI vs dotcom on multiple dimensions
    scores = []

    # Capex intensity comparison
    dc_capex = dotcom_entry.get("capex_intensity_ratio", 1.0)
    if dc_capex > 0:
        ratio = ai_capex_ratio / dc_capex
        scores.append(_normalize_linear(ratio, 0.5, 2.5))

    # Concentration comparison
    dc_conc = dotcom_entry.get("concentration_pct", 10.0)
    if dc_conc > 0:
        ratio = ai_concentration / dc_conc
        scores.append(_normalize_linear(ratio, 0.5, 3.0))

    # Build rate comparison (DC growth vs fiber build)
    dc_build = dotcom_entry.get("fiber_build_rate_yoy_pct", 10.0)
    if abs(dc_build) > 0.1:
        ratio = ai_dc_growth / max(abs(dc_build), 0.1)
        scores.append(_normalize_linear(ratio, 0.3, 2.0))

    if not scores:
        return 0.0

    return _clip(sum(scores) / len(scores))


def _estimate_total_ai_market(year: int, half: int) -> float:
    """Rough estimate of total AI market size for credit ratio normalization."""
    # Simple growth model: ~$50B in 2020, growing ~35% CAGR
    base = 50.0
    years_from_base = (year - 2020) + (half - 1) * 0.5
    return base * (1.35 ** years_from_base)


def compute_bubble_index(config: dict) -> pd.DataFrame:
    """Compute the AI Bubble Index from YAML configuration data.

    Args:
        config: Parsed YAML config dict containing 'bubble_index' key.

    Returns:
        DataFrame with columns: year, half, 8 subscores, composite_score, classification,
        plus raw metrics for transparency.
    """
    bi = config.get("bubble_index", {})

    capex_data = _build_lookup(bi.get("capex_intensity", []))
    conc_data = _build_lookup(bi.get("market_concentration", []))
    dc_data = _build_lookup(bi.get("dc_build_momentum", []))
    credit_data = _build_lookup(bi.get("credit_exposure", []))
    shadow_data = _build_lookup(bi.get("shadow_leverage", []))
    roi_data = _build_lookup(bi.get("enterprise_roi", []))
    prod_data = _build_lookup(bi.get("productivity_gap", []))
    dotcom_data = bi.get("dotcom_parallel", [])

    # Collect all (year, half) keys across all indicators
    all_periods = sorted(
        set(capex_data.keys())
        | set(conc_data.keys())
        | set(dc_data.keys())
        | set(credit_data.keys())
        | set(shadow_data.keys())
        | set(roi_data.keys())
        | set(prod_data.keys())
    )

    rows = []
    for year, half in all_periods:
        capex_entry = capex_data.get((year, half), {})
        conc_entry = conc_data.get((year, half), {})
        dc_entry = dc_data.get((year, half), {})
        credit_entry = credit_data.get((year, half), {})
        shadow_entry = shadow_data.get((year, half), {})
        roi_entry = roi_data.get((year, half), {})
        prod_entry = prod_data.get((year, half), {})

        # Total AI market for credit normalization
        total_market = _estimate_total_ai_market(year, half)

        # Compute all 8 subscores
        capex_score = _compute_capex_intensity_score(capex_entry)
        conc_score = _compute_concentration_score(conc_entry)
        dc_score = _compute_dc_build_score(dc_entry)
        credit_score = _compute_credit_score(credit_entry, total_market)
        shadow_score = _compute_shadow_score(shadow_entry)
        roi_score = _compute_enterprise_roi_score(roi_entry)
        prod_score = _compute_productivity_gap_score(prod_entry)

        # Capex ratio for dotcom comparison
        capex_usd = capex_entry.get("hyperscaler_ai_capex_usd_b", 0)
        rev_usd = capex_entry.get("ai_revenue_usd_b", 1)
        capex_ratio = capex_usd / max(rev_usd, 0.1)

        conc_pct = conc_entry.get("top_player_ai_share_pct", 0)
        dc_growth = dc_entry.get("yoy_growth_pct", 0)
        credit_total = (
            credit_entry.get("hyperscaler_bonds_usd_b", 0)
            + credit_entry.get("private_credit_ai_usd_b", 0)
            + credit_entry.get("off_balance_sheet_est_usd_b", 0)
        )

        dotcom_score = _compute_dotcom_parallel_score(
            year, half, capex_ratio, conc_pct, credit_total, dc_growth, dotcom_data
        )

        # Composite weighted average
        scores = {
            "capex_intensity_score": capex_score,
            "concentration_score": conc_score,
            "dc_build_score": dc_score,
            "credit_score": credit_score,
            "shadow_score": shadow_score,
            "enterprise_roi_score": roi_score,
            "productivity_gap_score": prod_score,
            "dotcom_parallel_score": dotcom_score,
        }

        composite = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
        composite = _clip(composite)
        classification = _classify(composite)

        row = {
            "year": year,
            "half": half,
            **scores,
            "composite_score": round(composite, 1),
            "classification": classification,
            # Raw metrics for transparency
            "capex_intensity_ratio": round(capex_ratio, 2),
            "ai_revenue_hhi": conc_entry.get("ai_revenue_hhi", 0),
            "top_player_ai_share_pct": conc_entry.get("top_player_ai_share_pct", 0),
            "dc_yoy_growth_pct": dc_growth,
            "credit_total_usd_b": round(credit_total, 1),
            "off_bs_ratio": shadow_entry.get("off_bs_ratio", 0),
            "spv_jv_count": shadow_entry.get("spv_jv_count", 0),
            "asset_life_mismatch_ratio": shadow_entry.get("asset_life_mismatch_ratio", 0),
            "revenue_and_cost_impact_pct": roi_entry.get("revenue_and_cost_impact_pct", 0),
            "enterprise_ai_spend_growth_pct": roi_entry.get("enterprise_ai_spend_growth_pct", 0),
            "roi_from_headcount_pct": roi_entry.get("roi_from_headcount_pct", 0),
            "margin_erosion_from_ai_infra_pct": roi_entry.get("margin_erosion_from_ai_infra_pct", 0),
            "us_productivity_growth_pct": prod_entry.get("us_productivity_growth_pct", 0),
            "ai_capex_growth_yoy_pct": prod_entry.get("ai_capex_growth_yoy_pct", 0),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    logger.info("Bubble Index computed: %d periods, composite range [%.0f, %.0f]",
                len(df), df.composite_score.min(), df.composite_score.max())
    return df


def run(config_path: str | Path | None = None, output_path: str | Path | None = None) -> pd.DataFrame:
    """Load config, compute bubble index, and write parquet.

    Args:
        config_path: Path to ai.yaml. Defaults to config/industries/ai.yaml.
        output_path: Path to output parquet. Defaults to data/processed/bubble_index.parquet.

    Returns:
        The computed DataFrame.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    if config_path is None:
        config_path = project_root / "config" / "industries" / "ai.yaml"
    if output_path is None:
        output_path = project_root / "data" / "processed" / "bubble_index.parquet"

    config_path = Path(config_path)
    output_path = Path(output_path)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    df = compute_bubble_index(config)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    logger.info("Wrote bubble_index.parquet: %s (%d rows)", output_path, len(df))

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    df = run()
    print(f"\nBubble Index computed: {len(df)} periods")
    print(f"Score range: [{df.composite_score.min():.0f}, {df.composite_score.max():.0f}]")
    print("\nTimeline:")
    for _, row in df.sort_values(["year", "half"]).iterrows():
        print(f"  {row.year} H{row.half}: {row.composite_score:.0f} ({row.classification})")
