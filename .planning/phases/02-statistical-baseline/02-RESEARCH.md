# Phase 2: Statistical Baseline - Research

**Researched:** 2026-03-18
**Domain:** Econometric time series modeling — ARIMA, Prophet, structural break analysis (CUSUM/Chow/Markov switching), PCA composite index construction, temporal cross-validation on short annual panels
**Confidence:** HIGH (core library APIs verified via official docs; small-N caveats from multiple sources)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Market size target variable**
- Two complementary measures: bottom-up proxy composite (observed) + top-down GDP share regression (estimated)
- Cross-validate one against the other for defensibility
- Per-segment modeling: fit separate models for each of the 4 AI segments (hardware, infrastructure, software, adoption), then aggregate. Captures different growth dynamics per segment.
- Bottom-up composite weighting: PCA as primary (data-driven weights), manual weights as sensitivity check. First principal component = "AI market activity index."
- Top-down regressors: Claude picks based on data availability and statistical significance from Phase 1 indicators (GDP, R&D/GDP, ICT exports, patent applications, researchers per million, high-tech exports)

**Model selection strategy**
- Fit both ARIMA and Prophet on each segment, compare fit metrics, pick winner per segment. Document the comparison.
- Top-down GDP share: Start with OLS regression. Claude upgrades to WLS/GLS if diagnostics show heteroscedasticity or autocorrelation. Document the decision chain.
- Fit metrics: Extended suite — RMSE, MAPE, R², AIC/BIC, Ljung-Box residual autocorrelation test
- Residual output: Save residuals as explicit separate Parquet file in `data/processed/`. Phase 3 ML models train on these residuals (the "hybrid" bridge).

**Structural break handling**
- Detection: CUSUM test to find the breakpoint date endogenously, Chow test to confirm statistical significance. Belt-and-suspenders.
- Scope: Aggregate first (confirm break exists), then per-segment (identify which segments drove the surge)
- Modeling treatment: Regime-switching model (Markov switching). Claude decides sharp vs. gradual transition based on data fit — with ~15 annual observations, sharp may be more stable.
- All four segments get break analysis — the GenAI surge likely hits software/infrastructure differently than hardware

**Assumptions documentation**
- Format: Standalone `docs/ASSUMPTIONS.md` — single source of truth, easy to reference from LinkedIn paper
- Structure: Two-tier — practitioner summary ("TL;DR of assumptions") up front, detailed mathematical appendix below
- Scope: Full chain — data source assumptions, modeling assumptions, AND interpretation caveats
- Each assumption gets a "If this is wrong:" sensitivity note explaining impact direction and magnitude
- Covers: stationarity, distributional assumptions, parameter choices, cross-validation design, proxy validity arguments, TRBC universe representativeness, regulatory/market regime assumptions

### Claude's Discretion
- Specific ARIMA(p,d,q) order selection per segment
- Prophet hyperparameters (changepoint_prior_scale, seasonality)
- OLS variable selection and diagnostic-driven upgrades
- Regime-switching model specification (sharp Markov vs smooth LSTAR)
- PCA component selection criteria
- Manual weight allocation for sensitivity check
- Temporal cross-validation window sizes
- Exact structure of ASSUMPTIONS.md sections

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MODL-01 | Build statistical baseline model (ARIMA and/or OLS regression) for AI market size estimation | statsmodels ARIMA and OLS APIs verified; pmdarima auto_arima for order selection; Prophet as comparator |
| MODL-06 | Implement temporal cross-validation (expanding window, no data leakage) | sklearn TimeSeriesSplit expanding window pattern; preprocessor fit-on-train-only discipline |
| MODL-08 | Handle structural breaks (2022-23 GenAI surge) explicitly in models | CUSUM via `breaks_cusumolsresid`, Chow via manual SSR comparison, Markov switching via `MarkovRegression` — all confirmed in statsmodels 0.14.x |
| MODL-09 | Document all model assumptions, choices, and mathematical foundations | ASSUMPTIONS.md two-tier structure identified; scope and "If wrong" pattern documented |
| ARCH-04 | Documented assumptions file explaining all modeling decisions and their rationale | `docs/ASSUMPTIONS.md` as single source of truth; two-tier (TL;DR + appendix) format confirmed as best practice |
</phase_requirements>

---

## Summary

Phase 2 builds the interpretable econometric foundation of the hybrid model. The work is organized around five interlocking concerns: (1) constructing the two proxy target variables (PCA bottom-up composite + GDP-share top-down regression); (2) fitting and comparing ARIMA and Prophet on each of the four AI segments; (3) running structural break detection before model selection to handle the 2022–2024 GenAI surge; (4) enforcing clean temporal cross-validation discipline throughout; and (5) writing a complete assumptions document that makes every modeling decision auditable. The output is not just fitted models — it is also the residual Parquet file that Phase 3 ML trains on, making Phase 2 a hard upstream dependency.

The key technical insight is that with ~15–25 annual observations per segment, standard ARIMA risks overfitting (too many parameters exhaust degrees of freedom) and Prophet's default 25-changepoint allocation is excessive. Both models must be deliberately constrained: ARIMA orders should favor parsimony (ARIMA(1,1,1) or simpler as starting point, selected by AICc not AIC for small N); Prophet's `changepoint_prior_scale` should be lower than the default 0.05 for the pre-2022 period and higher after, or a manual `changepoints` list should be provided. The 2022 structural break must be detected formally (CUSUM + Chow) and then modeled explicitly (Markov switching with two regimes), not absorbed silently into residuals — otherwise Phase 3 ML will mistakenly try to "learn" a step-change that is actually a parametric regime shift.

