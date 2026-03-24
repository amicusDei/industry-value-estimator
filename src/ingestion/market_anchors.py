"""
Analyst estimate registry loader and market anchor compilation module (DATA-09/DATA-11).

Loads the hand-curated YAML registry of published analyst market size estimates,
applies scope normalization using the scope_mapping_table from the industry config,
and aggregates to a per-(estimate_year, segment) DataFrame with p25/median/p75 statistics.

This module handles:
1. YAML registry loading (load_analyst_registry)
2. Scope normalization per firm (scope_normalize)
3. Full compilation pipeline (compile_market_anchors)
4. Schema validation against MARKET_ANCHOR_SCHEMA (validate_market_anchors)
5. Deflation to real_2020 USD (compile_and_write_market_anchors — DATA-11)
6. Gap interpolation for full 2017-2025 coverage (compile_and_write_market_anchors)
7. Parquet output with provenance metadata (compile_and_write_market_anchors)

Usage:
    # Nominal-only compilation (Plan 08-02 interface):
    df = compile_market_anchors("ai")
    df = validate_market_anchors(df)

    # Full pipeline with deflation, interpolation, and Parquet write (Plan 08-04):
    parquet_path = compile_and_write_market_anchors("ai")
"""
import glob
import yaml
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime, timezone
from pathlib import Path

from config.settings import DATA_RAW, DATA_PROCESSED, BASE_YEAR, load_industry_config
from src.processing.deflate import deflate_to_base_year
from src.processing.interpolate import interpolate_series
from src.processing.validate import MARKET_ANCHOR_SCHEMA, MARKET_ANCHOR_NOMINAL_SCHEMA


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
    return MARKET_ANCHOR_NOMINAL_SCHEMA.validate(df)


def _load_deflator_series(industry_id: str, base_year: int = BASE_YEAR) -> pd.Series:
    """
    Load the USA GDP deflator index from the raw World Bank data, returning a
    Series indexed by year.

    Falls back to a simple linear extrapolation for years beyond the raw data
    (e.g., 2025 if only available up to 2024), so that deflation can be applied
    to all years in the 2017-2025 market anchor target range.

    Parameters
    ----------
    industry_id : str
        Industry identifier (used to locate raw world_bank_{industry_id}_*.parquet).
    base_year : int
        The base year used for deflation (default: BASE_YEAR = 2020).

    Returns
    -------
    pd.Series
        GDP deflator index for USA, indexed by year. All years 2017-2025 will be
        populated (extrapolated if necessary). Index is of type int.

    Raises
    ------
    FileNotFoundError
        If no raw World Bank parquet file is found for the given industry_id.
    ValueError
        If the deflator data does not contain the base year.
    """
    raw_wb_dir = DATA_RAW / "world_bank"
    pattern = str(raw_wb_dir / f"world_bank_{industry_id}_*.parquet")
    files = sorted(glob.glob(pattern))

    if not files:
        raise FileNotFoundError(
            f"No raw World Bank parquet found at {pattern}. "
            "Run the World Bank ingestion step before compiling market anchors."
        )

    # Load the most recent raw file
    latest_file = files[-1]
    raw_df = pd.read_parquet(latest_file)

    # Extract USA rows — USA deflator is used as proxy for global USD deflation
    usa_rows = raw_df[raw_df["economy"] == "USA"][["year", "NY.GDP.DEFL.ZS"]].copy()
    usa_rows = usa_rows.dropna(subset=["NY.GDP.DEFL.ZS"])
    usa_rows["year"] = usa_rows["year"].astype(int)

    deflator_series = usa_rows.set_index("year")["NY.GDP.DEFL.ZS"].sort_index()

    # Validate that base year is present
    if base_year not in deflator_series.index:
        raise ValueError(
            f"USA GDP deflator missing for base year {base_year}. "
            f"Available years: {sorted(deflator_series.index.tolist())}."
        )

    # Extrapolate to cover 2017-2025 if necessary by extending linearly
    # using the last two known values as slope
    target_years = list(range(2017, 2026))
    missing_years = [y for y in target_years if y not in deflator_series.index]

    if missing_years:
        # Build a full reindex with NaN for missing years, then interpolate/extrapolate
        all_years = sorted(set(deflator_series.index.tolist() + missing_years))
        extended = deflator_series.reindex(all_years)

        # Use linear interpolation for interior gaps
        extended = extended.interpolate(method="index")

        # For years beyond the last known value, extrapolate linearly
        known_years = sorted(deflator_series.dropna().index.tolist())
        if known_years and max(missing_years) > max(known_years):
            if len(known_years) >= 2:
                slope = (
                    deflator_series.loc[known_years[-1]] - deflator_series.loc[known_years[-2]]
                )
                for y in sorted(missing_years):
                    if y > max(known_years):
                        extended.loc[y] = deflator_series.loc[known_years[-1]] + slope * (
                            y - known_years[-1]
                        )
            else:
                # Only one known year beyond target — hold flat
                for y in sorted(missing_years):
                    if y > max(known_years):
                        extended.loc[y] = deflator_series.loc[known_years[-1]]

        deflator_series = extended.dropna()

    return deflator_series


