"""
src/ingestion/merton_dd.py
===========================
Merton Distance-to-Default (DD) module — replaces CDS-based credit spread
approach for the Dynamic Mismatch event study.

Uses simplified Merton model: Equity = Call option on firm assets.

    Distance-to-Default = (ln(V/D) + (r - 0.5*sigma_V^2)*T) / (sigma_V*sqrt(T))

Where:
    V       = firm asset value (market_cap + total_debt)
    D       = debt face value (total_debt from LSEG)
    r       = risk-free rate (1Y UST from FRED)
    sigma_V = asset volatility (leverage-adjusted equity volatility)
    T       = time horizon (1 year standard)

Data sources:
    - LSEG get_history: equity prices (daily close)
    - LSEG get_data: fundamentals (TotalDebt, MarketCap)
    - FRED API: risk-free rate (DGS1 — 1Y Treasury constant maturity)
    - LSEG get_history: market controls (.SPX, .VIX)

Simplified Merton: no iterative Newton-Raphson for asset volatility.
Uses leverage-adjusted equity vol as proxy: sigma_V = sigma_E * (E / V).
"""

import lseg.data as rd
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import requests

from src.ingestion.credit_spreads import (
    ALL_ISSUERS,
    GROUP_LABELS,
    GENERATION_TRANSITIONS,
)

logger = logging.getLogger(__name__)


# ── EQUITY DATA ──────────────────────────────────────────────────────────────

def fetch_equity_timeseries(
    rics: list[str],
    start_date: str = "2020-01-01",
    end_date: str | None = None,
    interval: str = "daily",
) -> pd.DataFrame:
    """
    Pull historical equity closing prices for all issuers.

    Uses rd.get_history(ric, interval="daily", ...) — returns TRDPRC_1 as close.
    Returns wide DataFrame (Date x Issuer) of daily closing prices.
    """
    if end_date is None:
        end_date = datetime.today().strftime("%Y-%m-%d")

    logger.info(f"Pulling equity prices: {start_date} to {end_date}, {interval}...")

    all_series = {}
    ric_to_name = {v: k for k, v in ALL_ISSUERS.items()}

    for ric in rics:
        name = ric_to_name.get(ric, ric)
        try:
            df = rd.get_history(
                universe=ric,
                interval=interval,
                start=start_date,
                end=end_date,
            )
            if df is not None and not df.empty:
                # LSEG returns TRDPRC_1 as close price (not "CLOSE")
                close_col = "TRDPRC_1" if "TRDPRC_1" in df.columns else df.columns[0]
                series = df[close_col].rename(name)
                all_series[name] = series
                logger.info(f"  OK: {name} -- {len(series)} observations")
            else:
                logger.warning(f"  EMPTY: {name} ({ric})")
        except Exception as e:
            logger.error(f"  ERROR: {name} ({ric}) -- {e}")

    if not all_series:
        return pd.DataFrame()

    wide_df = pd.DataFrame(all_series)
    wide_df.index.name = "Date"
    wide_df.index = pd.to_datetime(wide_df.index)
    return wide_df.sort_index()


# ── DEBT / FUNDAMENTALS ─────────────────────────────────────────────────────

