"""
Tests for ARIMA and Prophet models, residual schema, and model comparison.
Covers MODL-01 (model fitting) and MODL-06 (temporal CV).
"""

import logging
import warnings

import numpy as np
import pandas as pd
import pytest

# Suppress cmdstanpy logging for Prophet tests
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------

def _trending_series(n: int = 25, seed: int = 42) -> pd.Series:
    """Trending series with noise — mimics AI segment aggregate annual data."""
    rng = np.random.default_rng(seed)
    return pd.Series(
        np.cumsum(rng.standard_normal(n)) + np.arange(n) * 0.5 + 100.0,
        index=pd.RangeIndex(start=2000, stop=2000 + n),
        name="value_real_2020",
    )


def _prophet_dataframe(n_years: int = 15, start_year: int = 2010, seed: int = 42) -> pd.DataFrame:
    """
    Synthetic annual DataFrame in PROCESSED_SCHEMA-like format for Prophet tests.
    Mimics 15 years of AI segment data with a level shift at 2022.
    """
    rng = np.random.default_rng(seed)
    years = list(range(start_year, start_year + n_years))
    values = np.cumsum(rng.standard_normal(n_years)) + np.arange(n_years) * 0.8 + 50.0
    # Level shift at 2022
    shift_idx = 2022 - start_year
    if shift_idx < n_years:
        values[shift_idx:] += 10.0

    return pd.DataFrame({
        "year": years,
        "value_real_2020": values,
        "industry_segment": "ai_software",
    })


# ---------------------------------------------------------------------------
# Task 1: TestARIMA
# ---------------------------------------------------------------------------

class TestARIMA:
    """Tests for src/models/statistical/arima.py"""

    def test_select_arima_order(self):
        """select_arima_order returns (p, d, q) with each element <= 2."""
        from src.models.statistical.arima import select_arima_order

        series = _trending_series(n=30)
        order = select_arima_order(series)

        assert isinstance(order, tuple)
        assert len(order) == 3
        p, d, q = order
        assert 0 <= p <= 2, f"p={p} exceeds max_p=2"
        assert 0 <= d <= 2, f"d={d} exceeds 2"
        assert 0 <= q <= 2, f"q={q} exceeds max_q=2"

    def test_arima_fits(self):
        """fit_arima_segment returns object with .resid attribute close to 20 in length."""
        from src.models.statistical.arima import fit_arima_segment

        series = _trending_series(n=20)
        result = fit_arima_segment(series, order=(1, 1, 0))

        assert hasattr(result, "resid"), "fitted result must have .resid attribute"
        # Residual length should be close to series length (may differ by 1 due to differencing)
        assert abs(len(result.resid) - 20) <= 2

    def test_forecast_arima(self):
        """forecast_arima returns DataFrame with 'mean' column and 5 rows."""
        from src.models.statistical.arima import fit_arima_segment, forecast_arima

        series = _trending_series(n=20)
        result = fit_arima_segment(series, order=(1, 1, 0))
        forecast = forecast_arima(result, steps=5)

        assert isinstance(forecast, pd.DataFrame)
        assert len(forecast) == 5
        mean_col = [c for c in forecast.columns if "mean" in str(c).lower()]
        assert len(mean_col) >= 1, f"Expected 'mean' column, got: {list(forecast.columns)}"

    def test_arima_residuals_indexed(self):
        """get_arima_residuals returns pd.Series with same index as original (year-aligned)."""
        from src.models.statistical.arima import fit_arima_segment, get_arima_residuals

        series = _trending_series(n=20)
        result = fit_arima_segment(series, order=(1, 1, 0))
        residuals = get_arima_residuals(result, original_index=series.index)

        assert isinstance(residuals, pd.Series)
        # Index must be year-aligned (values from series.index), not positional (0,1,2...)
        # The first element should match series.index[0], not 0
        assert residuals.index[0] == series.index[0], (
            f"Residuals not year-aligned: got {residuals.index[0]}, "
            f"expected {series.index[0]}"
        )
        # Length close to original
        assert len(residuals) <= len(series)

    def test_arima_cv(self):
        """run_arima_cv returns list of 3 dicts each with 'rmse' and 'mape' keys."""
        from src.models.statistical.arima import run_arima_cv

        series = _trending_series(n=25)
        results = run_arima_cv(series, order=(1, 1, 0), n_splits=3)

        assert isinstance(results, list)
        assert len(results) == 3
        for fold in results:
            assert "rmse" in fold, f"Missing 'rmse' key in fold: {fold}"
            assert "mape" in fold, f"Missing 'mape' key in fold: {fold}"


# ---------------------------------------------------------------------------
# Task 2: TestProphet
# ---------------------------------------------------------------------------

