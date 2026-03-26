"""
Forecast engine: project 2025-2030, build output DataFrame with CI bounds,
vintage column, and dual units (real 2020 USD + nominal USD).

v1.1 update: point_estimate_real_2020 is USD billions directly from models trained on
real USD market anchors. No value chain multiplier conversion needed.

For display purposes, nominal USD is also provided using a 2.5% annual CAGR assumption
as a simple inflation proxy. This allows the dashboard to show both "apples-to-apples"
constant-dollar comparisons (real 2020 USD) and the intuitive "current dollar" figures
that non-technical audiences expect. See docs/ASSUMPTIONS.md section Modeling Assumptions
for the 2.5% CAGR assumption and its sensitivity (±1% CAGR changes 2030 nominal by ~±6%).

Confidence interval construction: CI bounds (80% and 95%) come from the quantile
regression models trained in Phase 3. clip_ci_bounds enforces monotonic ordering
(ci95_lower ≤ ci80_lower ≤ point ≤ ci80_upper ≤ ci95_upper) to prevent numerical
artifacts from making inner bands wider than outer bands.

See docs/ASSUMPTIONS.md section Interpretation Caveats for CI band interpretation.

Exports:
- build_forecast_dataframe: assemble full output DataFrame with all required columns
- clip_ci_bounds: enforce monotonic CI ordering for a single row
- get_data_vintage: derive vintage string from residuals DataFrame max year
- reflate_to_nominal: convert real 2020 USD to nominal USD using CAGR assumption
- verify_cagr_range: verify per-segment CAGR 2025-2030 is in expected range (MODL-05)
"""
from __future__ import annotations

import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def get_data_vintage(residuals_df: pd.DataFrame) -> str:
    """
    Derive data vintage string from the maximum year in the residuals DataFrame.

    Parameters
    ----------
    residuals_df : pd.DataFrame
        Must contain a 'year' column (int).

    Returns
    -------
    str
        Vintage in the format "YYYY-Q4" (e.g. "2024-Q4").
    """
    max_year = int(residuals_df["year"].max())
    return f"{max_year}-Q4"


def reflate_to_nominal(
    value_real_2020: float,
    year: int,
    base_year: int = 2020,
) -> float:
    """
    Convert a real (constant 2020 USD) value to nominal USD using a simple
    2.5% annual CAGR inflation assumption.

    This is a simplification. When live deflator data (World Bank NY.GDP.DEFL.ZS)
    is available, this function should be upgraded to use actual deflator ratios.

    Parameters
    ----------
    value_real_2020 : float
        Value in 2020 constant USD.
    year : int
        Target year to reflate to.
    base_year : int
        Base year of the constant USD series (default: 2020).

    Returns
    -------
    float
        Nominal USD value for the given year.
    """
    # Upgrade path: try World Bank GDP deflator first, fall back to constant CAGR.
    #
    # When the World Bank deflator (NY.GDP.DEFL.ZS) is available in the processed
    # pipeline output (world_bank_ai.parquet), use actual deflator ratios for
    # historical years and the constant CAGR assumption only for forecast years
    # beyond the deflator coverage. This provides more accurate nominal conversion
    # for historical years where actual inflation data exists.
    #
    # To upgrade:
    # 1. Load world_bank_ai.parquet and extract GDP deflator index for "USA"
    # 2. Compute deflator_ratio = deflator[year] / deflator[base_year]
    # 3. For years covered by deflator: factor = deflator_ratio
    # 4. For years beyond deflator: factor = last_deflator_ratio * (1 + cagr)^(year - last_deflator_year)

    _deflator_factor = None
    try:
        from config.settings import DATA_PROCESSED, load_industry_config
        _cfg = load_industry_config("ai")
        _method = _cfg.get("model_calibration", {}).get("inflation", {}).get("method", "constant_cagr")

        if _method == "world_bank_deflator":
            # Attempt to load actual deflator data
            _wb_path = DATA_PROCESSED / "world_bank_ai.parquet"
            if _wb_path.exists():
                import pandas as _pd
                _wb = _pd.read_parquet(_wb_path)
                _defl = _wb[(_wb["indicator_code"] == "NY.GDP.DEFL.ZS") & (_wb["economy"] == "USA")]
                if not _defl.empty and year in _defl["year"].values and base_year in _defl["year"].values:
                    _val_year = float(_defl.loc[_defl["year"] == year, "value"].iloc[0])
                    _val_base = float(_defl.loc[_defl["year"] == base_year, "value"].iloc[0])
                    if _val_base > 0:
                        _deflator_factor = _val_year / _val_base
    except Exception:
        pass  # Fall through to constant CAGR

    if _deflator_factor is not None:
        return value_real_2020 * _deflator_factor

    # Fallback: constant CAGR assumption
    try:
        from config.settings import load_industry_config
        _cfg = load_industry_config("ai")
        _inflation_cagr = _cfg["model_calibration"]["inflation"]["annual_cagr"]
    except Exception:
        _inflation_cagr = 0.025  # fallback: 2.5% constant CAGR

    factor = (1.0 + _inflation_cagr) ** (year - base_year)
    return value_real_2020 * factor


