"""
Prophet per-segment fitting with explicit 2022 changepoint, forecasting, residuals,
temporal CV, and residual Parquet output for Phase 3 ML training.

Provides:
- fit_prophet_segment: Fit Prophet with configurable GenAI changepoint year
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
"""

import logging

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
        Override with a detected structural break year from _run_break_detection()
        in scripts/run_statistical_pipeline.py.

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
    in_sample = model.predict(model.history)
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
        Override with a detected structural break year from _run_break_detection()
        in scripts/run_statistical_pipeline.py. Must match the changepoint_year
        passed to fit_prophet_segment to ensure consistent CV and final-fit changepoints.

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
