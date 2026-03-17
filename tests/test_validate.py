"""Tests for pandera validation schemas (DATA-03, DATA-04, DATA-05, DATA-06)."""
import json
import pandas as pd
import pytest
from pathlib import Path

from src.processing.validate import (
    validate_raw_world_bank,
    validate_raw_oecd,
    validate_raw_lseg,
    validate_processed,
    check_no_nominal_columns,
    WORLD_BANK_RAW_SCHEMA,
    OECD_RAW_SCHEMA,
    LSEG_RAW_SCHEMA,
    PROCESSED_SCHEMA,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestWorldBankSchema:
    def test_valid_world_bank_data(self):
        df = pd.read_json(FIXTURES / "world_bank_sample.json")
        result = validate_raw_world_bank(df)
        assert len(result) == 4

    def test_rejects_missing_economy(self):
        df = pd.DataFrame({"year": [2020], "NY.GDP.MKTP.CD": [1e12]})
        with pytest.raises(Exception):  # SchemaError
            validate_raw_world_bank(df)

    def test_rejects_year_out_of_range(self):
        df = pd.DataFrame({"economy": ["USA"], "year": [1800], "NY.GDP.MKTP.CD": [1e12]})
        with pytest.raises(Exception):
            validate_raw_world_bank(df)


class TestOECDSchema:
    def test_valid_oecd_data(self):
        df = pd.read_json(FIXTURES / "oecd_sample.json")
        result = validate_raw_oecd(df)
        assert len(result) == 3

    def test_rejects_missing_location(self):
        df = pd.DataFrame({"TIME_PERIOD": ["2020"], "value": [100.0]})
        with pytest.raises(Exception):
            validate_raw_oecd(df)


class TestLSEGSchema:
    def test_valid_lseg_data(self):
        df = pd.read_json(FIXTURES / "lseg_sample.json")
        result = validate_raw_lseg(df)
        assert len(result) == 3

    def test_rejects_missing_instrument(self):
        df = pd.DataFrame({"TR.Revenue": [1e9]})
        with pytest.raises(Exception):
            validate_raw_lseg(df)


class TestProcessedSchema:
    def test_valid_processed_data(self):
        df = pd.DataFrame({
            "year": [2020, 2021],
            "economy": ["USA", "USA"],
            "industry_tag": ["ai", "ai"],
            "industry_segment": ["ai_hardware", "ai_hardware"],
            "estimated_flag": [False, True],
            "source": ["world_bank", "world_bank"],
            "gdp_real_2020": [21060474000000.0, 21200000000000.0],
        })
        result = validate_processed(df)
        assert len(result) == 2

    def test_rejects_invalid_segment(self):
        df = pd.DataFrame({
            "year": [2020],
            "economy": ["USA"],
            "industry_tag": ["ai"],
            "industry_segment": ["invalid_segment"],
            "estimated_flag": [False],
            "source": ["world_bank"],
        })
        with pytest.raises(Exception):
            validate_processed(df)

    def test_rejects_nominal_columns_in_processed(self):
        df = pd.DataFrame({
            "year": [2020],
            "economy": ["USA"],
            "gdp_nominal_2020": [21e12],
        })
        with pytest.raises(ValueError, match="Nominal columns found"):
            check_no_nominal_columns(df)

    def test_accepts_real_columns(self):
        df = pd.DataFrame({
            "gdp_real_2020": [21e12],
            "rd_pct_gdp": [3.45],
        })
        assert check_no_nominal_columns(df) is True
