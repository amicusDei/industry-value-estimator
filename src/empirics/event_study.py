"""
src/empirics/event_study.py
============================
Event study + DiD regression for the Dynamic Mismatch paper.

Tests the falsifiable prediction from Section 6.3:
    "Credit spreads on same-generation technology infrastructure assets
    should be cross-sectionally correlated and should widen systematically
    in the quarters following a major generational transition."

Regression specification:
    Δs_it = α_i + β·Post_t + γ·Post_t×Treated_i + δ·Market_t + ε_it

Where:
    Δs_it     = weekly change in CDS 5Y spread for issuer i at time t
    α_i       = issuer fixed effect
    Post_t    = 1 if t is within [0, event_window] days after a transition
    Treated_i = 1 if issuer is in Hyperscaler or DC-REIT group
    Market_t  = CDX.IG 5Y spread (market-wide credit conditions control)

Key coefficient: γ — systematic spread widening in treatment group
    post-transition, above and beyond market-wide movement.
    This is the empirical test of Proposition 1 (systematic risk).
"""

import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
import statsmodels.api as sm
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

from src.ingestion.credit_spreads import GROUP_LABELS, GENERATION_TRANSITIONS


# ── BUILD PANEL ───────────────────────────────────────────────────────────────

def build_panel(
    cds_df: pd.DataFrame,
    controls_df: pd.DataFrame,
    event_window_days: int = 90,
) -> pd.DataFrame:
    """
    Transforms wide CDS data + controls into a long panel DataFrame
    with event study variables constructed.

    Args:
        cds_df:           Wide DataFrame (Date × Issuer) of CDS 5Y spreads
        controls_df:      DataFrame with CDX_IG_5Y, VIX, UST_5Y columns
        event_window_days: Length of Post_t window after each transition

    Returns:
        Long panel DataFrame ready for regression
    """
    # Melt CDS to long format
    panel = cds_df.reset_index().melt(
        id_vars="Date",
        var_name="Issuer",
        value_name="CDS_5Y"
    ).dropna(subset=["CDS_5Y"])

    # Add group labels
    panel["Group"] = panel["Issuer"].map(GROUP_LABELS)
    panel["Treated"] = (panel["Group"].isin(["hyperscaler", "dc_reit"])).astype(int)
    panel["Hyperscaler"] = (panel["Group"] == "hyperscaler").astype(int)
    panel["DC_REIT"] = (panel["Group"] == "dc_reit").astype(int)

    # First difference of CDS spread (weekly change in bps)
    panel = panel.sort_values(["Issuer", "Date"])
    panel["Delta_CDS"] = panel.groupby("Issuer")["CDS_5Y"].diff()

    # Log spread (for percentage interpretation)
    panel["Log_CDS"] = np.log(panel["CDS_5Y"].clip(lower=0.1))

    # Merge market controls
    controls_aligned = controls_df.reindex(cds_df.index, method="ffill")
    controls_aligned = controls_aligned.reset_index()
    panel = panel.merge(controls_aligned, on="Date", how="left")

    # Market control: first difference of CDX.IG
    panel = panel.sort_values(["Issuer", "Date"])
    panel["Delta_CDX"] = panel.groupby("Issuer")["CDX_IG_5Y"].diff()

    # ── CONSTRUCT EVENT STUDY VARIABLES ───────────────────────────────────────

    transitions = pd.DataFrame(GENERATION_TRANSITIONS)
    transitions["date"] = pd.to_datetime(transitions["date"])

    # Post_t: 1 if within event_window_days after ANY transition
    panel["Post"] = 0
    panel["Event_Gen"] = np.nan  # which generation triggered Post=1

    for _, row in transitions.iterrows():
        t0 = row["date"]
        t1 = t0 + pd.Timedelta(days=event_window_days)
        mask = (panel["Date"] >= t0) & (panel["Date"] <= t1)
        panel.loc[mask, "Post"] = 1
        panel.loc[mask, "Event_Gen"] = row["generation"]

    # Interaction term
    panel["Post_x_Treated"] = panel["Post"] * panel["Treated"]
    panel["Post_x_Hyper"]   = panel["Post"] * panel["Hyperscaler"]
    panel["Post_x_REIT"]    = panel["Post"] * panel["DC_REIT"]

    # Issuer fixed effect encoding
    panel["Issuer_FE"] = pd.Categorical(panel["Issuer"])

    # Time fixed effect (year-week)
    panel["YearWeek"] = panel["Date"].dt.to_period("W").astype(str)

    return panel.dropna(subset=["Delta_CDS", "Delta_CDX"])


