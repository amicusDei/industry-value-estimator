"""CI bound contract tests — institutional-grade invariants.

CI coverage targets are NOT 100% — that was an artifact of circular backtesting.
With honest LOO evaluation, expect 40-90% CI80 coverage given limited data.
"""

import warnings
import pandas as pd
import pytest

PARQUET = "data/processed/forecasts_ensemble.parquet"
BT_PARQUET = "data/processed/backtesting_results.parquet"


@pytest.fixture(scope="module")
def fc():
    return pd.read_parquet(PARQUET)


@pytest.fixture(scope="module")
def bt():
    return pd.read_parquet(BT_PARQUET)


def test_ci_bounds_non_negative(fc):
    assert (fc["ci95_lower"] >= 0).all(), "Negative CI95 lower"
    assert (fc["ci80_lower"] >= 0).all(), "Negative CI80 lower"


def test_ci_ordering(fc):
    for _, r in fc.iterrows():
        assert r["ci95_lower"] <= r["ci80_lower"] + 0.01, (
            f"{r['segment']} {r['year']}Q{r['quarter']}: ci95_lower > ci80_lower"
        )
        assert r["ci80_lower"] <= r["point_estimate_real_2020"] + 0.01
        assert r["point_estimate_real_2020"] <= r["ci80_upper"] + 0.01
        assert r["ci80_upper"] <= r["ci95_upper"] + 0.01


def test_ci_width_floors(fc):
    """CI width >= minimum from ai.yaml (25% for CI80, 40% for CI95)."""
    forecast = fc[fc["is_forecast"] == True]
    for _, r in forecast.iterrows():
        pt = r["point_estimate_real_2020"]
        if pt <= 0:
            continue
        ci80_width = r["ci80_upper"] - r["ci80_lower"]
        ci95_width = r["ci95_upper"] - r["ci95_lower"]
        assert ci80_width >= pt * 0.4, f"CI80 too narrow for {r['segment']} {r['year']}Q{r['quarter']}"
        assert ci95_width >= pt * 0.7, f"CI95 too narrow for {r['segment']} {r['year']}Q{r['quarter']}"


def test_ci_nominal_consistent(fc):
    """Nominal CIs should be >= real CIs for post-2020 years."""
    post_2020 = fc[fc["year"] > 2020]
    if "ci80_lower_nominal" in post_2020.columns:
        assert (post_2020["ci80_upper_nominal"] >= post_2020["ci80_upper"] - 0.1).all()


def test_ci80_coverage_realistic(bt):
    """CI80 coverage from LOO should be in 30-100% range (NOT always 100%).

    100% CI80 coverage was an artifact of circular backtesting. With honest
    LOO, expect 40-90% depending on segment and data quality.
    """
    loo = bt[bt["model"] == "prophet_loo"]
    if loo.empty or "ci80_covered" not in loo.columns:
        pytest.skip("No prophet_loo CI80 data")

    coverage = loo["ci80_covered"].mean()
    if coverage > 0.99:
        warnings.warn(
            f"CI80 coverage is {coverage:.0%} — suspiciously high, may indicate "
            "circular validation or overly wide bands",
            UserWarning,
        )
    assert coverage >= 0.30, (
        f"CI80 coverage {coverage:.0%} is below 30% — CIs may be miscalibrated"
    )
