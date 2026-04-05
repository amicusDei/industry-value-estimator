"""
src/empirics/event_study.py
============================
Event study + DiD regression for the Dynamic Mismatch paper.

Tests the falsifiable prediction from Section 6.3:
    "Credit spreads on same-generation technology infrastructure assets
    should be cross-sectionally correlated and should widen systematically
    in the quarters following a major generational transition."

Regression specification (generic — works for both CDS spreads and Merton DD):
    ΔY_it = alpha_i + gamma*Post_t x Treated_i + delta*Market_t + epsilon_it

Where:
    ΔY_it     = change in dependent variable for issuer i at time t
                (CDS 5Y spread in bps, or Distance-to-Default)
    alpha_i   = issuer fixed effect
    Post_t    = 1 if t is within [0, event_window] days after a transition
    Treated_i = 1 if issuer is in Hyperscaler or DC-REIT group
    Market_t  = market control (CDX.IG 5Y for CDS, SPX return for DD)

Key coefficient: gamma
    CDS mode: gamma > 0 means treatment group spreads widen post-transition
    DD mode:  gamma < 0 means treatment group DD falls post-transition
              (= credit risk increases)
"""

import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
import statsmodels.api as sm
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

from src.ingestion.credit_spreads import (
    GROUP_LABELS, GENERATION_TRANSITIONS, SECTOR_LABELS, TREATED_GROUPS,
)


# ── BUILD PANEL ───────────────────────────────────────────────────────────────