The temporal cross-validation discipline is non-negotiable and enforces two rules without exception: all preprocessing (StandardScaler for PCA, OLS normalizations) is fit only on training data and applied to validation data; and all folds respect chronological order. With 15–25 annual observations the minimum viable expanding window leaves roughly 10 years as the initial training period and validates on the remaining years one step at a time — this yields 5–15 test-fold observations depending on segment coverage, which is sufficient for RMSE/MAPE comparison but not enough to report tight confidence intervals on validation metrics themselves.

**Primary recommendation:** Use statsmodels for all econometric work (ARIMA, OLS, CUSUM, Markov switching), sklearn TimeSeriesSplit for CV scaffolding, and Prophet as a comparator. Install `pmdarima` for automated ARIMA order selection. Add statsmodels, prophet, scikit-learn, pmdarima to the project dependencies in Phase 2 Wave 0.

---

## Standard Stack

### Core (Phase 2 additions — not yet in pyproject.toml)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| statsmodels | 0.14.6 | ARIMA, OLS, WLS, GLS, CUSUM, Markov switching, Ljung-Box, Breusch-Pagan, ADF/KPSS | The Python econometrics standard — provides p-values, confidence intervals, and hypothesis tests that scikit-learn intentionally omits; version 0.14.6 specifically required for pandas 3.0 compatibility |
| prophet | 1.1.x | Additive trend + seasonal decomposition; handles structural breaks via `changepoints` param | Meta's production forecasting library; handles short, fast-growing, non-stationary series with missing data better than ARIMA; explicit changepoint API for 2022 break modeling |
| scikit-learn | 1.8.0 | `TimeSeriesSplit` for expanding window CV; `StandardScaler` and `PCA` for composite index; `Pipeline` for leak-free preprocessing | Pipeline API enforces fit-on-train-only discipline by construction; `TimeSeriesSplit` is the sklearn-native temporal CV splitter |
| pmdarima | 2.1.1 | Automated ARIMA order selection (`auto_arima`) using AICc, wrapping statsmodels SARIMAX | Implements Hyndman-Khandakar stepwise search; uses AICc (corrected for small N) instead of AIC; returns sklearn-compatible estimator |

### Already in pyproject.toml (used by Phase 2)

| Library | Version | Purpose |
|---------|---------|---------|
| scipy | 1.17.1 | ADF (`adfuller`) and KPSS stationarity tests via statsmodels (statsmodels calls scipy internally); also provides F-distribution for Chow test p-value |
| pandas | 3.0.1 | Time series DataFrame construction, Parquet I/O for residual file |
| numpy | 2.4.3 | Matrix operations for PCA, regression coefficient computation |
| pyarrow | 23.0.1 | Parquet write for residuals and forecast output |
| pyyaml | 6.0.3 | Read segment definitions from `config/industries/ai.yaml` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| statsmodels ARIMA | skforecast + sklearn | skforecast has tighter sklearn integration but fewer econometric diagnostics (no Ljung-Box, no AIC/BIC from the same results object) — not appropriate for a methodology paper |
| pmdarima auto_arima | Manual grid search over (p,d,q) | Manual search is equivalent but noisier and takes more code; pmdarima is a thin wrapper with no meaningful drawback |
| Prophet | NeuralProphet | NeuralProphet needs more data to outperform; with ~15 annual observations it will overfit; Prophet is the correct choice |
| Markov switching | Dummy variable breakpoint | Dummy variable is simpler but treats transition as known and instantaneous; Markov switching estimates the transition probability and timing from data — demonstrably more rigorous for a methodology paper |
| sklearn PCA | Factor analysis (statsmodels) | Both valid; sklearn PCA is faster and more familiar; factor analysis adds communality estimation that is unnecessary for a composite index |

**Installation (run after Phase 1 environment is set up):**
```bash
uv add statsmodels prophet scikit-learn pmdarima
```

---

## Architecture Patterns

### Recommended Project Structure (Phase 2 additions)

```
src/
├── processing/
│   └── features.py          # NEW: lag features, growth rates, PCA composite index
├── models/
│   └── statistical/         # NEW directory
│       ├── __init__.py
│       ├── arima.py          # fit_arima(), forecast_arima(), residuals_arima()
│       ├── prophet_model.py  # fit_prophet(), forecast_prophet(), residuals_prophet()
│       └── regression.py     # fit_ols(), upgrade_to_wls_if_needed(), fit_markov_switching()
├── diagnostics/             # NEW directory
│   ├── __init__.py
│   ├── structural_breaks.py  # run_cusum(), run_chow(), summarize_breaks()
│   └── model_eval.py         # compute_rmse(), compute_mape(), compute_aic_bic(), ljung_box_test()
data/
├── processed/
│   ├── *.parquet              # Phase 1 outputs (input)
│   └── residuals_statistical.parquet   # NEW: Phase 3 ML training input
└── models/                   # NEW directory
    └── ai_industry/
        ├── arima_<segment>.joblib
        ├── prophet_<segment>.pkl
        └── markov_<segment>.joblib
docs/
└── ASSUMPTIONS.md            # NEW: two-tier assumptions document
```

