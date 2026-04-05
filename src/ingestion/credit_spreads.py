"""
src/ingestion/credit_spreads.py
================================
Pulls CDS 5Y spreads, Bond OAS, credit ratings, and market controls
for the Dynamic Mismatch event study.

Integrates with existing lseg.py session management pattern.
"""

import lseg.data as rd
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# ── UNIVERSE ──────────────────────────────────────────────────────────────────

# CONTROLLERS: Frontier AI infrastructure owners — set the generational pace
CONTROLLERS = {
    "Microsoft":  "MSFT.O",
    "Alphabet":   "GOOGL.O",
    "Amazon":     "AMZN.O",
    "Meta":       "META.O",
    "Oracle":     "ORCL.N",
}

# Data Centre REITs — indirect infrastructure exposure (kept separate)
DC_REITS = {
    "Equinix":       "EQIX.O",
    "DigitalRealty": "DLR.N",
    "IronMountain":  "IRM.N",
}

# ADAPTERS: Firms that must adapt to AI transitions but don't control the pace
ADAPTERS_FINANCE = {
    "JPMorgan":       "JPM.N",
    "BankOfAmerica":  "BAC.N",
    "Citigroup":      "C.N",
    "WellsFargo":     "WFC.N",
    "AXA":            "AXAF.PA",
    "Allianz":        "ALVG.DE",
    "GoldmanSachs":   "GS.N",
}

ADAPTERS_HEALTHCARE = {
    "JohnsonJohnson":  "JNJ.N",
    "Pfizer":          "PFE.N",
    "Merck":           "MRK.N",
    "AbbVie":          "ABBV.N",
    "UnitedHealth":    "UNH.N",
    "CVSHealth":       "CVS.N",
}

ADAPTERS_RETAIL = {
    "Walmart":         "WMT.N",
    "Target":          "TGT.N",
    "Kroger":          "KR.N",
    "Carrefour":       "CARR.PA",
    "Coca-Cola":       "KO.N",
    "ProcterGamble":   "PG.N",
}

ADAPTERS_TELECOM = {
    "ATT":             "T.N",
    "Verizon":         "VZ.N",
    "DeutscheTelekom": "DTEGn.DE",
    "Comcast":         "CMCSA.O",
    "Vodafone":        "VOD.L",
}

ALL_ADAPTERS = {**ADAPTERS_FINANCE, **ADAPTERS_HEALTHCARE, **ADAPTERS_RETAIL, **ADAPTERS_TELECOM}

# Legacy aliases for backward compatibility
HYPERSCALERS = CONTROLLERS
CONTROL_GROUP = ALL_ADAPTERS

ALL_ISSUERS = {**CONTROLLERS, **DC_REITS, **ALL_ADAPTERS}

# Group labels for regression
GROUP_LABELS = {
    **{k: "controller" for k in CONTROLLERS},
    **{k: "dc_reit" for k in DC_REITS},
    **{k: "adapter" for k in ALL_ADAPTERS},
}

# Sector labels for adapter heterogeneity analysis
SECTOR_LABELS = {
    **{k: "finance" for k in ADAPTERS_FINANCE},
    **{k: "healthcare" for k in ADAPTERS_HEALTHCARE},
    **{k: "retail" for k in ADAPTERS_RETAIL},
    **{k: "telecom" for k in ADAPTERS_TELECOM},
    **{k: "controller" for k in CONTROLLERS},
    **{k: "dc_reit" for k in DC_REITS},
}

# Backward-compatible: "treated" = controllers + dc_reits (original treatment group)
TREATED_GROUPS = {"controller", "dc_reit"}

# ── GENERATIONAL TRANSITION DATES ─────────────────────────────────────────────
# Defined exogenously from public release announcements.
# These are the event dates for the Post_t dummy in the event study.

GENERATION_TRANSITIONS = [
    {"date": "2020-06-11", "event": "GPT-3",         "generation": 1},
    {"date": "2022-11-30", "event": "ChatGPT launch", "generation": 2},
    {"date": "2023-03-14", "event": "GPT-4",          "generation": 3},
    {"date": "2024-05-13", "event": "GPT-4o",         "generation": 4},
    {"date": "2024-09-12", "event": "OpenAI o1",      "generation": 5},
]

