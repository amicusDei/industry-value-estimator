"""
src/empirics/fundamentals_study.py
====================================
Fundamentals-based event study for Dynamic Mismatch paper — Stage 1 + Stage 2.

Stage 1: DiD regression on quarterly fundamental metrics (gross margin, operating
         margin, capex ratio, R&D ratio, SGA ratio, revenue growth) to test whether
         Controllers and Adapters diverge post-generational-transition.

Stage 2: Mispricing test — do firms with deteriorating fundamentals (identified in
         Stage 1) subsequently underperform in equity markets?

Regression specification (Stage 1):
    Y_it = alpha_i + beta1*Post_t*Controller_i + beta2*Post_t*Adapter_i + epsilon_it

Where:
    Y_it     = fundamental metric for issuer i in quarter t
    alpha_i  = issuer fixed effect
    Post_t   = 1 if quarter t is within [0, event_window_quarters] after a transition
    Controller_i = 1 if issuer is a Controller (hyperscaler)
    Adapter_i    = 1 if issuer is an Adapter

Key coefficients:
    beta1: post-transition shift for Controllers
    beta2: post-transition shift for Adapters
"""

import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
import json
import logging
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from src.ingestion.credit_spreads import (
    GROUP_LABELS,
    SECTOR_LABELS,
    GENERATION_TRANSITIONS,
)

logger = logging.getLogger(__name__)

# Metrics to test in Stage 1
STAGE1_METRICS = [
    "gross_margin",
    "operating_margin",
    "capex_ratio",
    "rd_ratio",
    "sga_ratio",
    "revenue_growth_yoy",
]


# ── PANEL CONSTRUCTION ──────────────────────────────────────────────────────

def _snap_to_quarter_end(dt: pd.Timestamp) -> pd.Timestamp:
    """Snap a date to the nearest quarter-end (March, June, Sept, Dec)."""
    quarter_ends = [
        pd.Timestamp(f"{dt.year}-03-31"),
        pd.Timestamp(f"{dt.year}-06-30"),
        pd.Timestamp(f"{dt.year}-09-30"),
        pd.Timestamp(f"{dt.year}-12-31"),
    ]
    # Also consider previous year Q4 and next year Q1
    quarter_ends.append(pd.Timestamp(f"{dt.year - 1}-12-31"))
    quarter_ends.append(pd.Timestamp(f"{dt.year + 1}-03-31"))
    diffs = [abs((dt - qe).days) for qe in quarter_ends]
    return quarter_ends[np.argmin(diffs)]


def build_fundamentals_panel(
    fundamentals_df: pd.DataFrame,
    event_window_quarters: int = 8,
) -> pd.DataFrame:
    """
    Build a regression-ready panel from the long-format fundamentals DataFrame.

    Steps:
    1. Snap each date to nearest quarter-end
    2. Add Group, Sector, Controller, Adapter columns
    3. Map GENERATION_TRANSITIONS to nearest quarter-end
    4. Construct Post_t = 1 for event_window_quarters following each transition
    5. Add interaction terms

    Args:
        fundamentals_df: Long-format DataFrame from fetch_quarterly_fundamentals()
        event_window_quarters: Number of quarters after each transition to flag as Post=1

    Returns:
        Panel DataFrame with event study variables.
    """
    panel = fundamentals_df.copy()

    # Snap dates to quarter-end
    panel["Quarter"] = panel["Date"].apply(_snap_to_quarter_end)

    # Add group labels
    panel["Group"] = panel["Issuer"].map(GROUP_LABELS)
    panel["Sector"] = panel["Issuer"].map(SECTOR_LABELS)
    panel["Controller"] = (panel["Group"] == "controller").astype(int)
    panel["Adapter"] = (panel["Group"] == "adapter").astype(int)

    # Map transition dates to quarter-ends
    transitions = pd.DataFrame(GENERATION_TRANSITIONS)
    transitions["date"] = pd.to_datetime(transitions["date"])
    transitions["quarter"] = transitions["date"].apply(_snap_to_quarter_end)

    # Build list of all post-transition quarters for each event
    all_quarters = sorted(panel["Quarter"].unique())

    panel["Post"] = 0
    panel["Event_Gen"] = np.nan

    for _, row in transitions.iterrows():
        t0_quarter = row["quarter"]
        # Find quarters within the event window
        post_quarters = [
            q for q in all_quarters
            if q >= t0_quarter and _quarter_diff(t0_quarter, q) <= event_window_quarters
        ]
        mask = panel["Quarter"].isin(post_quarters)
        panel.loc[mask, "Post"] = 1
        # Tag with generation (use the latest if overlapping)
        panel.loc[mask, "Event_Gen"] = row["generation"]

    # Interaction terms
    panel["Post_x_Controller"] = panel["Post"] * panel["Controller"]
    panel["Post_x_Adapter"] = panel["Post"] * panel["Adapter"]

    # Issuer fixed effect encoding
    panel["Issuer_FE"] = pd.Categorical(panel["Issuer"])

    logger.info(
        f"Fundamentals panel: {len(panel)} rows, "
        f"{panel['Issuer'].nunique()} issuers, "
        f"Post=1 in {panel['Post'].sum()} rows"
    )
    return panel