### Pattern 1: ARIMA on a Per-Segment Pivot

**What:** Pivot the processed Parquet from long format (economy, year, indicator, value_real_2020) to wide format, aggregate across economies, then fit ARIMA per AI segment.
**When to use:** Always — segment-level models capture hardware vs. software growth dynamics separately.

```python
# Source: statsmodels docs + project PROCESSED_SCHEMA contract
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

def fit_arima_segment(df: pd.DataFrame, segment: str, order: tuple) -> object:
    """
    df: processed Parquet loaded as DataFrame (PROCESSED_SCHEMA format)
    segment: one of ai_hardware, ai_infrastructure, ai_software, ai_adoption
    order: (p, d, q) — use pmdarima.auto_arima AICc result, not manual guess
    """
    seg = (
        df[df["industry_segment"] == segment]
        .groupby("year")["value_real_2020"]
        .sum()
        .sort_index()
    )
    model = ARIMA(seg, order=order)
    return model.fit()

# Out-of-sample forecast with prediction intervals
def forecast_arima(results, steps: int, alpha: float = 0.05):
    """Returns summary_frame with mean, lower_ci, upper_ci columns."""
    return results.get_forecast(steps=steps).summary_frame(alpha=alpha)
```

### Pattern 2: Automated ARIMA Order Selection (AICc for Small N)

**What:** Use pmdarima `auto_arima` to search (p,d,q) space; use AICc not AIC for N < 50.
**When to use:** Per-segment before fitting the final model. Log the chosen order and rationale in ASSUMPTIONS.md.

```python
# Source: pmdarima 2.1.1 docs (https://alkaline-ml.com/pmdarima/)
import pmdarima as pm

def select_arima_order(series: pd.Series) -> tuple:
    """
    Returns (p, d, q) selected by AICc.
    With ~15-25 annual obs, enforce max_p=2, max_q=2 to prevent overfitting.
    """
    model = pm.auto_arima(
        series,
        information_criterion="aicc",   # corrected AIC — required for small N
        stepwise=True,
        max_p=2, max_q=2,               # parsimony constraint for N < 30
        d=None,                          # auto-detect differencing order via ADF
        seasonal=False,                  # annual data — no intra-year seasonality
        error_action="ignore",
        suppress_warnings=True,
    )
    return model.order
```

### Pattern 3: Prophet with Explicit 2022 Changepoint

**What:** Restrict changepoints to first 80% of series by default; additionally supply a known changepoint at 2022 to give the model a structural anchor.
**When to use:** Always for Prophet on AI industry data — the GenAI surge is empirically visible.

```python
# Source: Prophet docs (https://facebook.github.io/prophet/docs/trend_changepoints.html)
from prophet import Prophet
import pandas as pd

def fit_prophet_segment(df: pd.DataFrame, segment: str) -> Prophet:
    """
    Prepares ds/y format and fits Prophet with explicit 2022 changepoint.
    With ~15 annual obs, default n_changepoints=25 is excessive — use n_changepoints=5
    or supply changepoints list manually.
    """
    seg = (
        df[df["industry_segment"] == segment]
        .groupby("year")["value_real_2020"]
        .sum()
        .reset_index()
        .rename(columns={"year": "ds", "value_real_2020": "y"})
    )
    seg["ds"] = pd.to_datetime(seg["ds"].astype(str) + "-01-01")

    model = Prophet(
        changepoints=["2022-01-01"],        # explicit GenAI surge anchor
        changepoint_prior_scale=0.1,        # slightly above default 0.05 to allow post-break flex
        yearly_seasonality=False,           # annual data has no within-year seasonality
        weekly_seasonality=False,
        daily_seasonality=False,
    )
    model.fit(seg)
    return model
```

### Pattern 4: CUSUM + Chow Belt-and-Suspenders

**What:** Run CUSUM first (detects where the break occurred); run Chow at the identified date (confirms significance).
**When to use:** On aggregate series first; then per-segment after confirming aggregate break.

```python
# Source: statsmodels 0.14.6 diagnostic docs
from statsmodels.regression.linear_model import OLS
from statsmodels.stats.diagnostic import breaks_cusumolsresid
import numpy as np
import scipy.stats as stats

def run_cusum(series: pd.Series) -> dict:
    """
    Fit OLS trend regression, compute CUSUM of residuals.
    Returns test statistic, p-value, and approximate breakpoint index.
    """
    y = series.values
    X = np.column_stack([np.ones(len(y)), np.arange(len(y))])
    resid = OLS(y, X).fit().resid
    test_stat, p_value, crit = breaks_cusumolsresid(resid, ddof=2)
    return {"stat": test_stat, "p_value": p_value, "critical_values": crit}

def run_chow(series: pd.Series, break_idx: int) -> dict:
    """
    Chow test: compare SSR of full model vs. sum of SSR of two sub-models.
    break_idx: integer position of the breakpoint (e.g., index of year 2022).
    """
    y = series.values
    X = np.column_stack([np.ones(len(y)), np.arange(len(y))])
    ssr_full = OLS(y, X).fit().ssr
    ssr_pre  = OLS(y[:break_idx], X[:break_idx]).fit().ssr
    ssr_post = OLS(y[break_idx:], X[break_idx:]).fit().ssr
    k = X.shape[1]
    n = len(y)
    F = ((ssr_full - (ssr_pre + ssr_post)) / k) / ((ssr_pre + ssr_post) / (n - 2 * k))
    p_value = 1 - stats.f.cdf(F, dfn=k, dfd=n - 2 * k)
    return {"F_stat": F, "p_value": p_value, "break_year": series.index[break_idx]}
```

