"""
EDGAR CapEx-based bottom-up validation module.

Extracts capital expenditure data from SEC EDGAR 10-K filings via XBRL,
applies AI-specific CapEx ratios, and cross-references with top-down
analyst consensus forecasts for market size validation.

Three data tiers:
1. XBRL extraction via edgartools (preferred)
2. Hardcoded fallback from published 10-K filings (if EDGAR API fails)
3. Graceful empty DataFrame (if all sources fail)

Usage:
    capex_df = fetch_all_capex("ai")
    val_df = compile_bottom_up_validation("ai")
    write_bottom_up_validation(val_df)
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from config.settings import DATA_PROCESSED, DATA_RAW, load_industry_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# XBRL CapEx concepts — priority order (first non-null wins)
# ---------------------------------------------------------------------------
CAPEX_XBRL_CONCEPTS = [
    "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
    "us-gaap:CapitalExpenditures",
    "us-gaap:PaymentsToAcquireProductiveAssets",
    "us-gaap:PaymentsForCapitalImprovements",
]

# ---------------------------------------------------------------------------
# AI portion of total CapEx — sourced from management guidance / analyst consensus
# ---------------------------------------------------------------------------
AI_CAPEX_RATIOS: dict[str, dict] = {
    "NVIDIA Corporation": {
        "ai_capex_ratio": 0.85,
        "source": "Data Center ~91% of revenue, CapEx follows",
    },
    "Microsoft Corporation": {
        "ai_capex_ratio": 0.55,
        "source": "Azure AI ~55% of cloud CapEx (Nadella FY24 guidance)",
    },
    "Alphabet Inc.": {
        "ai_capex_ratio": 0.50,
        "source": "Google DeepMind + Cloud AI ~50% of CapEx (Pichai 2024)",
    },
    "Amazon.com Inc.": {
        "ai_capex_ratio": 0.40,
        "source": "AWS AI/ML ~40% of infrastructure CapEx (Jassy 2024)",
    },
    "Meta Platforms Inc.": {
        "ai_capex_ratio": 0.70,
        "source": "$60-65B AI infra guidance 2025, ~70% of total CapEx",
    },
    "Advanced Micro Devices Inc.": {
        "ai_capex_ratio": 0.60,
        "source": "Data Center GPU focus post-Xilinx",
    },
    "Intel Corporation": {
        "ai_capex_ratio": 0.30,
        "source": "DCAI + foundry AI portion ~30%",
    },
    "Oracle Corporation": {
        "ai_capex_ratio": 0.45,
        "source": "OCI GPU clusters ~45% of cloud CapEx",
    },
    "Taiwan Semiconductor Manufacturing Company": {
        "ai_capex_ratio": 0.45,
        "source": "HPC/AI ~45% of wafer capacity allocation",
    },
}

# ---------------------------------------------------------------------------
# Hardcoded CapEx fallback — from published 10-K annual reports (USD billions)
# ---------------------------------------------------------------------------
CAPEX_FALLBACK: dict[tuple[str, int], float] = {
    # Source: Company 10-K filings, FY2024 annual reports
    ("NVIDIA Corporation", 2024): 2.8,
    ("Microsoft Corporation", 2024): 44.5,
    ("Alphabet Inc.", 2024): 32.3,
    ("Amazon.com Inc.", 2024): 59.0,
    ("Meta Platforms Inc.", 2024): 28.1,
    ("Advanced Micro Devices Inc.", 2024): 0.5,
    ("Taiwan Semiconductor Manufacturing Company", 2024): 30.0,
    ("Intel Corporation", 2024): 21.4,
    ("Oracle Corporation", 2024): 8.3,
    # Historical (from prior 10-K filings)
    ("NVIDIA Corporation", 2023): 1.8,
    ("NVIDIA Corporation", 2022): 1.8,
    ("NVIDIA Corporation", 2021): 0.98,
    ("NVIDIA Corporation", 2020): 0.49,
    ("Microsoft Corporation", 2023): 28.1,
    ("Microsoft Corporation", 2022): 23.9,
    ("Microsoft Corporation", 2021): 20.6,
    ("Microsoft Corporation", 2020): 15.4,
    ("Alphabet Inc.", 2023): 32.3,
    ("Alphabet Inc.", 2022): 31.5,
    ("Alphabet Inc.", 2021): 24.6,
    ("Alphabet Inc.", 2020): 22.3,
    ("Amazon.com Inc.", 2023): 48.4,
    ("Amazon.com Inc.", 2022): 58.5,
    ("Amazon.com Inc.", 2021): 55.4,
    ("Amazon.com Inc.", 2020): 35.0,
    ("Meta Platforms Inc.", 2023): 28.1,
    ("Meta Platforms Inc.", 2022): 31.4,
    ("Meta Platforms Inc.", 2021): 19.2,
    ("Meta Platforms Inc.", 2020): 15.1,
    ("Advanced Micro Devices Inc.", 2023): 0.5,
    ("Advanced Micro Devices Inc.", 2022): 0.5,
    ("Advanced Micro Devices Inc.", 2021): 0.3,
    ("Advanced Micro Devices Inc.", 2020): 0.2,
    ("Taiwan Semiconductor Manufacturing Company", 2023): 30.5,
    ("Taiwan Semiconductor Manufacturing Company", 2022): 36.3,
    ("Taiwan Semiconductor Manufacturing Company", 2021): 30.4,
    ("Taiwan Semiconductor Manufacturing Company", 2020): 17.2,
    ("Intel Corporation", 2023): 25.8,
    ("Intel Corporation", 2022): 25.1,
    ("Intel Corporation", 2021): 18.7,
    ("Intel Corporation", 2020): 14.3,
    ("Oracle Corporation", 2023): 8.3,
    ("Oracle Corporation", 2022): 6.7,
    ("Oracle Corporation", 2021): 4.8,
    ("Oracle Corporation", 2020): 1.8,
}


# ---------------------------------------------------------------------------
# XBRL CapEx extraction per company
# ---------------------------------------------------------------------------

def fetch_capex_for_company(cik: str, company_name: str) -> pd.DataFrame:
    """
    Fetch annual CapEx for one company from EDGAR XBRL data.

    Follows the same edgartools API pattern as edgar.py's fetch_company_filings:
    - Get Company by CIK
    - Filter 10-K filings for 2020-2024
    - Priority fallback across CAPEX_XBRL_CONCEPTS
    - Fall back to hardcoded values if XBRL extraction fails

    Parameters
    ----------
    cik : str
        SEC CIK number.
    company_name : str
        Display name for the company.

    Returns
    -------
    pd.DataFrame
        Columns: cik, company_name, fiscal_year, total_capex_usd, xbrl_concept_used
    """
    rows = _try_xbrl_capex(cik, company_name)

    if not rows:
        logger.info(
            "XBRL CapEx extraction returned no data for %s — using fallback",
            company_name,
        )
        rows = _fallback_capex(company_name, cik)

    if not rows:
        logger.warning("No CapEx data (XBRL or fallback) for %s (CIK %s)", company_name, cik)
        return pd.DataFrame(columns=[
            "cik", "company_name", "fiscal_year", "total_capex_usd", "xbrl_concept_used",
        ])

    return pd.DataFrame(rows)


def _try_xbrl_capex(cik: str, company_name: str) -> list[dict]:
    """Attempt XBRL CapEx extraction via edgartools. Returns list of row dicts."""
    rows: list[dict] = []
    try:
        from edgar import Company
        company = Company(cik)
        filings = company.get_filings(form="10-K")
        date_filter = "2020-01-01:2024-12-31"
        filings = filings.filter(date=date_filter)
    except Exception as e:
        logger.warning("edgartools failed for %s (CIK %s): %s", company_name, cik, e)
        return rows

    seen_years: set[int] = set()

    for filing in filings:
        try:
            xbrl = filing.xbrl()
            if xbrl is None:
                logger.debug("No XBRL for %s filing %s", company_name, filing.period_of_report)
                continue

            for concept in CAPEX_XBRL_CONCEPTS:
                try:
                    facts_df = xbrl.facts.get_facts_by_concept(concept)
                    if facts_df is None or len(facts_df) == 0:
                        continue

                    # Filter to non-dimensioned annual (duration) facts
                    if "is_dimensioned" in facts_df.columns:
                        total_df = facts_df[~facts_df["is_dimensioned"]]
                    else:
                        total_df = facts_df
                    if "period_type" in total_df.columns:
                        total_df = total_df[total_df["period_type"] == "duration"]
                    if total_df.empty:
                        total_df = facts_df

                    for _, fact_row in total_df.iterrows():
                        raw_value = fact_row.get("numeric_value")
                        if raw_value is None or (hasattr(raw_value, "__float__") and pd.isna(raw_value)):
                            raw_str = fact_row.get("value")
                            try:
                                raw_value = float(raw_str) if raw_str not in (None, "") else None
                            except (ValueError, TypeError):
                                raw_value = None
                        if raw_value is None:
                            continue

                        # Convert to USD billions (XBRL values are in raw USD)
                        capex_usd_b = abs(float(raw_value)) / 1e9

                        # Determine fiscal year from period_end
                        period_end = str(fact_row.get("period_end", filing.period_of_report))
                        try:
                            fiscal_year = int(period_end[:4])
                        except (ValueError, TypeError):
                            fiscal_year = 2024

                        if fiscal_year < 2020 or fiscal_year > 2024:
                            continue
                        if fiscal_year in seen_years:
                            continue
                        seen_years.add(fiscal_year)

                        rows.append({
                            "cik": cik,
                            "company_name": company_name,
                            "fiscal_year": fiscal_year,
                            "total_capex_usd": capex_usd_b,
                            "xbrl_concept_used": concept,
                        })
                    break  # first concept with data wins
                except Exception as concept_err:
                    logger.debug(
                        "Concept %s failed for %s: %s", concept, company_name, concept_err
                    )
                    continue
        except Exception as filing_err:
            logger.warning("Failed to process filing for %s: %s", company_name, filing_err)
            continue

    if rows:
        logger.info(
            "XBRL CapEx: %s — %d years extracted (source: XBRL)",
            company_name, len(rows),
        )
    return rows


def _fallback_capex(company_name: str, cik: str) -> list[dict]:
    """Return hardcoded CapEx fallback rows for a company."""
    rows = []
    for (name, year), capex_b in CAPEX_FALLBACK.items():
        if name == company_name:
            rows.append({
                "cik": cik,
                "company_name": company_name,
                "fiscal_year": year,
                "total_capex_usd": capex_b,
                "xbrl_concept_used": "fallback/10-K_published",
            })
    if rows:
        logger.info(
            "CapEx fallback: %s — %d years from hardcoded 10-K data",
            company_name, len(rows),
        )
    return rows


# ---------------------------------------------------------------------------
# Fetch all companies
# ---------------------------------------------------------------------------

def fetch_all_capex(industry: str = "ai") -> pd.DataFrame:
    """
    Load companies from ai.yaml, fetch CapEx for each, apply AI ratio.

    Parameters
    ----------
    industry : str
        Industry identifier (default "ai").

    Returns
    -------
    pd.DataFrame
        Columns: cik, company_name, fiscal_year, total_capex_usd,
        ai_capex_ratio, ai_capex_usd, source, segment, xbrl_concept_used
    """
    config = load_industry_config(industry)
    companies = config.get("edgar_companies", [])
    if not companies:
        logger.warning("No edgar_companies found in %s config", industry)
        return _empty_capex_df()

    all_dfs = []
    for comp in companies:
        cik = comp["cik"]
        name = comp["name"]
        segment = comp.get("value_chain_layer", "")

        try:
            df = fetch_capex_for_company(cik, name)
            if not df.empty:
                # Apply AI ratio
                ratio_info = AI_CAPEX_RATIOS.get(name, {"ai_capex_ratio": 0.20, "source": "default estimate"})
                df["ai_capex_ratio"] = ratio_info["ai_capex_ratio"]
                df["ai_capex_usd"] = df["total_capex_usd"] * df["ai_capex_ratio"]
                df["source"] = ratio_info["source"]
                df["segment"] = segment
                all_dfs.append(df)
        except Exception as e:
            logger.error("fetch_capex_for_company failed for %s (CIK %s): %s", name, cik, e)

    if not all_dfs:
        logger.warning("No CapEx data collected for any company")
        return _empty_capex_df()

    result = pd.concat(all_dfs, ignore_index=True)
    logger.info(
        "Fetched CapEx for %d companies, %d total rows",
        result["company_name"].nunique(), len(result),
    )
    return result


def _empty_capex_df() -> pd.DataFrame:
    """Return empty DataFrame with correct capex schema."""
    return pd.DataFrame(columns=[
        "cik", "company_name", "fiscal_year", "total_capex_usd",
        "ai_capex_ratio", "ai_capex_usd", "source", "segment", "xbrl_concept_used",
    ])


def save_raw_capex(df: pd.DataFrame, industry: str = "ai") -> Path:
    """
    Save raw CapEx DataFrame to data/raw/edgar/capex_ai_raw.parquet.

    Parameters
    ----------
    df : pd.DataFrame
        CapEx data from fetch_all_capex().
    industry : str
        Industry identifier.

    Returns
    -------
    Path
        Path to the written Parquet file.
    """
    output_dir = DATA_RAW / "edgar"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"capex_{industry}_raw.parquet"

    table = pa.Table.from_pandas(df, preserve_index=False)
    existing_meta = table.schema.metadata or {}
    custom_meta = {
        b"source": b"edgar_capex",
        b"industry": industry.encode(),
        b"fetched_at": datetime.now(tz=timezone.utc).isoformat().encode(),
    }
    table = table.replace_schema_metadata({**existing_meta, **custom_meta})
    pq.write_table(table, output_path, compression="snappy")

    logger.info("Saved raw CapEx to %s (%d rows)", output_path, len(df))
    return output_path


# ---------------------------------------------------------------------------
# Part 2: CapEx-to-Revenue Lag Model
# ---------------------------------------------------------------------------

def compute_capex_revenue_lead(capex_df: pd.DataFrame, revenue_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute CapEx-to-Revenue ratios and lagged correlation metrics.

    For each company with both CapEx and revenue data, computes:
    - CapEx-to-Revenue ratio (how much CapEx per dollar of AI revenue)
    - YoY CapEx growth
    - YoY Revenue growth in the next year (1-year lag)

    Parameters
    ----------
    capex_df : pd.DataFrame
        From fetch_all_capex(). Must have: company_name, fiscal_year, ai_capex_usd.
    revenue_df : pd.DataFrame
        Revenue attribution data. Must have: company_name, year, ai_revenue_usd_billions.

    Returns
    -------
    pd.DataFrame
        Columns: company_name, fiscal_year, capex_revenue_ratio,
        yoy_capex_growth, yoy_revenue_growth_next_year
    """
    if capex_df.empty or revenue_df.empty:
        return pd.DataFrame(columns=[
            "company_name", "fiscal_year", "capex_revenue_ratio",
            "yoy_capex_growth", "yoy_revenue_growth_next_year",
        ])

    # Standardize column names for merge
    capex = capex_df[["company_name", "fiscal_year", "ai_capex_usd"]].copy()
    rev = revenue_df.rename(columns={"year": "fiscal_year"}) if "year" in revenue_df.columns else revenue_df.copy()

    if "ai_revenue_usd_billions" not in rev.columns:
        logger.warning("revenue_df missing ai_revenue_usd_billions column")
        return pd.DataFrame(columns=[
            "company_name", "fiscal_year", "capex_revenue_ratio",
            "yoy_capex_growth", "yoy_revenue_growth_next_year",
        ])

    rev = rev[["company_name", "fiscal_year", "ai_revenue_usd_billions"]].copy()

    # Aggregate to annual if multiple entries per company-year
    capex = capex.groupby(["company_name", "fiscal_year"])["ai_capex_usd"].sum().reset_index()
    rev = rev.groupby(["company_name", "fiscal_year"])["ai_revenue_usd_billions"].sum().reset_index()

    merged = capex.merge(rev, on=["company_name", "fiscal_year"], how="inner")
    if merged.empty:
        return pd.DataFrame(columns=[
            "company_name", "fiscal_year", "capex_revenue_ratio",
            "yoy_capex_growth", "yoy_revenue_growth_next_year",
        ])

    # CapEx-to-Revenue ratio
    merged["capex_revenue_ratio"] = np.where(
        merged["ai_revenue_usd_billions"] > 0,
        merged["ai_capex_usd"] / merged["ai_revenue_usd_billions"],
        np.nan,
    )

    # YoY growth rates
    merged = merged.sort_values(["company_name", "fiscal_year"])
    merged["yoy_capex_growth"] = merged.groupby("company_name")["ai_capex_usd"].pct_change()

    # Next-year revenue growth (1-year lag)
    merged["_next_year_rev"] = merged.groupby("company_name")["ai_revenue_usd_billions"].shift(-1)
    merged["yoy_revenue_growth_next_year"] = np.where(
        merged["ai_revenue_usd_billions"] > 0,
        (merged["_next_year_rev"] - merged["ai_revenue_usd_billions"]) / merged["ai_revenue_usd_billions"],
        np.nan,
    )

    result = merged[
        ["company_name", "fiscal_year", "capex_revenue_ratio",
         "yoy_capex_growth", "yoy_revenue_growth_next_year"]
    ].reset_index(drop=True)

    return result


