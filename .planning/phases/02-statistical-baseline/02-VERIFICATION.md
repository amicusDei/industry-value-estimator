---
phase: 02-statistical-baseline
verified: 2026-03-22T00:00:00Z
status: passed
score: 11/11 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 10/11
  gaps_closed:
    - "Residuals from the winning model per segment are saved to data/processed/residuals_statistical.parquet with year-aligned index"
  gaps_remaining: []
  regressions: []
---

# Phase 2: Statistical Baseline Verification Report

**Phase Goal:** Interpretable econometric models produce AI market size baselines and residuals, with documented assumptions and structural break analysis
**Verified:** 2026-03-22T00:00:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (plan 02-05)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | CUSUM test detects structural break in a synthetic series with a known level shift | VERIFIED | `run_cusum` in `structural_breaks.py` uses constant-only OLS residuals + `breaks_cusumolsresid`; `test_cusum_detects_break` confirms p < 0.05 on step-function series |
| 2 | Chow test confirms statistical significance of a break at a known index | VERIFIED | `run_chow` implements manual SSR-based F-test; `test_chow_known_break` passes, `test_chow_no_break` correctly fails to reject on linear series |
| 3 | Markov switching fits a two-regime model and falls back to dummy OLS on convergence failure | VERIFIED | `fit_markov_switching` with 20-obs minimum threshold and `_fallback_dummy_ols`; `test_markov_switching_fits` and `test_markov_fallback` both pass |
| 4 | Model evaluation functions compute RMSE, MAPE, R-squared, AIC/BIC, and Ljung-Box p-value | VERIFIED | All 6 functions in `model_eval.py`; 6 TestModelEval tests pass including AICc > AIC small-N check |
| 5 | PCA composite index is constructed with StandardScaler fitted only on training data | VERIFIED | `build_pca_composite` uses `pipe.fit(indicator_matrix[:train_end_idx])`; `test_pca_no_leakage` asserts `scaler.mean_` matches training-only mean |
| 6 | Manual weights composite produces an alternative index for sensitivity comparison | VERIFIED | `build_manual_composite` standardizes using training-period statistics only |
| 7 | OLS top-down regression fits GDP share model and upgrades to WLS/GLS based on diagnostic tests | VERIFIED | `fit_top_down_ols_with_upgrade` runs BP test (p<0.05 → WLS) and LB test (p<0.05 → GLSAR); `test_ols_upgrade_to_wls_on_heteroscedastic_data` confirms WLS upgrade on synthetic heteroscedastic data |
| 8 | Temporal cross-validation helper produces expanding window folds with no data leakage | VERIFIED | `temporal_cv_generic` uses `TimeSeriesSplit`; `test_temporal_cv_no_overlap` asserts `train_end < test_end` for each fold |
| 9 | ARIMA model fits on each of 4 AI segments with AICc-selected order and produces out-of-sample forecasts | VERIFIED | `select_arima_order` uses `information_criterion="aicc"`, `max_p=2`, `max_q=2`; 5 TestARIMA tests pass |
| 10 | Prophet model fits on each segment with explicit 2022 changepoint and produces forecasts | VERIFIED | `fit_prophet_segment` uses `changepoints=["2022-01-01"]`, `changepoint_prior_scale=0.1`, all seasonality disabled; 4 TestProphet tests pass |
| 11 | Residuals from the winning model per segment are saved to data/processed/residuals_statistical.parquet with year-aligned index | VERIFIED | File exists on disk (3,487 bytes, created 2026-03-22); shape (60, 4); columns year (int64), segment (str), residual (float64), model_type (str); all 4 segments present; no NaN in year column; model_type values are all "Prophet" (Prophet won all 4 segments on synthetic data with structural break at 2022) |

