"""
Assembles hard actuals (EDGAR direct-disclosure) and soft actuals (market anchor consensus)
for backtesting.

Hard actuals: EDGAR 10-K filed revenue from direct-disclosure companies only.
  - NVIDIA (CIK: 0001045810)
  - Palantir (CIK: 0001321655)
  - C3.ai (CIK: 0001577552)
  These are the ONLY companies whose filed revenue counts as hard actuals.
  Bundled-segment companies (Microsoft, Amazon, Alphabet, Meta, IBM, Accenture, Salesforce)
  are NEVER used as hard actuals — their attributed AI revenue would create circular validation.

Soft actuals: analyst consensus from market_anchors_ai.parquet.
  Uses median_usd_billions_real_2020 as the actual value per segment per year.
"""

import warnings
from pathlib import Path

import pandas as pd

from config.settings import DATA_RAW, DATA_PROCESSED

# CIKs of direct-disclosure companies — these are the ONLY sources of hard actuals.
# Bundled companies (Microsoft, Amazon, Alphabet, Meta, IBM, Accenture, Salesforce)
# must NEVER appear here — their attributed AI revenue would contaminate backtesting.
DIRECT_DISCLOSURE_CIKS = {
    "0001045810",  # NVIDIA Corporation
    "0001321655",  # Palantir Technologies Inc.
    "0001577552",  # C3.ai Inc.
}

# Value chain layer -> market segment mapping (from ai.yaml taxonomy)
_LAYER_TO_SEGMENT = {
    "chip": "ai_hardware",
    "ai_hardware": "ai_hardware",
    "cloud": "ai_infrastructure",
    "ai_infrastructure": "ai_infrastructure",
    "application": "ai_software",
    "ai_software": "ai_software",
    "end_market": "ai_adoption",
    "ai_adoption": "ai_adoption",
}


def _map_layer_to_segment(layer: str) -> str:
    """Map value_chain_layer to market segment. Returns layer unchanged if not found."""
    return _LAYER_TO_SEGMENT.get(layer, layer)


def assemble_actuals(industry_id: str = "ai") -> pd.DataFrame:
    """
    Assemble hard actuals (EDGAR direct-disclosure) and soft actuals (market anchor consensus).

    Parameters
    ----------
    industry_id : str
        Industry identifier (currently only 'ai' is supported). Default 'ai'.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - year (int): calendar year
        - segment (str): market segment (ai_hardware, ai_infrastructure, ai_software, ai_adoption)
        - actual_usd_billions (float): actual revenue in USD billions (real 2020)
        - actual_type (str): 'hard' or 'soft'
        - source (str): data source description
        - source_date (str/date): date or flag indicating source vintage

    Notes
    -----
    If EDGAR parquet does not exist, returns soft actuals only with a warning.
    Hard actuals are NOT available from bundled companies (Microsoft, Amazon, etc.)
    — only from DIRECT_DISCLOSURE_CIKS.
    """
    records = []

    # --- Hard actuals: EDGAR direct-disclosure companies ---
    edgar_path = DATA_RAW / "edgar" / f"edgar_{industry_id}_raw.parquet"
    if edgar_path.exists():
        edgar_df = pd.read_parquet(edgar_path)
        # Filter to direct-disclosure companies only
        if "cik" in edgar_df.columns:
            # Normalize CIK formatting (pad to 10 digits with leading zeros)
            edgar_df = edgar_df.copy()
            edgar_df["cik_str"] = edgar_df["cik"].astype(str).str.zfill(10)
            direct_df = edgar_df[edgar_df["cik_str"].isin(DIRECT_DISCLOSURE_CIKS)]
        else:
            direct_df = pd.DataFrame()
            warnings.warn("EDGAR parquet has no 'cik' column — skipping hard actuals.")

        if not direct_df.empty:
            # Extract year from period_end
            if "period_end" in direct_df.columns:
                direct_df = direct_df.copy()
                direct_df["year"] = pd.to_datetime(direct_df["period_end"]).dt.year
            elif "year" in direct_df.columns:
                pass  # already have year
            else:
                warnings.warn("EDGAR parquet missing 'period_end' and 'year' columns.")
                direct_df = pd.DataFrame()

            if not direct_df.empty:
                # Convert value_usd to USD billions (divide by 1e9)
                value_col = "value_usd" if "value_usd" in direct_df.columns else None
                if value_col:
                    direct_df = direct_df.copy()
                    direct_df["actual_usd_billions"] = direct_df[value_col] / 1e9
                else:
                    warnings.warn("EDGAR parquet missing 'value_usd' column — skipping hard actuals.")
                    direct_df = pd.DataFrame()

            if not direct_df.empty:
                # Map value_chain_layer to segment
                if "value_chain_layer" in direct_df.columns:
                    direct_df = direct_df.copy()
                    direct_df["segment"] = direct_df["value_chain_layer"].apply(_map_layer_to_segment)
                elif "segment" in direct_df.columns:
                    pass  # already have segment
                else:
                    direct_df["segment"] = "ai_hardware"  # fallback

                # Group by year + segment and sum actual_usd_billions
                period_col = "period_end" if "period_end" in direct_df.columns else "year"
                agg_df = (
                    direct_df.groupby(["year", "segment"], as_index=False)["actual_usd_billions"].sum()
                )
                agg_df["actual_type"] = "hard"
                agg_df["source"] = "EDGAR 10-K"
                agg_df["source_date"] = (
                    direct_df.groupby(["year", "segment"])[period_col].max().reset_index()[period_col]
                    if period_col in direct_df.columns else str(agg_df["year"])
                )
                records.append(agg_df[["year", "segment", "actual_usd_billions", "actual_type", "source", "source_date"]])
    else:
        print(
            f"[actuals_assembly] EDGAR parquet not found at {edgar_path} — "
            "using soft actuals only. Hard actuals require EDGAR ingestion (Plan 08-03)."
        )

    # --- Soft actuals: market anchor analyst consensus ---
    anchors_path = DATA_PROCESSED / f"market_anchors_{industry_id}.parquet"
    if anchors_path.exists():
        anchors_df = pd.read_parquet(anchors_path)

        # Use median_usd_billions_real_2020 as the actual value
        if "median_usd_billions_real_2020" in anchors_df.columns:
            soft_df = anchors_df[["estimate_year", "segment", "median_usd_billions_real_2020", "estimated_flag"]].copy()
            soft_df = soft_df.rename(columns={
                "estimate_year": "year",
                "median_usd_billions_real_2020": "actual_usd_billions",
            })
            soft_df["actual_type"] = "soft"
            soft_df["source"] = "analyst_consensus"
            soft_df["source_date"] = soft_df["estimated_flag"].apply(
                lambda flag: "estimate" if flag else "published"
            )
            soft_df = soft_df.drop(columns=["estimated_flag"])
            # Only include years where we have actual data (not future estimates)
            # Soft actuals for backtesting: include all years with data
            soft_df = soft_df[soft_df["actual_usd_billions"].notna()]
            records.append(soft_df[["year", "segment", "actual_usd_billions", "actual_type", "source", "source_date"]])
        else:
            warnings.warn(
                "market_anchors parquet missing 'median_usd_billions_real_2020' column — skipping soft actuals."
            )
    else:
        warnings.warn(f"market_anchors parquet not found at {anchors_path} — no soft actuals available.")

    if not records:
        # Return empty DataFrame with correct schema
        return pd.DataFrame(columns=["year", "segment", "actual_usd_billions", "actual_type", "source", "source_date"])

    result = pd.concat(records, ignore_index=True)
    result["year"] = result["year"].astype(int)
    return result