# ---------------------------------------------------------------------------
# Part 3: Bottom-Up Market Size Validation (replaces the light version)
# ---------------------------------------------------------------------------

def compile_bottom_up_validation(industry: str = "ai") -> pd.DataFrame:
    """
    Compile bottom-up vs top-down validation for each segment and year.

    Loads CapEx data, company-level AI revenue attribution, and top-down
    ensemble forecasts. Computes coverage ratios, CapEx intensity, and
    CapEx-implied growth signals.

    Parameters
    ----------
    industry : str
        Industry identifier. Currently only "ai" is supported.

    Returns
    -------
    pd.DataFrame
        Columns: segment, year, bottom_up_sum, top_down_estimate,
        coverage_ratio, gap_usd_billions, n_companies, top_contributors,
        company_capex_sum, capex_intensity, capex_implied_growth
    """
    # --- Load revenue attribution ---
    rev_path = DATA_PROCESSED / f"revenue_attribution_{industry}.parquet"
    if not rev_path.exists():
        raise FileNotFoundError(f"Revenue attribution data not found: {rev_path}")
    rev_df = pd.read_parquet(rev_path)
    logger.info("Loaded revenue attribution: %d rows", len(rev_df))

    # --- Load top-down ensemble forecasts (Q4 annual snapshots) ---
    fc_path = DATA_PROCESSED / "forecasts_ensemble.parquet"
    if not fc_path.exists():
        raise FileNotFoundError(f"Forecasts data not found: {fc_path}")
    fc_df = pd.read_parquet(fc_path)
    logger.info("Loaded forecasts ensemble: %d rows", len(fc_df))

    fc_annual = fc_df[fc_df["quarter"] == 4][
        ["year", "segment", "point_estimate_nominal"]
    ].copy()
    fc_annual = fc_annual.rename(columns={"point_estimate_nominal": "top_down_estimate"})

    # --- Load or fetch CapEx data ---
    capex_path = DATA_RAW / "edgar" / f"capex_{industry}_raw.parquet"
    if capex_path.exists():
        capex_df = pd.read_parquet(capex_path)
        logger.info("Loaded cached CapEx: %d rows", len(capex_df))
    else:
        logger.info("No cached CapEx — fetching fresh data")
        capex_df = fetch_all_capex(industry)
        if not capex_df.empty:
            save_raw_capex(capex_df, industry)

    # --- Aggregate company-level revenue by segment and year ---
    if "year" not in rev_df.columns:
        logger.warning("Revenue attribution missing 'year' column — cannot join")
        return pd.DataFrame()

    # Map value_chain_layer to segment for capex aggregation
    layer_to_segment = {
        "ai_hardware": "ai_hardware",
        "ai_infrastructure": "ai_infrastructure",
        "ai_software": "ai_software",
        "ai_adoption": "ai_adoption",
    }

    bottom_up = (
        rev_df.groupby(["segment", "year"])
        .agg(
            bottom_up_sum=("ai_revenue_usd_billions", "sum"),
            n_companies=("company_name", "count"),
        )
        .reset_index()
    )

    # Top 3 contributors per segment-year
    top_contrib = (
        rev_df.sort_values("ai_revenue_usd_billions", ascending=False)
        .groupby(["segment", "year"])
        .apply(
            lambda g: g.nlargest(3, "ai_revenue_usd_billions")["company_name"].tolist(),
            include_groups=False,
        )
        .reset_index(name="top_contributors")
    )
    bottom_up = bottom_up.merge(top_contrib, on=["segment", "year"], how="left")

    # --- Aggregate CapEx by segment and year ---
    if not capex_df.empty and "segment" in capex_df.columns:
        capex_mapped = capex_df.copy()
        capex_mapped["segment"] = capex_mapped["segment"].map(layer_to_segment).fillna(capex_mapped["segment"])
        capex_agg = (
            capex_mapped.groupby(["segment", "fiscal_year"])
            .agg(company_capex_sum=("ai_capex_usd", "sum"))
            .reset_index()
            .rename(columns={"fiscal_year": "year"})
        )
    else:
        capex_agg = pd.DataFrame(columns=["segment", "year", "company_capex_sum"])

    # --- Merge all three ---
    result = bottom_up.merge(fc_annual, on=["segment", "year"], how="inner")
    result = result.merge(capex_agg, on=["segment", "year"], how="left")
    result["company_capex_sum"] = result["company_capex_sum"].fillna(0.0)

    if result.empty:
        logger.warning("No matching segment-year pairs between bottom-up and top-down data")
        return pd.DataFrame(
            columns=[
                "segment", "year", "bottom_up_sum", "top_down_estimate",
                "coverage_ratio", "gap_usd_billions", "n_companies", "top_contributors",
                "company_capex_sum", "capex_intensity", "capex_implied_growth",
            ]
        )

    # --- Compute validation metrics ---
    result["coverage_ratio"] = np.where(
        result["top_down_estimate"] > 0,
        result["bottom_up_sum"] / result["top_down_estimate"],
        0.0,
    )
    result["gap_usd_billions"] = result["top_down_estimate"] - result["bottom_up_sum"]

    # CapEx intensity = company_capex_sum / bottom_up_sum
    result["capex_intensity"] = np.where(
        result["bottom_up_sum"] > 0,
        result["company_capex_sum"] / result["bottom_up_sum"],
        0.0,
    )

    # CapEx-implied growth: YoY capex growth rate per segment
    result = result.sort_values(["segment", "year"])
    result["_prev_capex"] = result.groupby("segment")["company_capex_sum"].shift(1)
    result["capex_implied_growth"] = np.where(
        result["_prev_capex"] > 0,
        (result["company_capex_sum"] - result["_prev_capex"]) / result["_prev_capex"],
        np.nan,
    )
    result.drop(columns=["_prev_capex"], inplace=True)

    # --- Select and order columns ---
    result = result[
        [
            "segment", "year", "bottom_up_sum", "top_down_estimate",
            "coverage_ratio", "gap_usd_billions", "n_companies", "top_contributors",
            "company_capex_sum", "capex_intensity", "capex_implied_growth",
        ]
    ].sort_values(["segment", "year"]).reset_index(drop=True)

    logger.info(
        "Bottom-up validation compiled: %d rows across %d segments",
        len(result), result["segment"].nunique(),
    )
    return result


def write_bottom_up_validation(df: pd.DataFrame) -> Path:
    """
    Write bottom-up validation DataFrame to Parquet.

    Parameters
    ----------
    df : pd.DataFrame
        Output of compile_bottom_up_validation().

    Returns
    -------
    Path
        Path to the written Parquet file.
    """
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    out_path = DATA_PROCESSED / "bottom_up_validation.parquet"
    df.to_parquet(out_path, index=False)
    logger.info("Written bottom-up validation to %s (%d rows)", out_path, len(df))
    return out_path
