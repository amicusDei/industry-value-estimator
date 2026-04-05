"""
src/ingestion/fundamentals.py
================================
Quarterly fundamental data for Controller vs Adapter analysis.

Uses yfinance to pull quarterly financials (Income Statement, Balance Sheet,
Cash Flow) for all issuers in the Dynamic Mismatch universe. Computes key
profitability and investment ratios for the fundamentals-based event study.
"""

import pandas as pd
import numpy as np
import yfinance as yf
import logging
import os
from datetime import datetime

from src.ingestion.credit_spreads import (
    ALL_ISSUERS,
    CONTROLLERS,
    DC_REITS,
    ALL_ADAPTERS,
    GROUP_LABELS,
    SECTOR_LABELS,
)

logger = logging.getLogger(__name__)

# ── TICKER MAPPING ───────────────────────────────────────────────────────────
# Maps issuer names (from credit_spreads.py) to yfinance tickers.

YFINANCE_TICKERS = {
    "Microsoft": "MSFT",
    "Alphabet": "GOOGL",
    "Amazon": "AMZN",
    "Meta": "META",
    "Oracle": "ORCL",
    "Equinix": "EQIX",
    "DigitalRealty": "DLR",
    "IronMountain": "IRM",
    "JPMorgan": "JPM",
    "BankOfAmerica": "BAC",
    "Citigroup": "C",
    "WellsFargo": "WFC",
    "AXA": "CS.PA",
    "Allianz": "ALV.DE",
    "GoldmanSachs": "GS",
    "JohnsonJohnson": "JNJ",
    "Pfizer": "PFE",
    "Merck": "MRK",
    "AbbVie": "ABBV",
    "UnitedHealth": "UNH",
    "CVSHealth": "CVS",
    "Walmart": "WMT",
    "Target": "TGT",
    "Kroger": "KR",
    "Carrefour": "CA.PA",
    "Coca-Cola": "KO",
    "ProcterGamble": "PG",
    "ATT": "T",
    "Verizon": "VZ",
    "DeutscheTelekom": "DTE.DE",
    "Comcast": "CMCSA",
    "Vodafone": "VOD",
}


# ── LINE ITEM MAPPINGS ──────────────────────────────────────────────────────
# yfinance uses various names for the same line items across tickers.
# We map common variants to canonical names.

REVENUE_KEYS = ["Total Revenue", "TotalRevenue", "Revenue"]
GROSS_PROFIT_KEYS = ["Gross Profit", "GrossProfit"]
OPERATING_INCOME_KEYS = ["Operating Income", "OperatingIncome", "EBIT"]
NET_INCOME_KEYS = ["Net Income", "NetIncome", "Net Income Common Stockholders"]
RD_KEYS = ["Research Development", "ResearchDevelopment", "Research And Development"]
SGA_KEYS = [
    "Selling General And Administrative",
    "SellingGeneralAndAdministrative",
    "Selling General Administrative",
]
TOTAL_ASSETS_KEYS = ["Total Assets", "TotalAssets"]
CAPEX_KEYS = ["Capital Expenditure", "CapitalExpenditure", "Capital Expenditures"]


def _extract_line_item(df: pd.DataFrame, keys: list[str]) -> pd.Series | None:
    """Extract a line item from a yfinance financials DataFrame, trying multiple key names."""
    for key in keys:
        if key in df.index:
            return df.loc[key]
    return None


