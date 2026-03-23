---
phase: 06-pipeline-integration-wiring
plan: "01"
subsystem: statistical-pipeline
tags:
  - prophet
  - changepoint
  - integration-tests
  - pipeline-wiring
dependency_graph:
  requires:
    - 02-statistical-baseline/02-03-PLAN.md
  provides:
    - configurable changepoint_year parameter on Prophet functions
    - integration test scaffold (5 classes, 10 methods) for Plan 06-02
  affects:
    - scripts/run_statistical_pipeline.py (consumed by Plan 06-02)
    - src/models/statistical/prophet_model.py
tech_stack:
  added: []
  patterns:
    - backward-compatible signature extension (default parameter)
    - xfail test markers for Plan N+1 wiring verification
key_files:
  created:
    - tests/test_pipeline_wiring.py
  modified:
    - src/models/statistical/prophet_model.py
decisions:
  - "changepoint_year: int = 2022 default on both fit_prophet_segment and run_prophet_cv — preserves all 222 existing tests without modification"
  - "Classes 1-4 of test scaffold marked xfail — they test pipeline functions (_load_lseg_scalar, _run_break_detection) and call-site wiring that does not exist until Plan 06-02"
  - "TestProphetChangepoint (Class 5) passes immediately — changepoint_year already wired by this plan"
  - "CapturingProphet subclass pattern used in test_run_prophet_cv_custom_changepoint to inspect constructor kwargs without disrupting Prophet internals"
metrics:
  duration: "~8 min"
  completed: "2026-03-23"
  tasks: 2
  files_changed: 2
---

# Phase 6 Plan 1: Prophet Changepoint Extension and Integration Test Scaffold

Prophet functions extended with configurable changepoint_year parameter (backward-compatible default=2022) and integration test scaffold created with 5 test classes covering all Phase 6 wiring points.

## What Was Built

### Task 1: changepoint_year parameter (a5245e4)

`fit_prophet_segment` and `run_prophet_cv` in `src/models/statistical/prophet_model.py` extended with `changepoint_year: int = 2022`:

- `fit_prophet_segment(df, segment, changepoint_year=2022)` — replaces hardcoded `"2022-01-01"` with `f"{changepoint_year}-01-01"`
- `run_prophet_cv(df, segment, n_splits=3, changepoint_year=2022)` — replaces hardcoded `if 2022 in train_years.values` with `if changepoint_year in train_years.values` and constructs changepoints list dynamically

Both functions updated together to prevent the Pitfall 2 scenario from RESEARCH.md (CV using different changepoint year than final fit). The pipeline in `scripts/run_statistical_pipeline.py` can now pass `changepoint_year=break_year` where `break_year` is the output of `_run_break_detection()` (wired in Plan 06-02).

### Task 2: Integration test scaffold (ea97797)

`tests/test_pipeline_wiring.py` created with 5 test classes and 10 test methods:

| Class | Tests | Status | Purpose |
|-------|-------|--------|---------|
| TestLsegScalar | 3 | xfail | Verifies _load_lseg_scalar() returns dict, handles missing file, scalar amplifies PCA scores |
| TestBreakDetection | 3 | xfail | Verifies _run_break_detection() returns int, detects 2022 on step series, falls back to 2022 |
| TestStationarityWiring | 1 | xfail | Verifies assess_stationarity called >= 4x per run_pipeline() invocation |
| TestOlsWiring | 1 | xfail | Verifies fit_top_down_ols_with_upgrade called >= 4x per run_pipeline() invocation |
| TestProphetChangepoint | 2 | PASS | Verifies changepoint_year threads into Prophet constructor in both fit and CV paths |

## Verification

```
uv run pytest tests/test_models.py tests/test_pipeline_wiring.py -x -q --tb=short
13 passed, 8 xfailed in 1.53s

grep -c "changepoint_year" src/models/statistical/prophet_model.py
11  (>= 4 required: 2 signatures + 2 usages)

uv run python -m pytest -q --tb=short
224 passed, 8 xfailed, 17 warnings in 14.13s
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Series.year AttributeError in test_fit_prophet_segment_custom_changepoint**
- **Found during:** Task 2 initial test run
- **Issue:** `pd.to_datetime(changepoint_dates).year` raises AttributeError — must use `.dt.year` on a Series
- **Fix:** Changed `pd.to_datetime(changepoint_dates).year.tolist()` to `pd.to_datetime(changepoint_dates).dt.year.tolist()`
- **Files modified:** tests/test_pipeline_wiring.py
- **Commit:** ea97797 (fixed inline before commit)

## Self-Check: PASSED

- [x] `src/models/statistical/prophet_model.py` exists and contains `changepoint_year`
- [x] `tests/test_pipeline_wiring.py` exists with 5 test classes, 10 test methods
- [x] Commit a5245e4 exists (Task 1)
- [x] Commit ea97797 exists (Task 2)
- [x] Full 224-test suite green with 8 xfailed