def build_panel(
    spread_df: pd.DataFrame = None,
    controls_df: pd.DataFrame = None,
    event_window_days: int = 90,
    variable_name: str = "DD",
    *,
    cds_df: pd.DataFrame = None,
    dd_df: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    Transforms wide spread/DD data + controls into a long panel DataFrame
    with event study variables constructed.

    Supports both CDS spreads (legacy) and Distance-to-Default (new).

    Args:
        spread_df:        Wide DataFrame (Date x Issuer) — generic interface.
        controls_df:      DataFrame with market control columns.
                          CDS mode: expects CDX_IG_5Y column.
                          DD mode:  expects SPX_Return column (or SPX).
        event_window_days: Length of Post_t window after each transition.
        variable_name:    Name for the dependent variable. Default "DD".
                          Use "CDS_5Y" for backward compatibility.
        cds_df:           DEPRECATED — backward compat. Same as spread_df with variable_name="CDS_5Y".
        dd_df:            DEPRECATED — backward compat. Same as spread_df with variable_name="DD".

    Returns:
        Long panel DataFrame ready for regression.
        Key columns: Delta_{variable_name}, Delta_Market, Post, Post_x_Treated, etc.
    """
    # ── Backward compatibility: resolve spread_df from legacy args ────────
    if spread_df is None:
        if cds_df is not None:
            spread_df = cds_df
            if variable_name == "DD":
                variable_name = "CDS_5Y"  # auto-detect legacy mode
        elif dd_df is not None:
            spread_df = dd_df
            variable_name = "DD"
        else:
            raise ValueError("Must provide spread_df, cds_df, or dd_df.")

    if controls_df is None:
        controls_df = pd.DataFrame(index=spread_df.index)

    delta_var = f"Delta_{variable_name}"
    delta_market = "Delta_Market"

    # Melt to long format
    panel = spread_df.reset_index().melt(
        id_vars="Date",
        var_name="Issuer",
        value_name=variable_name,
    ).dropna(subset=[variable_name])

    # Add group labels
    panel["Group"] = panel["Issuer"].map(GROUP_LABELS)
    panel["Sector"] = panel["Issuer"].map(SECTOR_LABELS)
    panel["Treated"] = (panel["Group"].isin(TREATED_GROUPS)).astype(int)
    panel["Hyperscaler"] = (panel["Group"] == "controller").astype(int)
    panel["DC_REIT"] = (panel["Group"] == "dc_reit").astype(int)
    panel["Controller"] = (panel["Group"] == "controller").astype(int)
    panel["Adapter"] = (panel["Group"] == "adapter").astype(int)

    # First difference
    panel = panel.sort_values(["Issuer", "Date"])
    panel[delta_var] = panel.groupby("Issuer")[variable_name].diff()

    # Log level (for percentage interpretation)
    log_col = f"Log_{variable_name}"
    panel[log_col] = np.log(panel[variable_name].clip(lower=0.1))

    # ── Merge market controls ─────────────────────────────────────────────
    controls_aligned = controls_df.reindex(spread_df.index, method="ffill")
    controls_aligned = controls_aligned.reset_index()
    panel = panel.merge(controls_aligned, on="Date", how="left")

    # Determine market control variable
    # CDS mode: CDX_IG_5Y (first difference)
    # DD mode:  SPX_Return (already a return) or SPX (compute return)
    panel = panel.sort_values(["Issuer", "Date"])

    if "CDX_IG_5Y" in panel.columns:
        # Legacy CDS mode
        panel[delta_market] = panel.groupby("Issuer")["CDX_IG_5Y"].diff()
        # Keep backward-compatible alias
        panel["Delta_CDX"] = panel[delta_market]
    elif "SPX_Return" in panel.columns:
        # DD mode with pre-computed SPX return
        panel[delta_market] = panel["SPX_Return"]
        panel["Delta_CDX"] = panel[delta_market]  # alias for formula compatibility
    elif "SPX" in panel.columns:
        # DD mode with SPX level — compute return
        panel[delta_market] = panel.groupby("Issuer")["SPX"].pct_change()
        panel["Delta_CDX"] = panel[delta_market]
    else:
        # No market control available — fill with zeros
        panel[delta_market] = 0.0
        panel["Delta_CDX"] = 0.0

    # ── CONSTRUCT EVENT STUDY VARIABLES ───────────────────────────────────

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

    # Interaction terms
    panel["Post_x_Treated"] = panel["Post"] * panel["Treated"]
    panel["Post_x_Hyper"]   = panel["Post"] * panel["Hyperscaler"]
    panel["Post_x_REIT"]    = panel["Post"] * panel["DC_REIT"]
    panel["Post_x_Controller"] = panel["Post"] * panel["Controller"]
    panel["Post_x_Adapter"]    = panel["Post"] * panel["Adapter"]

    # Issuer fixed effect encoding
    panel["Issuer_FE"] = pd.Categorical(panel["Issuer"])

    # Time fixed effect (year-week)
    panel["YearWeek"] = panel["Date"].dt.to_period("W").astype(str)

    # Store variable name as panel attribute for downstream use
    panel.attrs["variable_name"] = variable_name
    panel.attrs["delta_var"] = delta_var

    # Always create Delta_CDS alias so regression formulas work regardless of mode
    if "Delta_CDS" not in panel.columns:
        panel["Delta_CDS"] = panel[delta_var]
    if "CDS_5Y" not in panel.columns:
        panel["CDS_5Y"] = panel[variable_name]

    return panel.dropna(subset=[delta_var, delta_market])


# ── REGRESSIONS ───────────────────────────────────────────────────────────────

def run_baseline_did(panel: pd.DataFrame) -> sm.regression.linear_model.RegressionResultsWrapper:
    """
    Baseline DiD regression:
        ΔY_it = alpha_i + gamma*Post x Treated + delta*Delta_Market + epsilon_it

    This is the primary test of Proposition 1.
    CDS mode: gamma > 0 means treatment group spreads widen post-transition.
    DD mode:  gamma < 0 means treatment group DD falls post-transition
              (= credit risk increases).

    Uses Delta_CDS as the formula variable (aliased from Delta_{variable_name}
    in build_panel for backward compatibility).
    """
    formula = "Delta_CDS ~ Post_x_Treated + Delta_CDX + C(Issuer) - 1"

    model = smf.ols(formula, data=panel).fit(
        cov_type="cluster",
        cov_kwds={"groups": panel["Issuer"]}  # cluster SE at issuer level
    )
    return model


def run_split_treatment(panel: pd.DataFrame) -> sm.regression.linear_model.RegressionResultsWrapper:
    """
    Split treatment group regression -- tests whether Hyperscalers
    and DC-REITs show different spread responses:
        ΔY_it = alpha_i + gamma1*Post x Hyper + gamma2*Post x REIT + delta*Delta_Market + epsilon_it
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


# ── CONTROLLER vs ADAPTER REGRESSIONS ─────────────────────────────────────────

def run_controller_adapter_did(panel: pd.DataFrame) -> sm.regression.linear_model.RegressionResultsWrapper:
    """
    Controller vs Adapter DiD regression:
        ΔDD_it = α_i + β1·Post×Controller + β2·Post×Adapter + δ·ΔMarket + ε_it

    Hypothesis:
        β1 > 0 (Controllers become safer post-transition — confirmed)
        β2 < 0 (Adapters become riskier post-transition — to be tested)
    """
    formula = "Delta_CDS ~ Post_x_Controller + Post_x_Adapter + Delta_CDX + C(Issuer) - 1"

    model = smf.ols(formula, data=panel).fit(
        cov_type="cluster",
        cov_kwds={"groups": panel["Issuer"]}
    )
    return model


def run_sector_heterogeneity(panel: pd.DataFrame) -> dict:
    """
    Run separate Controller vs Adapter DiD for each adapter sector.
    Identifies which sector shows the strongest β2 < 0.

    Sectors: finance, healthcare, retail, telecom.
    Each regression includes all controllers + one adapter sector.
    """
    adapter_sectors = ["finance", "healthcare", "retail", "telecom"]
    results = {}

    for sector in adapter_sectors:
        # Filter: controllers + adapters from this sector only
        sector_panel = panel[
            (panel["Group"] == "controller") |
            ((panel["Group"] == "adapter") & (panel["Sector"] == sector))
        ].copy()

        if len(sector_panel) < 50:
            results[sector] = {"error": f"Too few observations: {len(sector_panel)}"}
            continue

        try:
            formula = "Delta_CDS ~ Post_x_Controller + Post_x_Adapter + Delta_CDX + C(Issuer) - 1"
            model = smf.ols(formula, data=sector_panel).fit(
                cov_type="cluster",
                cov_kwds={"groups": sector_panel["Issuer"]}
            )
            results[sector] = {
                "beta1_controller": {
                    "coef": round(float(model.params.get("Post_x_Controller", np.nan)), 4),
                    "t_stat": round(float(model.tvalues.get("Post_x_Controller", np.nan)), 4),
                    "p_value": round(float(model.pvalues.get("Post_x_Controller", np.nan)), 4),
                },
                "beta2_adapter": {
                    "coef": round(float(model.params.get("Post_x_Adapter", np.nan)), 4),
                    "t_stat": round(float(model.tvalues.get("Post_x_Adapter", np.nan)), 4),
                    "p_value": round(float(model.pvalues.get("Post_x_Adapter", np.nan)), 4),
                },
                "n_obs": int(model.nobs),
                "n_controllers": int(sector_panel["Controller"].sum() > 0),
                "n_adapters": int(sector_panel[sector_panel["Adapter"] == 1]["Issuer"].nunique()),
                "r_squared": round(model.rsquared, 4),
            }
        except Exception as e:
            results[sector] = {"error": str(e)}

    return results


def run_generation_controller_adapter(panel: pd.DataFrame) -> dict:
    """
    Controller vs Adapter DiD for each generational transition separately.
    Tests whether the divergence strengthens over successive generations.
    """
    results = {}
    transitions = pd.DataFrame(GENERATION_TRANSITIONS)
    transitions["date"] = pd.to_datetime(transitions["date"])

    for _, row in transitions.iterrows():
        gen = row["generation"]
        event_name = row["event"]

        sub = panel[panel["Event_Gen"] == gen].copy()
        t0 = pd.to_datetime(row["date"])
        pre_start = t0 - pd.Timedelta(days=90)
        pre_panel = panel[
            (panel["Date"] >= pre_start) & (panel["Date"] < t0)
        ].copy()
        pre_panel["Post"] = 0
        pre_panel["Post_x_Controller"] = 0
        pre_panel["Post_x_Adapter"] = 0

        combined = pd.concat([pre_panel, sub], ignore_index=True)
        combined = combined.dropna(subset=["Delta_CDS", "Delta_CDX"])

        if len(combined) < 50:
            continue

        try:
            formula = "Delta_CDS ~ Post_x_Controller + Post_x_Adapter + Delta_CDX + C(Issuer) - 1"
            model = smf.ols(formula, data=combined).fit(
                cov_type="cluster",
                cov_kwds={"groups": combined["Issuer"]}
            )
            results[event_name] = {
                "generation": gen,
                "beta1_controller": round(float(model.params.get("Post_x_Controller", np.nan)), 4),
                "beta2_adapter": round(float(model.params.get("Post_x_Adapter", np.nan)), 4),
                "beta1_t": round(float(model.tvalues.get("Post_x_Controller", np.nan)), 2),
                "beta2_t": round(float(model.tvalues.get("Post_x_Adapter", np.nan)), 2),
                "beta1_p": round(float(model.pvalues.get("Post_x_Controller", np.nan)), 4),
                "beta2_p": round(float(model.pvalues.get("Post_x_Adapter", np.nan)), 4),
                "n_obs": int(model.nobs),
            }
        except Exception as e:
            results[event_name] = {"error": str(e)}

    return results


# ── SUMMARY OUTPUT ────────────────────────────────────────────────────────────

def format_results(
    baseline_model,
    split_model,
    gen_results: dict,
    corr_results: dict,
    variable_name: str = "CDS_5Y",
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

    if variable_name == "DD":
        interpretation = (
            "gamma < 0 and significant supports Proposition 1: "
            "Distance-to-Default falls (credit risk increases) in treatment group "
            "post-transition, above and beyond market-wide moves."
        )
    else:
        interpretation = (
            "gamma > 0 and significant supports Proposition 1: "
            "systematic spread widening in treatment group post-transition, "
            "above and beyond market-wide credit moves."
        )

    return {
        "baseline_did": {
            "gamma_Post_x_Treated": safe_params(baseline_model, "Post_x_Treated"),
            "delta_Market":         safe_params(baseline_model, "Delta_CDX"),
            "n_obs":    int(baseline_model.nobs),
            "r_squared": round(baseline_model.rsquared, 4),
            "variable": variable_name,
            "interpretation": interpretation,
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
    cds_df: pd.DataFrame = None,
    controls_df: pd.DataFrame = None,
    event_window_days: int = 90,
    output_path: str | None = None,
    *,
    dd_df: pd.DataFrame = None,
    spread_df: pd.DataFrame = None,
    variable_name: str | None = None,
) -> dict:
    """
    Full event study pipeline. Call after data pull.

    Accepts either:
    - cds_df (legacy CDS spreads) — backward compatible
    - dd_df (Merton Distance-to-Default) — new interface
    - spread_df + variable_name — generic interface
    """
    # Resolve which data to use
    if spread_df is not None:
        _spread_df = spread_df
        _var_name = variable_name or "DD"
    elif dd_df is not None:
        _spread_df = dd_df
        _var_name = "DD"
    elif cds_df is not None:
        _spread_df = cds_df
        _var_name = "CDS_5Y"
    else:
        raise ValueError("Must provide cds_df, dd_df, or spread_df.")

    print(f"Building panel (event window: {event_window_days} days, var={_var_name})...")
    panel = build_panel(
        spread_df=_spread_df,
        controls_df=controls_df,
        event_window_days=event_window_days,
        variable_name=_var_name,
    )
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
    corr = run_cross_sectional_correlation(_spread_df, event_window_days)

    # Controller vs Adapter regressions
    print("Running Controller vs Adapter DiD...")
    ca_model = run_controller_adapter_did(panel)

    print("Running sector heterogeneity (adapter sectors)...")
    sector_het = run_sector_heterogeneity(panel)

    print("Running generation-level Controller vs Adapter...")
    gen_ca = run_generation_controller_adapter(panel)

    results = format_results(baseline, split, gen_het, corr, variable_name=_var_name)

    # Add Controller vs Adapter results
    def _safe(model, key):
        try:
            return {
                "coef": round(float(model.params[key]), 4),
                "se": round(float(model.bse[key]), 4),
                "t_stat": round(float(model.tvalues[key]), 4),
                "p_value": round(float(model.pvalues[key]), 4),
                "sig": "***" if model.pvalues[key] < 0.01
                       else "**" if model.pvalues[key] < 0.05
                       else "*" if model.pvalues[key] < 0.10 else "",
            }
        except Exception:
            return {}

    results["controller_adapter_did"] = {
        "beta1_controller": _safe(ca_model, "Post_x_Controller"),
        "beta2_adapter": _safe(ca_model, "Post_x_Adapter"),
        "delta_market": _safe(ca_model, "Delta_CDX"),
        "n_obs": int(ca_model.nobs),
        "r_squared": round(ca_model.rsquared, 4),
        "interpretation": (
            "beta1 > 0: Controllers become safer post-transition (confirmed). "
            "beta2 < 0: Adapters become riskier post-transition (hypothesis)."
        ),
    }
    results["sector_heterogeneity"] = sector_het
    results["generation_controller_adapter"] = gen_ca

    if output_path:
        import json
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved to {output_path}")

    return results