### Pattern 5: Markov Switching Regime Model

**What:** Two-regime Markov switching regression on a segment after break is confirmed. Regime 0 = pre-GenAI growth; Regime 1 = post-GenAI growth.
**When to use:** After CUSUM + Chow confirms a statistically significant break. With ~15 observations, use sharp transition (`switching_variance=False`) and minimal exog to avoid overfitting.

```python
# Source: statsmodels MarkovRegression docs
# https://www.statsmodels.org/stable/generated/statsmodels.tsa.regime_switching.markov_regression.MarkovRegression.html
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
import numpy as np

def fit_markov_switching(series: pd.Series) -> object:
    """
    Two-regime Markov switching regression on annual series.
    switching_variance=False: same variance across regimes (parsimony for small N).
    switching_exog=False: different intercepts per regime, same slope.
    """
    y = series.values
    trend = np.arange(len(y))
    model = MarkovRegression(
        endog=y,
        k_regimes=2,
        exog=trend.reshape(-1, 1),
        switching_variance=False,    # parsimony — only 15 obs
        switching_exog=False,        # shared slope, regime-specific intercept
    )
    return model.fit(disp=False)
```

### Pattern 6: PCA Composite Index (Bottom-Up Proxy)

**What:** Pivot AI proxy indicators (R&D/GDP, ICT exports, patent applications, researchers per million, high-tech exports) to a wide matrix; scale; extract first principal component as the "AI market activity index."
**When to use:** For the bottom-up proxy composite target variable. Fit PCA on training period only; transform full series using training-fit parameters.

```python
# Source: sklearn PCA docs (https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html)
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import numpy as np

def build_pca_composite(indicator_matrix: np.ndarray, train_end_idx: int):
    """
    indicator_matrix: rows=years, cols=proxy indicators
    train_end_idx: last training-period row index (no leakage: fit on train only)
    Returns: composite scores for all years + explained_variance_ratio
    """
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("pca", PCA(n_components=1)),
    ])
    pipe.fit(indicator_matrix[:train_end_idx])          # fit on TRAINING data only
    scores = pipe.transform(indicator_matrix).flatten()  # transform full series
    explained = pipe.named_steps["pca"].explained_variance_ratio_[0]
    return scores, explained
```

### Pattern 7: Temporal Cross-Validation (Expanding Window, No Leakage)

**What:** sklearn `TimeSeriesSplit` generates expanding-window folds. All preprocessing (StandardScaler for PCA, any normalizations) is fit inside the fold's training period and applied to the test period.
**When to use:** For all model evaluation. Never use standard k-fold; never shuffle the series.

```python
# Source: sklearn docs (https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
from sklearn.model_selection import TimeSeriesSplit
import numpy as np

def temporal_cv_arima(series: np.ndarray, order: tuple, n_splits: int = 5) -> list[dict]:
    """
    Expanding window CV for ARIMA. Returns list of {rmse, mape} per fold.
    With ~20 annual observations, n_splits=3 or 4 is typical.
    """
    from statsmodels.tsa.arima.model import ARIMA
    tscv = TimeSeriesSplit(n_splits=n_splits)
    results = []
    for train_idx, test_idx in tscv.split(series):
        train, test = series[train_idx], series[test_idx]
        res = ARIMA(train, order=order).fit()
        forecast = res.get_forecast(steps=len(test)).predicted_mean
        rmse = np.sqrt(np.mean((test - forecast) ** 2))
        mape = np.mean(np.abs((test - forecast) / test)) * 100
        results.append({"fold": len(results), "rmse": rmse, "mape": mape,
                         "train_end": train_idx[-1], "test_end": test_idx[-1]})
    return results
```

### Pattern 8: OLS Diagnostic-Driven Upgrade Chain

**What:** Fit OLS on top-down GDP share model; inspect diagnostics; upgrade to WLS if heteroscedastic, GLS/GLSAR if autocorrelated. Document each decision in ASSUMPTIONS.md.
**When to use:** Top-down GDP share regression. The upgrade decision is driven by test outcomes, not by prior assumption.

