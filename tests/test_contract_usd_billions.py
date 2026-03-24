"""
Contract tests for forecasts_ensemble.parquet output.

These tests assert that model output values are in USD billions (real 2020 USD),
not composite index units. They are Wave 0 scaffolds: they will be skipped until
Plan 09-03 generates the parquet file.

MODL-05: Forecast trajectories reflect realistic AI growth (25-40% CAGR).
The CAGR test uses a wider 15-60% gate to allow model flexibility — the 25-40%
target range is a documentation/verification concern, not a hard test gate.
"""
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from config.settings import DATA_PROCESSED

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PARQUET_PATH = DATA_PROCESSED / "forecasts_ensemble.parquet"


def _load_forecasts() -> pd.DataFrame:
    """Load forecasts_ensemble.parquet. Called only when file exists (skipif guard)."""
    return pd.read_parquet(PARQUET_PATH)


# ---------------------------------------------------------------------------
# Contract tests — skipped until forecasts_ensemble.parquet is generated
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not PARQUET_PATH.exists(),
    reason="forecasts not yet generated — run Plan 09-03 first",
)
def test_point_estimate_is_usd_billions():
    """All point_estimate_real_2020 values are >= 0 and > 1.0 for non-trivial segments."""
    df = _load_forecasts()
    assert "point_estimate_real_2020" in df.columns, (
        "point_estimate_real_2020 column missing from forecasts_ensemble.parquet"
    )
    # All values non-negative
    assert (df["point_estimate_real_2020"] >= 0).all(), (
        "Negative point estimates found — model output must be floored at 0 USD billions"
    )
    # At least some values > 1.0 USD billion (sanity check that we are not in index units)
    assert (df["point_estimate_real_2020"] > 1.0).any(), (
        "No point_estimate_real_2020 > 1.0 — values appear to be index units, not USD billions"
    )


@pytest.mark.skipif(
    not PARQUET_PATH.exists(),
    reason="forecasts not yet generated — run Plan 09-03 first",
)
def test_total_market_size_plausible():
    """Historical years 2017-2025: total per year is between $50B and $2000B."""
    df = _load_forecasts()
    assert "is_forecast" in df.columns, "is_forecast column missing"
    assert "year" in df.columns, "year column missing"

    historical = df[(df["is_forecast"] == False) & (df["year"].between(2017, 2025))]
    if historical.empty:
        pytest.skip("No historical rows (is_forecast==False) in 2017-2025 range")

    totals_by_year = historical.groupby("year")["point_estimate_real_2020"].sum()
    for year, total in totals_by_year.items():
        assert total > 50, (
            f"Year {year}: total market size {total:.1f}B is implausibly low (< $50B)"
        )
        assert total < 2000, (
            f"Year {year}: total market size {total:.1f}B is implausibly high (> $2000B)"
        )


@pytest.mark.skipif(
    not PARQUET_PATH.exists(),
    reason="forecasts not yet generated — run Plan 09-03 first",
)
def test_cagr_range():
    """CAGR from 2025 to 2030 per segment is between 15% and 60%."""
    df = _load_forecasts()
    assert "year" in df.columns, "year column missing"
    assert "industry_segment" in df.columns, "industry_segment column missing"

    for segment in df["industry_segment"].unique():
        seg_df = df[df["industry_segment"] == segment]

        val_2025 = seg_df.loc[seg_df["year"] == 2025, "point_estimate_real_2020"]
        val_2030 = seg_df.loc[seg_df["year"] == 2030, "point_estimate_real_2020"]

        if val_2025.empty or val_2030.empty:
            continue  # Skip if 2025 or 2030 not present for this segment

        v25 = val_2025.iloc[0]
        v30 = val_2030.iloc[0]

        if v25 <= 0:
            continue  # Cannot compute CAGR with zero/negative base

        cagr = (v30 / v25) ** (1 / 5) - 1
        assert 0.15 <= cagr <= 0.60, (
            f"Segment {segment}: CAGR 2025-2030 = {cagr:.1%} outside [15%, 60%] range. "
            f"Values: 2025={v25:.1f}B, 2030={v30:.1f}B"
        )


@pytest.mark.skipif(
    not PARQUET_PATH.exists(),
    reason="forecasts not yet generated — run Plan 09-03 first",
)
def test_no_negative_forecasts():
    """No row has point_estimate_real_2020 < 0."""
    df = _load_forecasts()
    assert "point_estimate_real_2020" in df.columns, (
        "point_estimate_real_2020 column missing"
    )
    negative_rows = df[df["point_estimate_real_2020"] < 0]
    assert len(negative_rows) == 0, (
        f"Found {len(negative_rows)} rows with negative point_estimate_real_2020. "
        f"Model output must be floored at 0 USD billions."
    )