def _quarter_diff(q1: pd.Timestamp, q2: pd.Timestamp) -> int:
    """Approximate number of quarters between two dates."""
    days = (q2 - q1).days
    return max(0, round(days / 91.25))


# ── STAGE 1: FUNDAMENTALS DiD ───────────────────────────────────────────────

def run_fundamentals_did(panel: pd.DataFrame) -> dict:
    """
    Stage 1 — Fundamentals DiD regression for each metric.

    For each metric Y in STAGE1_METRICS:
        Y_it = alpha_i + beta1*Post*Controller + beta2*Post*Adapter + epsilon_it

    Clustered SE at issuer level.

    Returns:
        dict mapping metric_name -> {beta1_controller, beta2_adapter, n_obs, r_squared}
    """
    results = {}

    for metric in STAGE1_METRICS:
        sub = panel.dropna(subset=[metric]).copy()
        if len(sub) < 30:
            results[metric] = {"error": f"Too few observations: {len(sub)}"}
            continue

        # Check we have variation in interaction terms
        if sub["Post_x_Controller"].sum() == 0 and sub["Post_x_Adapter"].sum() == 0:
            results[metric] = {"error": "No post-event observations"}
            continue

        try:
            formula = f"{metric} ~ Post_x_Controller + Post_x_Adapter + C(Issuer) - 1"
            model = smf.ols(formula, data=sub).fit(
                cov_type="cluster",
                cov_kwds={"groups": sub["Issuer"]},
            )

            results[metric] = {
                "beta1_controller": _extract_coef(model, "Post_x_Controller"),
                "beta2_adapter": _extract_coef(model, "Post_x_Adapter"),
                "n_obs": int(model.nobs),
                "r_squared": round(float(model.rsquared), 4),
            }
        except Exception as e:
            results[metric] = {"error": str(e)}
            logger.warning(f"Regression failed for {metric}: {e}")

    return results


def _extract_coef(model, key: str) -> dict:
    """Extract coefficient info from a statsmodels result."""
    try:
        return {
            "coef": round(float(model.params.get(key, np.nan)), 6),
            "se": round(float(model.bse.get(key, np.nan)), 6),
            "t_stat": round(float(model.tvalues.get(key, np.nan)), 4),
            "p_value": round(float(model.pvalues.get(key, np.nan)), 6),
            "sig": (
                "***" if model.pvalues.get(key, 1) < 0.01
                else "**" if model.pvalues.get(key, 1) < 0.05
                else "*" if model.pvalues.get(key, 1) < 0.10
                else ""
            ),
        }
    except Exception:
        return {"coef": np.nan, "se": np.nan, "t_stat": np.nan, "p_value": np.nan, "sig": ""}


# ── STAGE 1 BY SECTOR ───────────────────────────────────────────────────────

