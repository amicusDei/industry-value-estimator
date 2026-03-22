---
phase: 03-ml-ensemble-and-validation
plan: "01"
subsystem: ml-models
tags: [lightgbm, quantile-regression, feature-engineering, temporal-cv, confidence-intervals]
dependency_graph:
  requires:
    - data/processed/residuals_statistical.parquet
    - src/models/statistical/regression.py (temporal_cv_generic)
  provides:
    - src/models/ml/gradient_boost.py (build_residual_features, fit_lgbm_point, lgbm_cv_for_segment)
    - src/models/ml/quantile_models.py (fit_lgbm_quantile, fit_all_quantile_models, QUANTILE_ALPHAS)
  affects:
    - Phase 3 ensemble layer (03-02+) which combines point + quantile outputs
tech_stack:
  added:
    - lightgbm==4.6.0
    - shap==0.51.0
  patterns:
    - Closure-based feature-matrix alignment for temporal_cv_generic reuse
    - TDD red-green for each task
key_files:
  created:
    - src/models/ml/__init__.py
    - src/models/ml/gradient_boost.py
    - src/models/ml/quantile_models.py
    - tests/test_ml_models.py
  modified:
    - pyproject.toml (added lightgbm, shap)
    - uv.lock
decisions:
  - libomp installed via Homebrew — LightGBM macOS dylib requires OpenMP at runtime (blocking dep)
  - Closure with mutable _state dict aligns feature_matrix to temporal_cv_generic y-slice API
  - colsample_bytree omitted from quantile model (not needed for 3-feature matrix; point model retains it for parity with plan spec)
metrics:
  duration: "3 min"
  completed_date: "2026-03-22"
  tasks_completed: 2
  files_changed: 6
---

# Phase 3 Plan 01: LightGBM Point and Quantile Models Summary

**One-liner:** LightGBM point estimator and four quantile regressors trained on residual lag features + year normalisation, with temporal CV reusing the Phase 2 `temporal_cv_generic` scaffold.

## Tasks Completed

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 | Add dependencies and create LightGBM point estimator with feature engineering | d6e0d2f | Done |
| 2 | Build quantile regression models for confidence intervals | 9b77757 | Done |

## What Was Built

### src/models/ml/gradient_boost.py

- `FEATURE_COLS = ["residual_lag1", "residual_lag2", "year_norm"]` — module-level constant
- `build_residual_features(residuals_df)` — per-segment groupby shift(1)/shift(2), year_norm = (year-2010)/14.0, dropna on lag columns only; returns 4×13=52 rows from 4×15=60 input rows
- `fit_lgbm_point(X, y)` — LGBMRegressor with objective="regression", max_depth=3, n_estimators=100, learning_rate=0.05, num_leaves=7, min_child_samples=3, subsample=0.8, colsample_bytree=0.8, random_state=42
- `lgbm_cv_for_segment(residual_series, feature_matrix, n_splits=3)` — closure over feature_matrix with `_state["train_size"]` tracker, delegates to temporal_cv_generic; returns list of fold dicts with rmse/mape keys

### src/models/ml/quantile_models.py

- `QUANTILE_ALPHAS` — `{"ci80_lower": 0.10, "ci80_upper": 0.90, "ci95_lower": 0.025, "ci95_upper": 0.975}`
- `fit_lgbm_quantile(X, y, alpha)` — same hyperparameters as point model but with objective="quantile" and alpha parameter
- `fit_all_quantile_models(X, y)` — iterates QUANTILE_ALPHAS, returns dict of 4 fitted models

### tests/test_ml_models.py

11 tests across 3 classes: TestFeatureEngineering (3), TestLGBMPointModel (3), TestQuantileModels (5). All use synthetic inline fixtures — no live parquet dependency. All 162 project tests pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] libomp missing on macOS**
- **Found during:** Task 1 GREEN phase
- **Issue:** `lightgbm` shared library requires `libomp.dylib` (OpenMP), which is not bundled with the wheel on macOS. `ctypes.LoadLibrary` raised `OSError: Library not loaded: @rpath/libomp.dylib`.
- **Fix:** `brew install libomp` — installs to `/opt/homebrew/Cellar/libomp/22.1.1`, which LightGBM's rpath resolves automatically.
- **Files modified:** None (system-level install)
- **Commit:** d6e0d2f (included in Task 1 commit note)

## Self-Check: PASSED

| Item | Status |
|------|--------|
| src/models/ml/__init__.py | FOUND |
| src/models/ml/gradient_boost.py | FOUND |
| src/models/ml/quantile_models.py | FOUND |
| tests/test_ml_models.py | FOUND |
| Commit d6e0d2f (Task 1) | FOUND |
| Commit 9b77757 (Task 2) | FOUND |
| 162 tests pass | VERIFIED |
