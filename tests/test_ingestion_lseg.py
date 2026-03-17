"""Tests for LSEG Workspace connector (DATA-05)."""
import json
import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from config.settings import load_industry_config

FIXTURES = Path(__file__).parent / "fixtures"


class TestLSEGIngestion:
    """Unit tests — mock lseg.data to avoid requiring Workspace."""

    @pytest.fixture
    def ai_config(self):
        return load_industry_config("ai")

    @pytest.fixture
    def lseg_sample_df(self):
        return pd.read_json(FIXTURES / "lseg_sample.json")

    @patch("src.ingestion.lseg.ld")
    def test_fetch_companies_builds_screening_from_config(self, mock_ld, ai_config, lseg_sample_df):
        mock_ld.get_data.return_value = lseg_sample_df
        from src.ingestion.lseg import fetch_lseg_companies
        result = fetch_lseg_companies(ai_config)
        # Verify screening expression was built from config TRBC codes
        call_args = mock_ld.get_data.call_args
        universe_arg = call_args[1].get("universe", call_args[0][0] if call_args[0] else "")
        assert "57201010" in str(universe_arg)  # From config
        assert len(result) > 0

    @patch("src.ingestion.lseg.ld")
    def test_fetch_companies_returns_validated_df(self, mock_ld, ai_config, lseg_sample_df):
        mock_ld.get_data.return_value = lseg_sample_df
        from src.ingestion.lseg import fetch_lseg_companies
        result = fetch_lseg_companies(ai_config)
        assert "Instrument" in result.columns

    @patch("src.ingestion.lseg.ld")
    def test_fetch_financials_uses_config_fields(self, mock_ld, ai_config, lseg_sample_df):
        mock_ld.get_data.return_value = lseg_sample_df
        from src.ingestion.lseg import fetch_company_financials
        companies = lseg_sample_df[["Instrument"]].copy()
        result = fetch_company_financials(companies, ai_config)
        assert len(result) > 0

    @patch("src.ingestion.lseg.ld")
    def test_save_raw_lseg_creates_parquet(self, mock_ld, lseg_sample_df, tmp_path):
        from src.ingestion.lseg import save_raw_lseg
        import config.settings as settings
        original_raw = settings.DATA_RAW
        settings.DATA_RAW = tmp_path
        try:
            path = save_raw_lseg(lseg_sample_df, "ai")
            assert path.exists()
            assert path.suffix == ".parquet"
        finally:
            settings.DATA_RAW = original_raw

    def test_trbc_codes_from_config_not_hardcoded(self, ai_config):
        """TRBC codes come from config, not hardcoded in lseg.py."""
        import inspect
        from src.ingestion import lseg as lseg_module
        source = inspect.getsource(lseg_module.fetch_lseg_companies)
        # The function should NOT contain literal TRBC codes
        assert "57201010" not in source, "TRBC codes should come from config, not be hardcoded"


@pytest.mark.integration
class TestLSEGIntegration:
    """Integration tests — require LSEG Workspace running."""

    def test_lseg_session_opens(self):
        from src.ingestion.lseg import open_lseg_session, close_lseg_session
        open_lseg_session()
        close_lseg_session()

    def test_full_lseg_fetch(self):
        from src.ingestion.lseg import (
            open_lseg_session,
            close_lseg_session,
            fetch_lseg_companies,
        )
        config = load_industry_config("ai")
        open_lseg_session()
        try:
            df = fetch_lseg_companies(config)
            assert len(df) > 0, "LSEG company universe should not be empty"
            assert "Instrument" in df.columns
        finally:
            close_lseg_session()
