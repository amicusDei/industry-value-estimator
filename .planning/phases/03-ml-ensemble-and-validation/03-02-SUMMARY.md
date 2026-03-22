---
phase: 03-ml-ensemble-and-validation
plan: 02
subsystem: ml
tags: [lightgbm, shap, ensemble, forecast, confidence-intervals, inverse-rmse]

# Dependency graph
requires:
  - phase: 03-01
    provides: LightGBM point model (fit_lgbm_point), quantile models (fit_all_quantile_models), FEATURE_COLS
  - phase: 02-statistical-baseline
    provides: compute_rmse from model_eval.py for weight computation
provides:
  - Per-segment inverse-RMSE ensemble weighting (compute_ensemble_weights)
  - Additive blend combiner (blend_forecasts)
  - Full forecast DataFrame with dual units, CI bounds, vintage, is_forecast flag
  - SHAP TreeExplainer attribution + PNG summary plot
affects: [04-dashboard, 05-reports]

# Tech tracking
tech-stack:
  added: [shap]
  patterns:
    - Inverse-RMSE weighting with epsilon guard for zero RMSE edge case
    - Additive ensemble (stat_pred + lgbm_weight * correction), not convex blend
    - Monotonic CI clipping via min/max cascade
    - 2.5% annual CAGR as inflation proxy for nominal USD conversion
    - Matplotlib Agg backend for headless SHAP plot export

key-files:
  created:
    - src/models/ensemble.py
    - src/inference/__init__.py
    - src/inference/forecast.py
    - src/inference/shap_analysis.py
    - tests/test_ensemble.py
    - tests/test_forecast_output.py
    - tests/test_shap.py
  modified: []

key-decisions:
  - "Additive blend (stat_pred + lgbm_weight * correction) confirmed — LightGBM corrects statistical residuals, not a parallel full forecast"
  - "2.5% annual CAGR as inflation proxy for real-to-nominal conversion — upgradeable to live World Bank deflator when available"
  - "Epsilon guard (1e-10) in compute_ensemble_weights prevents division by zero when RMSE=0, zero-RMSE model receives near-infinite weight"
  - "matplotlib.use('Agg') called inside save_shap_summary_plot to keep headless-safe without forcing global backend change at import time"

patterns-established:
  - "Monotonic CI clipping: ci95_lower = min(ci95_lower, ci80_lower, point); ci80_lower = min(ci80_lower, point); ci80_upper = max(ci80_upper, point); ci95_upper = max(ci95_upper, ci80_upper)"
  - "data_vintage column embedded in every DataFrame row as str (not just metadata) per MODL-04"
  - "Inference package structure: src/inference/ with __init__.py, forecast.py, shap_analysis.py"

requirements-completed: [MODL-03, MODL-04, MODL-05, MODL-07]

# Metrics
duration: 3min
completed: 2026-03-22
---

# Phase 03 Plan 02: Ensemble Combiner and Forecast Engine Summary

**Inverse-RMSE ensemble weights, additive blend of statistical + LightGBM correction, 10-column forecast DataFrame with dual USD units and CI bounds, and SHAP TreeExplainer attribution with PNG export**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-22T12:53:55Z
- **Completed:** 2026-03-22T12:57:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Ensemble combiner with inverse-RMSE weighting per segment — lower RMSE gets higher weight; zero-RMSE guard via epsilon (1e-10)
- Additive forecast blend (stat_pred + lgbm_weight * correction) where LightGBM corrects statistical residuals rather than producing an independent forecast
- Full forecast DataFrame with all 10 required columns: year, segment, point_estimate_real_2020, point_estimate_nominal, ci80_lower, ci80_upper, ci95_lower, ci95_upper, is_forecast, data_vintage
- CI bounds monotonically clipped using min/max cascade so ci95_lower <= ci80_lower <= point <= ci80_upper <= ci95_upper is guaranteed on every row
- Nominal USD from real 2020 USD via 2.5% annual CAGR (upgradeable to live deflator)
- data_vintage embedded as a string column in every row (MODL-04 requirement)
- SHAP TreeExplainer wraps any fitted LGBMRegressor, returns shap_values array + expected_value + feature_names
- SHAP summary plot saves to PNG with Agg backend for headless CI execution

## Task Commits

Each task was committed atomically:

1. **Task 1: Ensemble combiner and forecast engine with CI bounds, dual units, and vintage** - `de076b5` (feat)
2. **Task 2: SHAP attribution analysis with TreeExplainer** - `347b5e9` (feat)

_Note: Both tasks followed TDD — tests written first (RED), implementation made them pass (GREEN)._

## Files Created/Modified

- `src/models/ensemble.py` - compute_ensemble_weights (inverse-RMSE) and blend_forecasts (additive)
- `src/inference/__init__.py` - Package marker for inference submodule
- `src/inference/forecast.py` - get_data_vintage, reflate_to_nominal, clip_ci_bounds, build_forecast_dataframe
- `src/inference/shap_analysis.py` - compute_shap_values (TreeExplainer) and save_shap_summary_plot (Agg backend)
- `tests/test_ensemble.py` - 9 tests: inverse-RMSE weights math and additive blend correctness
- `tests/test_forecast_output.py` - 12 tests: output schema, vintage, CI ordering, dual units, is_forecast flag
- `tests/test_shap.py` - 6 tests: SHAP values shape, expected value type, feature names, PNG plot creation

## Decisions Made

- **Additive blend confirmed:** LightGBM is trained on residuals from Phase 2 statistical models, so its output is a correction delta, not a full forecast. The blend formula is `stat_pred + lgbm_weight * correction`, not a weighted average of two parallel forecasts.
- **2.5% CAGR for nominal USD:** A hard-coded 2.5% annual inflation assumption is used as a placeholder. The `reflate_to_nominal` function is designed to be upgraded to use the World Bank NY.GDP.DEFL.ZS deflator once live data is available.
- **Epsilon guard in weights:** `1 / (rmse + 1e-10)` prevents division by zero and is numerically stable across the expected RMSE range for this project (0.0 to ~2.0 trillion USD residuals).
- **Agg backend inside function:** `matplotlib.use("Agg")` is called inside `save_shap_summary_plot` rather than at module import to avoid globally overriding the backend for callers that use interactive display.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ensemble combiner and inference package are ready for the pipeline runner (plan 03-03 or phase 04)
- SHAP summary plots can be referenced in Phase 5 methodology reports
- The `reflate_to_nominal` function is a known simplification — upgrade with live deflator data before final publication
- Full test suite: 189 tests passing (27 new in this plan)

---
*Phase: 03-ml-ensemble-and-validation*
*Completed: 2026-03-22*

## Self-Check: PASSED

All files verified:
- src/models/ensemble.py - FOUND
- src/inference/__init__.py - FOUND
- src/inference/forecast.py - FOUND
- src/inference/shap_analysis.py - FOUND
- tests/test_ensemble.py - FOUND
- tests/test_forecast_output.py - FOUND
- tests/test_shap.py - FOUND
- .planning/phases/03-ml-ensemble-and-validation/03-02-SUMMARY.md - FOUND

Commits verified:
- de076b5 - FOUND (Task 1)
- 347b5e9 - FOUND (Task 2)
