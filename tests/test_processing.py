"""
End-to-end processing pipeline tests.

Tests for:
- src/processing/tag.py (apply_industry_tags)
- src/processing/normalize.py (normalize_world_bank, normalize_oecd, write_processed_parquet)
"""
import pytest
import pandas as pd
import numpy as np
import pyarrow.parquet as pq
from pathlib import Path
import tempfile
import os

from src.processing.tag import apply_industry_tags, tag_lseg_by_trbc
from src.processing.normalize import (
    normalize_world_bank,
    normalize_oecd,
    normalize_lseg,
    write_processed_parquet,
)


# ================================================================
# Fixtures
# ================================================================


@pytest.fixture
def ai_config():
    """Minimal AI config dict for testing (mimics config/industries/ai.yaml)."""
    return {
        "industry": "ai",
        "base_year": 2020,
        "segments": [
            {"id": "ai_hardware"},
            {"id": "ai_infrastructure"},
            {"id": "ai_software"},
            {"id": "ai_adoption"},
        ],
        "lseg": {
            "trbc_codes": [
                {"code": "57201010", "segment": "ai_hardware"},
                {"code": "57201030", "segment": "ai_hardware"},
                {"code": "45101010", "segment": "ai_software"},
            ]
        },
        "source_attribution": {
            "world_bank": "World Bank Open Data (data.worldbank.org)",
            "oecd": "OECD.Stat (stats.oecd.org)",
            "lseg": "LSEG Workspace (Refinitiv)",
        },
    }


@pytest.fixture
def world_bank_raw_df():
    """Minimal raw World Bank DataFrame for testing."""
    return pd.DataFrame({
        "year": [2018, 2019, 2020, 2021, 2022],
        "economy": ["USA"] * 5,
        "gdp_deflator_index": [95.0, 97.5, 100.0, 103.0, 108.0],
        "rd_pct_gdp": [2.5, 2.6, 2.7, 2.8, 2.9],
        "estimated_flag": [False] * 5,
    })


@pytest.fixture
def world_bank_raw_df_with_nominal():
    """Raw World Bank DataFrame with nominal monetary columns."""
    return pd.DataFrame({
        "year": [2018, 2019, 2020, 2021, 2022],
        "economy": ["USA"] * 5,
        "gdp_nominal_usd": [800.0, 900.0, 1000.0, 1100.0, 1200.0],
        "rd_pct_gdp": [2.5, 2.6, 2.7, 2.8, 2.9],
        "gdp_deflator_index": [95.0, 97.5, 100.0, 103.0, 108.0],
        "estimated_flag": [False] * 5,
    })


@pytest.fixture
def oecd_raw_df():
    """Minimal raw OECD DataFrame (already renamed from LOCATION/TIME_PERIOD)."""
    return pd.DataFrame({
        "year": [2018, 2019, 2020, 2021, 2022],
        "economy": ["USA"] * 5,
        "value": [1.5, 1.6, 1.7, 1.8, 1.9],
        "estimated_flag": [False] * 5,
    })


@pytest.fixture
def oecd_raw_df_with_original_columns():
    """Raw OECD DataFrame with LOCATION and TIME_PERIOD as from API."""
    return pd.DataFrame({
        "LOCATION": ["USA", "DEU", "JPN"],
        "TIME_PERIOD": ["2020", "2020", "2020"],
        "value": [1.7, 1.5, 1.2],
        "estimated_flag": [False] * 3,
    })


# ================================================================
# apply_industry_tags tests
# ================================================================


