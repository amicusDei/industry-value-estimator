"""
Forecast engine: project 2025-2030, build output DataFrame with CI bounds,
vintage column, and dual units (real 2020 USD + nominal USD).

Exports:
- build_forecast_dataframe: assemble full output DataFrame with all required columns
- clip_ci_bounds: enforce monotonic CI ordering for a single row
- get_data_vintage: derive vintage string from residuals DataFrame max year
- reflate_to_nominal: convert real 2020 USD to nominal USD using CAGR assumption
"""
from __future__ import annotations

import pandas as pd
import numpy as np


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
    factor = (1.025) ** (year - base_year)
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

            # Compute nominal USD value using 2.5% CAGR from base year 2020
            row["point_estimate_nominal"] = reflate_to_nominal(
                row["point_estimate_real_2020"], year=int(year)
            )

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
        "is_forecast",
        "data_vintage",
    ])

    # Sort by (segment, year) for deterministic output
    df = df.sort_values(["segment", "year"]).reset_index(drop=True)

    return df
