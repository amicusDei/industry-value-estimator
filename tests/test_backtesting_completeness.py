"""Backtesting completeness contract tests."""

import pandas as pd
import pytest

PARQUET = "data/processed/backtesting_results.parquet"
SEGMENTS = ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]


@pytest.fixture(scope="module")
def bt():
    return pd.read_parquet(PARQUET)


def test_all_segments_have_results(bt):
    for seg in SEGMENTS:
        seg_rows = bt[bt["segment"] == seg]
        assert len(seg_rows) > 0, f"No backtesting results for {seg}"


def test_all_segments_have_prophet_loo(bt):
    for seg in SEGMENTS:
        loo = bt[(bt["segment"] == seg) & (bt["model"] == "prophet_loo")]
        assert len(loo) >= 3, f"{seg}: only {len(loo)} prophet_loo folds (need >= 3)"


def test_all_segments_have_ensemble(bt):
    for seg in SEGMENTS:
        ens = bt[(bt["segment"] == seg) & (bt["model"] == "ensemble")]
        assert len(ens) >= 1, f"{seg}: no ensemble results"


def test_no_future_leakage(bt):
    """No training data should include the holdout year."""
    loo = bt[bt["model"] == "prophet_loo"]
    # If actual_type is "held_out", the actual should not be circular
    held_out = loo[loo["actual_type"] == "held_out"]
    # All held_out rows should have mape > 0 (exact 0 would suggest circular)
    # Allow soft actuals (ensemble) to be 0 since those are intentionally circular
    assert (held_out["mape"] > 0).all() or len(held_out) == 0, (
        "Prophet LOO has 0% MAPE — possible data leakage"
    )


def test_regime_labels_present(bt):
    assert "regime_label" in bt.columns
    assert set(bt["regime_label"].dropna().unique()) == {"pre_genai", "post_genai"}
