"""
Pandera DataFrame schemas for data validation at fetch boundaries.

Every API response is validated IMMEDIATELY after fetch, before writing to data/raw/.
A schema mismatch raises pandera.errors.SchemaError — the pipeline fails loudly
rather than silently writing corrupt data.

Three schemas:
- WORLD_BANK_RAW_SCHEMA: Validates raw wbgapi DataFrame
- OECD_RAW_SCHEMA: Validates raw pandasdmx OECD DataFrame
- LSEG_RAW_SCHEMA: Validates raw lseg-data company DataFrame

Two processed schemas:
- PROCESSED_SCHEMA: Validates the final processed layer (post-deflation)
- validates no _nominal_ columns remain, all monetary cols are _real_2020
"""
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check


# ============================================================
# RAW LAYER SCHEMAS (validate immediately after API fetch)
# ============================================================

WORLD_BANK_RAW_SCHEMA = DataFrameSchema(
    {
        "economy": Column(str, nullable=False),
        "year": Column(int, Check.in_range(2000, 2030)),
    },
    # World Bank returns variable columns depending on indicators requested.
    # We validate structure; specific indicator columns are checked per-fetch.
    coerce=True,
    strict=False,  # allow extra columns from API
)


def make_world_bank_indicator_check(indicator_code: str) -> DataFrameSchema:
    """
    Create a schema that validates a specific World Bank indicator column exists
    and has reasonable values.

    Parameters
    ----------
    indicator_code : str
        World Bank indicator code, e.g. "NY.GDP.MKTP.CD"
    """
    return DataFrameSchema(
        {
            indicator_code: Column(float, nullable=True),  # some country/year combos missing
        },
        coerce=True,
        strict=False,
    )


OECD_RAW_SCHEMA = DataFrameSchema(
    {
        "LOCATION": Column(str, nullable=False),
        "TIME_PERIOD": Column(str, nullable=False),  # OECD returns year as string
        "value": Column(float, nullable=True),
    },
    coerce=True,
    strict=False,  # OECD SDMX includes many dimension columns
)


LSEG_RAW_SCHEMA = DataFrameSchema(
    {
        "Instrument": Column(str, nullable=False),  # RIC code
    },
    coerce=True,
    strict=False,  # LSEG returns requested fields as columns
)


# ============================================================
# PROCESSED LAYER SCHEMA (validate before writing to data/processed/)
# ============================================================

PROCESSED_SCHEMA = DataFrameSchema(
    {
        "year": Column(int, Check.in_range(2010, 2030)),
        "economy": Column(str, nullable=False),
        "industry_tag": Column(str, Check.isin(["ai"]), nullable=False),
        "industry_segment": Column(
            str,
            Check.isin(["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption", "macro"]),
            nullable=False,
        ),
        "estimated_flag": Column(bool, nullable=False),
        "source": Column(str, Check.isin(["world_bank", "oecd", "lseg"]), nullable=False),
    },
    coerce=True,
    strict=False,  # additional data columns vary by source
)


def check_no_nominal_columns(df) -> bool:
    """
    Verify that no column in the processed DataFrame has '_nominal_' in its name.
    All monetary columns must be deflated to _real_2020 before reaching processed layer.
    """
    nominal_cols = [c for c in df.columns if "_nominal_" in c.lower()]
    if nominal_cols:
        raise ValueError(
            f"Nominal columns found in processed layer (must be deflated): {nominal_cols}"
        )
    return True


def validate_raw_world_bank(df):
    """Validate raw World Bank fetch. Raises SchemaError on failure."""
    return WORLD_BANK_RAW_SCHEMA.validate(df)


def validate_raw_oecd(df):
    """Validate raw OECD fetch. Raises SchemaError on failure."""
    return OECD_RAW_SCHEMA.validate(df)


def validate_raw_lseg(df):
    """Validate raw LSEG fetch. Raises SchemaError on failure."""
    return LSEG_RAW_SCHEMA.validate(df)


def validate_processed(df):
    """Validate processed layer DataFrame. Raises SchemaError or ValueError."""
    check_no_nominal_columns(df)
    return PROCESSED_SCHEMA.validate(df)