**Score:** 11/11 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/diagnostics/__init__.py` | Package init | VERIFIED | Exists (unchanged from initial verification) |
| `src/diagnostics/structural_breaks.py` | `run_cusum`, `run_chow`, `fit_markov_switching`, `summarize_breaks` | VERIFIED | All 4 functions present, substantive, import `breaks_cusumolsresid` and `MarkovRegression` |
| `src/diagnostics/model_eval.py` | `compute_rmse`, `compute_mape`, `compute_r2`, `compute_aic_bic`, `ljung_box_test`, `compare_models` | VERIFIED | All 6 functions present, `acorr_ljungbox` imported and used |
| `tests/test_diagnostics.py` | 13 unit tests across TestStructuralBreaks + TestModelEval | VERIFIED | 13 tests confirmed; all pass |
| `src/processing/features.py` | `build_indicator_matrix`, `build_pca_composite`, `build_manual_composite`, `assess_stationarity` | VERIFIED | All 4 functions present; `PCA`, `StandardScaler`, `adfuller`, `kpss` all imported and used |
| `src/models/__init__.py` | Package init | VERIFIED | Exists |
| `src/models/statistical/__init__.py` | Package init | VERIFIED | Exists |
| `src/models/statistical/regression.py` | `fit_top_down_ols_with_upgrade`, `temporal_cv_generic` | VERIFIED | Both functions present; imports `OLS`, `WLS`, `GLSAR`, `het_breuschpagan`, `acorr_ljungbox`, `TimeSeriesSplit` |
| `tests/test_features.py` | 12 unit tests for features + regression + CV | VERIFIED | TestBuildIndicatorMatrix, TestPcaComposite, TestManualComposite, TestAssessStationarity, TestRegression, TestTemporalCV all present and passing |
| `src/models/statistical/arima.py` | `select_arima_order`, `fit_arima_segment`, `forecast_arima`, `get_arima_residuals`, `run_arima_cv` | VERIFIED | All 5 functions present; `pm.auto_arima` with `information_criterion="aicc"`, `max_p=2`, `max_q=2`; year index re-alignment confirmed |
| `src/models/statistical/prophet_model.py` | `fit_prophet_segment`, `forecast_prophet`, `get_prophet_residuals`, `run_prophet_cv`, `save_all_residuals` | VERIFIED | All 5 functions present; `changepoints=["2022-01-01"]`, `changepoint_prior_scale=0.1`, `yearly_seasonality=False` |
| `tests/test_models.py` | TestARIMA (5), TestProphet (4), TestResiduals (2) | VERIFIED | 11 tests present and passing |
| `scripts/run_statistical_pipeline.py` | End-to-end pipeline runner, min 80 lines | VERIFIED | 230 lines; imports from `src.models.statistical.arima`, `src.models.statistical.prophet_model`, `src.diagnostics.model_eval`; `__main__` guard present; `run_pipeline()` function is substantive |
| `data/processed/residuals_statistical.parquet` | `year (int), segment (str), residual (float), model_type (str)` | VERIFIED | File on disk at 3,487 bytes; shape (60, 4); all 4 segments; year range 2010-2024; no NaN; model_type in {ARIMA, Prophet}; all schema assertions passed |
| `docs/ASSUMPTIONS.md` | Two-tier structure: TL;DR + detailed appendix | VERIFIED | 366-line file with all 7 required sections and 16 "If this is wrong" sensitivity notes |
| `tests/test_docs.py` | `TestAssumptionsDoc` with 9 completeness tests | VERIFIED | Class present; all 9 tests pass |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `src/diagnostics/structural_breaks.py` | `statsmodels.stats.diagnostic.breaks_cusumolsresid` | import | WIRED | Line 9: `from statsmodels.stats.diagnostic import breaks_cusumolsresid`; used in `run_cusum` |
| `src/diagnostics/structural_breaks.py` | `statsmodels.tsa.regime_switching.markov_regression.MarkovRegression` | import | WIRED | Line 10: `from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression`; used in `fit_markov_switching` |
| `src/diagnostics/model_eval.py` | `statsmodels.stats.diagnostic.acorr_ljungbox` | import | WIRED | Line 3: `from statsmodels.stats.diagnostic import acorr_ljungbox`; used in `ljung_box_test` |
| `src/processing/features.py` | `sklearn.decomposition.PCA` | import | WIRED | Line 17: `from sklearn.decomposition import PCA`; used in `build_pca_composite` Pipeline |
| `src/processing/features.py` | `sklearn.preprocessing.StandardScaler` | import | WIRED | Line 18: `from sklearn.preprocessing import StandardScaler`; used in `build_pca_composite` Pipeline |
| `src/models/statistical/regression.py` | `statsmodels.regression.linear_model` (OLS, WLS, GLSAR) | import | WIRED | Line 18: `from statsmodels.regression.linear_model import GLSAR, OLS, WLS`; all three used in upgrade chain |
| `src/models/statistical/regression.py` | `sklearn.model_selection.TimeSeriesSplit` | import | WIRED | Line 17: `from sklearn.model_selection import TimeSeriesSplit`; used in `temporal_cv_generic` |
| `src/models/statistical/arima.py` | `pmdarima.auto_arima` | import | WIRED | Line 22: `import pmdarima as pm`; `pm.auto_arima` called in `select_arima_order` with `information_criterion="aicc"` |
| `src/models/statistical/arima.py` | `src/models/statistical/regression.py` (temporal_cv_generic) | import | WIRED | Line 25: `from src.models.statistical.regression import temporal_cv_generic`; called in `run_arima_cv` |
| `src/models/statistical/prophet_model.py` | `prophet.Prophet` | import | WIRED | Line 30: `from prophet import Prophet`; used in `fit_prophet_segment` and `run_prophet_cv` |
| `scripts/run_statistical_pipeline.py` | `src/models/statistical/arima.py` | import | WIRED | Lines 52-57: `from src.models.statistical.arima import select_arima_order, fit_arima_segment, get_arima_residuals, run_arima_cv`; all four called in `run_pipeline()` |
| `scripts/run_statistical_pipeline.py` | `src/models/statistical/prophet_model.py` | import | WIRED | Lines 58-63: `from src.models.statistical.prophet_model import fit_prophet_segment, get_prophet_residuals, run_prophet_cv, save_all_residuals`; all four called in `run_pipeline()` |
| `scripts/run_statistical_pipeline.py` | `src/diagnostics/model_eval.py` (compare_models) | import | WIRED | Line 64: `from src.diagnostics.model_eval import compare_models`; called as `compare_models(arima_cv, prophet_cv, seg)` in main loop |
| `data/processed/residuals_statistical.parquet` | Phase 3 ML training | file on disk | WIRED | File exists at `data/processed/residuals_statistical.parquet` (3,487 bytes); Phase 3 LightGBM consumer can read it via `pd.read_parquet` |

Note: Two cosmetic wiring deviations carried over from initial verification remain present and non-blocking — `arima.py` does not import from `model_eval` (RMSE/MAPE computed inline in `temporal_cv_generic`); `prophet_model.py` imports `compute_rmse, compute_mape` but does not call them (inline implementation). Neither affects correctness.

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| MODL-08 | 02-01 | Handle structural breaks (2022-23 GenAI surge) explicitly in models | SATISFIED | CUSUM, Chow, Markov switching with fallback all implemented and tested; 13 structural break tests pass |
| MODL-01 | 02-02, 02-03 | Build statistical baseline model (ARIMA and/or OLS regression) for AI market size estimation | SATISFIED | ARIMA with AICc order selection, OLS with WLS/GLSAR upgrade, and Prophet all implemented; 5+4 model tests pass |
| MODL-06 | 02-02, 02-03 | Implement temporal cross-validation (expanding window, no data leakage) | SATISFIED | `temporal_cv_generic` with `TimeSeriesSplit`, no-leakage PCA pipeline; 2 CV tests + 5 ARIMA CV tests + 4 Prophet CV tests pass |
| MODL-09 | 02-04 | Document all model assumptions, choices, and mathematical foundations | SATISFIED | `docs/ASSUMPTIONS.md` with 16 sensitivity notes, TL;DR, 5 sections, mathematical appendix; 9 automated tests pass |
| ARCH-04 | 02-04 | Documented assumptions file explaining all modeling decisions and their rationale | SATISFIED | `docs/ASSUMPTIONS.md` exists; cross-references `METHODOLOGY.md`; documents ARIMA, Prophet, Markov, PCA choices with failure modes |

All 5 required requirements are accounted for and satisfied. No orphaned requirement IDs found.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/models/statistical/prophet_model.py` | 33 | `from src.diagnostics.model_eval import compute_rmse, compute_mape` — imported but never called | Info | Dead import; inline numpy RMSE/MAPE in `run_prophet_cv` duplicates what model_eval already provides; no functional impact |

