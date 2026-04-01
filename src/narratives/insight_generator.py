"""
Rule-based insight generator for AI industry segments.

Produces 3-5 factual narrative insights per segment, derived purely from
the pipeline's parquet outputs. No LLM, no external API calls.
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"

SEGMENTS = ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]


def _fmt_usd(val: float) -> str:
    """Format USD billions: $142.3B or $310M for sub-billion."""
    if abs(val) < 1:
        return f"${val * 1000:.0f}M"
    if abs(val) >= 100:
        return f"${val:.0f}B"
    return f"${val:.1f}B"


def _fmt_pct(val: float) -> str:
    """Format percentage: 15.2%."""
    return f"{val:.1f}%"


def _load_ensemble() -> pd.DataFrame:
    path = DATA_DIR / "forecasts_ensemble.parquet"
    if not path.exists():
        logger.warning("forecasts_ensemble.parquet not found at %s", path)
        return pd.DataFrame()
    return pd.read_parquet(path)


def _load_scenarios() -> pd.DataFrame:
    path = DATA_DIR / "forecasts_scenarios.parquet"
    if not path.exists():
        logger.warning("forecasts_scenarios.parquet not found at %s", path)
        return pd.DataFrame()
    return pd.read_parquet(path)


def _load_dispersion() -> pd.DataFrame:
    path = DATA_DIR / "analyst_dispersion.parquet"
    if not path.exists():
        logger.warning("analyst_dispersion.parquet not found at %s", path)
        return pd.DataFrame()
    return pd.read_parquet(path)


def _compute_cagr(start_val: float, end_val: float, years: int) -> float:
    """Compute CAGR as a percentage."""
    if start_val <= 0 or years <= 0:
        return 0.0
    return ((end_val / start_val) ** (1.0 / years) - 1) * 100


def _cagr_insight(segment: str, ensemble: pd.DataFrame) -> dict | None:
    """Generate CAGR growth projection insight."""
    q4 = ensemble[(ensemble["segment"] == segment) & (ensemble["quarter"] == 4)]
    if q4.empty:
        return None

    fc = q4[q4["is_forecast"]]
    if fc.empty:
        return None

    start_year = int(fc["year"].min())
    end_year = int(fc["year"].max())
    start_row = fc[fc["year"] == start_year]
    end_row = fc[fc["year"] == end_year]

    if start_row.empty or end_row.empty:
        return None

    # Use the last historical Q4 value as CAGR start
    hist = q4[~q4["is_forecast"]].sort_values("year")
    if hist.empty:
        return None
    last_hist_year = int(hist["year"].max())
    last_hist_val = float(hist[hist["year"] == last_hist_year]["point_estimate_nominal"].iloc[0])

    end_val = float(end_row["point_estimate_nominal"].iloc[0])
    n_years = end_year - last_hist_year

    if n_years <= 0:
        return None

    cagr = _compute_cagr(last_hist_val, end_val, n_years)
    display_seg = segment.replace("_", " ").replace("ai ", "AI ")

    text = (
        f"{display_seg} is projected to grow at {_fmt_pct(cagr)} CAGR "
        f"({last_hist_year}\u2013{end_year}), reaching {_fmt_usd(end_val)} by {end_year}."
    )
    return {"type": "cagr_insight", "text": text, "priority": 1}


def _dispersion_insight(segment: str, dispersion: pd.DataFrame) -> dict | None:
    """Generate analyst dispersion convergence/divergence insight."""
    seg_disp = dispersion[
        (dispersion["segment"] == segment) & (dispersion["n_sources"] > 1)
    ].sort_values("year")

    if len(seg_disp) < 2:
        return None

    # Compare latest two data points with meaningful dispersion
    latest = seg_disp.iloc[-1]
    prior = seg_disp.iloc[-2]

    latest_iqr = float(latest["iqr_usd_billions"])
    prior_iqr = float(prior["iqr_usd_billions"])
    latest_year = int(latest["year"])
    n_years = latest_year - int(seg_disp.iloc[0]["year"])

    if prior_iqr == 0:
        return None

    display_seg = segment.replace("_", " ").replace("ai ", "AI ")

    if latest_iqr < prior_iqr:
        direction = "converging"
        signal = "higher"
        verb = "narrowed"
    else:
        direction = "diverging"
        signal = "lower"
        verb = "widened"

    text = (
        f"Analyst consensus for {display_seg} is {direction} \u2014 "
        f"IQR {verb} from {_fmt_usd(prior_iqr)} to {_fmt_usd(latest_iqr)} "
        f"over {n_years} years, signaling {signal} forecast confidence."
    )
    return {"type": "dispersion_insight", "text": text, "priority": 2}


def _scenario_spread_insight(segment: str, scenarios: pd.DataFrame) -> dict | None:
    """Generate scenario spread (conservative vs aggressive) insight."""
    seg_sc = scenarios[
        (scenarios["segment"] == segment)
        & (scenarios["quarter"] == 4)
    ]
    if seg_sc.empty:
        return None

    max_year = int(seg_sc["year"].max())
    final = seg_sc[seg_sc["year"] == max_year]

    conservative = final[final["scenario"] == "conservative"]
    aggressive = final[final["scenario"] == "aggressive"]

    if conservative.empty or aggressive.empty:
        return None

    cons_val = float(conservative["point_estimate_nominal"].iloc[0])
    agg_val = float(aggressive["point_estimate_nominal"].iloc[0])

    if cons_val <= 0:
        return None

    delta_pct = ((agg_val - cons_val) / cons_val) * 100

    if delta_pct > 100:
        uncertainty = "high"
    elif delta_pct > 50:
        uncertainty = "moderate"
    else:
        uncertainty = "low"

    display_seg = segment.replace("_", " ").replace("ai ", "AI ")

    text = (
        f"Scenario spread for {display_seg}: Conservative {_fmt_usd(cons_val)} "
        f"vs. Aggressive {_fmt_usd(agg_val)} by {max_year} "
        f"({_fmt_pct(delta_pct)} delta), reflecting {uncertainty} uncertainty "
        f"in growth assumptions."
    )
    return {"type": "scenario_spread", "text": text, "priority": 3}


def _top_growth_insight(segment: str, ensemble: pd.DataFrame) -> dict | None:
    """Compare this segment's CAGR against all others."""
    cagrs: dict[str, float] = {}
    for seg in SEGMENTS:
        q4 = ensemble[(ensemble["segment"] == seg) & (ensemble["quarter"] == 4)]
        hist = q4[~q4["is_forecast"]].sort_values("year")
        fc = q4[q4["is_forecast"]].sort_values("year")
        if hist.empty or fc.empty:
            continue
        start_val = float(hist.iloc[-1]["point_estimate_nominal"])
        end_val = float(fc.iloc[-1]["point_estimate_nominal"])
        end_year = int(fc.iloc[-1]["year"])
        start_year = int(hist.iloc[-1]["year"])
        n = end_year - start_year
        if n > 0 and start_val > 0:
            cagrs[seg] = _compute_cagr(start_val, end_val, n)

    if segment not in cagrs or len(cagrs) < 2:
        return None

    ranked = sorted(cagrs.items(), key=lambda x: x[1], reverse=True)
    rank = [s for s, _ in ranked].index(segment)

    display_seg = segment.replace("_", " ").replace("ai ", "AI ")

    if rank == 0:
        # This segment leads
        runner_up_cagr = ranked[1][1]
        gap = cagrs[segment] - runner_up_cagr
        runner_up_name = ranked[1][0].replace("_", " ").replace("ai ", "AI ")
        text = (
            f"{display_seg} leads all segments with {_fmt_pct(cagrs[segment])} projected CAGR, "
            f"{_fmt_pct(gap)} above the next fastest segment ({runner_up_name})."
        )
        return {"type": "top_growth", "text": text, "priority": 2}
    else:
        leader_name = ranked[0][0].replace("_", " ").replace("ai ", "AI ")
        gap = ranked[0][1] - cagrs[segment]
        text = (
            f"{display_seg} ranks #{rank + 1} across segments with "
            f"{_fmt_pct(cagrs[segment])} projected CAGR, "
            f"{_fmt_pct(gap)} behind the leader ({leader_name} at {_fmt_pct(ranked[0][1])})."
        )
        return {"type": "top_growth", "text": text, "priority": 4}


