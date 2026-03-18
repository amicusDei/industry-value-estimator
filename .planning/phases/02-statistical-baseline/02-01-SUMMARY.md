---
phase: 02-statistical-baseline
plan: "01"
subsystem: diagnostics
tags: [structural-breaks, cusum, chow-test, markov-switching, model-eval, rmse, mape, aic, ljung-box, statsmodels]
dependency_graph:
  requires: []
  provides:
    - src/diagnostics/structural_breaks.py
    - src/diagnostics/model_eval.py
  affects:
    - All Phase 2 model fitting plans (ARIMA, Prophet, OLS regression)
    - Phase 3 ML layer (consumes model evaluation metrics)
tech_stack:
  added:
    - statsmodels>=0.14.6
    - prophet>=1.3.0
    - scikit-learn>=1.8.0
    - pmdarima>=2.1.1
  patterns:
    - constant-only OLS for CUSUM (higher power for level-shift detection vs. trend-detrended)
    - manual SSR-based Chow F-test via scipy.stats.f.cdf
    - MarkovRegression(k_regimes=2, switching_variance=False) with convergence fallback to dummy OLS
    - AICc = AIC + 2k(k+1)/(n-k-1) for small-N correction
    - acorr_ljungbox(return_df=True) for residual autocorrelation
key_files:
  created:
    - src/diagnostics/__init__.py
    - src/diagnostics/structural_breaks.py
    - src/diagnostics/model_eval.py
    - tests/test_diagnostics.py
  modified:
    - pyproject.toml
    - uv.lock
decisions:
  - "constant-only OLS for CUSUM: linear trend detrending absorbs level shifts and loses detection power; constant-only (ddof=1) achieves p<0.05 on step-function series"
  - "Markov switching minimum series length set to 20 observations: fewer obs cause EM non-convergence; fallback captures series of any length"
  - "AICc used instead of AIC in compute_aic_bic: required for small N (n-k-1 denominator grows materially at n<50)"
metrics:
  duration: 4 minutes
  completed_date: "2026-03-18"
  tasks_completed: 2
  files_created: 4
  files_modified: 2
---

# Phase 2 Plan 1: Install Dependencies and Build Diagnostics Subsystem Summary

Phase 2 dependencies installed (statsmodels, prophet, scikit-learn, pmdarima) and a fully-tested `src/diagnostics/` package built with structural break detection (CUSUM + Chow + Markov switching with fallback) and six model evaluation metric functions used by every subsequent modeling plan.

## What Was Built

### src/diagnostics/structural_breaks.py

Four functions:

- **run_cusum(series)** — CUSUM test using constant-only OLS residuals. Returns `{"stat", "p_value", "critical_values"}`.
- **run_chow(series, break_idx)** — Manual SSR-based Chow F-test. Returns `{"F_stat", "p_value", "break_year"}`.
- **fit_markov_switching(series)** — Two-regime MarkovRegression with fallback to dummy-variable OLS on short series or convergence failure. Returns `{"model_type", "results", "regimes", "transition_matrix"}`.
- **summarize_breaks(segment_results)** — Aggregates per-segment break detection into a uniform summary dict.

### src/diagnostics/model_eval.py

Six functions:

- **compute_rmse** — `sqrt(mean((actual - predicted)^2))`
- **compute_mape** — `mean(|actual - predicted| / actual) * 100` with zero-guard
- **compute_r2** — `1 - SS_res / SS_tot`
- **compute_aic_bic** — Returns AIC, BIC, and AICc from residuals and parameter count
- **ljung_box_test** — Wraps `statsmodels.stats.diagnostic.acorr_ljungbox`
- **compare_models** — Compares ARIMA vs. Prophet CV fold results; returns winner and margin_pct

## Tests

13 tests in `tests/test_diagnostics.py`:
- 7 `TestStructuralBreaks` tests covering output shapes, level-shift detection, known break significance, no-break scenario, Markov fit, Markov fallback, and summarize_breaks
- 6 `TestModelEval` tests covering each metric function plus compare_models winner logic

Full suite: 131 tests pass, 0 failures, 0 regressions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CUSUM implementation using trend OLS had insufficient power for level-shift detection**

- **Found during:** Task 1 GREEN phase
- **Issue:** The plan's action specified fitting `y = a + b*t` (trend OLS, `ddof=2`) before passing residuals to `breaks_cusumolsresid`. For a pure step-function series (the test case), the linear trend absorbs the level shift, producing symmetric tent-shaped CUSUM residuals. The `sup_b` statistic reached only ~1.06, giving `p_value ≈ 0.21` — failing the behavior requirement of `p_value < 0.05`.
- **Fix:** Changed to constant-only OLS (`y = a`, `ddof=1`). The mean-detrended residuals preserve the level-shift signal. `stat = 2.18`, `p_value = 0.00015` on the test series.
- **Statistical justification:** For level-shift detection, trend detrending removes the very signal CUSUM is looking for. The RESEARCH.md notes low power for CUSUM under linear exog — this is the exact scenario. Constant-only is the standard approach for mean-shift detection.
- **Files modified:** `src/diagnostics/structural_breaks.py`
- **Commit:** ea23061

## Self-Check: PASSED

All 5 created/modified files confirmed present on disk. All 3 task commits confirmed in git history. 131 tests pass.