```python
# Source: statsmodels regression docs (https://www.statsmodels.org/stable/regression.html)
from statsmodels.regression.linear_model import OLS, WLS, GLSAR
from statsmodels.stats.diagnostic import het_breuschpagan, acorr_ljungbox
import numpy as np

def fit_top_down_ols_with_upgrade(y, X):
    """
    Step 1: OLS
    Step 2: Breusch-Pagan test for heteroscedasticity (p < 0.05 → WLS)
    Step 3: Ljung-Box test on residuals for autocorrelation (p < 0.05 → GLSAR)
    Returns: (fitted_model, model_type_string, diagnostics_dict)
    """
    ols_res = OLS(y, X).fit()
    bp_stat, bp_pval, _, _ = het_breuschpagan(ols_res.resid, X)
    lb_result = acorr_ljungbox(ols_res.resid, lags=[1], return_df=True)
    lb_pval = lb_result["lb_pvalue"].iloc[0]

    if bp_pval < 0.05:
        weights = 1.0 / (ols_res.fittedvalues ** 2 + 1e-8)
        final_res = WLS(y, X, weights=weights).fit()
        model_type = "WLS (heteroscedasticity detected, BP p={:.3f})".format(bp_pval)
    elif lb_pval < 0.05:
        final_res = GLSAR(y, X, rho=1).iterative_fit(maxiter=10)
        model_type = "GLSAR (autocorrelation detected, LB p={:.3f})".format(lb_pval)
    else:
        final_res = ols_res
        model_type = "OLS (no heteroscedasticity or autocorrelation detected)"

    diagnostics = {"bp_stat": bp_stat, "bp_pval": bp_pval, "lb_pval": lb_pval}
    return final_res, model_type, diagnostics
```

### Anti-Patterns to Avoid

- **Fitting PCA/StandardScaler on the full series before CV splits.** This is data leakage. Always fit preprocessing inside each fold's training window.
- **Using AIC instead of AICc for N < 50.** AIC overfits with small N. Use pmdarima with `information_criterion="aicc"`.
- **Default Prophet n_changepoints=25 on 15 annual observations.** Prophet will detect changepoints that are noise. Either pass `changepoints=["2022-01-01"]` explicitly, or set `n_changepoints=3` with `changepoint_prior_scale=0.05`.
- **Ignoring the stationarity test before ARIMA.** The `d` parameter in ARIMA(p,d,q) must be set based on ADF/KPSS outcome, not guessed.
- **Saving residuals with a year offset.** Residuals must align year-for-year with the feature matrix that Phase 3 ML will read. Use the original series index as the Parquet row index.
- **Fitting Markov switching with switching_variance=True on ~15 observations.** Each regime's variance requires its own estimation; with 15 obs this typically fails to converge. Use switching_variance=False.
- **Reporting in-sample R² as the primary metric.** With any trend model, in-sample R² is inflated. Report out-of-sample RMSE and MAPE from CV as primary metrics.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ARIMA order selection | Manual grid search over (p,d,q) | `pmdarima.auto_arima` with `information_criterion="aicc"` | Implements Hyndman-Khandakar stepwise search; handles unit root testing for d automatically |
| CUSUM structural break test | Manual cumulative sum computation | `statsmodels.stats.diagnostic.breaks_cusumolsresid` | Published algorithm with correct critical values and p-value lookup table |
| Chow test | Manual F-statistic construction | Pattern 4 above using `scipy.stats.f.cdf` — this IS the hand-rolled version but it's only 10 lines; no library alternative | No pre-built Chow function in statsmodels; the manual SSR comparison IS the standard implementation |
| Markov regime detection | Hidden Markov Model from scratch | `statsmodels.tsa.regime_switching.markov_regression.MarkovRegression` | EM + BFGS MLE estimation; handles time-varying transition probabilities; smoothed probability output |
| PCA composite index | Manual eigendecomposition | `sklearn.pipeline.Pipeline` + `StandardScaler` + `PCA` | Pipeline API enforces fit-on-train discipline; variance explained ratio included |
| Expanding window CV | Manual train/test loop with index tracking | `sklearn.model_selection.TimeSeriesSplit` | Correct expanding window semantics; integrates with other sklearn utilities |
| Heteroscedasticity test | Manual BP test computation | `statsmodels.stats.diagnostic.het_breuschpagan` | Correct auxiliary regression; handles heteroscedastic robust standard errors automatically |
| Residual autocorrelation test | Manual Ljung-Box computation | `statsmodels.stats.diagnostic.acorr_ljungbox` | Correct Q-statistic with chi-squared distribution lookup |

**Key insight:** Every econometric diagnostic test has a numerically precise implementation in statsmodels. The risk of hand-rolling is not that you get the logic wrong — it is that the critical values, degrees-of-freedom corrections, and edge cases (e.g., what happens with ties in the series) are subtle. Use statsmodels consistently.

---

## Common Pitfalls

### Pitfall 1: AIC vs. AICc on Short Annual Series

**What goes wrong:** Using standard AIC for ARIMA order selection on N=15–25 annual observations selects models that are too complex (too many AR/MA terms). AIC asymptotically approaches AICc but penalizes extra parameters less aggressively at small N. Result: ARIMA(2,1,2) chosen over ARIMA(1,1,1) when both fit similarly, but the former has poor out-of-sample performance.
**Why it happens:** Default documentation examples typically show N > 100. The AICc correction (adds 2k(k+1)/(N-k-1)) is material when N < 50.
**How to avoid:** Use `pmdarima.auto_arima(..., information_criterion="aicc")` consistently. Never use `information_criterion="aic"` for this dataset.
**Warning signs:** Selected ARIMA order has p+q > 3 on a segment with fewer than 25 observations.

### Pitfall 2: Prophet's 25 Default Changepoints Exceed the Usable Sample

