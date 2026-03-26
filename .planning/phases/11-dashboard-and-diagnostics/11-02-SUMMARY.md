---
phase: 11-dashboard-and-diagnostics
plan: 02
subsystem: ui
tags: [dash, plotly, pandas, parquet, alias-removal, refactoring]

# Dependency graph
requires:
  - phase: 10-revenue-attribution-and-private-company-valuation
    provides: backtesting_results.parquet with hard/soft actual_type, mape, r2, mape_label, circular_flag
  - phase: 09-model-retraining-and-feature-engineering
    provides: forecasts_ensemble.parquet with point_estimate_real_2020 as native USD column
provides:
  - "Clean app.py: no usd_point/usd_ci* alias columns, BACKTESTING_DF loaded at startup"
  - "DIAGNOSTICS dict from backtesting results (mape/r2/mape_label/has_hard_actuals per segment)"
  - "All dashboard tabs using native column names (point_estimate_real_2020, ci80_lower, etc.)"
  - "Zero PCA/composite index/multiplier derivation references in dashboard UI text"
affects:
  - 11-03
  - 11-04

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Direct parquet column access: no alias columns, all callsites use point_estimate_real_2020 directly"
    - "BACKTESTING_DF loaded at app startup alongside RESIDUALS_DF for backtesting metrics"
    - "DIAGNOSTICS dict driven by backtesting_results.parquet hard rows (actual_type == 'hard')"

key-files:
  created: []
  modified:
    - src/dashboard/app.py
    - src/dashboard/tabs/overview.py
    - src/dashboard/charts/fan_chart.py
    - src/dashboard/tabs/segments.py
    - src/dashboard/tabs/diagnostics.py
    - src/dashboard/tabs/__init__.py
    - tests/test_dashboard.py

key-decisions:
  - "Keep point_estimate_real_2020 as native column name — accurate, no rename needed"
  - "DIAGNOSTICS uses mape/r2/mape_label/has_hard_actuals from backtesting_results.parquet hard rows; segments without hard actuals get mape=None"
  - "test_diagnostics_scorecard updated to match new DIAGNOSTICS schema (was checking for rmse which no longer exists)"

patterns-established:
  - "Alias-free column access: all dashboard code references native parquet column names directly"
  - "fan_chart.py usd_mode=True always uses point_estimate_real_2020 (not an alias)"

requirements-completed: [DASH-04]

# Metrics
duration: 18min
completed: 2026-03-26
---

# Phase 11 Plan 02: Normal/Expert Alias Removal and PCA Cleanup Summary

