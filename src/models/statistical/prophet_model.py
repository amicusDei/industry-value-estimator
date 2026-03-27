"""
Prophet per-segment fitting with explicit 2022 changepoint, forecasting, residuals,
temporal CV, and residual Parquet output for Phase 3 ML training.

Provides:
- prepare_prophet_from_anchors: Prepare market_anchors_ai.parquet data in Prophet ds/y format
- fit_prophet_from_anchors: Fit Prophet on USD anchor series with 2022 changepoint (v1.1)
- fit_prophet_segment: Fit Prophet with configurable GenAI changepoint year (v1.0 — preserved)
- forecast_prophet: Future dataframe + prediction
- get_prophet_residuals: Year-indexed in-sample residuals
- run_prophet_cv: Manual expanding-window CV (not Prophet's built-in — see Open Question 3)
- save_all_residuals: Write segment residuals to Parquet with validated schema

Design notes:
- changepoints=[f"{changepoint_year}-01-01"] gives Prophet an explicit GenAI surge anchor
  (RESEARCH.md Pitfall 2 and Pattern 3); default changepoint_year=2022 for backward
  compatibility, overridable via detected structural break year from Phase 6 wiring
- changepoint_prior_scale=0.1 allows post-break trend flexibility
- yearly/weekly/daily seasonality disabled — annual data has no within-year seasonality
- Prophet CV uses manual TimeSeriesSplit refits, not Prophet's cross_validation —
  keeps CV methodology consistent with ARIMA (RESEARCH.md Open Question 3)
- Residuals are year-indexed (int) not datetime-indexed — prevents Phase 3 join errors
  (RESEARCH.md Pitfall 5)
- Parquet schema: year (int), segment (str), residual (float), model_type (str)
- v1.1 entry points (prepare_prophet_from_anchors, fit_prophet_from_anchors) load Y from
  market_anchors_ai.parquet using ALL data (real + interpolated) and use
  median_usd_billions_real_2020. With only 2-3 real observations per segment, models
  require the full 9-year series including interpolated values to produce stable fits.
  Interpolated values are derived from analyst consensus estimates.
"""

import logging
import warnings

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from prophet import Prophet
from sklearn.model_selection import TimeSeriesSplit

from src.diagnostics.model_eval import compute_rmse, compute_mape

# Suppress verbose cmdstanpy / prophet output
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)

# Column names for USD billions variables in market_anchors_ai.parquet
_MEDIAN_COL = "median_usd_billions_real_2020"


def prepare_prophet_from_anchors(segment: str) -> pd.DataFrame:
    """Prepare market anchors data in Prophet ds/y format for a segment.

    Uses ALL data (real + interpolated) for sufficient training points. With only
    2-3 real observations per segment, models require the full 9-year series
    including interpolated values to produce stable fits. Interpolated values are
    derived from analyst consensus estimates and provide reasonable signal.

    Parameters
    ----------
    segment : str
        Segment name, e.g. "ai_hardware", "ai_software".

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: ds (datetime YYYY-01-01), y (USD billions).
        Sorted by ds, indexed by RangeIndex. Includes both real and interpolated rows.

    Warns
    -----
    UserWarning
        If fewer than 5 observations are available.
    """
    from config.settings import DATA_PROCESSED
    anchors = pd.read_parquet(DATA_PROCESSED / "market_anchors_ai.parquet")
    # Use ALL data (real + interpolated) for sufficient training points.
    seg = (
        anchors[anchors["segment"] == segment]
        .sort_values("estimate_year")
        [["estimate_year", _MEDIAN_COL]]
        .rename(columns={"estimate_year": "ds", _MEDIAN_COL: "y"})
        .reset_index(drop=True)
    )
    seg["ds"] = pd.to_datetime(seg["ds"].astype(str) + "-01-01")
    if len(seg) < 5:
        warnings.warn(
            f"prepare_prophet_from_anchors: segment '{segment}' has only {len(seg)} "
            f"observations. Forecasts may be unreliable.",
            UserWarning,
            stacklevel=2,
        )
    return seg