# ── REGRESSIONS ───────────────────────────────────────────────────────────────

def run_baseline_did(panel: pd.DataFrame) -> sm.regression.linear_model.RegressionResultsWrapper:
    """
    Baseline DiD regression:
        Δs_it = α_i + γ·Post×Treated + δ·ΔMarket + ε_it

    This is the primary test of Proposition 1.
    γ > 0 means treatment group spreads widen more post-transition
    than the control group, after controlling for market-wide credit moves.
    """
    formula = "Delta_CDS ~ Post_x_Treated + Delta_CDX + C(Issuer) - 1"

    model = smf.ols(formula, data=panel).fit(
        cov_type="cluster",
        cov_kwds={"groups": panel["Issuer"]}  # cluster SE at issuer level
    )
    return model


def run_split_treatment(panel: pd.DataFrame) -> sm.regression.linear_model.RegressionResultsWrapper:
    """
    Split treatment group regression — tests whether Hyperscalers
    and DC-REITs show different spread responses:
        Δs_it = α_i + γ1·Post×Hyper + γ2·Post×REIT + δ·ΔMarket + ε_it
    """
    formula = "Delta_CDS ~ Post_x_Hyper + Post_x_REIT + Delta_CDX + C(Issuer) - 1"

    model = smf.ols(formula, data=panel).fit(
        cov_type="cluster",
        cov_kwds={"groups": panel["Issuer"]}
    )
    return model


def run_generation_heterogeneity(panel: pd.DataFrame) -> dict:
    """
    Run separate DiD for each generational transition.
    Tests whether the effect strengthens over successive generations.
    """
    results = {}
    transitions = pd.DataFrame(GENERATION_TRANSITIONS)
    transitions["date"] = pd.to_datetime(transitions["date"])

    for _, row in transitions.iterrows():
        gen = row["generation"]
        event_name = row["event"]

        # Restrict to this event's window
        sub = panel[panel["Event_Gen"] == gen].copy()
        # Add pre-period (90 days before)
        t0 = pd.to_datetime(row["date"])
        pre_start = t0 - pd.Timedelta(days=90)
        pre_panel = panel[
            (panel["Date"] >= pre_start) &
            (panel["Date"] < t0)
        ].copy()
        pre_panel["Post"] = 0
        pre_panel["Post_x_Treated"] = 0

        combined = pd.concat([pre_panel, sub], ignore_index=True)
        combined = combined.dropna(subset=["Delta_CDS", "Delta_CDX"])

        if len(combined) < 30:
            continue

        try:
            formula = "Delta_CDS ~ Post_x_Treated + Delta_CDX + C(Issuer) - 1"
            model = smf.ols(formula, data=combined).fit(
                cov_type="cluster",
                cov_kwds={"groups": combined["Issuer"]}
            )
            results[event_name] = {
                "generation": gen,
                "gamma": model.params.get("Post_x_Treated", np.nan),
                "t_stat": model.tvalues.get("Post_x_Treated", np.nan),
                "p_value": model.pvalues.get("Post_x_Treated", np.nan),
                "n_obs": int(model.nobs),
                "r_squared": model.rsquared,
            }
        except Exception as e:
            results[event_name] = {"error": str(e)}

    return results