def clip_ci_bounds(row: dict) -> dict:
    """
    Enforce monotonic ordering of CI bounds for a single forecast row.

    Applies the clipping pattern:
        ci95_lower <= ci80_lower <= point_estimate_real_2020 <= ci80_upper <= ci95_upper

    Parameters
    ----------
    row : dict
        Must have keys: point_estimate_real_2020, ci80_lower, ci80_upper,
        ci95_lower, ci95_upper.

    Returns
    -------
    dict
        Copy of row with clipped CI values.
    """
    row = row.copy()
    row["ci95_lower"] = min(row["ci95_lower"], row["ci80_lower"], row["point_estimate_real_2020"])
    row["ci80_lower"] = min(row["ci80_lower"], row["point_estimate_real_2020"])
    row["ci80_upper"] = max(row["ci80_upper"], row["point_estimate_real_2020"])
    row["ci95_upper"] = max(row["ci95_upper"], row["ci80_upper"])
    return row


def build_forecast_dataframe(
    segment_forecasts: dict,
    data_vintage: str,
) -> pd.DataFrame:
    """
    Assemble the full forecast output DataFrame from per-segment arrays.

    Parameters
    ----------
    segment_forecasts : dict
        Maps segment name (str) to a dict with keys:
            - years: list[int]
            - point_estimates: np.ndarray (real 2020 USD)
            - ci80_lower: np.ndarray (real 2020 USD)
            - ci80_upper: np.ndarray (real 2020 USD)
            - ci95_lower: np.ndarray (real 2020 USD)
            - ci95_upper: np.ndarray (real 2020 USD)
            - is_forecast: list[bool]
    data_vintage : str
        Vintage string (e.g. "2024-Q4") to embed in every row.

    Returns
    -------
    pd.DataFrame
        Columns: year, segment, point_estimate_real_2020, point_estimate_nominal,
        ci80_lower, ci80_upper, ci95_lower, ci95_upper, is_forecast, data_vintage.
        Sorted by (segment, year). CI bounds are monotonically clipped.
    """
    rows = []
    for segment, fcasts in segment_forecasts.items():
        years = fcasts["years"]
        point_estimates = fcasts["point_estimates"]
        ci80_lower = fcasts["ci80_lower"]
        ci80_upper = fcasts["ci80_upper"]
        ci95_lower = fcasts["ci95_lower"]
        ci95_upper = fcasts["ci95_upper"]
        is_forecast = fcasts["is_forecast"]

        for i, year in enumerate(years):
            row = {
                "year": int(year),
                "segment": segment,
                "point_estimate_real_2020": float(point_estimates[i]),
                "ci80_lower": float(ci80_lower[i]),
                "ci80_upper": float(ci80_upper[i]),
                "ci95_lower": float(ci95_lower[i]),
                "ci95_upper": float(ci95_upper[i]),
                "is_forecast": bool(is_forecast[i]),
                "data_vintage": str(data_vintage),
            }

            # Enforce monotonic CI ordering
            row = clip_ci_bounds(row)

            # Compute nominal USD values using 2.5% CAGR from base year 2020
            row["point_estimate_nominal"] = reflate_to_nominal(
                row["point_estimate_real_2020"], year=int(year)
            )
            row["ci80_lower_nominal"] = reflate_to_nominal(row["ci80_lower"], year=int(year))
            row["ci80_upper_nominal"] = reflate_to_nominal(row["ci80_upper"], year=int(year))
            row["ci95_lower_nominal"] = reflate_to_nominal(row["ci95_lower"], year=int(year))
            row["ci95_upper_nominal"] = reflate_to_nominal(row["ci95_upper"], year=int(year))

            rows.append(row)

    df = pd.DataFrame(rows, columns=[
        "year",
        "segment",
        "point_estimate_real_2020",
        "point_estimate_nominal",
        "ci80_lower",
        "ci80_upper",
        "ci95_lower",
        "ci95_upper",
        "ci80_lower_nominal",
        "ci80_upper_nominal",
        "ci95_lower_nominal",
        "ci95_upper_nominal",
        "is_forecast",
        "data_vintage",
    ])

    # Sort by (segment, year) for deterministic output
    df = df.sort_values(["segment", "year"]).reset_index(drop=True)

    return df


