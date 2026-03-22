---
phase: 03-ml-ensemble-and-validation
plan: "03"
subsystem: ml-pipeline
tags: [lightgbm, joblib, shap, parquet, ensemble, quantile-regression, forecasting]

requires:
  - phase: 03-01
    provides: LightGBM point estimator, quantile models, CV scaffold
  - phase: 03-02
    provides: ensemble combiner, forecast engine, SHAP attribution, CI bounds
  - phase: 02-statistical-baseline
    provides: residuals_statistical.parquet (training input)

provides:
  - scripts/run_ensemble_pipeline.py: single-command end-to-end pipeline runner
  - data/processed/forecasts_ensemble.parquet: 84-row Phase 4 dashboard input (4 segments x 21 years)
  - models/ai_industry/*.joblib: 21 serialized LightGBM models (point + 4 quantiles per segment + weights)
  - models/ai_industry/shap_summary.png: SHAP beeswarm summary plot
  - tests/test_serialization.py: joblib round-trip and parquet schema tests

affects: [04-dashboard, 05-reports]

tech-stack:
  added: [joblib (serialization)]
  patterns:
    - sys.path injection in script header for direct python invocation
    - constant forward-projection lag features for forecast horizon
    - inverse-RMSE ensemble weighting with std(residuals) as statistical baseline RMSE

key-files:
  created:
    - scripts/run_ensemble_pipeline.py
    - tests/test_serialization.py
  modified: []

key-decisions:
  - "Statistical baseline RMSE computed as std(residuals): the statistical model's predicted correction of its own residuals is zero, so residual std is the natural RMSE baseline for inverse-RMSE weighting"
  - "Forecast features use constant forward projection: last two known residuals projected flat for all forecast years — valid no-information extrapolation for mean-reverting residuals"
  - "Historical period in forecast DataFrame uses raw residual values as point estimates (centered around 0) representing the correction signal; actual market values come from source data for dashboard"
  - "joblib.dump handles all model serialization — .joblib files are gitignored per project convention (models/**/*.joblib)"

patterns-established:
  - "Pipeline runner pattern: sys.path injection -> load artifacts -> per-segment loop -> serialize -> save parquet -> print summary"
  - "Forecast horizon feature building: _build_forecast_features extracts last two residuals as constant lag values + year_norm for future years"

requirements-completed: [MODL-02, MODL-03, MODL-04, MODL-05, MODL-07]

duration: 2min
completed: 2026-03-22
---

# Phase 3 Plan 03: Pipeline Runner and Serialization Summary

**End-to-end ensemble pipeline that trains LightGBM + quantile models, blends with inverse-RMSE ensemble, forecasts 2025-2030, serializes 21 joblib models, saves SHAP PNG, and writes forecasts_ensemble.parquet for Phase 4 dashboard consumption.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-22T12:59:43Z
- **Completed:** 2026-03-22T13:01:43Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Single command `uv run python scripts/run_ensemble_pipeline.py` produces all Phase 3 artifacts from residuals_statistical.parquet
- forecasts_ensemble.parquet (84 rows, 10 columns) with all required schema columns including dual units (real 2020 + nominal), 4 CI bounds, and data_vintage
- 21 serialized .joblib files: 5 per segment (point + 4 quantiles) across 4 segments + 1 ensemble weights file
- 4 serialization tests all green; full 193-test suite remains green

## Task Commits

1. **Task 1: Pipeline runner and serialization tests** - `d08c169` (feat)

**Plan metadata:** _(final docs commit pending)_

_Note: TDD task; tests (RED) passed immediately since imported modules already existed — proceeded directly to GREEN (pipeline implementation)._

## Files Created/Modified

- `scripts/run_ensemble_pipeline.py` - End-to-end pipeline runner: load residuals -> per-segment LightGBM CV + fit -> forecast 2025-2030 -> SHAP -> serialize (joblib) -> save parquet
- `tests/test_serialization.py` - Joblib round-trip tests for LGBMRegressor and weights dict; parquet schema (10-column) and no-NaN checks

## Decisions Made

- Statistical baseline RMSE = std(residuals): because the statistical model's residuals are the LightGBM target, the "statistical forecast" of residuals is zero, making residual std the correct baseline RMSE for inverse-RMSE weighting
- Constant forward projection for forecast features: lag1 = last residual, lag2 = second-to-last residual, projected flat for 2025-2030 — no-information extrapolation appropriate for mean-reverting residuals
- Historical rows in forecast DataFrame use raw residual values (correction signal near 0) — Phase 4 dashboard will overlay actual market data from source parquet

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — residuals_statistical.parquet was already present from Phase 2. All Phase 3 plan 01 and 02 modules imported correctly without modification.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `data/processed/forecasts_ensemble.parquet` ready for Phase 4 dashboard to consume directly
- All 4 segments covered (ai_hardware, ai_infrastructure, ai_software, ai_adoption), years 2010-2030
- Serialized models in `models/ai_industry/` available for inference without re-training
- SHAP summary plot available for methodology reports in Phase 5
- Phase 3 is fully complete — all 3 plans executed

---
*Phase: 03-ml-ensemble-and-validation*
*Completed: 2026-03-22*
