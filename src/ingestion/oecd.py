"""
OECD data ingestion via pandasdmx (SDMX 2.1).

Fetches technology and innovation indicators: MSTI (Main Science & Technology
Indicators), PATS_IPC (Patents by IPC class, filtered to G06N for AI), and
ANBERD (Business R&D by industry).

OECD queries are SLOW (30s+). All HTTP traffic goes through requests-cache
with a 30-day SQLite TTL to avoid redundant network calls.

Usage:
    config = load_industry_config("ai")
    msti_df = fetch_oecd_msti(config)
    patents_df = fetch_oecd_ai_patents(config)
"""
import pandasdmx as sdmx
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests_cache
from datetime import datetime, timezone
from pathlib import Path

from config.settings import DATA_RAW, get_all_economy_codes
from src.processing.validate import validate_raw_oecd


def _sdmx_to_dataframe(raw) -> pd.DataFrame:
    """
    Convert pandasdmx output to a flat DataFrame.

    pandasdmx.to_pandas() can return either:
    - pd.Series with MultiIndex (dimensions as index levels, series name = value)
    - pd.DataFrame (less common)

    In both cases, we reset the index to get a flat DataFrame with all
    dimensions and the value column as regular columns.
    """
    if isinstance(raw, pd.Series):
        df = raw.reset_index()
        # Ensure value column is named "value"
        if raw.name and raw.name != 0:
            df = df.rename(columns={raw.name: "value"})
        elif 0 in df.columns:
            df = df.rename(columns={0: "value"})
    else:
        # DataFrame case — reset_index safely
        df = raw.reset_index()
    return df


def _setup_oecd_cache() -> None:
    """Install requests-cache with 30-day SQLite TTL for OECD SDMX queries."""
    cache_dir = DATA_RAW / "oecd"
    cache_dir.mkdir(parents=True, exist_ok=True)
    requests_cache.install_cache(
        str(cache_dir / ".cache"),
        backend="sqlite",
        expire_after=30 * 24 * 3600,  # 30 days — OECD updates annually/quarterly
    )


def _get_oecd_country_codes(config: dict) -> list[str]:
    """
    Extract OECD-compatible country codes from config.
    OECD uses ISO3 codes same as World Bank for major economies.
    """
    return get_all_economy_codes(config)


def fetch_oecd_msti(config: dict) -> pd.DataFrame:
    """
    Fetch OECD Main Science and Technology Indicators (MSTI).

    Variables include GERD (Gross Domestic R&D Expenditure), researchers count,
    and R&D intensity by performing sector.

    NOTE: OECD SDMX dimension keys must be verified against live metadata.
    The first run should call oecd.datastructure('MSTI') to inspect available
    dimensions before finalizing the query. If dimension names differ from
    expected (e.g., 'COU' instead of 'LOCATION'), adjust the key dict.
    """
    _setup_oecd_cache()

    countries = _get_oecd_country_codes(config)
    date_range = config["date_range"]

    oecd = sdmx.Request("OECD")

    # First: verify available dataflows (log for debugging)
    try:
        data_msg = oecd.data(
            "MSTI",
            key={"LOCATION": "+".join(countries)},
            params={
                "startPeriod": date_range["start"],
                "endPeriod": date_range["end"],
            },
        )
        raw = sdmx.to_pandas(data_msg.data[0], datetime="TIME_PERIOD")
        df = _sdmx_to_dataframe(raw)
    except Exception:
        # Dimension key mismatch — try alternative key name
        # OECD sometimes uses 'COU' or 'REF_AREA' instead of 'LOCATION'
        data_msg = oecd.data(
            "MSTI",
            key={"COU": "+".join(countries)},
            params={
                "startPeriod": date_range["start"],
                "endPeriod": date_range["end"],
            },
        )
        raw = sdmx.to_pandas(data_msg.data[0], datetime="TIME_PERIOD")
        df = _sdmx_to_dataframe(raw)
        # Rename to standard column names
        if "COU" in df.columns:
            df = df.rename(columns={"COU": "LOCATION"})

    # Validate against pandera schema
    df = validate_raw_oecd(df)
    return df


def fetch_oecd_ai_patents(config: dict) -> pd.DataFrame:
    """
    Fetch OECD patent filings filtered to IPC class G06N (AI/computing methods).

    IPC G06N: 'Computing; Calculating or Counting — methods based on specific
    computational models' — the standard proxy for AI patent activity in
    OECD methodology papers.
    """
    _setup_oecd_cache()

    countries = _get_oecd_country_codes(config)
    date_range = config["date_range"]

    # Get IPC filter from config (default G06N)
    pats_config = next(
        (d for d in config["oecd"]["datasets"] if d["id"] == "PATS_IPC"),
        None,
    )
    ipc_filter = pats_config.get("ipc_filter", "G06N") if pats_config else "G06N"

    oecd = sdmx.Request("OECD")
    try:
        data_msg = oecd.data(
            "PATS_IPC",
            key={"IPC": ipc_filter, "LOCATION": "+".join(countries)},
            params={
                "startPeriod": date_range["start"],
                "endPeriod": date_range["end"],
            },
        )
        raw = sdmx.to_pandas(data_msg.data[0], datetime="TIME_PERIOD")
        df = _sdmx_to_dataframe(raw)
    except Exception:
        # Fallback for alternative dimension key names
        data_msg = oecd.data(
            "PATS_IPC",
            key={"IPC": ipc_filter, "COU": "+".join(countries)},
            params={
                "startPeriod": date_range["start"],
                "endPeriod": date_range["end"],
            },
        )
        raw = sdmx.to_pandas(data_msg.data[0], datetime="TIME_PERIOD")
        df = _sdmx_to_dataframe(raw)
        if "COU" in df.columns:
            df = df.rename(columns={"COU": "LOCATION"})

    df = validate_raw_oecd(df)
    return df


def save_raw_oecd(df: pd.DataFrame, dataset_name: str, industry_id: str = "ai") -> Path:
    """
    Write raw OECD data to data/raw/oecd/ as immutable Parquet.

    Parameters
    ----------
    df : pd.DataFrame
        Validated OECD DataFrame
    dataset_name : str
        OECD dataset name (e.g., "msti", "pats_ipc") — used in filename
    industry_id : str
        Industry identifier for file namespacing
    """
    output_dir = DATA_RAW / "oecd"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    output_path = output_dir / f"oecd_{dataset_name}_{industry_id}_{timestamp}.parquet"

    table = pa.Table.from_pandas(df, preserve_index=False)
    existing_meta = table.schema.metadata or {}
    custom_meta = {
        b"source": b"oecd",
        b"dataset": dataset_name.encode(),
        b"industry": industry_id.encode(),
        b"fetched_at": datetime.now(tz=timezone.utc).isoformat().encode(),
    }
    table = table.replace_schema_metadata({**existing_meta, **custom_meta})
    pq.write_table(table, output_path, compression="snappy")

    return output_path
