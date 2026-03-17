"""
LSEG Workspace data ingestion via lseg-data (Desktop Session).

Fetches company-level financial data for AI-related companies identified by
TRBC (Thomson Reuters Business Classification) sector codes. TRBC is the
methodological anchor — it makes the company selection reproducible and defensible.

REQUIRES: LSEG Workspace desktop application running on the same machine.
Authentication flows through the open Workspace app — no separate API key needed.
Config file: lseg-data.config.json (gitignored, copy from .example)

Usage:
    config = load_industry_config("ai")
    open_lseg_session()
    companies_df = fetch_lseg_companies(config)
    financials_df = fetch_company_financials(companies_df, config)
    save_raw_lseg(financials_df)
    close_lseg_session()
"""
import lseg.data as ld
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime, timezone
from pathlib import Path

from config.settings import DATA_RAW, load_industry_config
from src.processing.validate import validate_raw_lseg


def open_lseg_session() -> None:
    """
    Open a Desktop Session to LSEG Workspace.

    Requires:
    - LSEG Workspace Desktop App running on this machine
    - lseg-data.config.json in project root or ~/.config/lseg/
      (copy from lseg-data.config.json.example)
    """
    ld.open_session()


def close_lseg_session() -> None:
    """Close the LSEG Workspace session."""
    ld.close_session()


def fetch_lseg_companies(config: dict) -> pd.DataFrame:
    """
    Fetch all companies classified under AI-related TRBC sector codes.

    Builds a SCREEN() expression from the TRBC codes in config/industries/ai.yaml.
    The first run also serves as TRBC code verification — if the company universe
    returns fewer than 50 companies, the codes may need adjustment.

    Returns DataFrame with columns: Instrument (RIC), plus requested fields.
    """
    trbc_entries = config["lseg"]["trbc_codes"]
    trbc_codes = [entry["code"] for entry in trbc_entries]

    # Build screening expression from config
    screening_parts = [f'TR.TRBCActivityCode=="{code}"' for code in trbc_codes]
    screening_expr = " OR ".join(screening_parts)

    # Discovery fields: always include TRBC activity info for verification
    discovery_fields = [
        "TR.CommonName",
        "TR.TRBCActivity",
        "TR.TRBCActivityCode",
    ]

    df = ld.get_data(
        universe=f"SCREEN(U(IN(Equity(active,public,primary))),{screening_expr})",
        fields=discovery_fields,
    )

    # Validate against pandera schema
    df = validate_raw_lseg(df)

    return df


def fetch_company_financials(
    companies_df: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    """
    Fetch annual financial data for the AI company universe.

    Parameters
    ----------
    companies_df : pd.DataFrame
        Output of fetch_lseg_companies — must have 'Instrument' column with RIC codes
    config : dict
        Industry config with lseg.fields list

    Returns DataFrame with financial data indexed by Instrument.
    """
    rics = companies_df["Instrument"].tolist()
    fields = config["lseg"]["fields"]

    # Fetch in batches of 100 to avoid API limits
    batch_size = 100
    all_dfs = []
    for i in range(0, len(rics), batch_size):
        batch_rics = rics[i : i + batch_size]
        batch_df = ld.get_data(universe=batch_rics, fields=fields)
        all_dfs.append(batch_df)

    if all_dfs:
        result = pd.concat(all_dfs, ignore_index=True)
    else:
        result = pd.DataFrame(columns=["Instrument"] + fields)

    result = validate_raw_lseg(result)
    return result


def save_raw_lseg(df: pd.DataFrame, industry_id: str = "ai") -> Path:
    """
    Write raw LSEG data to data/raw/lseg/ as immutable Parquet.

    Includes provenance metadata (source, fetch timestamp, industry).
    Raw data is NEVER modified after writing.
    """
    output_dir = DATA_RAW / "lseg"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    output_path = output_dir / f"lseg_{industry_id}_{timestamp}.parquet"

    table = pa.Table.from_pandas(df, preserve_index=False)
    existing_meta = table.schema.metadata or {}
    custom_meta = {
        b"source": b"lseg",
        b"industry": industry_id.encode(),
        b"fetched_at": datetime.now(tz=timezone.utc).isoformat().encode(),
    }
    table = table.replace_schema_metadata({**existing_meta, **custom_meta})
    pq.write_table(table, output_path, compression="snappy")

    return output_path