# ── FIELDS ────────────────────────────────────────────────────────────────────

CREDIT_FIELDS = [
    "TR.CreditDefaultSwapSpread5Y",   # 5Y CDS par spread (bps)
    "TR.CreditDefaultSwapSpread10Y",  # 10Y CDS par spread (bps)
    "TR.BondSpreadOAS",               # Option-adjusted spread (bps)
    "TR.SPLongTermRating",            # S&P long-term issuer rating
    "TR.ModysLongTermRating",         # Moody's long-term issuer rating
]

TIMESERIES_FIELDS = [
    "TR.CreditDefaultSwapSpread5Y",
    "TR.BondSpreadOAS",
]

# ── PULL FUNCTIONS ────────────────────────────────────────────────────────────

def fetch_credit_snapshot(rics: list[str]) -> pd.DataFrame:
    """
    Pull current credit snapshot for all issuers.
    Returns: DataFrame with RIC as index, credit fields as columns.
    """
    logger.info(f"Pulling credit snapshot for {len(rics)} issuers...")

    # Batch at 100 RICs per call (existing pattern)
    results = []
    for i in range(0, len(rics), 100):
        batch = rics[i:i+100]
        try:
            df = rd.get_data(batch, fields=CREDIT_FIELDS)
            results.append(df)
            logger.info(f"  Batch {i//100 + 1}: OK ({len(batch)} RICs)")
        except Exception as e:
            logger.error(f"  Batch {i//100 + 1} failed: {e}")

    if not results:
        return pd.DataFrame()

    return pd.concat(results, ignore_index=True)


def fetch_cds_timeseries(
    rics: list[str],
    start_date: str = "2020-01-01",
    end_date: str | None = None,
    interval: str = "weekly"
) -> pd.DataFrame:
    """
    Pull historical CDS 5Y spread time series for all issuers.
    Uses weekly intervals to reduce API load while maintaining
    sufficient resolution for the 90-day event windows.

    Returns: Wide DataFrame with Date as index, issuer names as columns.
    """
    if end_date is None:
        end_date = datetime.today().strftime("%Y-%m-%d")

    logger.info(f"Pulling CDS time series: {start_date} to {end_date}, {interval}...")

    all_series = {}
    ric_to_name = {v: k for k, v in ALL_ISSUERS.items()}

    for ric in rics:
        name = ric_to_name.get(ric, ric)
        try:
            df = rd.get_history(
                universe=ric,
                fields=["TR.CreditDefaultSwapSpread5Y"],
                interval=interval,
                start=start_date,
                end=end_date
            )
            if df is not None and not df.empty:
                series = df["TR.CreditDefaultSwapSpread5Y"].rename(name)
                all_series[name] = series
                logger.info(f"  OK: {name} — {len(series)} observations")
            else:
                logger.warning(f"  EMPTY: {name} ({ric})")
        except Exception as e:
            logger.error(f"  ERROR: {name} ({ric}) — {e}")

    if not all_series:
        return pd.DataFrame()

    wide_df = pd.DataFrame(all_series)
    wide_df.index.name = "Date"
    wide_df.index = pd.to_datetime(wide_df.index)
    return wide_df.sort_index()


