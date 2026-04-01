"""
Bottom-up validation module (v2-AP6).

Cross-references top-down analyst consensus forecasts with actual company-level
AI revenue data from EDGAR filings (10-K/10-Q). Provides a "sum-of-parts"
sanity check: for each segment and year, how much of the top-down market
estimate is explained by known companies?

Uses ONLY existing processed data — no external API calls.

Usage:
    df = compile_bottom_up_validation("ai")
    path = write_bottom_up_validation(df)
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import DATA_PROCESSED

logger = logging.getLogger(__name__)


def compile_bottom_up_validation(industry: str = "ai") -> pd.DataFrame:
    """
    Compile bottom-up vs top-down validation for each segment and year.

    Loads company-level AI revenue attribution and top-down ensemble forecasts,
    then computes coverage ratios showing what fraction of each segment's
    top-down estimate is explained by known public companies.

    Parameters
    ----------
    industry : str
        Industry identifier. Currently only "ai" is supported.

    Returns
    -------
    pd.DataFrame
        Columns: segment, year, bottom_up_sum, top_down_estimate,
        coverage_ratio, gap_usd_billions, n_companies, top_contributors
    """
    # Load company-level AI revenue attribution
    rev_path = DATA_PROCESSED / "revenue_attribution_ai.parquet"
    if not rev_path.exists():
        raise FileNotFoundError(f"Revenue attribution data not found: {rev_path}")
    rev_df = pd.read_parquet(rev_path)
    logger.info("Loaded revenue attribution: %d rows", len(rev_df))

    # Load top-down ensemble forecasts (Q4 annual snapshots)
    fc_path = DATA_PROCESSED / "forecasts_ensemble.parquet"
    if not fc_path.exists():
        raise FileNotFoundError(f"Forecasts data not found: {fc_path}")
    fc_df = pd.read_parquet(fc_path)
    logger.info("Loaded forecasts ensemble: %d rows", len(fc_df))

    # Use Q4 snapshots as annual figures, nominal USD
    fc_annual = fc_df[fc_df["quarter"] == 4][
        ["year", "segment", "point_estimate_nominal"]
    ].copy()
    fc_annual = fc_annual.rename(columns={"point_estimate_nominal": "top_down_estimate"})

    # Aggregate company-level revenue by segment and year
    if "year" not in rev_df.columns:
        logger.warning("Revenue attribution missing 'year' column — cannot join")
        return pd.DataFrame()

    bottom_up = (
        rev_df.groupby(["segment", "year"])
        .agg(
            bottom_up_sum=("ai_revenue_usd_billions", "sum"),
            n_companies=("company_name", "count"),
        )
        .reset_index()
    )

    # Get top 3 contributors per segment-year
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

    # Merge with top-down forecasts
    result = bottom_up.merge(fc_annual, on=["segment", "year"], how="inner")

    if result.empty:
        logger.warning("No matching segment-year pairs between bottom-up and top-down data")
        return pd.DataFrame(
            columns=[
                "segment", "year", "bottom_up_sum", "top_down_estimate",
                "coverage_ratio", "gap_usd_billions", "n_companies", "top_contributors",
            ]
        )

    # Compute validation metrics
    result["coverage_ratio"] = np.where(
        result["top_down_estimate"] > 0,
        result["bottom_up_sum"] / result["top_down_estimate"],
        0.0,
    )
    result["gap_usd_billions"] = result["top_down_estimate"] - result["bottom_up_sum"]

    # Select and order columns
    result = result[
        [
            "segment", "year", "bottom_up_sum", "top_down_estimate",
            "coverage_ratio", "gap_usd_billions", "n_companies", "top_contributors",
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
    out_path = DATA_PROCESSED / "bottom_up_validation.parquet"
    df.to_parquet(out_path, index=False)
    logger.info("Written bottom-up validation to %s (%d rows)", out_path, len(df))
    return out_path
