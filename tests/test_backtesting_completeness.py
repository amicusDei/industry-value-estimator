"""Backtesting completeness contract tests — honest LOO validation only."""

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


def test_all_segments_have_loo_results(bt):
    """All 4 segments have at least one LOO-based ensemble or prophet result."""
    for seg in SEGMENTS:
        loo = bt[
            (bt["segment"] == seg)
            & (bt["model"].isin(["prophet_loo", "ensemble_loo", "ensemble"]))
        ]
        assert len(loo) >= 1, f"{seg}: no LOO results at all"


def test_no_circular_soft_actuals(bt):
    """No circular soft actuals — these were removed in the LOO fix."""
    soft = bt[bt["actual_type"] == "soft"]
    assert len(soft) == 0, f"Found {len(soft)} circular soft actual rows"


def test_mape_is_nonzero(bt):
    """No ensemble/ensemble_loo row should have MAPE exactly 0.0."""
    ens = bt[bt["model"].str.contains("ensemble")]
    zeros = ens[ens["mape"] < 0.01]
    assert len(zeros) == 0, (
        f"Found {len(zeros)} ensemble rows with MAPE < 0.01 — "
        "likely circular (training data = test data)"
    )


def test_no_future_leakage(bt):
    """LOO held-out rows should have nonzero MAPE (data was genuinely excluded)."""
    held_out = bt[bt["actual_type"] == "held_out"]
    if len(held_out) > 0:
        assert (held_out["mape"] > 0).all(), (
            "Held-out rows with 0% MAPE — possible data leakage"
        )


def test_regime_labels_present(bt):
    assert "regime_label" in bt.columns
    assert set(bt["regime_label"].dropna().unique()) == {"pre_genai", "post_genai"}