def fetch_bond_oas_timeseries(
    rics: list[str],
    start_date: str = "2020-01-01",
    end_date: str | None = None,
    interval: str = "weekly"
) -> pd.DataFrame:
    """
    Pull historical bond OAS time series.
    Used as robustness check against CDS spreads.
    """
    if end_date is None:
        end_date = datetime.today().strftime("%Y-%m-%d")

    logger.info(f"Pulling Bond OAS time series: {start_date} to {end_date}...")

    all_series = {}
    ric_to_name = {v: k for k, v in ALL_ISSUERS.items()}

    for ric in rics:
        name = ric_to_name.get(ric, ric)
        try:
            df = rd.get_history(
                universe=ric,
                fields=["TR.BondSpreadOAS"],
                interval=interval,
                start=start_date,
                end=end_date
            )
            if df is not None and not df.empty:
                series = df["TR.BondSpreadOAS"].rename(name)
                all_series[name] = series
                logger.info(f"  OK: {name} — {len(series)} observations")
            else:
                logger.warning(f"  EMPTY: {name} ({ric})")
        except Exception as e:
            logger.error(f"  ERROR: {name} ({ric}) — {e}")

    if not all_series:
        return pd.DataFrame()

    wide_df = pd.DataFrame(all_series)
    wide_df.index.name = "Date"
    wide_df.index = pd.to_datetime(wide_df.index)
    return wide_df.sort_index()


def fetch_market_controls(
    start_date: str = "2020-01-01",
    end_date: str | None = None,
    interval: str = "weekly"
) -> pd.DataFrame:
    """
    Pull market-level control variables:
    - CDX.IG 5Y (investment grade credit index) as market spread control
    - VIX (volatility control)
    - UST 5Y yield (risk-free rate control)
    """
    if end_date is None:
        end_date = datetime.today().strftime("%Y-%m-%d")

    logger.info("Pulling market controls...")

    control_rics = {
        "CDX_IG_5Y": "CDXIG5Y=R",
        "VIX":       ".VIX",
        "UST_5Y":    "US5YT=RR",
    }

    results = {}
    for name, ric in control_rics.items():
        try:
            df = rd.get_history(
                universe=ric,
                fields=["CLOSE"],
                interval=interval,
                start=start_date,
                end=end_date
            )
            if df is not None and not df.empty:
                results[name] = df["CLOSE"]
                logger.info(f"  OK: {name}")
            else:
                logger.warning(f"  EMPTY: {name} ({ric})")
        except Exception as e:
            logger.error(f"  ERROR: {name} ({ric}) — {e}")

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df.index = pd.to_datetime(df.index)
    df.index.name = "Date"
    return df.sort_index()


# ── MAIN PULL ORCHESTRATION ───────────────────────────────────────────────────

def run_full_pull(
    output_dir: str = "data/raw/credit",
    start_date: str = "2020-01-01",
) -> dict[str, pd.DataFrame]:
    """
    Run the complete data pull. Call this from your existing
    lseg.py session management wrapper:

        rd.open_session()
        results = run_full_pull()
        rd.close_session()
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    all_rics = list(ALL_ISSUERS.values())
    results = {}

    # CDS time series (primary)
    cds_df = fetch_cds_timeseries(all_rics, start_date=start_date)
    if not cds_df.empty:
        path = f"{output_dir}/cds_spreads_{datetime.today().strftime('%Y%m%d')}.parquet"
        cds_df.to_parquet(path)
        logger.info(f"Saved CDS data: {path}")
        results["cds"] = cds_df

    # Bond OAS (robustness)
    oas_df = fetch_bond_oas_timeseries(all_rics, start_date=start_date)
    if not oas_df.empty:
        path = f"{output_dir}/bond_oas_{datetime.today().strftime('%Y%m%d')}.parquet"
        oas_df.to_parquet(path)
        logger.info(f"Saved OAS data: {path}")
        results["oas"] = oas_df

    # Market controls
    ctrl_df = fetch_market_controls(start_date=start_date)
    if not ctrl_df.empty:
        path = f"{output_dir}/market_controls_{datetime.today().strftime('%Y%m%d')}.parquet"
        ctrl_df.to_parquet(path)
        logger.info(f"Saved controls: {path}")
        results["controls"] = ctrl_df

    # Generation transitions (static, no API needed)
    trans_df = pd.DataFrame(GENERATION_TRANSITIONS)
    trans_df["date"] = pd.to_datetime(trans_df["date"])
    path = f"{output_dir}/generation_transitions.parquet"
    trans_df.to_parquet(path)
    results["transitions"] = trans_df

    logger.info("Full pull complete.")
    return results