def compile_and_write_market_anchors(industry_id: str = "ai") -> Path:
    """
    Full market anchors pipeline: YAML -> compile -> deflate -> interpolate -> validate -> Parquet.

    Steps:
    1. Call compile_market_anchors(industry_id) to get nominal compiled DataFrame.
    2. Filter to estimate years 2017-2025 (the defensible historical + near-term range).
    3. Load USA GDP deflator from the latest raw World Bank parquet.
    4. For each nominal percentile column (p25, median, p75), apply deflate_to_base_year()
       to produce corresponding real_2020 columns.
    5. Interpolate gaps: for each segment, ensure all years 2017-2025 are present.
       Missing years are filled via linear interpolation with estimated_flag=True,
       n_sources=0, and source_list="".
    6. Validate against MARKET_ANCHOR_SCHEMA (requires both nominal and real_2020 columns).
    7. Write to data/processed/market_anchors_{industry_id}.parquet with provenance metadata.

    Parameters
    ----------
    industry_id : str
        Industry identifier (default: "ai").

    Returns
    -------
    Path
        Path to the written Parquet file.

    Raises
    ------
    FileNotFoundError
        If the raw World Bank data is not available for deflation.
    pandera.errors.SchemaError
        If the final DataFrame does not conform to MARKET_ANCHOR_SCHEMA.
    """
    # Step 1: Compile nominal market anchors
    nominal_df = compile_market_anchors(industry_id)

    # Step 2: Load the GDP deflator series (USA proxy for global USD)
    registry_path = DATA_RAW / "market_anchors" / f"{industry_id}_analyst_registry.yaml"
    deflator_series = _load_deflator_series(industry_id, base_year=BASE_YEAR)

    # Step 3: For each segment, build the full 2017-2025 series with interpolation
    target_years = list(range(2017, 2026))
    all_segments = nominal_df["segment"].unique().tolist()
    output_records = []

    for segment in sorted(all_segments):
        seg_df = nominal_df[nominal_df["segment"] == segment].copy()
        seg_df = seg_df[seg_df["estimate_year"].isin(target_years)].copy()
        seg_df = seg_df.set_index("estimate_year").sort_index()

        # Reindex to full year range, tracking which rows were originally missing
        full_index = pd.Index(target_years, name="estimate_year")
        originally_present = set(seg_df.index.tolist())
        seg_df = seg_df.reindex(full_index)

        # Mark newly added rows (will be interpolated)
        new_rows_mask = ~seg_df.index.isin(originally_present)

        # Interpolate the three nominal percentile columns
        # Uses linear interpolation for interior gaps, and forward/backward fill
        # for edge years (before first data point and after last data point).
        nominal_cols = [
            "p25_usd_billions_nominal",
            "median_usd_billions_nominal",
            "p75_usd_billions_nominal",
        ]
        for col in nominal_cols:
            if col in seg_df.columns:
                series = seg_df[col]
                # First fill interior gaps using linear interpolation
                filled, _ = interpolate_series(series)
                # Then fill leading NaNs (backward fill from first known value)
                filled = filled.bfill()
                # Then fill trailing NaNs (forward fill from last known value)
                filled = filled.ffill()
                seg_df[col] = filled

        # Set metadata for interpolated rows
        for year in seg_df.index[new_rows_mask]:
            seg_df.loc[year, "estimated_flag"] = True
            seg_df.loc[year, "n_sources"] = 0
            seg_df.loc[year, "source_list"] = ""

        seg_df["segment"] = segment

        # Cast types for interpolated metadata columns
        seg_df["estimated_flag"] = seg_df["estimated_flag"].astype(bool)
        seg_df["n_sources"] = seg_df["n_sources"].fillna(0).astype(int)
        seg_df["source_list"] = seg_df["source_list"].fillna("").astype(str)

        # Step 4: Deflate nominal -> real_2020
        # Build a deflator aligned to the segment's year index
        seg_years = seg_df.index
        deflator_aligned = pd.Series(
            [deflator_series.get(int(y), float("nan")) for y in seg_years],
            index=seg_years,
            name="gdp_deflator_index",
        )

        for nom_col, real_suffix in [
            ("p25_usd_billions_nominal", "p25_usd_billions_real_2020"),
            ("median_usd_billions_nominal", "median_usd_billions_real_2020"),
            ("p75_usd_billions_nominal", "p75_usd_billions_real_2020"),
        ]:
            if nom_col in seg_df.columns and not seg_df[nom_col].isna().all():
                nominal_s = seg_df[nom_col]
                real_s = deflate_to_base_year(
                    nominal_series=nominal_s,
                    deflator_series=deflator_aligned,
                    base_year=BASE_YEAR,
                    nominal_col_name=nom_col,
                )
                seg_df[real_suffix] = real_s

        seg_df = seg_df.reset_index()
        output_records.append(seg_df)

    if not output_records:
        raise ValueError(
            f"compile_and_write_market_anchors: no data found for industry_id={industry_id!r} "
            "in years 2017-2025."
        )

    result_df = pd.concat(output_records, ignore_index=True)

    # Ensure column dtypes are correct before validation
    result_df["estimate_year"] = result_df["estimate_year"].astype(int)
    result_df["n_sources"] = result_df["n_sources"].astype(int)
    result_df["estimated_flag"] = result_df["estimated_flag"].astype(bool)

    # Step 5: Validate against MARKET_ANCHOR_SCHEMA (includes real_2020 columns)
    validated_df = MARKET_ANCHOR_SCHEMA.validate(result_df)

    # Step 6: Write to data/processed/market_anchors_{industry_id}.parquet
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    output_path = DATA_PROCESSED / f"market_anchors_{industry_id}.parquet"

    table = pa.Table.from_pandas(validated_df, preserve_index=False)
    existing_meta = table.schema.metadata or {}
    custom_meta = {
        b"source": b"market_anchors",
        b"industry": industry_id.encode(),
        b"fetched_at": datetime.now(tz=timezone.utc).isoformat().encode(),
        b"registry_path": str(registry_path).encode(),
        b"reconciliation_method": b"scope_normalized_median",
    }
    table = table.replace_schema_metadata({**existing_meta, **custom_meta})
    pq.write_table(table, output_path, compression="snappy")

    return output_path