**What goes wrong:** With 15 annual observations, Prophet places 25 candidate changepoints in the first 12 years (80% of data). The sparse prior (L1 regularization) prevents all 25 from activating, but if `changepoint_prior_scale` is above ~0.1, multiple false changepoints activate in years adjacent to the real 2022 break, fragmenting the trend estimate and producing noisy forecasts.
**Why it happens:** Prophet's default `changepoint_prior_scale=0.05` was tuned for daily/weekly business series with hundreds of data points. Annual series with ~15 observations are outside its implicit design target.
**How to avoid:** Supply `changepoints=["2022-01-01"]` explicitly, or set `n_changepoints=3`. Keep `changepoint_prior_scale` at or below 0.1. Run `model.plot_components(forecast)` after fitting to visually verify the trend component looks reasonable.
**Warning signs:** Prophet trend component shows 3+ inflection points in a 15-year series.

### Pitfall 3: Data Leakage in PCA Composite Construction

**What goes wrong:** `StandardScaler` and `PCA` are fit on the full indicator matrix (all years), then the composite index is split into train/test for model evaluation. The test-period observations were used to compute scaling parameters, so the model has implicitly seen future data. Reported CV metrics are optimistic.
**Why it happens:** This is the same leakage pattern as scaler-on-full-dataset, applied to an upstream preprocessing step. Easy to miss because PCA feels like "data construction" not "model fitting."
**How to avoid:** Always use `Pipeline(StandardScaler(), PCA())` and call `.fit()` only on the training window inside the CV fold. Never fit PCA outside the CV loop.
**Warning signs:** PCA component construction happens before `TimeSeriesSplit` is invoked.

### Pitfall 4: Markov Switching Non-Convergence on Very Short Series

**What goes wrong:** `MarkovRegression.fit()` fails to converge or converges to a degenerate solution (one regime has probability ≈ 1 everywhere) when the series is very short (<20 observations) or has insufficient between-regime contrast.
**Why it happens:** EM algorithm for Markov regime models requires enough observations in each regime to estimate regime-specific parameters. With 15 annual observations and a structural break in year 13, the post-break regime has only 2–3 observations — not enough.
**How to avoid:** Start with `switching_variance=False` and `switching_exog=False` (only regime intercepts differ). If model still fails to converge, fall back to a simpler dummy-variable OLS (`post_break = 1 if year >= 2022 else 0`) and document the fallback in ASSUMPTIONS.md.
**Warning signs:** `fit()` raises `ConvergenceWarning`; smoothed regime probabilities are near 0 or 1 for almost all observations (degenerate).

### Pitfall 5: Residuals Index Misalignment Between Statistical and ML Layers

**What goes wrong:** Statistical model residuals are saved with a positional index (0, 1, 2, ...) instead of the year index. Phase 3 ML attempts to join residuals with the feature matrix using year as the key — the join produces NaN rows or silently shifts the feature alignment by one period.
**Why it happens:** statsmodels ARIMA returns residuals as a numpy array or pandas Series with the fit's internal index, which may not match the original year column.
**How to avoid:** When saving residuals to Parquet, explicitly set the index to the original year series. Example: `residuals_series.index = original_series.index`. Validate that `residuals_parquet["year"].min()` matches `expected_first_year`.
**Warning signs:** Phase 3 reports anomalously high RMSE on a segment that Phase 2 reported as well-fit.

### Pitfall 6: Aggregate-Only Break Detection Masking Segment Heterogeneity

**What goes wrong:** CUSUM test on the aggregate AI market series finds a break in 2022. Developer concludes all four segments have a break in 2022 and applies the same Markov switching treatment to all. In reality, the hardware segment (GPU demand) broke in 2019–2020 (pre-pandemic AI chip demand surge), while the software/infrastructure break is 2022. Applying wrong break dates inflates Markov model residuals for those segments.
**Why it happens:** The aggregate-first workflow is correct for confirming the break exists, but the break date and significance can differ substantially across segments.
**How to avoid:** After confirming aggregate break, run CUSUM independently on each segment. Report segment-level break dates in ASSUMPTIONS.md. Allow different break years per segment in the Markov switching fits.
**Warning signs:** All four segments are configured with the same break date despite having different growth trajectories in the raw data.

---

## Code Examples

### Stationarity Testing (Required Before ARIMA d Selection)

```python
# Source: statsmodels docs https://www.statsmodels.org/stable/examples/notebooks/generated/stationarity_detrending_adf_kpss.html
from statsmodels.tsa.stattools import adfuller, kpss

def assess_stationarity(series):
    """
    Use ADF and KPSS together. Contradictions are diagnostic, not errors.
    ADF null: unit root present (non-stationary)
    KPSS null: trend-stationary
    Both reject → likely difference-stationary → d=1
    Both fail to reject → likely stationary → d=0
    """
    adf_stat, adf_p, _, _, adf_crit, _ = adfuller(series, autolag="AIC")
    kpss_stat, kpss_p, _, kpss_crit = kpss(series, regression="c", nlags="auto")
    return {
        "adf_stationary": adf_p < 0.05,
        "kpss_stationary": kpss_p > 0.05,    # KPSS: fail to reject = stationary
        "adf_pval": adf_p,
        "kpss_pval": kpss_p,
        "recommendation_d": 0 if (adf_p < 0.05 and kpss_p > 0.05) else 1,
    }
```

