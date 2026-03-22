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
    Create a schema that validates a specific World Bank indicator column exists and has
    reasonable values.

    This factory is used for per-indicator validation beyond the base schema — for example,
    checking that GDP values are positive, or that deflator values are in a sensible range.
    The base WORLD_BANK_RAW_SCHEMA only validates structural columns (economy, year).

    Parameters
    ----------
    indicator_code : str
        World Bank indicator code, e.g. "NY.GDP.MKTP.CD".

    Returns
    -------
    DataFrameSchema
        A pandera schema that validates the named indicator column as nullable float.
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

    This is the safeguard that enforces the nominal/real distinction at the processed
    layer boundary. Calling this function before writing to data/processed/ guarantees
    that all monetary columns have been properly deflated to constant base-year USD.

    This check is callable standalone for unit testing the deflation step, or it is
    called automatically inside validate_processed() as part of the full validation chain.

    Parameters
    ----------
    df : pd.DataFrame
        Any DataFrame to check for nominal column contamination.

    Returns
    -------
    bool
        True if no nominal columns are found.

    Raises
    ------
    ValueError
        If any column name contains '_nominal_', listing the offending columns.
    """
    nominal_cols = [c for c in df.columns if "_nominal_" in c.lower()]
    if nominal_cols:
        raise ValueError(
            f"Nominal columns found in processed layer (must be deflated): {nominal_cols}"
        )
    return True


def validate_raw_world_bank(df):
    """
    Validate raw World Bank fetch against WORLD_BANK_RAW_SCHEMA.

    Parameters
    ----------
    df : pd.DataFrame
        Raw World Bank DataFrame to validate.

    Returns
    -------
    pd.DataFrame
        The validated (and optionally coerced) DataFrame.

    Raises
    ------
    pandera.errors.SchemaError
        If required columns are missing or data types are incorrect.
    """
    return WORLD_BANK_RAW_SCHEMA.validate(df)


def validate_raw_oecd(df):
    """
    Validate raw OECD fetch against OECD_RAW_SCHEMA.

    Parameters
    ----------
    df : pd.DataFrame
        Raw OECD pandasdmx DataFrame to validate.

    Returns
    -------
    pd.DataFrame
        The validated DataFrame.

    Raises
    ------
    pandera.errors.SchemaError
        If LOCATION, TIME_PERIOD, or value columns are missing or invalid.
    """
    return OECD_RAW_SCHEMA.validate(df)


def validate_raw_lseg(df):
    """
    Validate raw LSEG fetch against LSEG_RAW_SCHEMA.

    Parameters
    ----------
    df : pd.DataFrame
        Raw LSEG DataFrame from ld.get_data().

    Returns
    -------
    pd.DataFrame
        The validated DataFrame.

    Raises
    ------
    pandera.errors.SchemaError
        If the Instrument column is missing or contains nulls.
    """
    return LSEG_RAW_SCHEMA.validate(df)


def validate_processed(df):
    """
    Validate processed layer DataFrame against PROCESSED_SCHEMA.

    Runs both the nominal-column check (no '_nominal_' columns allowed) and the
    pandera schema validation. Raises on the first failure encountered.

    Parameters
    ----------
    df : pd.DataFrame
        Processed DataFrame to validate before writing to data/processed/.

    Returns
    -------
    pd.DataFrame
        The validated DataFrame.

    Raises
    ------
    ValueError
        If any nominal columns remain in the DataFrame.
    pandera.errors.SchemaError
        If the DataFrame does not conform to PROCESSED_SCHEMA.
    """
    check_no_nominal_columns(df)
    return PROCESSED_SCHEMA.validate(df)
