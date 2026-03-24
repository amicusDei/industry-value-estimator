"""
AI revenue attribution pipeline module (MODL-02).

Implements per-company AI revenue attribution for mixed-tech public companies.
Each company in the EDGAR corpus gets an attributed AI revenue figure with
documented source, method, and uncertainty range.

Purpose:
    Every mixed-tech public company gets an attributed AI revenue figure
    with documented source, method, and uncertainty range. Pure-play companies
    (NVIDIA, Palantir, C3.ai) receive pass-through attribution with ratio=1.0
    and attribution_method="direct_disclosure".

Output:
    data/processed/revenue_attribution_{industry_id}.parquet

    Parquet has pyarrow provenance metadata and validates against
    ATTRIBUTION_SCHEMA from src.processing.validate.

Usage:
    # Load raw registry as DataFrame:
    df = load_attribution_registry(Path("data/raw/attribution/ai_attribution_registry.yaml"))

    # Estimate AI revenue for a single company given total revenue:
    result = estimate_ai_revenue(100.0, "0000789019", config={}, year=2024)

    # Full pipeline: load YAML, validate, write Parquet, return Path:
    path = compile_and_write_attribution("ai")
"""
import yaml
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime, timezone
from pathlib import Path

from config.settings import DATA_RAW, DATA_PROCESSED
from src.processing.validate import ATTRIBUTION_SCHEMA


# CIKs of pure-play AI companies — 100% of revenue is AI, use ratio=1.0.
PURE_PLAY_CIKS = {
    "0001045810",  # NVIDIA
    "0001321655",  # Palantir
    "0001577552",  # C3.ai
}


def load_attribution_registry(registry_path: Path) -> pd.DataFrame:
    """
    Load the YAML AI revenue attribution registry and return a raw DataFrame.

    Reads the YAML file at registry_path, extracts the 'entries' list, and
    converts it to a pandas DataFrame with one row per company entry. All
    YAML fields become DataFrame columns; no transformation is applied.

    Follows the same pattern as load_analyst_registry() in market_anchors.py.

    Parameters
    ----------
    registry_path : Path
        Absolute or relative path to the YAML registry file.
        Typically: DATA_RAW / "attribution" / "ai_attribution_registry.yaml"

    Returns
    -------
    pd.DataFrame
        Raw DataFrame with one row per company. All YAML fields are preserved
        as-is. No normalization or validation is applied here.

    Raises
    ------
    FileNotFoundError
        If the registry file does not exist at the given path.
    KeyError
        If the YAML file does not contain a top-level 'entries' key.
    """
    registry_path = Path(registry_path)
    if not registry_path.exists():
        raise FileNotFoundError(
            f"Attribution registry YAML not found at {registry_path}"
        )

    with open(registry_path, "r") as f:
        raw = yaml.safe_load(f)

    if "entries" not in raw:
        raise KeyError(
            f"Attribution registry YAML at {registry_path} missing required "
            f"top-level 'entries' key"
        )

    df = pd.DataFrame(raw["entries"])
    return df


