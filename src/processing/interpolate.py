"""
Missing value interpolation with transparency flagging.

Every interpolated value is flagged with estimated_flag=True.
This is NON-NEGOTIABLE — unflagged interpolation creates invisible data
that undermines the credibility of the entire analysis.

Strategy (from CONTEXT.md):
- Linear interpolation for dense series (<=2 consecutive gaps)
- Cubic spline for sparse series (>2 consecutive gaps)
- All interpolated values flagged as estimated
"""
import pandas as pd
import numpy as np


def interpolate_series(
    series: pd.Series,
    max_linear_gap: int = 2,
) -> tuple[pd.Series, pd.Series]:
    """
    Interpolate missing values in a time series.

    Uses linear interpolation for small gaps (<=max_linear_gap consecutive NaNs)
    and index-based interpolation for larger gaps.

    Parameters
    ----------
    series : pd.Series
        Time series with potential NaN gaps. Index should be numeric (years).
    max_linear_gap : int
        Maximum consecutive NaN count for linear interpolation.
        Larger gaps use index-based interpolation.

    Returns
    -------
    tuple of (filled_series, estimated_flags)
        filled_series: Series with NaN gaps filled
        estimated_flags: Boolean Series — True where value was interpolated
    """
    original_nulls = series.isna()

    # Count consecutive NaN runs
    max_consecutive_nan = _max_consecutive_nans(series)

    if max_consecutive_nan <= max_linear_gap:
        filled = series.interpolate(method="linear")
    else:
        # Use index-based interpolation for irregularly spaced years
        filled = series.interpolate(method="index")

    # Build estimated flag: True where original was NaN and is now filled
    estimated_flags = original_nulls & filled.notna()

    return filled, estimated_flags


def _max_consecutive_nans(series: pd.Series) -> int:
    """Count the longest run of consecutive NaN values."""
    is_nan = series.isna()
    if not is_nan.any():
        return 0
    groups = (is_nan != is_nan.shift()).cumsum()
    nan_groups = groups[is_nan]
    if nan_groups.empty:
        return 0
    return nan_groups.value_counts().max()


def apply_interpolation(
    df: pd.DataFrame,
    value_columns: list[str] | None = None,
    max_linear_gap: int = 2,
) -> pd.DataFrame:
    """
    Apply interpolation to specified columns and add estimated_flag.

    If estimated_flag column already exists, it is OR-ed with new flags
    (a row flagged by a prior step stays flagged).

    Parameters
    ----------
    df : pd.DataFrame
        Must have a 'year' column or numeric index.
    value_columns : list[str] or None
        Columns to interpolate. If None, interpolates all float columns.
    max_linear_gap : int
        Passed to interpolate_series.

    Returns
    -------
    pd.DataFrame
        With NaN gaps filled and estimated_flag column added/updated.
    """
    result = df.copy()

    if value_columns is None:
        value_columns = [c for c in df.columns if df[c].dtype in ("float64", "float32")]

    # Initialize estimated_flag if not present
    if "estimated_flag" not in result.columns:
        result["estimated_flag"] = False

    for col in value_columns:
        if col not in result.columns:
            continue
        filled, flags = interpolate_series(result[col], max_linear_gap=max_linear_gap)
        result[col] = filled
        # OR with existing flags — once flagged, always flagged
        result["estimated_flag"] = result["estimated_flag"] | flags

    return result
