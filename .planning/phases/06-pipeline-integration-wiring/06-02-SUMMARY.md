---
phase: 06-pipeline-integration-wiring
plan: 02
subsystem: scripts/run_statistical_pipeline.py
tags: [pipeline-wiring, lseg, structural-breaks, stationarity, ols, integration]
dependency_graph:
  requires:
    - 06-01  # Prophet changepoint_year extension
  provides:
    - Production pipeline with all 4 orphaned functions wired in
    - Structural break detection driving Prophet changepoint
    - LSEG scalar applied to PCA composite scores
    - Stationarity assessment logged per-segment before ARIMA
    - OLS complementary model per-segment with diagnostics logged
  affects:
    - scripts/run_statistical_pipeline.py
    - tests/test_pipeline_wiring.py
tech_stack:
  added: []
  patterns:
    - Post-PCA scalar weight: LSEG revenue-share applied as gentle amplification on PCA scores
    - Data-driven changepoint: CUSUM+Chow break detection replaces hardcoded 2022 Prophet changepoint
    - Complementary OLS: fit_top_down_ols_with_upgrade as diagnostics-only model (not competing with ARIMA/Prophet winner)
key_files:
  created: []
  modified:
    - scripts/run_statistical_pipeline.py
    - tests/test_pipeline_wiring.py
decisions:
  - Stationarity and OLS logging only — no algorithmic override of pmdarima AICc-based order selection
  - OLS residuals not written to residuals_statistical.parquet — logged to stdout only for ASSUMPTIONS.md traceability
  - LSEG scalar applied post-PCA: lseg_ai.parquet is a cross-section (year=2026), cannot be a time-series column
metrics:
  duration: 3 min
  completed: "2026-03-23"
  tasks_completed: 2
  files_modified: 2
---

# Phase 6 Plan 2: Pipeline Integration Wiring Summary

**One-liner:** Wired four orphaned function groups (LSEG scalar, CUSUM/Chow break detection, ADF+KPSS stationarity, diagnostic OLS) into `run_statistical_pipeline.py` — all 8 xfail integration tests now pass.

## What Was Done

### Task 1: Wire LSEG scalar, break detection, stationarity, and OLS

Modified `scripts/run_statistical_pipeline.py` to close all three integration gaps from the v1.0 milestone audit:

**New imports added:**
- `from src.diagnostics.structural_breaks import run_cusum, run_chow`
- `from src.processing.features import assess_stationarity` (added to existing import)
- `from src.models.statistical.regression import fit_top_down_ols_with_upgrade`
- `import statsmodels.api as sm`

**New function `_load_lseg_scalar()`:**
- Loads `lseg_ai.parquet`, groups by `industry_segment`, sums `Revenue` (in billions), normalizes to revenue-share [0,1]
- Returns empty dict if file missing (graceful degradation — pipeline runs without LSEG)
- Only `ai_software` is covered (4215 rows); hardware/infrastructure/adoption receive no scalar (correct behavior)

**New function `_run_break_detection(combined_series)`:**
- Runs `run_cusum()` and `run_chow()` on the provided series
- Guards `break_idx` at 3 to `len-3` boundary to prevent Chow singular matrix (Pitfall 3)
- Returns `int(chow["break_year"])` if Chow p < 0.05, else 2022 (default fallback)
- Detects 2022 as expected on synthetic step-function series

**Modified `_build_segment_series()`:**
- Added `lseg_scalar: dict | None = None` parameter (backward-compatible)
- After `build_pca_composite()` call: `scores *= (1.0 + lseg_scalar[segment])` if segment has LSEG coverage

**Modified `run_pipeline()`:**

Real data path (before segment loop):
- Calls `_load_lseg_scalar()` and stores result
- Calls `_build_segment_series(..., lseg_scalar=lseg_scalar)` for each segment
- Builds aggregate series for `ai_software`, calls `_run_break_detection()`, stores `break_year`

Per-segment loop (both real and synthetic paths):
- Calls `assess_stationarity(series.values)` before `select_arima_order()`, logs ADF/KPSS p-values and recommended d
- Adds `N < 20` note for reliability warning
- Passes `changepoint_year=break_year` to both `run_prophet_cv()` and `fit_prophet_segment()`
- After winner selection: calls `fit_top_down_ols_with_upgrade(y_ols, sm.add_constant(x_ols))`
  - Real mode: GDP as X, aligned by index intersection
  - Synthetic mode: time trend index as X proxy
- Wrapped in try/except — logs warning and continues on short-series OLS failure

### Task 2: Remove xfail markers

Removed `@pytest.mark.xfail` from 4 test classes in `tests/test_pipeline_wiring.py`:
- `TestLsegScalar` (3 tests)
- `TestBreakDetection` (3 tests)
- `TestStationarityWiring` (1 test)
- `TestOlsWiring` (1 test)

All 10 tests in `test_pipeline_wiring.py` now PASS cleanly.

## Verification Results

```
tests/test_pipeline_wiring.py — 10/10 PASSED (no xfail, no xpass)
Full suite: 232 passed (0 failed, 0 errors)
```

Acceptance criteria:
- `grep -c "_load_lseg_scalar"`: 2 (definition + call) ✓
- `grep -c "_run_break_detection"`: 2 (definition + call) ✓
- `grep -c "assess_stationarity"`: 3 (import + 2 call sites) ✓
- `grep -c "fit_top_down_ols_with_upgrade"`: 3 (import + 2 references) ✓
- `grep -c "changepoint_year"`: 3 (passed to both prophet functions + detection) ✓
- All 8 xfail markers removed ✓
- Full suite green (232 passed) ✓

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 5a89668 | feat(06-02): wire LSEG scalar, break detection, stationarity, and OLS into pipeline |
| 2 | 4f4adaf | feat(06-02): remove xfail markers from pipeline wiring tests — all 8 now pass |

## Self-Check

- [x] `scripts/run_statistical_pipeline.py` modified and committed
- [x] `tests/test_pipeline_wiring.py` xfail markers removed and committed
- [x] Commit 5a89668 exists
- [x] Commit 4f4adaf exists
- [x] 232 tests passing
