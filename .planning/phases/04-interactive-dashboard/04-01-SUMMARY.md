---
phase: 04-interactive-dashboard
plan: 01
subsystem: ui
tags: [dash, plotly, dash-bootstrap-components, pandas, numpy, parquet]

# Dependency graph
requires:
  - phase: 03-ml-ensemble-and-validation
    provides: forecasts_ensemble.parquet, residuals_statistical.parquet, shap_summary.png

provides:
  - Dash app instance (src/dashboard/app.py) with module-level data loading
  - make_fan_chart: Plotly fan chart with 95%/80% CI bands, historical/forecast lines, vrect, vline
  - make_backtest_chart: Plotly residuals bar chart (positive=blue, negative=coral)
  - Style constants: colors, CI fills, typography, attribution style
  - DIAGNOSTICS dict: RMSE per segment computed from residuals at startup
  - 7 unit tests covering PRES-01, PRES-02, PRES-03, DATA-07

affects:
  - 04-02 (tab layout and callbacks will import app, FORECASTS_DF, RESIDUALS_DF, chart builders)

# Tech tracking
tech-stack:
  added:
    - dash==4.0.0
    - dash-bootstrap-components==2.0.4
    - plotly==6.6.0 (transitive)
  patterns:
    - Module-level data loading: read parquet once at startup, filter in callbacks
    - CI band using toself fill on doubled x-axis (fore + reversed fore)
    - Forecast bridge: prepend last historical point to forecast trace for continuity
    - Color-coded bars: positive residuals blue, negative coral
    - usd_col parameter: point line toggles between real/nominal while CI bands stay real

key-files:
  created:
    - src/dashboard/__init__.py
    - src/dashboard/app.py
    - src/dashboard/charts/__init__.py
    - src/dashboard/charts/styles.py
    - src/dashboard/charts/fan_chart.py
    - src/dashboard/charts/backtest.py
    - tests/test_dashboard.py
  modified:
    - pyproject.toml (dash, dash-bootstrap-components added)
    - uv.lock

key-decisions:
  - "uv run required for dash imports — dash/plotly not in base python3 path, only in uv-managed venv"
  - "CI bands always use real 2020 USD columns; usd_col only affects the point line (historical/forecast traces)"
  - "MAPE and R^2 documented as N/A with inline comment — residuals_statistical.parquet has only residual column, no actual/predicted values"
  - "Forecast bridge: last historical point prepended to forecast x/y arrays for visual continuity at boundary"

patterns-established:
  - "Fan chart pattern: CI toself + historical solid + forecast dashed + vrect + vline"
  - "Backtest pattern: go.Bar with per-value color list (positive=blue, negative=coral)"
  - "Dashboard data layer: all globals computed at module level in app.py, imported by layout modules"

requirements-completed: [PRES-01, PRES-03]

# Metrics
duration: 2min
completed: 2026-03-22
---

# Phase 4 Plan 01: Dashboard Data Layer and Chart Builders Summary

**Dash app scaffold with fan chart (95%/80% CI bands, dashed forecast, vline) and backtest residuals chart, 7 unit tests all passing**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-22T13:47:45Z
- **Completed:** 2026-03-22T13:50:19Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Dashboard package installed with Dash 4.0.0 and dash-bootstrap-components 2.0.4
- Module-level data loading: FORECASTS_DF (84 rows), RESIDUALS_DF (60 rows), DIAGNOSTICS (4 segments with RMSE), SEGMENTS, SEGMENT_DISPLAY, SOURCE_ATTRIBUTION
- make_fan_chart produces go.Figure with 4 traces (95% CI, 80% CI, Historical, Forecast dashed) plus vline/vrect at forecast boundary; supports segment="all" aggregation and real/nominal USD toggle
- make_backtest_chart produces go.Bar figure of residuals per year with color-coded positive/negative bars
- 7 unit tests pass covering all PRES-01/02/03 and DATA-07 requirements

## Task Commits

Each task was committed atomically:

1. **Task 1: Install dependencies and create dashboard package** - `669123d` (feat)
2. **Task 2: Create comprehensive test suite** - `5c7ec35` (test)

## Files Created/Modified

- `src/dashboard/__init__.py` - Package marker
- `src/dashboard/app.py` - Dash app instance, module-level data loading, DIAGNOSTICS computation
- `src/dashboard/charts/__init__.py` - Package marker
- `src/dashboard/charts/styles.py` - Color constants, CI fills, typography tokens, attribution style dict
- `src/dashboard/charts/fan_chart.py` - make_fan_chart function with full spec compliance
- `src/dashboard/charts/backtest.py` - make_backtest_chart function with residuals bar chart
- `tests/test_dashboard.py` - 7 pytest unit tests for dashboard requirements
- `pyproject.toml` - dash, dash-bootstrap-components dependencies added
- `uv.lock` - lock file updated

## Decisions Made

- uv run required for dash imports since dash/plotly are in the uv-managed venv, not base python3
- CI bands always use real 2020 USD columns; the usd_col parameter only toggles the point line (historical and forecast traces), not the filled CI bands — as specified in the plan interfaces
- MAPE and R^2 documented as "N/A" with inline comment in DIAGNOSTICS — residuals_statistical.parquet has only the residual column (no actual/predicted), which is consistent with the schema NOTE in the plan
- Forecast bridge: the last historical point is prepended to the forecast trace x/y arrays to create visual continuity at the forecast boundary

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 02 can import `app`, `FORECASTS_DF`, `RESIDUALS_DF`, `DIAGNOSTICS`, `SEGMENTS`, `SEGMENT_DISPLAY`, `SOURCE_ATTRIBUTION` from `src.dashboard.app`
- Plan 02 can import `make_fan_chart` from `src.dashboard.charts.fan_chart` and `make_backtest_chart` from `src.dashboard.charts.backtest`
- 7 tests in tests/test_dashboard.py are green and will continue to pass as Plan 02 adds layout/callbacks

---
*Phase: 04-interactive-dashboard*
*Completed: 2026-03-22*
