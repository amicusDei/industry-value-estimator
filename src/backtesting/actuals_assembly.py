"""
Assembles hard actuals (EDGAR direct-disclosure) and soft actuals (market anchor consensus)
for backtesting.

Hard actuals: EDGAR 10-K filed revenue from direct-disclosure companies only.
  - NVIDIA (CIK: 0001045810)
  - Palantir (CIK: 0001321655)
  - C3.ai (CIK: 0001577526)
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
    "0001045810",  # NVIDIA Corporation — representative of ai_hardware segment
    # Palantir EXCLUDED: $2.5B revenue is <5% of ai_software segment ($56-117B).
    # Individual company revenue cannot represent an entire market segment.
    # Hard actual validation requires segment-representative revenue, not single companies.
    # NVIDIA is the exception: its data center revenue (~$47B) IS the majority of AI hardware.
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
                # Deduplicate EDGAR rows: the raw EDGAR parquet contains duplicate revenue facts
                # because each 10-K filing reports comparative prior-year data, and the XBRL
                # extractor captures all instances. Deduplicate by keeping the maximum value_usd
                # per (cik, period_end, xbrl_concept) — this retains the one unique fact per
                # company/period/concept combination and eliminates cross-filing duplicates.
                if "xbrl_concept" in direct_df.columns:
                    direct_df = (
                        direct_df.sort_values("value_usd", ascending=False)
                        .drop_duplicates(subset=["cik", "period_end", "xbrl_concept"])
                        .copy()
                    )
                else:
                    direct_df = direct_df.drop_duplicates(subset=["cik", "period_end"]).copy()

                # For backtesting, use annual totals only (10-K filings).
                # 10-Q quarterly filings are filtered out to avoid double-counting
                # (Q1+Q2+Q3 quarterly revenues would sum to less than the annual total,
                # and mixing with 10-K annuals would distort the aggregated actual).
                if "form_type" in direct_df.columns:
                    annual_df = direct_df[direct_df["form_type"].isin(["10-K", "20-F"])]
                    if annual_df.empty:
                        # Fallback: if no 10-K/20-F rows, use all rows
                        annual_df = direct_df
                    direct_df = annual_df

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

                # For each (year, segment), take the maximum actual_usd_billions
                # (avoids double-counting when multiple companies map to same segment/year).
                # NVIDIA: ai_hardware, Palantir: ai_software, C3.ai: ai_software
                # Since these are separate companies, we SUM their revenues per segment/year.
                period_col = "period_end" if "period_end" in direct_df.columns else "year"
                agg_df = (
                    direct_df.groupby(["year", "segment"], as_index=False)
                    .agg(
                        actual_usd_billions=("actual_usd_billions", "sum"),
                        source_date=(period_col, "max"),
                    )
                )
                agg_df["actual_type"] = "hard"
                agg_df["source"] = "EDGAR 10-K"
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