def run_sector_fundamentals(panel: pd.DataFrame) -> dict:
    """
    Stage 1 by adapter sector.

    For each adapter sector x each metric: run separate regression including
    all controllers + that sector's adapters only.

    Returns:
        nested dict: sector -> metric -> {beta2_adapter coef/t/p}
    """
    adapter_sectors = ["finance", "healthcare", "retail", "telecom"]
    results = {}

    for sector in adapter_sectors:
        results[sector] = {}

        # Filter: controllers + adapters from this sector only
        sector_panel = panel[
            (panel["Group"] == "controller")
            | ((panel["Group"] == "adapter") & (panel["Sector"] == sector))
        ].copy()

        if len(sector_panel) < 30:
            results[sector] = {"error": f"Too few observations: {len(sector_panel)}"}
            continue

        for metric in STAGE1_METRICS:
            sub = sector_panel.dropna(subset=[metric]).copy()
            if len(sub) < 20:
                results[sector][metric] = {"error": f"Too few obs: {len(sub)}"}
                continue

            try:
                formula = f"{metric} ~ Post_x_Controller + Post_x_Adapter + C(Issuer) - 1"
                model = smf.ols(formula, data=sub).fit(
                    cov_type="cluster",
                    cov_kwds={"groups": sub["Issuer"]},
                )
                results[sector][metric] = {
                    "beta2_adapter": _extract_coef(model, "Post_x_Adapter"),
                    "n_obs": int(model.nobs),
                }
            except Exception as e:
                results[sector][metric] = {"error": str(e)}

    return results


# ── STAGE 2: MISPRICING TEST ────────────────────────────────────────────────

def run_mispricing_test(
    fundamentals_panel: pd.DataFrame,
    equity_prices_df: pd.DataFrame,
) -> dict:
    """
    Stage 2 — Mispricing test.

    1. Compute forward 4-quarter equity return for each issuer at each quarter.
    2. Create 'fundamental_deterioration' score: average z-scored change in
       significant Stage 1 metrics.
    3. Regress: Forward_Return = alpha + gamma*FundamentalDeterioration + epsilon
    4. If gamma < 0 and significant: deterioration predicts poor future returns.

    Args:
        fundamentals_panel: Panel from build_fundamentals_panel()
        equity_prices_df: Wide DataFrame with Date index, issuer names as columns
                         (equity prices, e.g. from data/raw/credit/equity_prices.parquet)

    Returns:
        dict with {gamma, t_stat, p_value, n_obs, interpretation}
    """
    try:
        # First run Stage 1 to identify significant metrics
        stage1 = run_fundamentals_did(fundamentals_panel)
        significant_metrics = []
        for metric, res in stage1.items():
            if "error" in res:
                continue
            b2 = res.get("beta2_adapter", {})
            if isinstance(b2, dict) and b2.get("p_value", 1) < 0.10:
                significant_metrics.append(metric)

        if not significant_metrics:
            # Fall back to all metrics if none significant
            significant_metrics = [m for m in STAGE1_METRICS if m in fundamentals_panel.columns]
            logger.info("No individually significant metrics; using all metrics for deterioration score.")

        # Compute quarterly equity returns from price data
        if equity_prices_df.index.name != "Date":
            equity_prices_df = equity_prices_df.set_index("Date") if "Date" in equity_prices_df.columns else equity_prices_df
        equity_prices_df.index = pd.to_datetime(equity_prices_df.index)

        # Resample to quarter-end prices
        quarterly_prices = equity_prices_df.resample("QE").last()

        # Forward 4-quarter return
        fwd_returns = quarterly_prices.pct_change(4).shift(-4)

        # Melt to long format
        fwd_long = fwd_returns.reset_index().melt(
            id_vars=fwd_returns.index.name or "Date",
            var_name="Issuer",
            value_name="Forward_Return",
        )
        date_col = fwd_returns.index.name or "Date"
        fwd_long[date_col] = pd.to_datetime(fwd_long[date_col])
        fwd_long = fwd_long.rename(columns={date_col: "Quarter"})

        # Snap fundamentals panel quarters
        fund_q = fundamentals_panel[["Quarter", "Issuer"] + significant_metrics].copy()
        fund_q = fund_q.drop_duplicates(subset=["Quarter", "Issuer"])

        # Compute z-scored quarter-over-quarter change for each metric
        fund_q = fund_q.sort_values(["Issuer", "Quarter"])
        for m in significant_metrics:
            diff_col = f"{m}_diff"
            fund_q[diff_col] = fund_q.groupby("Issuer")[m].diff()
            # Z-score within each quarter
            fund_q[f"{m}_z"] = fund_q.groupby("Quarter")[diff_col].transform(
                lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0
            )

        # Average z-score across significant metrics = deterioration score
        z_cols = [f"{m}_z" for m in significant_metrics]
        fund_q["fundamental_deterioration"] = fund_q[z_cols].mean(axis=1)

        # Merge with forward returns
        merged = fund_q.merge(fwd_long, on=["Quarter", "Issuer"], how="inner")
        merged = merged.dropna(subset=["fundamental_deterioration", "Forward_Return"])

        if len(merged) < 20:
            return {
                "error": f"Too few observations after merge: {len(merged)}",
                "n_obs": len(merged),
                "significant_metrics_used": significant_metrics,
            }

        # Regression: Forward_Return ~ fundamental_deterioration
        import statsmodels.api as sm

        X = sm.add_constant(merged["fundamental_deterioration"])
        y = merged["Forward_Return"]
        model = sm.OLS(y, X).fit(
            cov_type="cluster",
            cov_kwds={"groups": merged["Issuer"]},
        )

        gamma = float(model.params.get("fundamental_deterioration", np.nan))
        t_stat = float(model.tvalues.get("fundamental_deterioration", np.nan))
        p_value = float(model.pvalues.get("fundamental_deterioration", np.nan))

        interpretation = (
            "Fundamental deterioration PREDICTS poor future returns (mispricing evidence)."
            if gamma < 0 and p_value < 0.10
            else "No significant mispricing detected: deterioration does not predict returns."
        )

        return {
            "gamma": round(gamma, 6),
            "t_stat": round(t_stat, 4),
            "p_value": round(p_value, 6),
            "n_obs": int(model.nobs),
            "r_squared": round(float(model.rsquared), 4),
            "significant_metrics_used": significant_metrics,
            "interpretation": interpretation,
        }

    except Exception as e:
        logger.error(f"Mispricing test failed: {e}")
        return {"error": str(e)}


