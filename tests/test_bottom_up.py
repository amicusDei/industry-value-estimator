"""Tests for bottom-up validation module with CapEx-based validation."""

import pandas as pd
import pytest

from src.ingestion.edgar_capex import (
    AI_CAPEX_RATIOS,
    CAPEX_XBRL_CONCEPTS,
    compile_bottom_up_validation,
    write_bottom_up_validation,
)


@pytest.fixture(scope="module")
def validation_df() -> pd.DataFrame:
    """Compile bottom-up validation once for all tests."""
    return compile_bottom_up_validation("ai")


EXPECTED_COLUMNS = [
    "segment", "year", "bottom_up_sum", "top_down_estimate",
    "coverage_ratio", "gap_usd_billions", "n_companies", "top_contributors",
    "company_capex_sum", "capex_intensity", "capex_implied_growth",
]


# ---------------------------------------------------------------------------
# CapEx constants tests
# ---------------------------------------------------------------------------

def test_capex_xbrl_concepts_has_enough_entries():
    """CAPEX_XBRL_CONCEPTS should have at least 3 entries."""
    assert len(CAPEX_XBRL_CONCEPTS) >= 3, (
        f"Expected at least 3 CAPEX_XBRL_CONCEPTS, got {len(CAPEX_XBRL_CONCEPTS)}"
    )


def test_ai_capex_ratios_valid_range():
    """All AI CapEx ratios should be between 0 and 1."""
    for company, info in AI_CAPEX_RATIOS.items():
        ratio = info["ai_capex_ratio"]
        assert 0.0 <= ratio <= 1.0, (
            f"{company} has ai_capex_ratio={ratio}, expected [0, 1]"
        )
        assert "source" in info, f"{company} missing 'source' key"


def test_ai_capex_ratios_has_major_companies():
    """AI_CAPEX_RATIOS should cover key hyperscalers."""
    expected = {"NVIDIA Corporation", "Microsoft Corporation", "Alphabet Inc."}
    actual = set(AI_CAPEX_RATIOS.keys())
    assert expected.issubset(actual), (
        f"Missing companies: {expected - actual}"
    )


# ---------------------------------------------------------------------------
# Validation DataFrame tests
# ---------------------------------------------------------------------------

def test_non_empty_with_correct_columns(validation_df: pd.DataFrame):
    """Bottom-up validation produces non-empty DataFrame with correct columns."""
    assert not validation_df.empty, "Validation DataFrame should not be empty"
    assert validation_df.columns.tolist() == EXPECTED_COLUMNS


def test_coverage_ratio_range(validation_df: pd.DataFrame):
    """Coverage ratio should be between 0 and ~2.0 (some double-counting possible in hardware)."""
    assert (validation_df["coverage_ratio"] >= 0).all(), "Coverage ratio must be >= 0"
    assert (validation_df["coverage_ratio"] <= 2.0).all(), (
        "Coverage ratio > 2.0 suggests severe double-counting"
    )


def test_n_companies_positive(validation_df: pd.DataFrame):
    """Each segment should have at least 1 contributing company."""
    assert (validation_df["n_companies"] >= 1).all(), "n_companies must be >= 1"


def test_gap_usd_billions_mostly_positive(validation_df: pd.DataFrame):
    """Top-down should generally exceed bottom-up (gap >= 0 for most rows)."""
    negative_count = (validation_df["gap_usd_billions"] < 0).sum()
    total = len(validation_df)
    assert negative_count <= total * 0.5, (
        f"More than half of rows have negative gap ({negative_count}/{total}) — "
        "bottom-up should generally be less than top-down"
    )


def test_top_contributors_is_list(validation_df: pd.DataFrame):
    """top_contributors should be a list of company names."""
    for contrib in validation_df["top_contributors"]:
        assert isinstance(contrib, list), f"Expected list, got {type(contrib)}"
        assert len(contrib) >= 1, "Should have at least 1 contributor"
        assert len(contrib) <= 3, "Should have at most 3 contributors"


def test_capex_intensity_positive_where_data_exists(validation_df: pd.DataFrame):
    """CapEx intensity should be positive where companies have both capex and revenue."""
    has_both = validation_df[
        (validation_df["company_capex_sum"] > 0) & (validation_df["bottom_up_sum"] > 0)
    ]
    if not has_both.empty:
        assert (has_both["capex_intensity"] > 0).all(), (
            "capex_intensity must be > 0 where both capex and revenue exist"
        )


def test_capex_columns_present(validation_df: pd.DataFrame):
    """New CapEx columns should be present."""
    for col in ["company_capex_sum", "capex_intensity", "capex_implied_growth"]:
        assert col in validation_df.columns, f"Missing column: {col}"


def test_write_and_read_roundtrip(validation_df: pd.DataFrame, tmp_path):
    """Write and read back validation data."""
    out_path = tmp_path / "bottom_up_validation.parquet"
    validation_df.to_parquet(out_path, index=False)
    reloaded = pd.read_parquet(out_path)
    assert reloaded.shape == validation_df.shape
    assert reloaded.columns.tolist() == EXPECTED_COLUMNS