def _yoy_momentum_insight(segment: str, ensemble: pd.DataFrame) -> dict | None:
    """Calculate YoY growth rate trend from the latest historical years."""
    q4 = ensemble[
        (ensemble["segment"] == segment)
        & (ensemble["quarter"] == 4)
        & (~ensemble["is_forecast"])
    ].sort_values("year")

    if len(q4) < 3:
        return None

    # Take the last 3 historical years to compute 2 YoY rates
    recent = q4.tail(3)
    vals = recent["point_estimate_nominal"].tolist()
    years = recent["year"].tolist()

    if vals[0] <= 0 or vals[1] <= 0:
        return None

    yoy_prev = ((vals[1] - vals[0]) / vals[0]) * 100
    yoy_latest = ((vals[2] - vals[1]) / vals[1]) * 100

    display_seg = segment.replace("_", " ").replace("ai ", "AI ")

    if yoy_latest > yoy_prev:
        direction = "accelerating"
        verb = "increased"
    else:
        direction = "decelerating"
        verb = "decreased"

    text = (
        f"{display_seg} momentum {direction}: "
        f"YoY growth {verb} from {_fmt_pct(yoy_prev)} to {_fmt_pct(yoy_latest)} "
        f"in {int(years[2])}."
    )
    return {"type": "yoy_momentum", "text": text, "priority": 3}


def generate_segment_insights(segment: str) -> list[dict]:
    """
    Generate 3-5 rule-based narrative insights for a given AI segment.

    Parameters
    ----------
    segment : str
        One of: ai_hardware, ai_infrastructure, ai_software, ai_adoption

    Returns
    -------
    list[dict]
        Each dict has keys: type (str), text (str), priority (int, 1=highest).
        Sorted by priority ascending.
    """
    ensemble = _load_ensemble()
    scenarios = _load_scenarios()
    dispersion = _load_dispersion()

    generators = [
        lambda: _cagr_insight(segment, ensemble),
        lambda: _dispersion_insight(segment, dispersion),
        lambda: _scenario_spread_insight(segment, scenarios),
        lambda: _top_growth_insight(segment, ensemble),
        lambda: _yoy_momentum_insight(segment, ensemble),
    ]

    insights: list[dict] = []
    for gen in generators:
        try:
            result = gen()
            if result is not None:
                insights.append(result)
        except Exception:
            logger.warning("Insight generator failed for %s", segment, exc_info=True)

    # Sort by priority (1=highest) and cap at 5
    insights.sort(key=lambda x: x["priority"])
    return insights[:5]