def _fetch_single_issuer(issuer: str, ticker_symbol: str, start: str) -> pd.DataFrame:
    """Fetch quarterly financials for a single issuer from yfinance."""
    start_dt = pd.Timestamp(start)
    try:
        t = yf.Ticker(ticker_symbol)

        # Income Statement (quarterly)
        inc = t.quarterly_financials
        if inc is None or inc.empty:
            logger.warning(f"No income statement for {issuer} ({ticker_symbol})")
            return pd.DataFrame()

        # Balance Sheet (quarterly)
        bs = t.quarterly_balance_sheet
        if bs is None or bs.empty:
            bs = pd.DataFrame()

        # Cash Flow (quarterly)
        cf = t.quarterly_cashflow
        if cf is None or cf.empty:
            cf = pd.DataFrame()

        # yfinance returns columns as dates, rows as line items. Transpose.
        records = []
        all_dates = sorted(set(inc.columns.tolist()), reverse=False)

        for date_col in all_dates:
            dt = pd.Timestamp(date_col)
            if dt < start_dt:
                continue

            row = {"Date": dt, "Issuer": issuer}

            # Income statement items
            rev = _extract_line_item(inc, REVENUE_KEYS)
            row["Revenue"] = float(rev[date_col]) if rev is not None and date_col in rev.index else np.nan

            gp = _extract_line_item(inc, GROSS_PROFIT_KEYS)
            row["GrossProfit"] = float(gp[date_col]) if gp is not None and date_col in gp.index else np.nan

            oi = _extract_line_item(inc, OPERATING_INCOME_KEYS)
            row["OperatingIncome"] = float(oi[date_col]) if oi is not None and date_col in oi.index else np.nan

            ni = _extract_line_item(inc, NET_INCOME_KEYS)
            row["NetIncome"] = float(ni[date_col]) if ni is not None and date_col in ni.index else np.nan

            rd = _extract_line_item(inc, RD_KEYS)
            row["RD"] = float(rd[date_col]) if rd is not None and date_col in rd.index else np.nan

            sga = _extract_line_item(inc, SGA_KEYS)
            row["SGA"] = float(sga[date_col]) if sga is not None and date_col in sga.index else np.nan

            # Balance sheet items
            if not bs.empty and date_col in bs.columns:
                ta = _extract_line_item(bs, TOTAL_ASSETS_KEYS)
                row["TotalAssets"] = float(ta[date_col]) if ta is not None and date_col in ta.index else np.nan
            else:
                row["TotalAssets"] = np.nan

            # Cash flow items
            if not cf.empty and date_col in cf.columns:
                capex = _extract_line_item(cf, CAPEX_KEYS)
                row["CapEx"] = float(capex[date_col]) if capex is not None and date_col in capex.index else np.nan
            else:
                row["CapEx"] = np.nan

            records.append(row)

        if not records:
            logger.warning(f"No quarterly data found for {issuer} after {start}")
            return pd.DataFrame()

        df = pd.DataFrame(records)
        logger.info(f"  OK: {issuer} ({ticker_symbol}) — {len(df)} quarters")
        return df

    except Exception as e:
        logger.error(f"  ERROR: {issuer} ({ticker_symbol}) — {e}")
        return pd.DataFrame()


def fetch_quarterly_fundamentals(start: str = "2019-01-01") -> pd.DataFrame:
    """
    Fetch quarterly financials for all issuers in ALL_ISSUERS using yfinance.

    Returns a long-format DataFrame with columns:
        Date, Issuer, Revenue, GrossProfit, OperatingIncome, NetIncome,
        RD, SGA, TotalAssets, CapEx, plus all computed ratios.
    """
    logger.info(f"Fetching quarterly fundamentals from yfinance (start={start})...")

    frames = []
    for issuer in ALL_ISSUERS:
        ticker_symbol = YFINANCE_TICKERS.get(issuer)
        if ticker_symbol is None:
            logger.warning(f"  SKIP: No yfinance ticker mapping for {issuer}")
            continue
        df = _fetch_single_issuer(issuer, ticker_symbol, start)
        if not df.empty:
            frames.append(df)

    if not frames:
        logger.error("No fundamentals data fetched.")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined["Date"] = pd.to_datetime(combined["Date"])
    combined = combined.sort_values(["Issuer", "Date"]).reset_index(drop=True)

    # Compute ratios
    combined = compute_ratios(combined)

    logger.info(
        f"Fundamentals complete: {combined.shape[0]} rows, "
        f"{combined['Issuer'].nunique()} issuers, "
        f"{combined['Date'].min().date()} to {combined['Date'].max().date()}"
    )
    return combined


def compute_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute fundamental ratios from raw financials.

    Adds columns:
        gross_margin, operating_margin, capex_ratio, rd_ratio, sga_ratio,
        revenue_growth_qoq, revenue_growth_yoy
    """
    out = df.copy()

    # Margin ratios (NaN where revenue is zero or missing)
    rev = out["Revenue"].replace(0, np.nan)
    out["gross_margin"] = out["GrossProfit"] / rev
    out["operating_margin"] = out["OperatingIncome"] / rev
    out["capex_ratio"] = out["CapEx"].abs() / rev
    out["rd_ratio"] = out["RD"] / rev  # NaN if R&D not reported
    out["sga_ratio"] = out["SGA"] / rev

    # Revenue growth (within each issuer)
    out = out.sort_values(["Issuer", "Date"])
    out["revenue_growth_qoq"] = out.groupby("Issuer")["Revenue"].pct_change(1)
    out["revenue_growth_yoy"] = out.groupby("Issuer")["Revenue"].pct_change(4)

    return out


def save_fundamentals(df: pd.DataFrame, output_dir: str = "data/raw/fundamentals") -> str:
    """Save fundamentals DataFrame to a dated parquet file."""
    os.makedirs(output_dir, exist_ok=True)
    date_str = datetime.today().strftime("%Y%m%d")
    path = f"{output_dir}/fundamentals_{date_str}.parquet"
    df.to_parquet(path, index=False)
    logger.info(f"Saved fundamentals to {path}")
    return path
