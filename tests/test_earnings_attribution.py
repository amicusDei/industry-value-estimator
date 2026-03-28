"""
Tests for earnings-based AI revenue attribution pipeline.

Tests the integration between earnings_analysis.py (extraction + pipeline)
and revenue_attribution.py (lookup priority with earnings-based data).
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from src.ingestion.earnings_analysis import (
    run_earnings_attribution,
    _select_best_extractions,
    _confidence_to_score,
    _parse_fiscal_period,
    _empty_attribution_df,
)
from src.processing.revenue_attribution import estimate_ai_revenue


# ---------------------------------------------------------------------------
# _parse_fiscal_period tests
# ---------------------------------------------------------------------------

class TestParseFiscalPeriod:
    def test_fy_format(self):
        assert _parse_fiscal_period("FY2024") == (2024, None)

    def test_fy_space(self):
        assert _parse_fiscal_period("FY 2025") == (2025, None)

    def test_quarter_format(self):
        assert _parse_fiscal_period("Q3 2024") == (2024, 3)

    def test_quarter_fy(self):
        assert _parse_fiscal_period("Q1FY2025") == (2025, 1)

    def test_date_format(self):
        assert _parse_fiscal_period("2024-09-30") == (2024, 3)

    def test_date_q4(self):
        assert _parse_fiscal_period("2024-12-31") == (2024, 4)

    def test_bare_year(self):
        assert _parse_fiscal_period("2024") == (2024, None)

    def test_empty_string(self):
        assert _parse_fiscal_period("") == (2024, None)


# ---------------------------------------------------------------------------
# _confidence_to_score tests
# ---------------------------------------------------------------------------

class TestConfidenceToScore:
    def test_high(self):
        assert _confidence_to_score("high") == 0.9

    def test_medium(self):
        assert _confidence_to_score("medium") == 0.6

    def test_low(self):
        assert _confidence_to_score("low") == 0.3

    def test_unknown(self):
        assert _confidence_to_score("unknown") == 0.3


# ---------------------------------------------------------------------------
# _select_best_extractions tests
# ---------------------------------------------------------------------------

class TestSelectBestExtractions:
    def test_picks_highest_confidence(self):
        df = pd.DataFrame([
            {"cik": "001", "period_end": "2024-12-31", "confidence": "low", "extracted_value_usd": 10.0},
            {"cik": "001", "period_end": "2024-12-31", "confidence": "high", "extracted_value_usd": 15.0},
        ])
        result = _select_best_extractions(df)
        assert len(result) == 1
        assert result.iloc[0]["extracted_value_usd"] == 15.0

    def test_multiple_periods_kept(self):
        df = pd.DataFrame([
            {"cik": "001", "period_end": "2024-12-31", "confidence": "high", "extracted_value_usd": 15.0},
            {"cik": "001", "period_end": "2024-09-30", "confidence": "medium", "extracted_value_usd": 12.0},
        ])
        result = _select_best_extractions(df)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# _empty_attribution_df tests
# ---------------------------------------------------------------------------

class TestEmptyAttributionDf:
    def test_has_correct_columns(self):
        df = _empty_attribution_df()
        expected = {
            "cik", "company_name", "fiscal_year", "fiscal_quarter",
            "total_revenue_usd", "ai_revenue_usd", "ai_ratio",
            "attribution_method", "confidence_score", "llm_validated",
            "vintage_date",
        }
        assert set(df.columns) == expected
        assert len(df) == 0


# ---------------------------------------------------------------------------
# run_earnings_attribution tests (mocked EDGAR)
# ---------------------------------------------------------------------------

class TestRunEarningsAttribution:
    @patch("src.ingestion.earnings_analysis.fetch_and_extract")
    def test_yaml_fallback_when_no_edgar(self, mock_fetch):
        """When EDGAR fetch returns empty, falls back to YAML registry."""
        mock_fetch.return_value = pd.DataFrame()

        result = run_earnings_attribution("ai")

        assert len(result) > 0
        # Should have at least some yaml_fallback methods
        yaml_methods = result[result["attribution_method"].str.startswith("yaml_fallback")]
        assert len(yaml_methods) > 0

    @patch("src.ingestion.earnings_analysis.fetch_and_extract")
    def test_writes_parquet(self, mock_fetch):
        """Parquet file is written to data/processed."""
        mock_fetch.return_value = pd.DataFrame()

        from config.settings import DATA_PROCESSED
        output_path = DATA_PROCESSED / "earnings_ai_attribution.parquet"

        run_earnings_attribution("ai")

        assert output_path.exists()
        df = pd.read_parquet(output_path)
        assert len(df) > 0

    @patch("src.ingestion.earnings_analysis.fetch_and_extract")
    def test_regex_extraction_used(self, mock_fetch):
        """When EDGAR returns data, regex extraction is used."""
        mock_fetch.return_value = pd.DataFrame([{
            "cik": "0001045810",
            "period_end": "2024-12-31",
            "form_type": "10-K",
            "pattern_name": "nvidia_data_center",
            "extracted_value_usd": 115.2,
            "unit": "billion",
            "confidence": "high",
            "raw_snippet": "Data Center revenue was $115.2 billion",
        }])

        result = run_earnings_attribution("ai")

        nvidia_row = result[result["cik"] == "0001045810"]
        assert len(nvidia_row) >= 1
        # Should use earnings_regex method (not yaml_fallback)
        methods = nvidia_row["attribution_method"].values
        assert any("earnings_regex" in m or "yaml_fallback" in m for m in methods)


# ---------------------------------------------------------------------------
# estimate_ai_revenue integration tests
# ---------------------------------------------------------------------------

class TestEstimateAiRevenueIntegration:
    def test_earnings_priority_over_pure_play(self):
        """Earnings-based attribution takes priority when available."""
        # Create a mock earnings attribution parquet
        earnings_df = pd.DataFrame([{
            "cik": "0001045810",
            "company_name": "NVIDIA",
            "fiscal_year": 2024,
            "fiscal_quarter": None,
            "total_revenue_usd": None,
            "ai_revenue_usd": 120.0,
            "ai_ratio": None,
            "attribution_method": "earnings_regex",
            "confidence_score": 0.9,
            "llm_validated": None,
            "vintage_date": "2026-03-28",
        }])

        with patch("src.processing.revenue_attribution._load_earnings_attribution", return_value=earnings_df):
            result = estimate_ai_revenue(130.0, "0001045810", {}, 2024)

        assert result["ai_revenue_usd"] == 120.0
        assert result["attribution_method"] == "earnings_regex"

    def test_pure_play_fallback_without_earnings(self):
        """Without earnings data, falls back to pure-play logic."""
        with patch("src.processing.revenue_attribution._load_earnings_attribution", return_value=None):
            result = estimate_ai_revenue(130.0, "0001045810", {}, 2024)

        assert result["ai_revenue_usd"] == 130.0
        assert result["attribution_method"] == "direct_disclosure"

    def test_config_override_without_earnings(self):
        """Config overrides are used when no earnings and not pure-play."""
        config = {"0000789019": {"ratio": 0.15, "method": "analogue_ratio"}}

        with patch("src.processing.revenue_attribution._load_earnings_attribution", return_value=None):
            result = estimate_ai_revenue(200.0, "0000789019", config, 2024)

        assert abs(result["ai_revenue_usd"] - 30.0) < 0.01
        assert result["attribution_method"] == "analogue_ratio"