def fetch_debt_snapshot(rics: list[str]) -> pd.DataFrame:
    """
    Pull current total debt and market cap for all issuers.

    Uses rd.get_data(rics, fields=["TR.TotalDebt", "TR.MarketCap", "TR.CompanyMarketCap"]).
    Returns DataFrame with columns: Issuer, total_debt, market_cap.
    """
    logger.info(f"Pulling debt snapshot for {len(rics)} issuers...")

    ric_to_name = {v: k for k, v in ALL_ISSUERS.items()}

    results = []
    for i in range(0, len(rics), 100):
        batch = rics[i : i + 100]
        try:
            df = rd.get_data(
                batch,
                fields=["TR.TotalDebt", "TR.MarketCap", "TR.CompanyMarketCap"],
            )
            results.append(df)
            logger.info(f"  Batch {i // 100 + 1}: OK ({len(batch)} RICs)")
        except Exception as e:
            logger.error(f"  Batch {i // 100 + 1} failed: {e}")

    if not results:
        return pd.DataFrame(columns=["Issuer", "total_debt", "market_cap"])

    raw = pd.concat(results, ignore_index=True)

    # Normalise column names
    out = pd.DataFrame()
    out["ric"] = raw.iloc[:, 0]  # first column is the instrument
    out["Issuer"] = out["ric"].map(ric_to_name)

    # Use TR.CompanyMarketCap as primary, fall back to TR.MarketCap
    if "TR.CompanyMarketCap" in raw.columns and "TR.MarketCap" in raw.columns:
        out["market_cap"] = pd.to_numeric(
            raw["TR.CompanyMarketCap"].fillna(raw["TR.MarketCap"]), errors="coerce"
        )
    elif "TR.CompanyMarketCap" in raw.columns:
        out["market_cap"] = pd.to_numeric(raw["TR.CompanyMarketCap"], errors="coerce")
    elif "TR.MarketCap" in raw.columns:
        out["market_cap"] = pd.to_numeric(raw["TR.MarketCap"], errors="coerce")
    else:
        out["market_cap"] = np.nan

    if "TR.TotalDebt" in raw.columns:
        out["total_debt"] = pd.to_numeric(raw["TR.TotalDebt"], errors="coerce")
    else:
        out["total_debt"] = np.nan

    return out[["Issuer", "total_debt", "market_cap"]].dropna(subset=["Issuer"])


# ── RISK-FREE RATE (FRED) ───────────────────────────────────────────────────

def fetch_risk_free_rate(
    start_date: str = "2020-01-01",
    end_date: str | None = None,
) -> pd.Series:
    """
    Pull 1Y Treasury constant maturity rate from FRED (DGS1).

    Uses free FRED JSON API with DEMO_KEY (sufficient for low-volume requests).
    Returns Series with DatetimeIndex and daily yield values (as decimal, e.g. 0.04 = 4%).
    """
    if end_date is None:
        end_date = datetime.today().strftime("%Y-%m-%d")

    logger.info(f"Pulling risk-free rate from FRED: {start_date} to {end_date}...")

    url = (
        "https://api.stlouisfed.org/fred/series/observations"
        f"?series_id=DGS1"
        f"&file_type=json"
        f"&api_key=DEMO_KEY"
        f"&observation_start={start_date}"
        f"&observation_end={end_date}"
    )

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"FRED API request failed: {e}")
        return pd.Series(dtype=float, name="risk_free_rate")

    observations = data.get("observations", [])
    if not observations:
        logger.warning("FRED returned no observations.")
        return pd.Series(dtype=float, name="risk_free_rate")

    records = []
    for obs in observations:
        if obs["value"] != ".":
            records.append({
                "date": obs["date"],
                "rate": float(obs["value"]) / 100.0,  # convert from pct to decimal
            })

    if not records:
        return pd.Series(dtype=float, name="risk_free_rate")

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    series = df.set_index("date")["rate"]
    series.index.name = "Date"
    series.name = "risk_free_rate"
    return series.sort_index()


# ── VOLATILITY ───────────────────────────────────────────────────────────────