class TestApplyIndustryTags:
    """Tests for the tagging module."""

    def test_adds_industry_tag_to_every_row(self, ai_config, world_bank_raw_df):
        """apply_industry_tags adds industry_tag='ai' to every row."""
        result = apply_industry_tags(world_bank_raw_df, ai_config, source="world_bank")

        assert "industry_tag" in result.columns
        assert (result["industry_tag"] == "ai").all()

    def test_adds_industry_segment_to_every_row(self, ai_config, world_bank_raw_df):
        """apply_industry_tags adds industry_segment to every row."""
        result = apply_industry_tags(
            world_bank_raw_df, ai_config, source="world_bank", segment="macro"
        )

        assert "industry_segment" in result.columns
        assert not result["industry_segment"].isna().any()

    def test_adds_source_column(self, ai_config, world_bank_raw_df):
        """apply_industry_tags adds source column (DATA-07 attribution)."""
        result = apply_industry_tags(world_bank_raw_df, ai_config, source="world_bank")

        assert "source" in result.columns
        assert (result["source"] == "world_bank").all()

    def test_segment_assignment_from_config(self, ai_config, world_bank_raw_df):
        """Industry segment value comes from the segment parameter."""
        result = apply_industry_tags(
            world_bank_raw_df, ai_config, source="world_bank", segment="ai_hardware"
        )

        assert (result["industry_segment"] == "ai_hardware").all()

    def test_lseg_tag_by_trbc(self, ai_config):
        """tag_lseg_by_trbc maps TRBC codes to segments from config."""
        df = pd.DataFrame({
            "Instrument": ["RIC1", "RIC2"],
            "TR.TRBCActivityCode": ["57201010", "45101010"],
            "TR.Revenue": [1e9, 2e9],
        })
        result = tag_lseg_by_trbc(df, ai_config)

        assert result.loc[0, "industry_segment"] == "ai_hardware"
        assert result.loc[1, "industry_segment"] == "ai_software"
        assert (result["source"] == "lseg").all()


# ================================================================
# normalize_world_bank tests
# ================================================================


class TestNormalizeWorldBank:
    """Tests for the World Bank normalization pipeline."""

    def test_normalize_world_bank_passes_processed_schema(
        self, ai_config, world_bank_raw_df
    ):
        """normalize_world_bank output passes PROCESSED_SCHEMA validation."""
        result = normalize_world_bank(world_bank_raw_df, ai_config)

        # If schema validation fails, it raises — no assertion needed
        assert result is not None
        assert len(result) == len(world_bank_raw_df)

    def test_normalize_world_bank_industry_tag_non_null(
        self, ai_config, world_bank_raw_df
    ):
        """Every row in normalized World Bank data has non-null industry_tag."""
        result = normalize_world_bank(world_bank_raw_df, ai_config)

        assert not result["industry_tag"].isna().any()

    def test_normalize_world_bank_source_column_set(
        self, ai_config, world_bank_raw_df
    ):
        """Normalized World Bank data has source column set for DATA-07."""
        result = normalize_world_bank(world_bank_raw_df, ai_config)

        assert "source" in result.columns
        assert (result["source"] == "world_bank").all()

    def test_normalize_world_bank_no_nominal_columns(
        self, ai_config, world_bank_raw_df_with_nominal
    ):
        """No _nominal_ columns in normalized World Bank output."""
        result = normalize_world_bank(world_bank_raw_df_with_nominal, ai_config)

        nominal_cols = [c for c in result.columns if "_nominal_" in c.lower()]
        assert len(nominal_cols) == 0, f"Nominal columns found: {nominal_cols}"

    def test_normalize_world_bank_deflates_nominal_columns(
        self, ai_config, world_bank_raw_df_with_nominal
    ):
        """Nominal monetary columns are deflated and renamed to _real_2020."""
        result = normalize_world_bank(world_bank_raw_df_with_nominal, ai_config)

        real_cols = [c for c in result.columns if "_real_" in c.lower()]
        assert len(real_cols) >= 1, "Expected at least one _real_ column after deflation"


# ================================================================
# normalize_oecd tests
# ================================================================


