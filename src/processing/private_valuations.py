"""
Private company valuation module (MODL-03).

Implements comparable EV/Revenue multiple valuation for major private AI companies.
No DCF — only comparable multiples per user decision.

Each company gets a low/mid/high EV estimate derived from:
    implied_ev = estimated_arr * comparable_multiple

Uncertainty is captured by the low/mid/high multiple range. Confidence tiers
(HIGH/MEDIUM/LOW) reflect data quality: HIGH = known post-money funding round
available for crosscheck; MEDIUM = press estimate + comparable; LOW = revenue
unknown, valuation inferred from market signals only.

Usage:
    from src.processing.private_valuations import compile_and_write_private_valuations

    parquet_path = compile_and_write_private_valuations("ai")

Exports:
    load_private_registry
    apply_comparable_multiples
    compile_and_write_private_valuations
"""
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from config.settings import DATA_PROCESSED, DATA_RAW
from src.processing.validate import PRIVATE_VALUATION_SCHEMA


def load_private_registry(registry_path: Path) -> pd.DataFrame:
    """
    Load the private company YAML registry and return a raw DataFrame.

    Reads the YAML file at registry_path, extracts the 'entries' list, and
    converts it to a pandas DataFrame with one row per company entry. All
    YAML fields become DataFrame columns; no transformation is applied.

    Parameters
    ----------
    registry_path : Path
        Absolute or relative path to the YAML registry file.
        Typically: DATA_RAW / "private_companies" / "ai_private_registry.yaml"

    Returns
    -------
    pd.DataFrame
        Raw DataFrame with one row per registry entry. All YAML fields are
        preserved as-is. No normalization or valuation computation is applied here.

    Raises
    ------
    FileNotFoundError
        If the registry file does not exist at the given path.
    KeyError
        If the YAML file does not contain a top-level 'entries' key.
    """
    if not Path(registry_path).exists():
        raise FileNotFoundError(
            f"Private company registry not found at: {registry_path}"
        )

    with open(registry_path, "r") as f:
        raw = yaml.safe_load(f)

    if "entries" not in raw:
        raise KeyError(
            f"Registry YAML at {registry_path} missing required top-level 'entries' key"
        )

    df = pd.DataFrame(raw["entries"])
    return df


def apply_comparable_multiples(
    estimated_arr: float,
    low_mult: float,
    mid_mult: float,
    high_mult: float,
) -> tuple[float, float, float]:
    """
    Compute implied enterprise value (EV) from ARR and comparable multiples.

    This is a pure function for recomputation when ARR estimates are updated.
    The result is:
        implied_ev_low  = estimated_arr * low_mult
        implied_ev_mid  = estimated_arr * mid_mult
        implied_ev_high = estimated_arr * high_mult

    Parameters
    ----------
    estimated_arr : float
        Estimated annual recurring revenue in USD billions.
    low_mult : float
        Low end of the EV/ARR multiple range from comparable peer group.
    mid_mult : float
        Mid (base case) EV/ARR multiple.
    high_mult : float
        High end of the EV/ARR multiple range.

    Returns
    -------
    tuple[float, float, float]
        (implied_ev_low, implied_ev_mid, implied_ev_high) in USD billions.
        Guaranteed to satisfy implied_ev_low <= implied_ev_mid <= implied_ev_high
        when low_mult <= mid_mult <= high_mult.
    """
    implied_ev_low = float(estimated_arr * low_mult)
    implied_ev_mid = float(estimated_arr * mid_mult)
    implied_ev_high = float(estimated_arr * high_mult)
    return (implied_ev_low, implied_ev_mid, implied_ev_high)


def compile_and_write_private_valuations(industry_id: str = "ai") -> Path:
    """
    Load private company YAML registry, validate, and write to Parquet.

    Pipeline steps:
    1. Load YAML registry from DATA_RAW / "private_companies" / f"{industry_id}_private_registry.yaml"
    2. Construct DataFrame with all PRIVATE_VALUATION_SCHEMA columns
    3. Validate with PRIVATE_VALUATION_SCHEMA (raises pandera.errors.SchemaError on failure)
    4. Assert implied_ev_low <= implied_ev_mid <= implied_ev_high for every row
    5. Write to DATA_PROCESSED / f"private_valuations_{industry_id}.parquet" with provenance metadata
    6. Return output Path

    Parameters
    ----------
    industry_id : str
        Industry identifier — used to locate the registry and name the output file.
        Default: "ai"

    Returns
    -------
    Path
        Absolute path to the written Parquet file.

    Raises
    ------
    FileNotFoundError
        If the YAML registry does not exist.
    pandera.errors.SchemaError
        If the compiled DataFrame fails PRIVATE_VALUATION_SCHEMA validation.
    ValueError
        If any row violates implied_ev_low <= implied_ev_mid <= implied_ev_high.
    """
    registry_path = DATA_RAW / "private_companies" / f"{industry_id}_private_registry.yaml"
    df = load_private_registry(registry_path)

    # Ensure all required schema columns are present and coerced to correct types
    schema_cols = [
        "company_name",
        "confidence_tier",
        "implied_ev_low",
        "implied_ev_mid",
        "implied_ev_high",
        "segment",
        "vintage_date",
        "comparable_mid_multiple",
    ]
    for col in schema_cols:
        if col not in df.columns:
            raise ValueError(
                f"Registry DataFrame missing required column '{col}'. "
                f"Available columns: {list(df.columns)}"
            )

    # Cast EV and multiple columns to float explicitly
    for float_col in ["implied_ev_low", "implied_ev_mid", "implied_ev_high", "comparable_mid_multiple"]:
        df[float_col] = df[float_col].astype(float)

    # Validate against PRIVATE_VALUATION_SCHEMA (raises SchemaError on failure)
    df = PRIVATE_VALUATION_SCHEMA.validate(df)

    # Assert EV ordering invariant for every row
    ev_ordering_low_mid = (df["implied_ev_low"] <= df["implied_ev_mid"]).all()
    ev_ordering_mid_high = (df["implied_ev_mid"] <= df["implied_ev_high"]).all()

    if not ev_ordering_low_mid:
        violators = df[df["implied_ev_low"] > df["implied_ev_mid"]]["company_name"].tolist()
        raise ValueError(
            f"EV ordering violation (implied_ev_low > implied_ev_mid) for: {violators}"
        )
    if not ev_ordering_mid_high:
        violators = df[df["implied_ev_mid"] > df["implied_ev_high"]]["company_name"].tolist()
        raise ValueError(
            f"EV ordering violation (implied_ev_mid > implied_ev_high) for: {violators}"
        )

    # Write to Parquet with provenance metadata
    output_path = DATA_PROCESSED / f"private_valuations_{industry_id}.parquet"
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    fetched_at = datetime.now(timezone.utc).isoformat()
    metadata = {
        b"source": b"private_registry",
        b"industry": industry_id.encode("utf-8"),
        b"fetched_at": fetched_at.encode("utf-8"),
        b"n_companies": str(len(df)).encode("utf-8"),
    }

    table = pa.Table.from_pandas(df)
    existing_metadata = table.schema.metadata or {}
    merged_metadata = {**existing_metadata, **metadata}
    table = table.replace_schema_metadata(merged_metadata)

    pq.write_table(table, output_path)

    return output_path