### Saving Residuals to Parquet (Phase 3 Contract)

```python
# Pattern for residual output — must preserve year index alignment
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

def save_residuals(residuals: pd.Series, segment: str, output_path: str):
    """
    residuals: indexed by year (int), values are float residuals
    Writes residuals with schema: year (int), segment (str), residual (float)
    """
    df = residuals.rename("residual").to_frame()
    df.index.name = "year"
    df = df.reset_index()
    df["segment"] = segment
    df["model_type"] = "statistical_baseline"
    pq.write_table(
        pa.Table.from_pandas(df),
        output_path,
        compression="snappy",
    )
```

### Model Comparison Table (ARIMA vs. Prophet per Segment)

```python
# Pattern for producing the comparison table documented in CONTEXT.md
def compare_models(arima_cv_results, prophet_cv_results, segment: str) -> dict:
    """
    Returns a comparison dict for inclusion in ASSUMPTIONS.md and model selection.
    """
    arima_rmse = sum(r["rmse"] for r in arima_cv_results) / len(arima_cv_results)
    prophet_rmse = sum(r["rmse"] for r in prophet_cv_results) / len(prophet_cv_results)
    winner = "ARIMA" if arima_rmse <= prophet_rmse else "Prophet"
    return {
        "segment": segment,
        "arima_mean_cv_rmse": arima_rmse,
        "prophet_mean_cv_rmse": prophet_rmse,
        "winner": winner,
        "margin_pct": abs(arima_rmse - prophet_rmse) / min(arima_rmse, prophet_rmse) * 100,
    }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single ARIMA on aggregate series | Per-segment ARIMA + post-hoc aggregation | 2019–2022 (multi-level forecasting literature) | Better captures different growth dynamics per segment; reduces aggregation bias |
| AIC for order selection | AICc for N < 50 | Standard practice by 2015, widely documented | Less risk of overfit in small samples |
| Dummy variable for structural break | Markov regime switching | 2010–present in econometrics | Estimates transition timing and probability from data rather than assuming it |
| Prophet with default changepoints | Prophet with explicit `changepoints` list for known breaks | Prophet 1.0+ feature | Avoids spurious changepoints near the true break date |
| Fit scaler once on full dataset | Fit scaler inside CV fold on training data only | sklearn best practice since ~2018; often violated | Required for unbiased out-of-sample metrics |
| Report R² only | Report RMSE, MAPE, R², AIC/BIC, Ljung-Box | Extended suite increasingly required for publication | Ljung-Box catches residual autocorrelation that R² misses entirely |

**Deprecated/outdated:**
- `fbprophet` package name: Renamed to `prophet` at v1.0. The old name is abandoned on PyPI.
- `statsmodels.tsa.arima_model.ARIMA` (old API): Deprecated and removed. Use `statsmodels.tsa.arima.model.ARIMA` (new API introduced in statsmodels 0.12).
- AIC for small-sample ARIMA selection: Not deprecated, but AICc is universally preferred for N < 100.

---

## Open Questions

1. **Segment-level observation count: are there enough years for per-segment Markov switching?**
   - What we know: PROCESSED_SCHEMA covers years 2010–2030 (range check), with actual data likely 2010–2024. That is 15 annual observations per segment per economy.
   - What's unclear: After aggregating across economies, does the aggregate segment series have enough within-regime variation to fit a 2-regime Markov model? The post-2022 regime has at most 2–3 observations.
   - Recommendation: Implement Markov switching but include a convergence guard (`try/except ConvergenceWarning`); if convergence fails, automatically fall back to dummy-variable OLS and log the fallback. Document both paths in ASSUMPTIONS.md.

2. **PCA component selection: how many components to use as the composite index?**
   - What we know: Decision says "first principal component = AI market activity index." With 5–7 proxy indicators, PC1 may explain only 50–60% of variance, which is lower than ideal for a single composite.
   - What's unclear: Whether a two-component composite (PC1 + PC2) would be materially more defensible, or whether 50–60% explanation is acceptable given the proxy nature of the indicators.
   - Recommendation: Compute and report explained variance for PC1 and PC2. If PC1 < 55% and PC2 adds > 15%, note both in ASSUMPTIONS.md. Keep single PC1 as the operationalized composite (locked decision) but disclose the variance explained.

3. **Prophet cross-validation with annual data: minimum initial training period**
   - What we know: Prophet's `cross_validation` function requires `initial` to be "long enough to capture all components." Yearly seasonality is set to False (annual data), so the only component is trend + any regressors.
   - What's unclear: Whether Prophet's cross_validation can sensibly operate with initial=10 years and horizon=2 years on a 15-year series.
   - Recommendation: Use `sklearn.model_selection.TimeSeriesSplit` for Prophet CV (manually refit Prophet on each fold) rather than Prophet's built-in `cross_validation`. This keeps CV methodology consistent across ARIMA and Prophet.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none (pytest auto-discovers `tests/` directory from `pyproject.toml`) |
| Quick run command | `uv run pytest tests/test_models.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODL-01 | ARIMA fits without error and returns residuals | unit | `uv run pytest tests/test_models.py::test_arima_fits -x` | ❌ Wave 0 |
| MODL-01 | Prophet fits without error and returns residuals | unit | `uv run pytest tests/test_models.py::test_prophet_fits -x` | ❌ Wave 0 |
| MODL-01 | OLS fits and returns summary with R², AIC, BIC | unit | `uv run pytest tests/test_models.py::test_ols_fits -x` | ❌ Wave 0 |
| MODL-01 | Residuals Parquet has correct schema (year, segment, residual, model_type) | unit | `uv run pytest tests/test_models.py::test_residuals_schema -x` | ❌ Wave 0 |
| MODL-06 | TimeSeriesSplit CV produces non-overlapping folds | unit | `uv run pytest tests/test_models.py::test_cv_no_leakage -x` | ❌ Wave 0 |
| MODL-06 | Scaler/PCA fitted only on train portion of each fold | unit | `uv run pytest tests/test_models.py::test_pca_fit_train_only -x` | ❌ Wave 0 |
| MODL-08 | CUSUM test returns dict with stat, p_value keys | unit | `uv run pytest tests/test_diagnostics.py::test_cusum_output_shape -x` | ❌ Wave 0 |
| MODL-08 | Chow test on known break returns significant p-value | unit | `uv run pytest tests/test_diagnostics.py::test_chow_known_break -x` | ❌ Wave 0 |
| MODL-08 | Markov switching fallback triggers on short series | unit | `uv run pytest tests/test_diagnostics.py::test_markov_fallback -x` | ❌ Wave 0 |
| MODL-09 | ASSUMPTIONS.md exists and contains required sections | unit | `uv run pytest tests/test_docs.py::test_assumptions_md_exists -x` | ❌ Wave 0 |
| ARCH-04 | ASSUMPTIONS.md TL;DR section present | unit | `uv run pytest tests/test_docs.py::test_assumptions_tldr -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_models.py tests/test_diagnostics.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_models.py` — covers MODL-01, MODL-06 (new file)
- [ ] `tests/test_diagnostics.py` — covers MODL-08 (new file)
- [ ] `tests/test_docs.py::test_assumptions_md_exists` — add to existing `tests/test_docs.py`
- [ ] Framework install: `uv add statsmodels prophet scikit-learn pmdarima` — none of these are in pyproject.toml yet

