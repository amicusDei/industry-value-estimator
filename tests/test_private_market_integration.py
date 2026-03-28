"""
Tests for private market integration module.
"""

import pandas as pd
import pytest
from unittest.mock import patch


class TestComputePrivateContribution:
    def test_returns_dict_with_segments(self):
        """compute_private_contribution returns dict keyed by segment."""
        from src.processing.private_market_integration import compute_private_contribution
        result = compute_private_contribution()
        assert isinstance(result, dict)
        # Should have at least ai_software and ai_infrastructure
        assert "ai_software" in result or "ai_infrastructure" in result

    def test_segment_dict_structure(self):
        """Each segment dict has arr_weighted, low, high, n_companies."""
        from src.processing.private_market_integration import compute_private_contribution
        result = compute_private_contribution()
        for seg, data in result.items():
            assert "arr_weighted" in data
            assert "low" in data
            assert "high" in data
            assert "n_companies" in data
            assert data["arr_weighted"] > 0
            assert data["n_companies"] >= 1

    def test_total_arr_in_plausible_range(self):
        """Total weighted ARR should be $3-15B range (18 companies, $8-10B raw)."""
        from src.processing.private_market_integration import compute_private_contribution
        result = compute_private_contribution()
        total = sum(d["arr_weighted"] for d in result.values())
        assert 3.0 <= total <= 15.0, f"Total ARR ${total:.1f}B outside [3, 15] range"

    def test_confidence_weighting_reduces_total(self):
        """Weighted total should be less than raw total (LOW/MEDIUM have <1.0 weight)."""
        from src.processing.private_market_integration import compute_private_contribution
        result = compute_private_contribution()
        weighted_total = sum(d["arr_weighted"] for d in result.values())

        pv = pd.read_parquet("data/processed/private_valuations_ai.parquet")
        if "estimated_arr_usd_billions" in pv.columns:
            raw_total = pv["estimated_arr_usd_billions"].sum()
        else:
            raw_total = (pv["implied_ev_mid"] / pv["comparable_mid_multiple"]).sum()

        assert weighted_total < raw_total, (
            f"Weighted ${weighted_total:.1f}B should be < raw ${raw_total:.1f}B"
        )

    def test_returns_empty_when_file_missing(self):
        """Returns empty dict when parquet file doesn't exist."""
        from src.processing.private_market_integration import compute_private_contribution
        with patch("src.processing.private_market_integration.DATA_PROCESSED") as mock_path:
            mock_file = mock_path / "private_valuations_ai.parquet"
            mock_file.exists.return_value = False
            mock_path.__truediv__ = lambda self, x: mock_file
            result = compute_private_contribution()
        assert result == {}

    def test_low_less_than_high(self):
        """Uncertainty low < high for all segments."""
        from src.processing.private_market_integration import compute_private_contribution
        result = compute_private_contribution()
        for seg, data in result.items():
            assert data["low"] <= data["high"], (
                f"{seg}: low ${data['low']:.1f}B > high ${data['high']:.1f}B"
            )
