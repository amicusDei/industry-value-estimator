"""
Tests for data ingestion connectors.

Uses mocked API calls to test the connector logic without live network access.
Tests are organized by connector class.

Run unit tests only (no live API):
    uv run pytest tests/test_ingestion.py -v -m "not integration"
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pandas as pd
import pytest


# ============================================================
# World Bank ingestion tests
# ============================================================

class TestWorldBankIngestion:
    """Tests for src/ingestion/world_bank.py — mocked wbgapi calls."""

    @pytest.fixture
    def ai_config(self):
        """Load the real AI industry config."""
        from config.settings import load_industry_config
        return load_industry_config("ai")

    @pytest.fixture
    def wb_sample_df(self):
        """Wide-format sample matching what fetch_world_bank_indicators returns."""
        fixture_path = Path(__file__).parent / "fixtures" / "world_bank_sample.json"
        data = json.loads(fixture_path.read_text())
        return pd.DataFrame(data)

    def test_returns_dataframe_with_required_columns(self, ai_config, wb_sample_df):
        """Test 1: fetch_world_bank_indicators returns DataFrame with economy, year, and indicator columns."""
        with patch("wbgapi.data.DataFrame") as mock_wb:
            # wbgapi returns a MultiIndex DataFrame: index=(economy, series), cols=YR2020, YR2021...
            # Build a mock that mimics wbgapi output shape
            mock_raw = _make_wbgapi_mock_df(wb_sample_df)
            mock_wb.return_value = mock_raw

            from src.ingestion.world_bank import fetch_world_bank_indicators
            result = fetch_world_bank_indicators(ai_config)

        assert isinstance(result, pd.DataFrame)
        assert "economy" in result.columns
        assert "year" in result.columns
        # At least one indicator column beyond economy/year
        assert len(result.columns) > 2

    def test_deflator_always_included(self, ai_config, wb_sample_df):
        """Test 2: GDP deflator NY.GDP.DEFL.ZS is ALWAYS fetched even if already in config."""
        indicators_called = []

        def mock_wb_call(series, economy, time, labels):
            indicators_called.extend(series if isinstance(series, list) else [series])
            return _make_wbgapi_mock_df(wb_sample_df)

        with patch("wbgapi.data.DataFrame", side_effect=mock_wb_call):
            from src.ingestion.world_bank import fetch_world_bank_indicators
            # Reload to clear cache
            import importlib
            import src.ingestion.world_bank as wb_mod
            importlib.reload(wb_mod)
            result = wb_mod.fetch_world_bank_indicators(ai_config)

        assert "NY.GDP.DEFL.ZS" in indicators_called

    def test_deflator_added_when_missing_from_config(self):
        """Test 2b: Deflator is appended even if not in the config indicators list."""
        # Config with deflator NOT in world_bank.indicators
        mock_config = {
            "world_bank": {
                "indicators": [
                    {"code": "NY.GDP.MKTP.CD", "name": "gdp_current_usd"},
                ]
            },
            "regions": [{"economy_codes": ["USA"]}],
            "date_range": {"start": "2020", "end": "2021"},
        }
        # The fixture df has deflator column — reuse it
        sample_df = pd.DataFrame([
            {"economy": "USA", "year": 2020, "NY.GDP.MKTP.CD": 21000000.0, "NY.GDP.DEFL.ZS": 112.0},
        ])

        indicators_called = []

        def mock_wb_call(series, economy, time, labels):
            indicators_called.extend(series)
            return _make_wbgapi_mock_df(sample_df)

        with patch("wbgapi.data.DataFrame", side_effect=mock_wb_call):
            import importlib
            import src.ingestion.world_bank as wb_mod
            importlib.reload(wb_mod)
            wb_mod.fetch_world_bank_indicators(mock_config)

        assert "NY.GDP.DEFL.ZS" in indicators_called

    def test_returned_dataframe_passes_schema_validation(self, ai_config, wb_sample_df):
        """Test 3: Returned DataFrame passes WORLD_BANK_RAW_SCHEMA validation."""
        with patch("wbgapi.data.DataFrame") as mock_wb:
            mock_wb.return_value = _make_wbgapi_mock_df(wb_sample_df)

            import importlib
            import src.ingestion.world_bank as wb_mod
            importlib.reload(wb_mod)
            result = wb_mod.fetch_world_bank_indicators(ai_config)

        # Should not raise — schema validation happens inside the function
        from src.processing.validate import validate_raw_world_bank
        validated = validate_raw_world_bank(result)
        assert isinstance(validated, pd.DataFrame)

    def test_save_writes_parquet_to_correct_path(self, wb_sample_df, tmp_path):
        """Test 4: save_raw_world_bank writes a Parquet file to data/raw/world_bank/."""
        from src.ingestion.world_bank import save_raw_world_bank
        import src.ingestion.world_bank as wb_mod

        # Patch DATA_RAW to point at temp dir
        with patch.object(wb_mod, "DATA_RAW", tmp_path):
            output_path = save_raw_world_bank(wb_sample_df, industry_id="ai")

        assert output_path.exists()
        assert output_path.suffix == ".parquet"
        assert "world_bank" in str(output_path)
        # Can be read back
        df_read = pd.read_parquet(output_path)
        assert len(df_read) == len(wb_sample_df)

    def test_uses_indicator_codes_from_config(self, ai_config):
        """Test 5: fetch function uses indicator codes from ai.yaml config, not hardcoded."""
        indicators_requested = []

        expected_codes = {ind["code"] for ind in ai_config["world_bank"]["indicators"]}
        # deflator may already be in config — but at minimum config codes must be fetched
        sample_df = pd.DataFrame([
            {"economy": "USA", "year": 2020, "NY.GDP.MKTP.CD": 21e12, "NY.GDP.DEFL.ZS": 112.0},
        ])

        def mock_wb_call(series, economy, time, labels):
            indicators_requested.extend(series)
            return _make_wbgapi_mock_df(sample_df)

        with patch("wbgapi.data.DataFrame", side_effect=mock_wb_call):
            import importlib
            import src.ingestion.world_bank as wb_mod
            importlib.reload(wb_mod)
            wb_mod.fetch_world_bank_indicators(ai_config)

        fetched_set = set(indicators_requested)
        # All config indicator codes must be in the fetch call
        for code in expected_codes:
            assert code in fetched_set, f"Expected indicator {code} to be fetched"


# ============================================================
# OECD ingestion tests
# ============================================================

class TestOECDIngestion:
    """Tests for src/ingestion/oecd.py — mocked pandasdmx calls."""

    @pytest.fixture
    def ai_config(self):
        from config.settings import load_industry_config
        return load_industry_config("ai")

    @pytest.fixture
    def oecd_sample_df(self):
        """OECD fixture data as DataFrame."""
        fixture_path = Path(__file__).parent / "fixtures" / "oecd_sample.json"
        data = json.loads(fixture_path.read_text())
        return pd.DataFrame(data)

    def _make_sdmx_mock(self, df):
        """Create a pandasdmx mock that returns a DataFrame via sdmx.to_pandas."""
        mock_request = MagicMock()
        mock_data_msg = MagicMock()
        mock_request.return_value = mock_data_msg
        mock_data_msg.data = [MagicMock()]
        return mock_request, mock_data_msg, df

    def test_fetch_oecd_msti_returns_required_columns(self, ai_config, oecd_sample_df):
        """Test 1: fetch_oecd_msti returns DataFrame with LOCATION, TIME_PERIOD, value columns."""
        with patch("pandasdmx.Request") as mock_req_cls, \
             patch("pandasdmx.to_pandas") as mock_to_pandas, \
             patch("requests_cache.install_cache"):

            mock_req = MagicMock()
            mock_req_cls.return_value = mock_req
            mock_data_msg = MagicMock()
            mock_req.data.return_value = mock_data_msg
            mock_data_msg.data = [MagicMock()]
            mock_to_pandas.return_value = oecd_sample_df.set_index(
                pd.MultiIndex.from_frame(oecd_sample_df[["LOCATION", "TIME_PERIOD", "INDICATOR"]])
            )

            import importlib
            import src.ingestion.oecd as oecd_mod
            importlib.reload(oecd_mod)
            result = oecd_mod.fetch_oecd_msti(ai_config)

        assert isinstance(result, pd.DataFrame)
        assert "LOCATION" in result.columns
        assert "TIME_PERIOD" in result.columns

    def test_fetch_oecd_ai_patents_filters_to_g06n(self, ai_config, oecd_sample_df):
        """Test 2: fetch_oecd_ai_patents uses IPC class G06N from config."""
        ipc_filters_used = []

        def mock_data_call(dataset, key, params):
            if "IPC" in key:
                ipc_filters_used.append(key["IPC"])
            mock_msg = MagicMock()
            mock_msg.data = [MagicMock()]
            return mock_msg

        with patch("pandasdmx.Request") as mock_req_cls, \
             patch("pandasdmx.to_pandas") as mock_to_pandas, \
             patch("requests_cache.install_cache"):

            mock_req = MagicMock()
            mock_req_cls.return_value = mock_req
            mock_req.data.side_effect = mock_data_call
            mock_to_pandas.return_value = oecd_sample_df.set_index(
                pd.MultiIndex.from_frame(oecd_sample_df[["LOCATION", "TIME_PERIOD", "INDICATOR"]])
            )

            import importlib
            import src.ingestion.oecd as oecd_mod
            importlib.reload(oecd_mod)
            result = oecd_mod.fetch_oecd_ai_patents(ai_config)

        # G06N should appear as the IPC filter
        assert any("G06N" in f for f in ipc_filters_used)

    def test_returned_dataframes_pass_oecd_schema(self, ai_config, oecd_sample_df):
        """Test 3: Returned DataFrames pass OECD_RAW_SCHEMA validation."""
        with patch("pandasdmx.Request") as mock_req_cls, \
             patch("pandasdmx.to_pandas") as mock_to_pandas, \
             patch("requests_cache.install_cache"):

            mock_req = MagicMock()
            mock_req_cls.return_value = mock_req
            mock_data_msg = MagicMock()
            mock_req.data.return_value = mock_data_msg
            mock_data_msg.data = [MagicMock()]
            mock_to_pandas.return_value = oecd_sample_df.set_index(
                pd.MultiIndex.from_frame(oecd_sample_df[["LOCATION", "TIME_PERIOD", "INDICATOR"]])
            )

            import importlib
            import src.ingestion.oecd as oecd_mod
            importlib.reload(oecd_mod)
            result = oecd_mod.fetch_oecd_msti(ai_config)

        from src.processing.validate import validate_raw_oecd
        validated = validate_raw_oecd(result)
        assert isinstance(validated, pd.DataFrame)

    def test_save_raw_oecd_writes_parquet(self, oecd_sample_df, tmp_path):
        """Test 4: save_raw_oecd writes Parquet to data/raw/oecd/."""
        import importlib
        import src.ingestion.oecd as oecd_mod
        importlib.reload(oecd_mod)

        with patch.object(oecd_mod, "DATA_RAW", tmp_path):
            output_path = oecd_mod.save_raw_oecd(oecd_sample_df, "msti", "ai")

        assert output_path.exists()
        assert output_path.suffix == ".parquet"
        assert "oecd" in str(output_path)
        df_read = pd.read_parquet(output_path)
        assert len(df_read) == len(oecd_sample_df)

    def test_requests_cache_configured_for_oecd(self, ai_config, oecd_sample_df):
        """Test 6: requests-cache is configured with 30-day TTL for OECD calls."""
        cache_calls = []

        def mock_install_cache(*args, **kwargs):
            cache_calls.append(kwargs)

        with patch("pandasdmx.Request") as mock_req_cls, \
             patch("pandasdmx.to_pandas") as mock_to_pandas, \
             patch("requests_cache.install_cache", side_effect=mock_install_cache):

            mock_req = MagicMock()
            mock_req_cls.return_value = mock_req
            mock_data_msg = MagicMock()
            mock_req.data.return_value = mock_data_msg
            mock_data_msg.data = [MagicMock()]
            mock_to_pandas.return_value = oecd_sample_df.set_index(
                pd.MultiIndex.from_frame(oecd_sample_df[["LOCATION", "TIME_PERIOD", "INDICATOR"]])
            )

            import importlib
            import src.ingestion.oecd as oecd_mod
            importlib.reload(oecd_mod)
            oecd_mod.fetch_oecd_msti(ai_config)

        assert len(cache_calls) > 0
        # 30-day TTL = 30 * 24 * 3600 = 2592000 seconds
        assert any(c.get("expire_after") == 30 * 24 * 3600 for c in cache_calls)


# ============================================================
# Pipeline orchestrator tests
# ============================================================

class TestIngestionPipeline:
    """Tests for src/ingestion/pipeline.py — mocked connector calls."""

    @pytest.fixture
    def mock_wb_path(self, tmp_path):
        p = tmp_path / "world_bank_ai_20260101.parquet"
        p.touch()
        return p

    @pytest.fixture
    def mock_oecd_msti_path(self, tmp_path):
        p = tmp_path / "oecd_msti_ai_20260101.parquet"
        p.touch()
        return p

    @pytest.fixture
    def mock_oecd_patents_path(self, tmp_path):
        p = tmp_path / "oecd_pats_ipc_ai_20260101.parquet"
        p.touch()
        return p

    def test_run_ingestion_reads_config_and_calls_connectors(
        self, mock_wb_path, mock_oecd_msti_path, mock_oecd_patents_path, tmp_path
    ):
        """Test 5: run_ingestion reads config and calls both World Bank and OECD connectors."""
        sample_wb_df = pd.DataFrame([{"economy": "USA", "year": 2020, "NY.GDP.DEFL.ZS": 112.0}])
        sample_oecd_df = pd.DataFrame([{"LOCATION": "USA", "TIME_PERIOD": "2020", "value": 100.0}])

        with patch("src.ingestion.pipeline.fetch_world_bank_indicators", return_value=sample_wb_df) as mock_wb, \
             patch("src.ingestion.pipeline.save_raw_world_bank", return_value=mock_wb_path) as mock_wb_save, \
             patch("src.ingestion.pipeline.fetch_oecd_msti", return_value=sample_oecd_df) as mock_msti, \
             patch("src.ingestion.pipeline.save_raw_oecd", return_value=mock_oecd_msti_path) as mock_oecd_save, \
             patch("src.ingestion.pipeline.fetch_oecd_ai_patents", return_value=sample_oecd_df) as mock_patents:

            import importlib
            import src.ingestion.pipeline as pipeline_mod
            importlib.reload(pipeline_mod)
            results = pipeline_mod.run_ingestion("ai")

        # Both connectors must be called
        mock_wb.assert_called_once()
        mock_msti.assert_called_once()
        mock_patents.assert_called_once()

    def test_run_ingestion_returns_dict_of_paths(
        self, mock_wb_path, mock_oecd_msti_path, mock_oecd_patents_path
    ):
        """Test 5b: run_ingestion returns a dict mapping step names to paths."""
        sample_wb_df = pd.DataFrame([{"economy": "USA", "year": 2020, "NY.GDP.DEFL.ZS": 112.0}])
        sample_oecd_df = pd.DataFrame([{"LOCATION": "USA", "TIME_PERIOD": "2020", "value": 100.0}])

        with patch("src.ingestion.pipeline.fetch_world_bank_indicators", return_value=sample_wb_df), \
             patch("src.ingestion.pipeline.save_raw_world_bank", return_value=mock_wb_path), \
             patch("src.ingestion.pipeline.fetch_oecd_msti", return_value=sample_oecd_df), \
             patch("src.ingestion.pipeline.save_raw_oecd", return_value=mock_oecd_msti_path), \
             patch("src.ingestion.pipeline.fetch_oecd_ai_patents", return_value=sample_oecd_df):

            import importlib
            import src.ingestion.pipeline as pipeline_mod
            importlib.reload(pipeline_mod)
            results = pipeline_mod.run_ingestion("ai")

        assert isinstance(results, dict)
        assert len(results) > 0
        # Values should be Path-like objects
        for key, val in results.items():
            assert isinstance(val, Path), f"Expected Path, got {type(val)} for key {key}"

    def test_run_ingestion_uses_load_industry_config(self):
        """Test that pipeline reads config via load_industry_config, not hardcoded values."""
        sample_wb_df = pd.DataFrame([{"economy": "USA", "year": 2020, "NY.GDP.DEFL.ZS": 112.0}])
        sample_oecd_df = pd.DataFrame([{"LOCATION": "USA", "TIME_PERIOD": "2020", "value": 100.0}])
        dummy_path = Path("/tmp/dummy.parquet")

        config_loaded = []

        def mock_load_config(industry_id):
            from config.settings import load_industry_config
            cfg = load_industry_config(industry_id)
            config_loaded.append(industry_id)
            return cfg

        with patch("src.ingestion.pipeline.load_industry_config", side_effect=mock_load_config), \
             patch("src.ingestion.pipeline.fetch_world_bank_indicators", return_value=sample_wb_df), \
             patch("src.ingestion.pipeline.save_raw_world_bank", return_value=dummy_path), \
             patch("src.ingestion.pipeline.fetch_oecd_msti", return_value=sample_oecd_df), \
             patch("src.ingestion.pipeline.save_raw_oecd", return_value=dummy_path), \
             patch("src.ingestion.pipeline.fetch_oecd_ai_patents", return_value=sample_oecd_df):

            import importlib
            import src.ingestion.pipeline as pipeline_mod
            importlib.reload(pipeline_mod)
            pipeline_mod.run_ingestion("ai")

        assert "ai" in config_loaded


# ============================================================
# Helper: Build a wbgapi-shaped mock DataFrame
# ============================================================

def _make_wbgapi_mock_df(wide_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert a wide test DataFrame (economy, year, <indicators>...) into the shape
    that wbgapi.data.DataFrame returns:
        MultiIndex (economy, series), columns = YR2020, YR2021, ...

    This allows our reshape logic in fetch_world_bank_indicators to work correctly
    in tests without live API calls.
    """
    indicator_cols = [c for c in wide_df.columns if c not in ("economy", "year")]

    rows = []
    for _, row in wide_df.iterrows():
        for ind in indicator_cols:
            rows.append({
                "economy": row["economy"],
                "series": ind,
                f"YR{int(row['year'])}": row[ind],
            })

    if not rows:
        return pd.DataFrame()

    long_df = pd.DataFrame(rows)

    # Aggregate by (economy, series) — pivot years as columns
    year_cols = [c for c in long_df.columns if c.startswith("YR")]
    pivot = long_df.groupby(["economy", "series"])[year_cols].first()

    # Return with MultiIndex (economy, series) — same as wbgapi output
    return pivot
