"""CAGR calibration contract tests."""

import pandas as pd
import pytest
import yaml

PARQUET = "data/processed/forecasts_ensemble.parquet"
CONFIG = "config/industries/ai.yaml"
SEGMENTS = ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]


@pytest.fixture(scope="module")
def fc():
    return pd.read_parquet(PARQUET)


@pytest.fixture(scope="module")
def floors():
    with open(CONFIG) as f:
        cfg = yaml.safe_load(f)
    return cfg["model_calibration"]["cagr_floors"]


def _cagr(fc, seg, start=2025, end=2030):
    q4 = fc[(fc["segment"] == seg) & (fc["quarter"] == 4)]
    v_s = q4[q4["year"] == start]["point_estimate_real_2020"]
    v_e = q4[q4["year"] == end]["point_estimate_real_2020"]
    if v_s.empty or v_e.empty or float(v_s.iloc[0]) <= 0:
        return None
    return (float(v_e.iloc[0]) / float(v_s.iloc[0])) ** (1 / (end - start)) - 1


def test_cagr_meets_floor(fc, floors):
    for seg in SEGMENTS:
        cagr = _cagr(fc, seg)
        if cagr is not None:
            floor = floors[seg]
            assert cagr >= floor - 0.005, (
                f"{seg}: CAGR {cagr:.3f} < floor {floor}"
            )


def test_cagr_within_range(fc, floors):
    for seg in SEGMENTS:
        cagr = _cagr(fc, seg)
        if cagr is not None:
            ceiling = floors[seg] * 2.5
            assert cagr <= ceiling, f"{seg}: CAGR {cagr:.3f} > ceiling {ceiling}"


def test_calibration_ratio_finite(fc):
    """No NaN or Inf in point estimates."""
    assert fc["point_estimate_real_2020"].notna().all()
    assert (fc["point_estimate_real_2020"] < 1e6).all()