def compute_equity_volatility(
    prices_df: pd.DataFrame,
    window: int = 252,
) -> pd.DataFrame:
    """
    Compute rolling annualised volatility from daily log returns.

    Args:
        prices_df: Wide DataFrame (Date x Issuer) of daily closing prices.
        window: Rolling window in trading days (default 252 = 1 year).

    Returns:
        DataFrame same shape as prices_df with annualised volatility values.
    """
    log_returns = np.log(prices_df / prices_df.shift(1))
    rolling_vol = log_returns.rolling(window=window, min_periods=max(60, window // 4)).std()
    annualised_vol = rolling_vol * np.sqrt(252)
    return annualised_vol


# ── MERTON DISTANCE-TO-DEFAULT ──────────────────────────────────────────────

def compute_distance_to_default(
    market_cap: float,
    total_debt: float,
    equity_vol: float,
    risk_free_rate: float,
    T: float = 1.0,
) -> float:
    """
    Simplified Merton Distance-to-Default.

    Uses leverage-adjusted equity volatility as proxy for asset volatility
    (no iterative Newton-Raphson solving).

    Args:
        market_cap:     Equity market capitalisation (same units as total_debt).
        total_debt:     Total debt face value.
        equity_vol:     Annualised equity volatility (e.g. 0.25 = 25%).
        risk_free_rate: Risk-free rate as decimal (e.g. 0.04 = 4%).
        T:              Time horizon in years (default 1.0).

    Returns:
        Distance-to-Default value. Higher = safer, lower = riskier.
        Typical IG company: DD ~ 5-15.
    """
    if total_debt <= 0 or market_cap <= 0 or equity_vol <= 0 or T <= 0:
        return np.nan

    V = market_cap + total_debt  # firm asset value
    D = total_debt               # default barrier

    # Leverage-adjusted volatility: sigma_V = sigma_E * (E / V)
    sigma_V = equity_vol * (market_cap / V)

    if sigma_V <= 0:
        return np.nan

    dd = (np.log(V / D) + (risk_free_rate - 0.5 * sigma_V**2) * T) / (
        sigma_V * np.sqrt(T)
    )
    return float(dd)


# ── DD TIME SERIES ───────────────────────────────────────────────────────────

def compute_dd_timeseries(
    equity_prices: pd.DataFrame,
    debt_data: pd.DataFrame,
    risk_free_rates: pd.Series,
    vol_window: int = 252,
) -> pd.DataFrame:
    """
    Compute Distance-to-Default time series for all issuers.

    For each issuer at each date, computes DD using:
    - Rolling equity volatility
    - Static debt snapshot (latest available)
    - Daily risk-free rate

    Args:
        equity_prices:   Wide DataFrame (Date x Issuer) of daily closing prices.
        debt_data:       DataFrame with Issuer, total_debt, market_cap columns.
        risk_free_rates: Series with DatetimeIndex and daily risk-free rate.
        vol_window:      Rolling window for volatility computation.

    Returns:
        Wide DataFrame (Date x Issuer) of DD values.
    """
    # Compute rolling volatility
    vol_df = compute_equity_volatility(equity_prices, window=vol_window)

    # Build debt lookup
    debt_lookup = debt_data.set_index("Issuer")

    # Align risk-free rate to equity price dates
    rf_aligned = risk_free_rates.reindex(equity_prices.index, method="ffill")

    dd_results = {}

    for issuer in equity_prices.columns:
        if issuer not in debt_lookup.index:
            logger.warning(f"No debt data for {issuer}, skipping DD computation.")
            continue

        total_debt = debt_lookup.loc[issuer, "total_debt"]
        if pd.isna(total_debt) or total_debt <= 0:
            logger.warning(f"Invalid debt for {issuer}: {total_debt}")
            continue

        dd_series = []
        for date in equity_prices.index:
            price = equity_prices.loc[date, issuer]
            vol = vol_df.loc[date, issuer] if date in vol_df.index else np.nan
            rf = rf_aligned.get(date, np.nan)

            if pd.isna(price) or pd.isna(vol) or pd.isna(rf):
                dd_series.append(np.nan)
                continue

            # Use current price as proxy for market cap scaling
            # (debt_data.market_cap is a snapshot; scale proportionally with price)
            snapshot_mcap = debt_lookup.loc[issuer, "market_cap"]
            if pd.isna(snapshot_mcap) or snapshot_mcap <= 0:
                dd_series.append(np.nan)
                continue

            # Scale market cap by price ratio relative to latest price
            latest_price = equity_prices[issuer].dropna().iloc[-1]
            if latest_price > 0:
                scaled_mcap = snapshot_mcap * (price / latest_price)
            else:
                scaled_mcap = snapshot_mcap

            dd = compute_distance_to_default(
                market_cap=scaled_mcap,
                total_debt=total_debt,
                equity_vol=vol,
                risk_free_rate=rf,
            )
            dd_series.append(dd)

        dd_results[issuer] = dd_series

    if not dd_results:
        return pd.DataFrame()

    dd_df = pd.DataFrame(dd_results, index=equity_prices.index)
    dd_df.index.name = "Date"
    return dd_df


# ── MARKET CONTROLS ──────────────────────────────────────────────────────────

def fetch_market_controls(
    start_date: str = "2020-01-01",
    end_date: str | None = None,
    interval: str = "daily",
) -> pd.DataFrame:
    """
    Pull market-level control variables:
    - SPX daily returns (S&P 500 as market control)
    - VIX (volatility index)
    - Risk-free rate from FRED

    Replaces the CDX.IG-based approach (not available in LSEG subscription).
    """
    if end_date is None:
        end_date = datetime.today().strftime("%Y-%m-%d")

    logger.info("Pulling market controls (SPX, VIX, FRED risk-free)...")

    control_rics = {
        "SPX": ".SPX",
        "VIX": ".VIX",
    }

    results = {}
    for name, ric in control_rics.items():
        try:
            df = rd.get_history(
                universe=ric,
                interval=interval,
                start=start_date,
                end=end_date,
            )
            if df is not None and not df.empty:
                close_col = "TRDPRC_1" if "TRDPRC_1" in df.columns else df.columns[0]
                results[name] = df[close_col]
                logger.info(f"  OK: {name}")
            else:
                logger.warning(f"  EMPTY: {name} ({ric})")
        except Exception as e:
            logger.error(f"  ERROR: {name} ({ric}) -- {e}")

    # Add risk-free rate from FRED
    rf = fetch_risk_free_rate(start_date, end_date)
    if not rf.empty:
        results["UST_1Y"] = rf
        logger.info("  OK: UST_1Y (FRED)")

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df.index = pd.to_datetime(df.index)
    df.index.name = "Date"

    # Compute SPX daily return as market control variable
    if "SPX" in df.columns:
        df["SPX_Return"] = df["SPX"].pct_change()

    return df.sort_index()


# ── MAIN PULL ORCHESTRATION ─────────────────────────────────────────────────

def run_full_pull(
    output_dir: str = "data/raw/credit",
    start_date: str = "2020-01-01",
) -> dict[str, pd.DataFrame]:
    """
    Run the complete Merton DD data pull.

    Call this from your LSEG session management wrapper:
        rd.open_session()
        results = run_full_pull()
        rd.close_session()

    Pulls equity prices, debt snapshot, risk-free rate, market controls.
    Computes DD time series. Saves all as parquet.
    """
    import os

    os.makedirs(output_dir, exist_ok=True)

    all_rics = list(ALL_ISSUERS.values())
    results = {}
    today_str = datetime.today().strftime("%Y%m%d")

    # 1. Equity prices
    equity_df = fetch_equity_timeseries(all_rics, start_date=start_date)
    if not equity_df.empty:
        path = f"{output_dir}/equity_prices_{today_str}.parquet"
        equity_df.to_parquet(path)
        logger.info(f"Saved equity prices: {path}")
        results["equity_prices"] = equity_df

    # 2. Debt snapshot
    debt_df = fetch_debt_snapshot(all_rics)
    if not debt_df.empty:
        path = f"{output_dir}/debt_snapshot_{today_str}.parquet"
        debt_df.to_parquet(path)
        logger.info(f"Saved debt snapshot: {path}")
        results["debt_snapshot"] = debt_df

    # 3. Risk-free rate from FRED
    rf_series = fetch_risk_free_rate(start_date)
    if not rf_series.empty:
        rf_df = rf_series.to_frame()
        path = f"{output_dir}/risk_free_rate_{today_str}.parquet"
        rf_df.to_parquet(path)
        logger.info(f"Saved risk-free rate: {path}")
        results["risk_free_rate"] = rf_series

    # 4. Market controls
    ctrl_df = fetch_market_controls(start_date=start_date)
    if not ctrl_df.empty:
        path = f"{output_dir}/market_controls_{today_str}.parquet"
        ctrl_df.to_parquet(path)
        logger.info(f"Saved market controls: {path}")
        results["controls"] = ctrl_df

    # 5. Compute DD time series
    if (
        not equity_df.empty
        and not debt_df.empty
        and not rf_series.empty
    ):
        dd_df = compute_dd_timeseries(equity_df, debt_df, rf_series)
        if not dd_df.empty:
            path = f"{output_dir}/dd_timeseries_{today_str}.parquet"
            dd_df.to_parquet(path)
            logger.info(f"Saved DD time series: {path}")
            results["dd"] = dd_df

    # 6. Generation transitions (static)
    trans_df = pd.DataFrame(GENERATION_TRANSITIONS)
    trans_df["date"] = pd.to_datetime(trans_df["date"])
    path = f"{output_dir}/generation_transitions.parquet"
    trans_df.to_parquet(path)
    results["transitions"] = trans_df

    logger.info("Full Merton DD pull complete.")
    return results