# ── ORCHESTRATOR ─────────────────────────────────────────────────────────────

def run_full_fundamentals_study(
    fundamentals_df: pd.DataFrame,
    equity_prices_df: pd.DataFrame | None = None,
    event_window_quarters: int = 8,
    output_path: str | None = None,
) -> dict:
    """
    Full fundamentals event study pipeline.

    Stage 1: Fundamentals DiD (all issuers + by sector)
    Stage 2: Mispricing test (if equity_prices_df provided)

    Args:
        fundamentals_df: Long-format fundamentals from fetch_quarterly_fundamentals()
        equity_prices_df: Optional equity prices for Stage 2 mispricing test
        event_window_quarters: Quarters after each transition to flag as Post=1
        output_path: Optional path to save results JSON

    Returns:
        Complete results dict.
    """
    print(f"Building fundamentals panel (event window: {event_window_quarters} quarters)...")
    panel = build_fundamentals_panel(fundamentals_df, event_window_quarters)
    print(
        f"  Panel: {len(panel)} observations, "
        f"{panel['Issuer'].nunique()} issuers, "
        f"{panel['Quarter'].nunique()} quarters"
    )

    # Stage 1: Fundamentals DiD
    print("Running Stage 1 — Fundamentals DiD...")
    stage1_did = run_fundamentals_did(panel)

    print("Running Stage 1 — Sector heterogeneity...")
    stage1_sector = run_sector_fundamentals(panel)

    results = {
        "stage1_did": stage1_did,
        "stage1_sector": stage1_sector,
        "panel_stats": {
            "n_rows": len(panel),
            "n_issuers": int(panel["Issuer"].nunique()),
            "n_quarters": int(panel["Quarter"].nunique()),
            "n_post": int(panel["Post"].sum()),
            "n_controllers": int((panel["Controller"] == 1).sum()),
            "n_adapters": int((panel["Adapter"] == 1).sum()),
            "date_range": {
                "start": str(panel["Quarter"].min().date()),
                "end": str(panel["Quarter"].max().date()),
            },
        },
    }

    # Stage 2: Mispricing test
    if equity_prices_df is not None:
        print("Running Stage 2 — Mispricing test...")
        stage2 = run_mispricing_test(panel, equity_prices_df)
        results["stage2_mispricing"] = stage2
    else:
        print("Skipping Stage 2 (no equity prices provided).")

    # Save results
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        def _json_default(obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.ndarray,)):
                return obj.tolist()
            if isinstance(obj, pd.Timestamp):
                return str(obj)
            return str(obj)

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=_json_default)
        print(f"Results saved to {output_path}")

    return results