No TODO/FIXME/placeholder comments, no stub implementations, no empty return bodies found in any Phase 2 source file including the new `scripts/run_statistical_pipeline.py`.

---

## Human Verification Required

### 1. Structural Break Analysis Against Real Data

**Test:** Run `run_cusum` and `run_chow` on actual AI segment series from `data/processed/` and check whether detected break years cluster around 2022-2023.
**Expected:** CUSUM p-value < 0.05 for at least one segment; Chow break_year in range [2021, 2024].
**Why human:** Tests use only synthetic data; whether the implementation produces meaningful results on real time series cannot be verified programmatically without executing against actual data.

### 2. Markov Switching Convergence on Real Segments

**Test:** Call `fit_markov_switching` on actual 15-25 year AI segment series; check whether it converges or falls back.
**Expected:** If at least some segments are long enough (>= 20 obs), at least one segment should return `model_type = "markov_switching"` rather than fallback.
**Why human:** Whether real data series are long enough to avoid the fallback depends on actual data coverage in `data/processed/`, which is not determinable from file inspection alone.

---

## Re-Verification Summary

**Gap closed:** `data/processed/residuals_statistical.parquet` now exists on disk (3,487 bytes, created 2026-03-22). Plan 02-05 created `scripts/run_statistical_pipeline.py` (230 lines) which generates synthetic data for all 4 AI segments, runs ARIMA vs. Prophet CV comparison per segment, and calls `save_all_residuals` to persist the validated Parquet file.

**Schema confirmed:** year (int64), segment (str), residual (float64), model_type (str) — 60 rows, 4 segments (ai_hardware, ai_infrastructure, ai_software, ai_adoption), year range 2010-2024, zero NaN values.

**No regressions:** Full test suite 151 passed (up from 140 previously, reflecting 11 test_models.py tests that also continue to pass).

**All previously verified truths remain verified.** No regressions detected.

---

_Verified: 2026-03-22T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