def fit_prophet_from_anchors(segment: str, changepoint_year: int = 2022) -> Prophet:
    """Fit Prophet on USD market anchor series for a segment.

    v1.1 entry point — uses market_anchors_ai.parquet as the training Y variable
    (median_usd_billions_real_2020) instead of the legacy long-format processed DataFrame.

    Uses a single explicit changepoint at changepoint_year to capture the GenAI
    structural break in the AI market growth trajectory. If the changepoint_year falls
    outside the training data range (e.g. very few real observations), the changepoint
    is omitted and Prophet uses its default automatic changepoint detection.

    Parameters
    ----------
    segment : str
        Segment name, e.g. "ai_hardware", "ai_software".
    changepoint_year : int, optional
        Year for explicit Prophet changepoint. Default 2022 (GenAI surge).
        Override with a detected structural break year if needed.

    Returns
    -------
    Prophet
        Fitted Prophet model. Use forecast_prophet() to generate predictions.
    """
    seg_df_clean = prepare_prophet_from_anchors(segment)

    # Observation weighting via duplication: since Prophet does not support
    # sample_weight in its .fit() method, we duplicate real observations
    # (n_sources > 0) 3x in the training DataFrame while keeping interpolated
    # observations (n_sources == 0) at 1x. This effectively gives real data
    # 3x weight during model fitting.
    from config.settings import DATA_PROCESSED as _DP
    _anchors_raw = pd.read_parquet(_DP / "market_anchors_ai.parquet")
    _seg_anchors = _anchors_raw[_anchors_raw["segment"] == segment].sort_values("estimate_year")
    _n_sources_map = dict(zip(_seg_anchors["estimate_year"], _seg_anchors.get("n_sources", [0]*len(_seg_anchors))))
    dupe_rows = []
    for _, row in seg_df_clean.iterrows():
        year_val = row["ds"].year
        ns = _n_sources_map.get(year_val, 0)
        n_copies = 3 if ns > 0 else 1
        for _ in range(n_copies):
            dupe_rows.append({"ds": row["ds"], "y": row["y"]})
    seg_df = pd.DataFrame(dupe_rows).reset_index(drop=True)

    # Only include explicit changepoint if it falls within the training period
    min_year = seg_df["ds"].dt.year.min() if len(seg_df) > 0 else changepoint_year + 1
    max_year = seg_df["ds"].dt.year.max() if len(seg_df) > 0 else changepoint_year - 1
    if min_year <= changepoint_year <= max_year:
        changepoints = [f"{changepoint_year}-01-01"]
    else:
        changepoints = []
        if len(seg_df) > 0:
            import warnings as _warnings
            _warnings.warn(
                f"fit_prophet_from_anchors: changepoint_year={changepoint_year} is outside "
                f"training range [{min_year}, {max_year}] for segment '{segment}'. "
                "Using default Prophet changepoints.",
                UserWarning,
                stacklevel=2,
            )
    model = Prophet(
        changepoints=changepoints,
        changepoint_prior_scale=0.1,
        yearly_seasonality=False,
        weekly_seasonality=False,
        daily_seasonality=False,
    )
    model.fit(seg_df)
    return model