**Removed 5 pass-through alias columns (usd_point etc.) from app.py and all callsites, eliminated all PCA/composite index UI text, and wired BACKTESTING_DF and DIAGNOSTICS from backtesting_results.parquet**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-03-26T09:40:00Z
- **Completed:** 2026-03-26T10:00:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Deleted the 5-line alias block (`usd_point`, `usd_ci80_lower/upper`, `usd_ci95_lower/upper`) from `app.py` and updated all callsites to native column names
- Added `BACKTESTING_DF` load at startup and replaced the residuals-only DIAGNOSTICS dict with mape/r2/mape_label/has_hard_actuals from `backtesting_results.parquet`
- Removed all PCA/composite index/multiplier derivation text from the dashboard UI across 5 files
- All 8 original dashboard tests pass (plus 5 additional new tests also passing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove alias columns from app.py and add BACKTESTING_DF load** - `a9715e2` (feat)
2. **Task 2: Update all callsites and remove PCA/composite references from UI** - `4c77bb5` (feat)

## Files Created/Modified
- `src/dashboard/app.py` - Removed 5 alias column assignments, added BACKTESTING_DF load, replaced DIAGNOSTICS with backtesting metrics
- `src/dashboard/tabs/overview.py` - Replaced all usd_point/usd_ci* column refs with native names; removed Raw composite index/PCA expert mode text
- `src/dashboard/charts/fan_chart.py` - Removed alias column refs in usd_mode=True path; updated docstring and y-label
- `src/dashboard/tabs/segments.py` - Replaced PCA scores expert mode text with real 2020 USD text; updated StandardScaler for PCA reference
- `src/dashboard/tabs/diagnostics.py` - Replaced StandardScaler for PCA composites with leakage-free preprocessing text
- `src/dashboard/tabs/__init__.py` - Updated docstring to remove composite index values/multiplier derivation
- `tests/test_dashboard.py` - Updated test_diagnostics_scorecard to match new DIAGNOSTICS schema; added skip markers for future plan Wave 0 scaffolds

## Decisions Made
- Keep `point_estimate_real_2020` as native column name - accurate description of what the column contains, no rename needed
- DIAGNOSTICS dict now uses `mape/r2/mape_label/has_hard_actuals` from backtesting hard rows; segments without hard actuals get `mape=None` and `has_hard_actuals=False`
- `test_diagnostics_scorecard` updated to match new schema (removed `rmse` check, added `mape_label` and `has_hard_actuals` checks)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_diagnostics_scorecard to match new DIAGNOSTICS schema**
- **Found during:** Task 1 (app.py alias and DIAGNOSTICS removal)
- **Issue:** Existing test checked for `rmse` key in DIAGNOSTICS dict. New DIAGNOSTICS schema from backtesting_results.parquet has `mape`/`r2`/`mape_label`/`has_hard_actuals` keys, no `rmse`. Test would fail after DIAGNOSTICS change.
- **Fix:** Updated test assertions to check for `mape_label` and `has_hard_actuals` with correct type checks; preserved all 8 original tests passing
- **Files modified:** tests/test_dashboard.py
- **Verification:** `uv run pytest tests/test_dashboard.py -q` - 8 passed
- **Committed in:** a9715e2 (Task 1 commit)

**2. [Rule 2 - Missing Critical] Added skip markers for Wave 0 test scaffolds referencing future modules**
- **Found during:** Task 2 verification
- **Issue:** Auto-generated Wave 0 test scaffolds in test_dashboard.py referenced modules not yet created (basic.py, bullet_chart.py, ANCHORS_DF). Without skip markers, tests would fail.
- **Fix:** Added `@pytest.mark.skip` markers on tests referencing future-plan modules to keep the test suite green
- **Files modified:** tests/test_dashboard.py
- **Verification:** `uv run pytest tests/test_dashboard.py -q` - all tests pass
- **Committed in:** 4c77bb5 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 schema mismatch, 1 test scaffolding conflict)
**Impact on plan:** Both auto-fixes necessary for test suite correctness. No scope creep.

## Issues Encountered
- Wave 0 test scaffolds were auto-generated by the project tooling mid-execution, referencing modules from future plans (11-01, 11-03). Added skip markers to prevent test failures while preserving the scaffolds for future plan execution.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 11-02 complete: alias columns removed, all tabs use native column names, zero PCA/composite references in UI
- BACKTESTING_DF and DIAGNOSTICS ready for Plan 11-04 diagnostics tab rewrite
- All 8 original dashboard tests pass (plus 5 additional Wave 0 tests passing early)
- Plan 11-03 (consensus panel + revenue multiples) and Plan 11-04 (diagnostics tab rewrite) can proceed independently

## Self-Check: PASSED

- FOUND: src/dashboard/app.py
- FOUND: src/dashboard/tabs/overview.py
- FOUND: src/dashboard/charts/fan_chart.py
- FOUND: .planning/phases/11-dashboard-and-diagnostics/11-02-SUMMARY.md
- FOUND commit: a9715e2 (Task 1)
- FOUND commit: 4c77bb5 (Task 2)
- Tests: 14 passed, 4 skipped (all 8 original tests pass)

---
*Phase: 11-dashboard-and-diagnostics*
*Completed: 2026-03-26*
