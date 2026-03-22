"""
Full normalization pipeline.

Transforms raw ingested data into the final processed Parquet cache:
1. Rename monetary columns to _nominal_ convention
2. Deflate to 2020 constant USD
3. Interpolate missing values with estimated_flag
4. Apply industry/segment tags
5. Validate against PROCESSED_SCHEMA
6. Write to data/processed/ as Parquet with provenance metadata

This module orchestrates the processing steps. Each step is a separate
module (deflate.py, interpolate.py, tag.py, validate.py) for testability.
"""
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime, timezone
from pathlib import Path

from config.settings import DATA_PROCESSED, BASE_YEAR, load_industry_config
from src.processing.deflate import apply_deflation
from src.processing.interpolate import apply_interpolation
from src.processing.tag import apply_industry_tags, tag_lseg_by_trbc
from src.processing.validate import validate_processed


def normalize_world_bank(
    raw_df: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    """
    Normalize raw World Bank data through the full pipeline.

    The rename step (step 1) is critical for correct deflation: apply_deflation
    in step 2 identifies monetary columns by the '_nominal_' pattern. Columns that
    are NOT monetary (e.g., R&D as % of GDP, patent counts) must NOT get the
    '_nominal_' suffix — they pass through unchanged.

    Steps:
    1. Rename monetary columns to _nominal_ convention (e.g., NY.GDP.MKTP.CD -> gdp_nominal_usd)
    2. Deflate using GDP deflator to 2020 constant USD (removes _nominal_ columns)
    3. Interpolate missing values with estimated_flag
    4. Tag with industry and source (adds industry_tag, industry_segment, source columns)
    5. Validate against PROCESSED_SCHEMA (pandera, raises on schema mismatch)

    Parameters
    ----------
    raw_df : pd.DataFrame
        Validated raw World Bank DataFrame from fetch_world_bank_indicators().
    config : dict
        Industry config for tagging (industry name and economies).

    Returns
    -------
    pd.DataFrame
        Processed DataFrame conforming to PROCESSED_SCHEMA. All monetary columns
        are in 2020 constant USD (no _nominal_ columns remain).
    """
    df = raw_df.copy()

    # Step 1: Rename monetary columns to nominal convention
    # World Bank monetary indicators (unit=current_usd) get _nominal_ prefix
    monetary_indicators = {
        "NY.GDP.MKTP.CD": "gdp_nominal_usd",
        "TX.VAL.TECH.CD": "hightech_exports_nominal_usd",
        "BX.GSR.CCIS.CD": "ict_service_exports_nominal_usd",
    }
    non_monetary_indicators = {
        "GB.XPD.RSDV.GD.ZS": "rd_pct_gdp",
        "NY.GDP.MKTP.KD.ZG": "gdp_growth_annual_pct",
        "SP.POP.SCIE.RD.P6": "researchers_per_million",
        "IP.PAT.RESD": "patent_applications_residents",
        "NY.GDP.DEFL.ZS": "gdp_deflator_index",
    }

    rename_map = {**monetary_indicators, **non_monetary_indicators}
    for old_name, new_name in rename_map.items():
        if old_name in df.columns:
            df = df.rename(columns={old_name: new_name})

    # Step 2: Deflate monetary columns
    if "gdp_deflator_index" in df.columns:
        df = apply_deflation(df, deflator_col="gdp_deflator_index", base_year=BASE_YEAR)

    # Step 3: Interpolate missing values
    df = apply_interpolation(df)

    # Step 4: Tag
    df = apply_industry_tags(df, config, source="world_bank", segment="macro")

    # Step 5: Validate
    df = validate_processed(df)

    return df


def normalize_oecd(
    raw_df: pd.DataFrame,
    config: dict,
    dataset_name: str,
) -> pd.DataFrame:
    """
    Normalize raw OECD data through the pipeline.

    OECD data is typically in long format with a 'value' column. Unlike World Bank,
    OECD data does not need deflation in the current pipeline because the composite
    index construction (PCA) standardizes all indicators anyway — deflation of OECD
    count variables (patents, researchers) would be incorrect. If GERD monetary values
    are used directly in future, deflation should be added here.

    Validates that the 'economy' column exists (derived from LOCATION in raw OECD data).
    Raises ValueError rather than silently passing through rows with no economy —
    silent pass-through would produce invalid processed rows with no economy identifier,
    which would then fail the PROCESSED_SCHEMA check at an opaque location downstream.

    Parameters
    ----------
    raw_df : pd.DataFrame
        Validated raw OECD DataFrame. Expected columns: LOCATION (renamed to economy),
        TIME_PERIOD (renamed to year), value.
    config : dict
        Industry config for tagging.
    dataset_name : str
        Dataset identifier string (e.g., "msti", "pats_ipc") — used in error messages.

    Returns
    -------
    pd.DataFrame
        Processed DataFrame conforming to PROCESSED_SCHEMA.

    Raises
    ------
    ValueError
        If 'economy' column is missing after column rename attempt.
    """
    df = raw_df.copy()

    # Standardize column names
    if "TIME_PERIOD" in df.columns:
        df = df.rename(columns={"TIME_PERIOD": "year"})
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "LOCATION" in df.columns:
        df = df.rename(columns={"LOCATION": "economy"})

    # Defensive check: PROCESSED_SCHEMA requires non-null economy column.
    # OECD raw data should have LOCATION (renamed above to economy).
    # If neither exists, fail loudly rather than producing invalid processed rows.
    if "economy" not in df.columns:
        raise ValueError(
            "OECD DataFrame missing 'economy' column (expected 'LOCATION' in raw data). "
            f"Available columns: {list(df.columns)}. "
            "Cannot tag processed row without economy identifier."
        )

    # Add estimated_flag
    if "estimated_flag" not in df.columns:
        df["estimated_flag"] = False

    # Tag
    df = apply_industry_tags(df, config, source="oecd", segment="macro")

    # Validate
    df = validate_processed(df)

    return df


def normalize_lseg(
    raw_df: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    """
    Normalize raw LSEG company data.

    LSEG data is company-level (one row per company instrument), not country-level.
    The TRBC code mapping in config/industries/*.yaml drives segment assignment —
    each company is tagged to the AI segment (hardware, infrastructure, software, adoption)
    that its TRBC Industry code maps to. Companies with no mapping default to ai_software.

    The 'economy' column is set to 'GLOBAL' as a placeholder because LSEG company data
    spans multiple countries and the PROCESSED_SCHEMA requires a non-null economy value.
    This is a known limitation — see docs/ASSUMPTIONS.md section Data Source Assumptions.

    Parameters
    ----------
    raw_df : pd.DataFrame
        Validated raw LSEG DataFrame from fetch_company_financials().
    config : dict
        Industry config with lseg.trbc_codes for segment mapping.

    Returns
    -------
    pd.DataFrame
        Processed DataFrame conforming to PROCESSED_SCHEMA. Segment column populated
        from TRBC code mapping.
    """
    df = raw_df.copy()

    # Add year column if not present (LSEG data may need fiscal year extraction)
    if "year" not in df.columns:
        df["year"] = datetime.now().year  # placeholder — refine with fiscal year data

    # Add economy column if not present
    if "economy" not in df.columns:
        df["economy"] = "GLOBAL"  # company-level data is not country-specific by default

    # Add estimated_flag
    if "estimated_flag" not in df.columns:
        df["estimated_flag"] = False

    # Tag by TRBC segment
    df = tag_lseg_by_trbc(df, config)

    # Validate
    df = validate_processed(df)

    return df


def write_processed_parquet(
    df: pd.DataFrame,
    filename: str,
    source: str,
    industry_id: str = "ai",
    base_year: int = BASE_YEAR,
) -> Path:
    """
    Write processed DataFrame to data/processed/ as Parquet with provenance metadata.

    Metadata embedded in the Parquet file:
    - source: data source name
    - industry: industry identifier
    - base_year: deflation base year
    - fetched_at: UTC timestamp

    Parameters
    ----------
    df : pd.DataFrame
        Validated processed DataFrame
    filename : str
        Output filename (without directory), e.g. "world_bank_ai.parquet"
    source : str
        Data source for metadata
    industry_id : str
        Industry identifier for metadata
    base_year : int
        Deflation base year for metadata

    Returns
    -------
    Path to written file
    """
    output_dir = DATA_PROCESSED
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    table = pa.Table.from_pandas(df, preserve_index=False)
    existing_meta = table.schema.metadata or {}
    custom_meta = {
        b"source": source.encode(),
        b"industry": industry_id.encode(),
        b"base_year": str(base_year).encode(),
        b"fetched_at": datetime.now(tz=timezone.utc).isoformat().encode(),
    }
    table = table.replace_schema_metadata({**existing_meta, **custom_meta})
    pq.write_table(table, output_path, compression="snappy")

    return output_path