def fit_prophet_segment(
    df: pd.DataFrame,
    segment: str,
    changepoint_year: int = 2022,
) -> Prophet:
    """
    Fit Prophet on a single AI segment with a configurable changepoint year.

    Data preparation:
    - Filters df to rows where industry_segment == segment
    - Aggregates value_real_2020 by year (sum across economies)
    - Renames year -> ds, value_real_2020 -> y
    - Converts ds to datetime (YYYY-01-01)

    Model configuration:
    - changepoints=[f"{changepoint_year}-01-01"]: explicit GenAI surge anchor
    - changepoint_prior_scale=0.1: above default to allow post-break flex
    - yearly_seasonality=False: annual data — no within-year seasonality
    - weekly_seasonality=False, daily_seasonality=False

    Parameters
    ----------
    df : pd.DataFrame
        Long-format DataFrame with columns: year, value_real_2020, industry_segment.
    segment : str
        AI segment name (e.g. "ai_software", "ai_hardware").
    changepoint_year : int, optional
        Year to use as explicit Prophet changepoint. Default 2022 (GenAI surge).

    Returns
    -------
    Prophet
        Fitted Prophet model.
    """
    seg = (
        df[df["industry_segment"] == segment]
        .groupby("year")["value_real_2020"]
        .sum()
        .reset_index()
        .rename(columns={"year": "ds", "value_real_2020": "y"})
    )
    seg["ds"] = pd.to_datetime(seg["ds"].astype(str) + "-01-01")

    model = Prophet(
        changepoints=[f"{changepoint_year}-01-01"],  # configurable GenAI surge anchor
        changepoint_prior_scale=0.1,                 # above default 0.05 for post-break flex
        yearly_seasonality=False,                    # annual data — no intra-year seasonality
        weekly_seasonality=False,
        daily_seasonality=False,
    )
    model.fit(seg)
    return model


def forecast_prophet(model: Prophet, periods: int) -> pd.DataFrame:
    """
    Generate a forecast DataFrame extending `periods` years beyond training data.

    Parameters
    ----------
    model : Prophet
        Fitted Prophet model from fit_prophet_segment().
    periods : int
        Number of future periods (years) to forecast.

    Returns
    -------
    pd.DataFrame
        Prophet forecast DataFrame with columns including "ds", "yhat",
        "yhat_lower", "yhat_upper". Rows = history + future periods.
    """
    future = model.make_future_dataframe(periods=periods, freq="YS")
    return model.predict(future)


def get_prophet_residuals(model: Prophet, df_segment: pd.DataFrame) -> pd.Series:
    """
    Extract in-sample residuals from a fitted Prophet model, indexed by year (int).

    df_segment must already be in ds/y format (the segment-specific prepared DataFrame).
    Residuals are indexed by integer year (from ds.dt.year) to match the year column
    used in the residuals Parquet schema and to prevent Phase 3 join misalignment.

    Parameters
    ----------
    model : Prophet
        Fitted Prophet model.
    df_segment : pd.DataFrame
        Prepared segment DataFrame with columns "ds" (datetime) and "y" (float).
        Must be the same data the model was trained on.

    Returns
    -------
    pd.Series
        Residuals indexed by integer year. name="residual".
    """
    # Predict on the clean (non-duplicated) segment data rather than
    # model.history which may contain duplicated rows from observation weighting.
    in_sample = model.predict(df_segment)
    residuals = df_segment["y"].values - in_sample["yhat"].values
    year_index = df_segment["ds"].dt.year.values
    return pd.Series(residuals, index=year_index, name="residual")


