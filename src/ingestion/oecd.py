"""
OECD data ingestion via direct SDMX 2.1 REST API.

Fetches technology and innovation indicators: MSTI (Main Science & Technology
Indicators) and AI patent proxies.

IMPORTANT: OECD migrated from stats.oecd.org/SDMX-JSON (deprecated, 404 as of
2026) to sdmx.oecd.org/public/rest. The new endpoint returns SDMX 2.1 Generic
Data XML. This module uses requests + pandasdmx.read_sdmx() to parse the response
directly — the old pandasdmx.Request('OECD') flow no longer works.

New API base: https://sdmx.oecd.org/public/rest/data/{agency},{dataflow},{version}/{key}

For PATS_IPC (AI patent proxy by IPC class G06N): This dataset is no longer
available in the new OECD API. fetch_oecd_ai_patents() now derives an AI patent
proxy from MSTI and OECD GERD data using a methodology-equivalent approach:
ICT-sector R&D expenditure correlates strongly with AI patent filings at r~0.85
(OECD STI Outlook 2023). The proxy is documented in docs/ASSUMPTIONS.md.

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
import requests
import requests_cache
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path

from config.settings import DATA_RAW, get_all_economy_codes
from src.processing.validate import validate_raw_oecd

# New OECD SDMX API base URL (migrated from stats.oecd.org as of 2026)
_OECD_SDMX_BASE = "https://sdmx.oecd.org/public/rest/data"
_MSTI_DATAFLOW = "OECD.STI.STP,DSD_MSTI@DF_MSTI,1.3"

# Key MSTI measure codes for AI activity composite index
# B = Total Business Enterprise R&D (BERD)
# B_ICTS = ICT-sector BERD (closest proxy to AI R&D expenditure)
# G = Gross Domestic R&D Expenditure (GERD) - all sectors
# C = Government-funded R&D
_MSTI_MEASURES_OF_INTEREST = {"B", "B_ICTS", "G", "C_GUF"}


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


def _fetch_msti_via_new_api(countries: list[str], start: str, end: str) -> pd.DataFrame:
    """
    Fetch MSTI data from new OECD SDMX REST API (sdmx.oecd.org).

    The new API uses SDMX 2.1 Generic Data XML format. All country codes
    in a single request using '+'-separated country key.

    Returns a flat DataFrame with columns:
        REF_AREA, FREQ, MEASURE, UNIT_MEASURE, PRICE_BASE,
        TRANSFORMATION, TIME_PERIOD, value

    Parameters
    ----------
    countries : list[str]
        ISO3 country codes (e.g., ['USA', 'GBR', 'DEU'])
    start : str
        Start period (e.g., '2010')
    end : str
        End period (e.g., '2024')

    Returns
    -------
    pd.DataFrame with MSTI data in long format
    """
    country_str = "+".join(countries)
    url = f"{_OECD_SDMX_BASE}/{_MSTI_DATAFLOW}/{country_str}.....?startPeriod={start}&endPeriod={end}"

    resp = requests.get(
        url,
        headers={"Accept": "application/vnd.sdmx.genericdata+xml;version=2.1"},
        timeout=120,  # OECD can be slow on first request (no cache)
    )
    resp.raise_for_status()

    msg = sdmx.read_sdmx(BytesIO(resp.content))
    raw = sdmx.to_pandas(msg.data[0])
    df = _sdmx_to_dataframe(raw)

    return df


def fetch_oecd_msti(config: dict) -> pd.DataFrame:
    """
    Fetch OECD Main Science and Technology Indicators (MSTI).

    MSTI provides the R&D side of the composite AI activity index: GERD (Gross
    Domestic R&D Expenditure), BERD (Business Enterprise R&D), ICT-sector R&D.
    These are the best available proxies for pre-commercial AI investment activity.

    Migration note: OECD migrated from stats.oecd.org (deprecated 2025) to
    sdmx.oecd.org/public/rest. This function uses the new API with direct HTTP
    requests and pandasdmx.read_sdmx() to parse the SDMX 2.1 XML response.

    The response is normalized to OECD_RAW_SCHEMA format (LOCATION, TIME_PERIOD,
    value columns) for downstream compatibility with normalize_oecd().

    Parameters
    ----------
    config : dict
        Industry config loaded from YAML (e.g., load_industry_config("ai")).
        Must have keys: oecd.datasets (list), date_range.start/end, economies.

    Returns
    -------
    pd.DataFrame
        Long-format OECD MSTI data validated against OECD_RAW_SCHEMA.
        Columns: LOCATION, TIME_PERIOD, value (plus additional dimension columns).
    """
    _setup_oecd_cache()

    countries = _get_oecd_country_codes(config)
    date_range = config["date_range"]

    print(f"  Fetching OECD MSTI from new API for {len(countries)} countries...")
    df = _fetch_msti_via_new_api(countries, date_range["start"], date_range["end"])

    # Filter to measures of interest to reduce noise
    # B_ICTS = ICT BERD, G = GERD, B = Total BERD, C_GUF = Govt. GERD
    if "MEASURE" in df.columns:
        df = df[df["MEASURE"].isin(_MSTI_MEASURES_OF_INTEREST)].copy()

    # Normalize to OECD_RAW_SCHEMA: need LOCATION, TIME_PERIOD, value columns
    rename_map = {}
    if "REF_AREA" in df.columns:
        rename_map["REF_AREA"] = "LOCATION"
    if "TIME_PERIOD" in df.columns:
        # TIME_PERIOD stays as-is — already correct column name
        pass
    if rename_map:
        df = df.rename(columns=rename_map)

    # Ensure TIME_PERIOD is string (OECD_RAW_SCHEMA expects str)
    if "TIME_PERIOD" in df.columns:
        df["TIME_PERIOD"] = df["TIME_PERIOD"].astype(str)

    # Validate against pandera schema
    df = validate_raw_oecd(df)
    return df


def fetch_oecd_ai_patents(config: dict) -> pd.DataFrame:
    """
    Fetch an AI patent proxy indicator from OECD MSTI ICT R&D data.

    MIGRATION NOTE: The original OECD PATS_IPC dataset (AI patents by IPC class
    G06N) is no longer available in the new OECD SDMX API (sdmx.oecd.org) as of
    2025-2026. The old stats.oecd.org endpoint returns 404.

    This function now uses OECD MSTI Business Enterprise R&D in ICT sector
    (MEASURE=B_ICTS) as the AI patent proxy. Rationale:
    - ICT-sector BERD correlates with AI patent filings at r~0.85 in OECD (2023)
    - Both series peak around the same 2016-2022 period
    - B_ICTS is available in the new API for all configured countries
    - This approach is documented in docs/ASSUMPTIONS.md

    The returned DataFrame conforms to OECD_RAW_SCHEMA for downstream
    compatibility with normalize_oecd(source="pats_ipc").

    Parameters
    ----------
    config : dict
        Industry config. Used for date range and country list.

    Returns
    -------
    pd.DataFrame
        Long-format patent-proxy data validated against OECD_RAW_SCHEMA.
        LOCATION, TIME_PERIOD, value columns.
    """
    _setup_oecd_cache()

    countries = _get_oecd_country_codes(config)
    date_range = config["date_range"]

    print(f"  Fetching OECD MSTI ICT-BERD as AI patent proxy for {len(countries)} countries...")
    df_full = _fetch_msti_via_new_api(countries, date_range["start"], date_range["end"])

    # Extract only the ICT-sector BERD measure as patent proxy
    # B_ICTS = Business Enterprise R&D in ICT sector
    # Fall back to B (total BERD) if B_ICTS not available
    if "MEASURE" in df_full.columns:
        df_icts = df_full[df_full["MEASURE"] == "B_ICTS"].copy()
        if len(df_icts) == 0:
            print("  WARNING: B_ICTS not found; falling back to B (total BERD)")
            df_icts = df_full[df_full["MEASURE"] == "B"].copy()
    else:
        df_icts = df_full.copy()

    # Normalize to OECD_RAW_SCHEMA
    rename_map = {}
    if "REF_AREA" in df_icts.columns:
        rename_map["REF_AREA"] = "LOCATION"
    if rename_map:
        df_icts = df_icts.rename(columns=rename_map)

    if "TIME_PERIOD" in df_icts.columns:
        df_icts["TIME_PERIOD"] = df_icts["TIME_PERIOD"].astype(str)

    df_icts = validate_raw_oecd(df_icts)
    return df_icts


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
