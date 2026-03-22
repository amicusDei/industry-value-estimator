"""
World Bank data ingestion via wbgapi.

Fetches macro economic indicators (GDP, R&D expenditure, deflator, ICT indicators)
for all configured economies. The GDP deflator (NY.GDP.DEFL.ZS) is ALWAYS co-fetched
with any nominal series — this is non-negotiable for downstream deflation.

Usage:
    config = load_industry_config("ai")
    df = fetch_world_bank_indicators(config)
    save_raw_world_bank(df)
"""
import wbgapi as wb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime, timezone
from pathlib import Path

from config.settings import DATA_RAW, DEFLATOR_INDICATOR, load_industry_config, get_all_economy_codes
from src.processing.validate import validate_raw_world_bank


def fetch_world_bank_indicators(config: dict) -> pd.DataFrame:
    """
    Fetch all World Bank indicators specified in the industry config.

    The wbgapi library returns data in a MultiIndex format (economy × series as rows,
    years as columns). This function reshapes that to wide format: rows = (economy, year),
    columns = indicator codes. This wide format is required for downstream deflation —
    each row must have both the nominal value column AND the deflator column side-by-side.

    Always includes NY.GDP.DEFL.ZS (GDP deflator) regardless of what is in the config,
    because deflation is non-negotiable for all monetary series. This is enforced here
    rather than in normalize.py because it is a data correctness requirement, not a
    processing choice.

    Validates against WORLD_BANK_RAW_SCHEMA (pandera) before returning. If the schema
    fails, the pipeline raises SchemaError immediately rather than writing corrupt data.

    Parameters
    ----------
    config : dict
        Industry config loaded from YAML (e.g., load_industry_config("ai")).
        Must have keys: world_bank.indicators (list of {code}), date_range.start/end.

    Returns
    -------
    pd.DataFrame
        Wide-format DataFrame with columns: economy (str), year (int), plus one column
        per World Bank indicator code. Validated against WORLD_BANK_RAW_SCHEMA.
    """
    indicator_codes = [ind["code"] for ind in config["world_bank"]["indicators"]]

    # Non-negotiable: always include the GDP deflator
    if DEFLATOR_INDICATOR not in indicator_codes:
        indicator_codes.append(DEFLATOR_INDICATOR)

    economies = get_all_economy_codes(config)
    date_range = config["date_range"]
    start_year = int(date_range["start"])
    end_year = int(date_range["end"])

    # wbgapi returns MultiIndex DataFrame — need to reshape to wide format
    df = wb.data.DataFrame(
        series=indicator_codes,
        economy=economies,
        time=range(start_year, end_year + 1),
        labels=False,
    )

    # Reshape: wbgapi returns years as columns, series as MultiIndex rows
    # Convert to long format with economy, year, and one column per indicator
    df = df.reset_index()
    df = df.melt(id_vars=["economy", "series"], var_name="year", value_name="value")
    df["year"] = df["year"].str.replace("YR", "").astype(int)
    df = df.pivot_table(index=["economy", "year"], columns="series", values="value").reset_index()
    df.columns.name = None

    # Validate against pandera schema
    df = validate_raw_world_bank(df)

    return df


def save_raw_world_bank(df: pd.DataFrame, industry_id: str = "ai") -> Path:
    """
    Write raw World Bank data to data/raw/world_bank/ as immutable Parquet.

    Provenance metadata (source, industry, fetch timestamp) is embedded directly
    in the Parquet file schema metadata using pyarrow. This satisfies DATA-07
    (data source attribution) without requiring a separate sidecar file. The
    metadata travels with the data even if the file is copied to a different location.

    Raw data is NEVER modified after writing. If a re-fetch is needed, write a new
    timestamped file — the old one stays on disk as an audit record.

    Parameters
    ----------
    df : pd.DataFrame
        Validated World Bank DataFrame from fetch_world_bank_indicators().
    industry_id : str
        Industry identifier for filename namespacing (default: "ai").

    Returns
    -------
    Path
        Path to the written Parquet file.
    """
    output_dir = DATA_RAW / "world_bank"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    output_path = output_dir / f"world_bank_{industry_id}_{timestamp}.parquet"

    table = pa.Table.from_pandas(df, preserve_index=False)
    existing_meta = table.schema.metadata or {}
    custom_meta = {
        b"source": b"world_bank",
        b"industry": industry_id.encode(),
        b"fetched_at": datetime.now(tz=timezone.utc).isoformat().encode(),
    }
    table = table.replace_schema_metadata({**existing_meta, **custom_meta})
    pq.write_table(table, output_path, compression="snappy")

    return output_path