class TestNormalizeOecd:
    """Tests for the OECD normalization pipeline."""

    def test_normalize_oecd_passes_processed_schema(
        self, ai_config, oecd_raw_df
    ):
        """normalize_oecd output passes PROCESSED_SCHEMA validation."""
        result = normalize_oecd(oecd_raw_df, ai_config, dataset_name="MSTI")

        assert result is not None
        assert len(result) == len(oecd_raw_df)

    def test_normalize_oecd_renames_location_to_economy(
        self, ai_config, oecd_raw_df_with_original_columns
    ):
        """normalize_oecd renames LOCATION -> economy and TIME_PERIOD -> year."""
        result = normalize_oecd(
            oecd_raw_df_with_original_columns, ai_config, dataset_name="MSTI"
        )

        assert "economy" in result.columns
        assert "LOCATION" not in result.columns

    def test_normalize_oecd_industry_tag_non_null(
        self, ai_config, oecd_raw_df
    ):
        """Every row in normalized OECD data has non-null industry_tag."""
        result = normalize_oecd(oecd_raw_df, ai_config, dataset_name="PATS_IPC")

        assert not result["industry_tag"].isna().any()

    def test_normalize_oecd_source_column_set(
        self, ai_config, oecd_raw_df
    ):
        """Normalized OECD data has source column set (DATA-07 attribution)."""
        result = normalize_oecd(oecd_raw_df, ai_config, dataset_name="MSTI")

        assert "source" in result.columns
        assert (result["source"] == "oecd").all()

    def test_normalize_oecd_raises_value_error_missing_economy(
        self, ai_config
    ):
        """normalize_oecd raises ValueError if DataFrame has no economy/LOCATION column."""
        df_no_economy = pd.DataFrame({
            "year": [2020, 2021],
            "value": [1.5, 1.6],
            "estimated_flag": [False, False],
        })

        with pytest.raises(ValueError, match="OECD DataFrame missing 'economy' column"):
            normalize_oecd(df_no_economy, ai_config, dataset_name="MSTI")

    def test_normalize_oecd_no_nominal_columns_in_output(
        self, ai_config, oecd_raw_df
    ):
        """No _nominal_ columns in OECD output."""
        result = normalize_oecd(oecd_raw_df, ai_config, dataset_name="MSTI")

        nominal_cols = [c for c in result.columns if "_nominal_" in c.lower()]
        assert len(nominal_cols) == 0, f"Nominal columns found: {nominal_cols}"


# ================================================================
# write_processed_parquet tests
# ================================================================


class TestWriteProcessedParquet:
    """Tests for Parquet output with provenance metadata."""

    @pytest.fixture
    def minimal_processed_df(self, ai_config, world_bank_raw_df):
        """Minimal validated processed DataFrame."""
        from src.processing.normalize import normalize_world_bank
        return normalize_world_bank(world_bank_raw_df, ai_config)

    def test_write_processed_parquet_creates_file(
        self, minimal_processed_df, tmp_path, monkeypatch
    ):
        """write_processed_parquet creates a Parquet file."""
        import config.settings as settings
        monkeypatch.setattr(settings, "DATA_PROCESSED", tmp_path)

        from src.processing.normalize import write_processed_parquet
        output_path = write_processed_parquet(
            minimal_processed_df,
            filename="test_output.parquet",
            source="world_bank",
            industry_id="ai",
        )

        assert output_path.exists()
        assert output_path.suffix == ".parquet"

    def test_write_processed_parquet_has_provenance_metadata(
        self, minimal_processed_df, tmp_path, monkeypatch
    ):
        """Parquet file has provenance metadata: source, industry, base_year, fetched_at."""
        import config.settings as settings
        monkeypatch.setattr(settings, "DATA_PROCESSED", tmp_path)

        from src.processing.normalize import write_processed_parquet
        output_path = write_processed_parquet(
            minimal_processed_df,
            filename="test_metadata.parquet",
            source="world_bank",
            industry_id="ai",
        )

        pq_file = pq.read_metadata(output_path)
        meta = pq_file.metadata
        schema_meta = pq.read_schema(output_path).metadata

        assert b"source" in schema_meta
        assert schema_meta[b"source"] == b"world_bank"
        assert b"industry" in schema_meta
        assert schema_meta[b"industry"] == b"ai"
        assert b"base_year" in schema_meta
        assert b"fetched_at" in schema_meta

    def test_write_processed_parquet_readable_dataframe(
        self, minimal_processed_df, tmp_path, monkeypatch
    ):
        """Written Parquet file can be read back as DataFrame."""
        import config.settings as settings
        monkeypatch.setattr(settings, "DATA_PROCESSED", tmp_path)

        from src.processing.normalize import write_processed_parquet
        output_path = write_processed_parquet(
            minimal_processed_df,
            filename="test_readable.parquet",
            source="world_bank",
        )

        read_back = pd.read_parquet(output_path)
        assert len(read_back) == len(minimal_processed_df)

    def test_processed_output_has_source_column_for_attribution(
        self, minimal_processed_df
    ):
        """Processed DataFrame has source column set (DATA-07 requirement)."""
        assert "source" in minimal_processed_df.columns
        assert not minimal_processed_df["source"].isna().any()

    def test_processed_output_industry_tag_on_every_row(
        self, minimal_processed_df
    ):
        """Every processed row has non-null industry_tag and industry_segment."""
        assert not minimal_processed_df["industry_tag"].isna().any()
        assert not minimal_processed_df["industry_segment"].isna().any()