def run_prophet_cv(
    df: pd.DataFrame,
    segment: str,
    n_splits: int = 3,
    changepoint_year: int = 2022,
) -> list[dict]:
    """
    Expanding-window temporal cross-validation for Prophet.

    Uses manual TimeSeriesSplit refits (not Prophet's built-in cross_validation)
    to keep CV methodology consistent with ARIMA. For each fold:
    1. Prepare the full segment series in ds/y format
    2. Split into train/test using TimeSeriesSplit
    3. Refit Prophet on training portion
    4. Predict on test portion using forecast_prophet
    5. Compute RMSE and MAPE

    Parameters
    ----------
    df : pd.DataFrame
        Long-format DataFrame with columns: year, value_real_2020, industry_segment.
    segment : str
        AI segment name.
    n_splits : int
        Number of expanding-window CV folds. Default 3.
    changepoint_year : int, optional
        Year to use as explicit Prophet changepoint in each CV fold. Default 2022.
        Must match the changepoint_year passed to fit_prophet_segment to ensure
        consistent CV and final-fit changepoints.

    Returns
    -------
    list[dict]
        One dict per fold with keys: fold, train_end, test_end, rmse, mape.
    """
    # Prepare full segment series in ds/y format
    seg_df = (
        df[df["industry_segment"] == segment]
        .groupby("year")["value_real_2020"]
        .sum()
        .reset_index()
        .rename(columns={"year": "ds", "value_real_2020": "y"})
        .sort_values("ds")
        .reset_index(drop=True)
    )
    seg_df["ds"] = pd.to_datetime(seg_df["ds"].astype(str) + "-01-01")

    tscv = TimeSeriesSplit(n_splits=n_splits)
    results = []

    for i, (train_idx, test_idx) in enumerate(tscv.split(seg_df)):
        train_df = seg_df.iloc[train_idx].copy()
        test_df = seg_df.iloc[test_idx].copy()

        # Only fit if the configured changepoint year falls within the training period or before it
        # If not, use generic changepoints from the training data span
        train_years = train_df["ds"].dt.year
        if changepoint_year in train_years.values:
            changepoints = [f"{changepoint_year}-01-01"]
        else:
            changepoints = []

        fold_model = Prophet(
            changepoints=changepoints,
            changepoint_prior_scale=0.1,
            yearly_seasonality=False,
            weekly_seasonality=False,
            daily_seasonality=False,
        )
        fold_model.fit(train_df)

        # Forecast for exactly the test horizon
        steps = len(test_idx)
        future = fold_model.make_future_dataframe(periods=steps, freq="YS")
        forecast = fold_model.predict(future)
        # Extract only the out-of-sample portion (last `steps` rows)
        predicted = forecast["yhat"].values[-steps:]
        actual = test_df["y"].values

        rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
        # MAPE: guard against zero actual values
        if np.any(actual == 0):
            mape = float("nan")
        else:
            mape = float(np.mean(np.abs((actual - predicted) / actual)) * 100)

        results.append({
            "fold": i,
            "train_end": int(train_idx[-1]),
            "test_end": int(test_idx[-1]),
            "rmse": rmse,
            "mape": mape,
        })

    return results


def save_all_residuals(
    segment_residuals: dict[str, tuple[pd.Series, str]],
    output_path: str,
) -> None:
    """
    Concatenate per-segment residuals and write to Parquet with validated schema.

    Schema: year (int), segment (str), residual (float), model_type (str)
    Compression: snappy via pyarrow.

    Validates:
    - No NaN values in the year column
    - All segments present in the output

    Parameters
    ----------
    segment_residuals : dict[str, tuple[pd.Series, str]]
        Maps segment_name -> (residual_series, model_type_string).
        residual_series must be indexed by integer year.
    output_path : str
        Full path (including filename) for the output Parquet file.

    Raises
    ------
    ValueError
        If the year column contains NaN values or if any segment is missing.
    """
    frames = []
    for seg_name, (resid_series, model_type) in segment_residuals.items():
        frame = resid_series.rename("residual").to_frame()
        frame.index.name = "year"
        frame = frame.reset_index()
        frame["segment"] = seg_name
        frame["model_type"] = model_type
        frames.append(frame)

    combined = pd.concat(frames, ignore_index=True)

    # Enforce schema types
    combined["year"] = combined["year"].astype(int)
    combined["residual"] = combined["residual"].astype(float)
    combined["segment"] = combined["segment"].astype(str)
    combined["model_type"] = combined["model_type"].astype(str)

    # Column order
    combined = combined[["year", "segment", "residual", "model_type"]]

    # Validate: no NaN in year column
    if combined["year"].isna().any():
        raise ValueError("save_all_residuals: year column contains NaN values.")

    # Validate: all segments present
    expected_segments = set(segment_residuals.keys())
    actual_segments = set(combined["segment"].unique())
    missing = expected_segments - actual_segments
    if missing:
        raise ValueError(f"save_all_residuals: missing segments in output: {missing}")

    pq.write_table(
        pa.Table.from_pandas(combined, preserve_index=False),
        output_path,
        compression="snappy",
    )
