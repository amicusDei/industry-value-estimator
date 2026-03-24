"""
Analyst estimate registry loader and market anchor compilation module (DATA-09).

Loads the hand-curated YAML registry of published analyst market size estimates,
applies scope normalization using the scope_mapping_table from the industry config,
and aggregates to a per-(estimate_year, segment) DataFrame with p25/median/p75 statistics.

This module handles:
1. YAML registry loading (load_analyst_registry)
2. Scope normalization per firm (scope_normalize)
3. Full compilation pipeline (compile_market_anchors)
4. Schema validation against MARKET_ANCHOR_SCHEMA (validate_market_anchors)

NOTE: Deflation to real_2020 and gap interpolation are handled in Plan 08-04.
This module produces a nominal USD compiled DataFrame only.

Usage:
    df = compile_market_anchors("ai")
    df = validate_market_anchors(df)
"""
import yaml
import numpy as np
import pandas as pd
from pathlib import Path

from config.settings import DATA_RAW, load_industry_config
from src.processing.validate import MARKET_ANCHOR_SCHEMA


def load_analyst_registry(registry_path: Path) -> pd.DataFrame:
    """
    Load the YAML analyst estimate registry and return a raw DataFrame.

    Reads the YAML file at registry_path, extracts the 'entries' list, and
    converts it to a pandas DataFrame with one row per estimate entry. All
    YAML fields become DataFrame columns; no transformation is applied.

    Parameters
    ----------
    registry_path : Path
        Absolute or relative path to the YAML registry file.
        Typically: DATA_RAW / "market_anchors" / "{industry_id}_analyst_registry.yaml"

    Returns
    -------
    pd.DataFrame
        Raw DataFrame with one row per registry entry. All YAML fields are
        preserved as-is. No normalization or scope adjustment is applied here.

    Raises
    ------
    FileNotFoundError
        If the registry file does not exist at the given path.
    KeyError
        If the YAML file does not contain a top-level 'entries' key.
    """
    with open(registry_path, "r") as f:
        raw = yaml.safe_load(f)

    if "entries" not in raw:
        raise KeyError(f"Registry YAML at {registry_path} missing required top-level 'entries' key")

    df = pd.DataFrame(raw["entries"])
    return df


def scope_normalize(as_published_usd_billions: float, scope_coefficient: float) -> float:
    """
    Normalize a published estimate to our market scope by multiplying by the scope coefficient.

    The scope_coefficient is defined in config/industries/ai.yaml scope_mapping_table
    as the ratio of our scope to the analyst firm's scope:
        scope_coefficient = our_scope / their_scope

    A coefficient of 1.0 means the firm's definition closely matches ours (IDC).
    A coefficient of 0.18 means we must multiply by 0.18 to extract our portion (Gartner).
    A coefficient > 1.0 means the firm's definition is narrower than ours and we upscale (Grand View).

    Parameters
    ----------
    as_published_usd_billions : float
        The nominal USD billions figure as published by the analyst firm.
    scope_coefficient : float
        Multiplier that converts the firm's scope to our scope definition.

    Returns
    -------
    float
        Scope-normalized estimate in USD billions, rounded to 6 decimal places.
    """
    return round(as_published_usd_billions * scope_coefficient, 6)


def compile_market_anchors(industry_id: str = "ai") -> pd.DataFrame:
    """
    Full analyst estimate compilation pipeline.

    Steps:
    1. Load YAML registry from data/raw/market_anchors/{industry_id}_analyst_registry.yaml
    2. Load scope_mapping_table from config/industries/{industry_id}.yaml
    3. Join scope_coefficient from mapping table to each registry entry by source_firm
    4. Compute scope_normalized_usd_billions = as_published_usd_billions * scope_coefficient
    5. Group by (estimate_year, segment) and compute p25, median, p75 of scope-normalized values
    6. Return compiled DataFrame (deflation to real_2020 is Plan 08-04 responsibility)

    Parameters
    ----------
    industry_id : str
        Industry identifier for file path lookups (default: "ai").
        Used to locate: data/raw/market_anchors/{industry_id}_analyst_registry.yaml
        and config/industries/{industry_id}.yaml

    Returns
    -------
    pd.DataFrame
        Compiled DataFrame with columns:
        - estimate_year (int): Year the estimate refers to
        - segment (str): Market segment (total, ai_hardware, ai_infrastructure, ai_software, ai_adoption)
        - p25_usd_billions_nominal (float): 25th percentile of scope-normalized estimates
        - median_usd_billions_nominal (float): Median of scope-normalized estimates
        - p75_usd_billions_nominal (float): 75th percentile of scope-normalized estimates
        - n_sources (int): Number of analyst estimates contributing to this (year, segment) group
        - source_list (str): Comma-separated list of contributing source_firm names
        - estimated_flag (bool): False for actual estimates; True for forecasts (estimate_year > publication_year)
    """
    # Step 1: Load YAML registry
    registry_path = DATA_RAW / "market_anchors" / f"{industry_id}_analyst_registry.yaml"
    raw_df = load_analyst_registry(registry_path)

    # Step 2: Load scope_mapping_table from industry config
    config = load_industry_config(industry_id)
    scope_table = config.get("scope_mapping_table", [])

    # Build firm -> scope_coefficient lookup dict
    scope_map: dict[str, float] = {
        entry["firm"]: entry["scope_coefficient"]
        for entry in scope_table
    }

    # Step 3: Join scope_coefficient to each registry entry by source_firm
    # Firms not in the scope table default to 1.0 (no normalization applied)
    raw_df["scope_coefficient"] = raw_df["source_firm"].map(scope_map).fillna(1.0)

    # Step 4: Compute scope-normalized estimate
    raw_df["scope_normalized_usd_billions"] = (
        raw_df["as_published_usd_billions"] * raw_df["scope_coefficient"]
    )

    # Step 5: Determine estimated_flag — True if estimate_year > publication_year (forward forecast)
    raw_df["estimated_flag"] = raw_df["estimate_year"] > raw_df["publication_year"]

    # Step 6: Group by (estimate_year, segment) and compute percentile statistics
    records = []
    for (estimate_year, segment), group in raw_df.groupby(["estimate_year", "segment"], sort=True):
        values = group["scope_normalized_usd_billions"].values.astype(float)
        p25, median, p75 = np.percentile(values, [25, 50, 75], method="linear")

        # estimated_flag is True if ANY entry in the group is a forward forecast
        estimated_flag = bool(group["estimated_flag"].any())

        source_list = ", ".join(sorted(group["source_firm"].unique()))

        records.append({
            "estimate_year": int(estimate_year),
            "segment": str(segment),
            "p25_usd_billions_nominal": float(p25),
            "median_usd_billions_nominal": float(median),
            "p75_usd_billions_nominal": float(p75),
            "n_sources": len(values),
            "source_list": source_list,
            "estimated_flag": estimated_flag,
        })

    compiled_df = pd.DataFrame(records)
    return compiled_df


def validate_market_anchors(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate the compiled market anchors DataFrame against MARKET_ANCHOR_SCHEMA.

    Raises pandera.errors.SchemaError if the DataFrame does not conform to
    the expected schema (columns, types, value ranges).

    Parameters
    ----------
    df : pd.DataFrame
        Compiled market anchors DataFrame from compile_market_anchors().

    Returns
    -------
    pd.DataFrame
        The validated (and optionally coerced) DataFrame.

    Raises
    ------
    pandera.errors.SchemaError
        If any column is missing, has wrong type, or violates value constraints.
    """
    return MARKET_ANCHOR_SCHEMA.validate(df)