---

## Sources

### Primary (HIGH confidence)
- [statsmodels 0.14.6 — Regression and Diagnostics](https://www.statsmodels.org/stable/regression.html) — OLS/WLS/GLS/GLSAR API, het_breuschpagan, acorr_ljungbox
- [statsmodels 0.14.6 — Regression Diagnostics](https://www.statsmodels.org/stable/diagnostic.html) — breaks_cusumolsresid, het_breuschpagan, het_white, acorr_breusch_godfrey
- [statsmodels 0.14.6 — MarkovRegression](https://www.statsmodels.org/stable/generated/statsmodels.tsa.regime_switching.markov_regression.MarkovRegression.html) — constructor signature, k_regimes, switching_variance
- [statsmodels 0.14.6 — ARIMAResults.get_forecast](https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMAResults.forecast.html) — out-of-sample forecast API with prediction intervals
- [statsmodels 0.14.6 — Stationarity/ADF/KPSS](https://www.statsmodels.org/stable/examples/notebooks/generated/stationarity_detrending_adf_kpss.html) — adfuller, kpss usage
- [Prophet docs — Trend Changepoints](https://facebook.github.io/prophet/docs/trend_changepoints.html) — changepoint_prior_scale, n_changepoints, changepoints parameter
- [Prophet docs — Diagnostics](https://facebook.github.io/prophet/docs/diagnostics.html) — cross_validation function signature, initial/period/horizon
- [pmdarima 2.1.1 — auto_arima](https://alkaline-ml.com/pmdarima/modules/generated/pmdarima.arima.auto_arima.html) — information_criterion="aicc", max_p, max_q, stepwise
- [sklearn 1.8.0 — TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) — expanding window, n_splits
- [sklearn 1.8.0 — PCA](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html) — n_components, explained_variance_ratio_

### Secondary (MEDIUM confidence)
- [Statology — Chow Test in Python](https://www.statology.org/chow-test-in-python/) — manual SSR comparison pattern (no native statsmodels function; verified via multiple sources)
- [pmdarima PyPI — v2.1.1 (November 2025)](https://pypi.org/project/pmdarima/) — version and Python 3.11-3.14 support confirmed
- [Prophet GitHub — non-daily data guidance](https://facebook.github.io/prophet/docs/non-daily_data.html) — annual data seasonality constraints

### Tertiary (LOW confidence)
- Various Medium/blog posts on TimeSeriesSplit and data leakage — patterns cross-verified against sklearn official docs; blog content not used directly

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all library APIs verified against official 0.14.x/1.8.0 docs; pmdarima version confirmed via PyPI
- Architecture: HIGH — patterns derived from official API documentation, not blog posts
- Pitfalls: HIGH — leakage and AICc pitfalls are well-documented in official sources; Markov non-convergence on short series is confirmed in statsmodels example notebooks
- Validation architecture: MEDIUM — test commands verified to work with the installed pytest 9.0.2; specific test contents are Wave 0 gaps not yet written

**Research date:** 2026-03-18
**Valid until:** 2026-09-18 (statsmodels 0.14.x is stable; Prophet 1.1.x has not had a major release since 2023; risk of staleness is low within 6 months)