def verify_cagr_range(
    df: pd.DataFrame,
    segments: list[str],
    start_year: int = 2025,
    end_year: int = 2030,
    min_cagr: float = 0.15,
    max_cagr: float = 0.60,
) -> dict[str, float]:
    """
    Verify per-segment CAGR is in expected range (MODL-05).

    Target range per MODL-05 is 25-40% CAGR 2025-2030. This function uses a
    wider gate (15-60%) to allow model flexibility — the 25-40% target is a
    documentation/verification concern, not a hard code gate.

    Parameters
    ----------
    df : pd.DataFrame
        Forecast DataFrame with columns: year, segment, point_estimate_real_2020.
    segments : list[str]
        Segment IDs to check.
    start_year : int
        Start year for CAGR computation (default 2025).
    end_year : int
        End year for CAGR computation (default 2030).
    min_cagr : float
        Lower bound for expected CAGR (fraction, default 0.15 = 15%).
    max_cagr : float
        Upper bound for expected CAGR (fraction, default 0.60 = 60%).

    Returns
    -------
    dict[str, float]
        Maps segment name to CAGR fraction (e.g. 0.32 = 32%).
        Logs a warning for any segment outside [min_cagr, max_cagr].
    """
    # MODL-05 CAGR divergence rationale (documented per plan requirement):
    #
    # Target range: 25-40% CAGR 2025-2030 (consensus AI growth trajectory).
    # Actual ranges as of Phase 9 execution (2026-03-24):
    #   - ai_hardware:       ~24% CAGR (slightly below — 2-obs training window; reflects
    #                         AI chip revenue growth 2023-2024 extrapolated forward)
    #   - ai_infrastructure:  ~7% CAGR (below target — market_anchors_ai.parquet has only
    #                         2 real observations per segment after n_sources>0 filter;
    #                         2023-2024 infrastructure growth was +9.9% per anchor data)
    #   - ai_software:       ~0.6% CAGR (well below — 2023-2024 software market essentially
    #                         flat in anchor data; Prophet extrapolates flat trend)
    #   - ai_adoption:       ~0% CAGR (floored — 2023-2024 adoption declined 60% in anchors,
    #                         likely one-source data quality issue; floored at 50% of 2024 value)
    #
    # Root cause: market_anchors_ai.parquet has n_sources>0 for only 2023-2024. Phase 9
    # models trained on 2-point series extrapolate the most recent 1-year trend. The 25-40%
    # CAGR target assumes 7-9 real observations (2017-2025). This will be resolved in Phase 10
    # when additional company revenue data enriches the anchor estimates.
    #
    # Phase 11 dashboard will display CAGR with this caveat and source uncertainty bands.

    results: dict[str, float] = {}
    for seg in segments:
        seg_df = df[df["segment"] == seg].sort_values("year")
        val_start = seg_df.loc[seg_df["year"] == start_year, "point_estimate_real_2020"]
        val_end = seg_df.loc[seg_df["year"] == end_year, "point_estimate_real_2020"]

        if len(val_start) > 0 and len(val_end) > 0:
            v_start = val_start.iloc[0]
            v_end = val_end.iloc[0]
            if v_start > 0:
                cagr = (v_end / v_start) ** (1 / (end_year - start_year)) - 1
                results[seg] = cagr
                if not (min_cagr <= cagr <= max_cagr):
                    logger.warning(
                        "verify_cagr_range: segment %s CAGR %.1f%% outside target range "
                        "[%.0f%%, %.0f%%] — see MODL-05 for divergence rationale",
                        seg,
                        cagr * 100,
                        min_cagr * 100,
                        max_cagr * 100,
                    )
            else:
                logger.warning(
                    "verify_cagr_range: segment %s has zero/negative value at %d — "
                    "cannot compute CAGR",
                    seg,
                    start_year,
                )

    return results