def estimate_ai_revenue(
    company_revenue: float,
    cik: str,
    attribution_config: dict,
    year: int,
) -> dict:
    """
    Estimate AI-attributable revenue for a single company by CIK.

    For pure-play companies (NVIDIA, Palantir, C3.ai), uses ratio=1.0 with
    attribution_method="direct_disclosure". For all other companies, the
    function is a lightweight lookup helper that can be extended with
    config-driven ratios.

    Parameters
    ----------
    company_revenue : float
        Total company revenue in USD billions for the given year.
    cik : str
        SEC EDGAR CIK for the company (zero-padded 10-digit string).
    attribution_config : dict
        Optional configuration dict with company-level attribution overrides.
        Keys: CIK strings. Values: dicts with ratio, method, source, etc.
        Pass empty dict {} to use pure-play defaults only.
    year : int
        Fiscal year for the estimate (2017-2026).

    Returns
    -------
    dict
        {
            "ai_revenue_usd": float,       # USD billions
            "attribution_method": str,      # direct_disclosure | management_commentary | analogue_ratio
            "ratio": float,                 # AI revenue / total revenue (0.0-1.0 or >1 not expected)
            "ratio_source": str,            # Provenance citation
            "uncertainty_low": float,       # Lower bound USD billions
            "uncertainty_high": float,      # Upper bound USD billions
            "vintage_date": str,            # ISO date string
        }
    """
    # Pure-play companies: pass-through with ratio=1.0
    if cik in PURE_PLAY_CIKS:
        ai_revenue = company_revenue
        uncertainty_low = company_revenue * 0.95
        uncertainty_high = company_revenue * 1.05
        return {
            "ai_revenue_usd": ai_revenue,
            "attribution_method": "direct_disclosure",
            "ratio": 1.0,
            "ratio_source": f"Pure-play AI company (CIK {cik}): 100% of revenue attributed to AI",
            "uncertainty_low": uncertainty_low,
            "uncertainty_high": uncertainty_high,
            "vintage_date": f"{year}-12-31",
        }

    # Config-driven overrides for other companies
    if cik in attribution_config:
        cfg = attribution_config[cik]
        ratio = cfg.get("ratio", 0.0)
        ai_revenue = company_revenue * ratio
        uncertainty_factor = cfg.get("uncertainty_factor", 0.2)
        return {
            "ai_revenue_usd": ai_revenue,
            "attribution_method": cfg.get("method", "analogue_ratio"),
            "ratio": ratio,
            "ratio_source": cfg.get("source", "Config-driven estimate"),
            "uncertainty_low": ai_revenue * (1.0 - uncertainty_factor),
            "uncertainty_high": ai_revenue * (1.0 + uncertainty_factor),
            "vintage_date": cfg.get("vintage_date", f"{year}-12-31"),
        }

    # Default fallback: analogue_ratio with unknown ratio
    return {
        "ai_revenue_usd": 0.0,
        "attribution_method": "analogue_ratio",
        "ratio": 0.0,
        "ratio_source": f"No attribution config for CIK {cik}",
        "uncertainty_low": 0.0,
        "uncertainty_high": 0.0,
        "vintage_date": f"{year}-12-31",
    }


def compile_and_write_attribution(industry_id: str = "ai") -> Path:
    """
    Load the attribution YAML registry, validate against ATTRIBUTION_SCHEMA,
    and write to data/processed/revenue_attribution_{industry_id}.parquet.

    Follows the same pattern as compile_and_write_market_anchors() in
    market_anchors.py: load YAML, build DataFrame, validate schema,
    write Parquet with pyarrow provenance metadata.

    Parameters
    ----------
    industry_id : str
        Industry identifier, used for filename namespacing. Default "ai".
        Looks up: DATA_RAW / "attribution" / "{industry_id}_attribution_registry.yaml"

    Returns
    -------
    Path
        Path to the written revenue_attribution_{industry_id}.parquet file.

    Raises
    ------
    FileNotFoundError
        If the attribution registry YAML does not exist.
    pandera.errors.SchemaError
        If the compiled DataFrame fails ATTRIBUTION_SCHEMA validation.
    """
    registry_path = DATA_RAW / "attribution" / f"{industry_id}_attribution_registry.yaml"

    # Load raw YAML registry
    df = load_attribution_registry(registry_path)

    # Coerce types to match schema expectations
    df["ai_revenue_usd_billions"] = df["ai_revenue_usd_billions"].astype(float)
    df["uncertainty_low"] = df["uncertainty_low"].astype(float)
    df["uncertainty_high"] = df["uncertainty_high"].astype(float)
    df["year"] = df["year"].astype(int)

    # Select only ATTRIBUTION_SCHEMA columns (drop extras like notes, estimated_flag)
    schema_cols = [
        "company_name",
        "cik",
        "value_chain_layer",
        "attribution_method",
        "ai_revenue_usd_billions",
        "uncertainty_low",
        "uncertainty_high",
        "vintage_date",
        "ratio_source",
        "segment",
        "year",
    ]
    # Keep additional columns that happen to be in the DataFrame
    df_out = df[[c for c in schema_cols if c in df.columns]].copy()

    # Validate against ATTRIBUTION_SCHEMA before writing
    ATTRIBUTION_SCHEMA.validate(df_out)

    # Write Parquet with pyarrow provenance metadata
    output_dir = DATA_PROCESSED
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"revenue_attribution_{industry_id}.parquet"

    table = pa.Table.from_pandas(df_out, preserve_index=False)
    existing_meta = table.schema.metadata or {}
    custom_meta = {
        b"source": b"attribution_registry",
        b"industry": industry_id.encode(),
        b"registry": str(registry_path).encode(),
        b"compiled_at": datetime.now(tz=timezone.utc).isoformat().encode(),
        b"schema_version": b"ATTRIBUTION_SCHEMA_v1",
        b"n_companies": str(len(df_out)).encode(),
    }
    table = table.replace_schema_metadata({**existing_meta, **custom_meta})
    pq.write_table(table, output_path, compression="snappy")

    return output_path