class TestProphet:
    """Tests for src/models/statistical/prophet_model.py"""

    def test_prophet_fits(self):
        """fit_prophet_segment returns a Prophet model object."""
        from prophet import Prophet
        from src.models.statistical.prophet_model import fit_prophet_segment

        df = _prophet_dataframe(n_years=15, start_year=2010)
        model = fit_prophet_segment(df, segment="ai_software")

        assert isinstance(model, Prophet), f"Expected Prophet, got {type(model)}"

    def test_prophet_forecast(self):
        """forecast_prophet returns DataFrame with 'yhat' column and 5 rows."""
        from src.models.statistical.prophet_model import fit_prophet_segment, forecast_prophet

        df = _prophet_dataframe(n_years=15, start_year=2010)
        model = fit_prophet_segment(df, segment="ai_software")
        forecast = forecast_prophet(model, periods=5)

        assert isinstance(forecast, pd.DataFrame)
        assert "yhat" in forecast.columns, f"Expected 'yhat' column, got: {list(forecast.columns)}"
        # forecast returns history + future; future portion is last `periods` rows
        assert len(forecast) >= 5

    def test_prophet_residuals(self):
        """get_prophet_residuals returns pd.Series indexed by year integers (not datetime)."""
        from src.models.statistical.prophet_model import fit_prophet_segment, get_prophet_residuals

        df = _prophet_dataframe(n_years=15, start_year=2010)
        # Prepare segment DataFrame in ds/y format as the function expects
        seg = (
            df[df["industry_segment"] == "ai_software"]
            .groupby("year")["value_real_2020"]
            .sum()
            .reset_index()
            .rename(columns={"year": "ds", "value_real_2020": "y"})
        )
        seg["ds"] = pd.to_datetime(seg["ds"].astype(str) + "-01-01")

        model = fit_prophet_segment(df, segment="ai_software")
        residuals = get_prophet_residuals(model, seg)

        assert isinstance(residuals, pd.Series)
        # Index should be integer years, not datetime
        assert residuals.index.dtype in (np.int64, np.int32, int, "int64", "int32"), (
            f"Expected integer year index, got dtype={residuals.index.dtype}"
        )
        # First year should be 2010, not 0 or some offset
        assert residuals.index[0] == 2010, (
            f"Expected first year=2010, got {residuals.index[0]}"
        )

    def test_prophet_cv(self):
        """run_prophet_cv returns list of 3 dicts each with 'rmse' key."""
        from src.models.statistical.prophet_model import run_prophet_cv

        df = _prophet_dataframe(n_years=15, start_year=2010)
        results = run_prophet_cv(df, segment="ai_software", n_splits=3)

        assert isinstance(results, list)
        assert len(results) == 3
        for fold in results:
            assert "rmse" in fold, f"Missing 'rmse' key in fold: {fold}"


# ---------------------------------------------------------------------------
# Task 2: TestResiduals
# ---------------------------------------------------------------------------

class TestResiduals:
    """Tests for save_all_residuals — Parquet output schema and year alignment."""

    def _make_residual_series(self, segment: str, start_year: int = 2010, n: int = 15) -> pd.Series:
        """Helper: create a residual series indexed by year integers."""
        rng = np.random.default_rng(0)
        years = list(range(start_year, start_year + n))
        return pd.Series(
            rng.standard_normal(n),
            index=pd.Index(years, name="year"),
            name="residual",
        )

    def test_residuals_schema(self, tmp_path):
        """save_all_residuals produces Parquet with columns [year, segment, residual, model_type]."""
        from src.models.statistical.prophet_model import save_all_residuals
        import pyarrow.parquet as pq

        output_path = str(tmp_path / "residuals_test.parquet")
        segment_residuals = {
            "ai_software": (self._make_residual_series("ai_software"), "Prophet"),
            "ai_hardware": (self._make_residual_series("ai_hardware"), "ARIMA"),
        }

        save_all_residuals(segment_residuals, output_path)

        table = pq.read_table(output_path)
        df = table.to_pandas()

        required_cols = {"year", "segment", "residual", "model_type"}
        assert required_cols.issubset(set(df.columns)), (
            f"Missing columns: {required_cols - set(df.columns)}"
        )
        assert df["year"].dtype in (np.int64, np.int32, "int64", "int32"), (
            f"year column must be integer, got {df['year'].dtype}"
        )
        assert df["residual"].dtype in (np.float64, np.float32, "float64", "float32"), (
            f"residual column must be float, got {df['residual'].dtype}"
        )
        assert df["segment"].dtype == object or str(df["segment"].dtype) == "string", (
            f"segment column must be string/object, got {df['segment'].dtype}"
        )

    def test_residuals_year_alignment(self, tmp_path):
        """Saved residuals year column starts at the first year of the input series."""
        from src.models.statistical.prophet_model import save_all_residuals
        import pyarrow.parquet as pq

        output_path = str(tmp_path / "residuals_align.parquet")
        start_year = 2010
        seg_series = self._make_residual_series("ai_software", start_year=start_year)
        segment_residuals = {
            "ai_software": (seg_series, "ARIMA"),
        }

        save_all_residuals(segment_residuals, output_path)

        df = pq.read_table(output_path).to_pandas()
        sw_df = df[df["segment"] == "ai_software"]
        assert sw_df["year"].min() == start_year, (
            f"Expected first year={start_year}, got {sw_df['year'].min()}"
        )