def run_cross_sectional_correlation(
    cds_df: pd.DataFrame,
    event_window_days: int = 90
) -> dict:
    """
    Tests Proposition 1 directly: within-group correlation should be
    higher than between-group correlation, especially post-transition.
    """
    transitions = pd.DataFrame(GENERATION_TRANSITIONS)
    transitions["date"] = pd.to_datetime(transitions["date"])

    treatment_issuers = [k for k, v in GROUP_LABELS.items() if v in ["hyperscaler", "dc_reit"]]
    control_issuers   = [k for k, v in GROUP_LABELS.items() if v == "control"]

    # Filter to available columns
    treatment_cols = [c for c in treatment_issuers if c in cds_df.columns]
    control_cols   = [c for c in control_issuers   if c in cds_df.columns]

    results = {}

    for _, row in transitions.iterrows():
        t0 = pd.to_datetime(row["date"])
        t1 = t0 + pd.Timedelta(days=event_window_days)
        event_name = row["event"]

        window = cds_df[(cds_df.index >= t0) & (cds_df.index <= t1)]
        if len(window) < 5:
            continue

        delta = window.diff().dropna()

        def mean_pairwise_corr(cols):
            sub = delta[cols].dropna(axis=1, how="all")
            if sub.shape[1] < 2:
                return np.nan
            corr_mat = sub.corr()
            upper = corr_mat.where(np.triu(np.ones(corr_mat.shape), k=1).astype(bool))
            return upper.stack().mean()

        results[event_name] = {
            "generation":          row["generation"],
            "within_treatment":    mean_pairwise_corr(treatment_cols),
            "within_control":      mean_pairwise_corr(control_cols),
            "cross_group":         delta[treatment_cols + control_cols].corr()
                                       .loc[treatment_cols, control_cols].mean().mean()
                                   if treatment_cols and control_cols else np.nan,
        }

    return results


# ── SUMMARY OUTPUT ────────────────────────────────────────────────────────────

def format_results(
    baseline_model,
    split_model,
    gen_results: dict,
    corr_results: dict,
) -> dict:
    """
    Formats all results into a clean dict for API response or export.
    """
    def safe_params(model, key):
        try:
            return {
                "coef":    round(float(model.params[key]), 4),
                "se":      round(float(model.bse[key]), 4),
                "t_stat":  round(float(model.tvalues[key]), 4),
                "p_value": round(float(model.pvalues[key]), 4),
                "sig":     "***" if model.pvalues[key] < 0.01
                           else "**" if model.pvalues[key] < 0.05
                           else "*"  if model.pvalues[key] < 0.10
                           else "",
            }
        except Exception:
            return {}

    return {
        "baseline_did": {
            "gamma_Post_x_Treated": safe_params(baseline_model, "Post_x_Treated"),
            "delta_Market":         safe_params(baseline_model, "Delta_CDX"),
            "n_obs":    int(baseline_model.nobs),
            "r_squared": round(baseline_model.rsquared, 4),
            "interpretation": (
                "gamma > 0 and significant supports Proposition 1: "
                "systematic spread widening in treatment group post-transition, "
                "above and beyond market-wide credit moves."
            )
        },
        "split_treatment": {
            "gamma_Hyperscaler": safe_params(split_model, "Post_x_Hyper"),
            "gamma_DC_REIT":     safe_params(split_model, "Post_x_REIT"),
            "n_obs":    int(split_model.nobs),
            "r_squared": round(split_model.rsquared, 4),
        },
        "generation_heterogeneity": gen_results,
        "cross_sectional_correlation": corr_results,
    }


# ── MAIN ENTRY POINT ──────────────────────────────────────────────────────────

def run_event_study(
    cds_df: pd.DataFrame,
    controls_df: pd.DataFrame,
    event_window_days: int = 90,
    output_path: str | None = None,
) -> dict:
    """
    Full event study pipeline. Call after data pull.
    """
    print(f"Building panel (event window: {event_window_days} days)...")
    panel = build_panel(cds_df, controls_df, event_window_days)
    print(f"  Panel: {len(panel)} observations, "
          f"{panel['Issuer'].nunique()} issuers, "
          f"{panel['Date'].nunique()} time periods")

    print("Running baseline DiD...")
    baseline = run_baseline_did(panel)

    print("Running split treatment regression...")
    split = run_split_treatment(panel)

    print("Running generation heterogeneity analysis...")
    gen_het = run_generation_heterogeneity(panel)

    print("Running cross-sectional correlation test...")
    corr = run_cross_sectional_correlation(cds_df, event_window_days)

    results = format_results(baseline, split, gen_het, corr)

    if output_path:
        import json
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved to {output_path}")

    return results
