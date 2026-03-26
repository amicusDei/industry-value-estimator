---
phase: 11-dashboard-and-diagnostics
plan: "04"
subsystem: dashboard
tags: [diagnostics, backtesting, visualization, testing]
dependency_graph:
  requires: ["11-02"]
  provides: ["diagnostics-hard-soft-panels", "backtest-scatter-chart", "vintage-footers-complete"]
  affects: ["src/dashboard/tabs/diagnostics.py", "src/dashboard/charts/backtest.py", "src/dashboard/tabs/segments.py", "src/dashboard/tabs/drivers.py"]
tech_stack:
  added: []
  patterns: ["actual-vs-predicted scatter", "split Hard/Soft validation panels", "walk-forward CV transparency"]
key_files:
  created: []
  modified:
    - src/dashboard/tabs/diagnostics.py
    - src/dashboard/charts/backtest.py
    - src/dashboard/tabs/segments.py
    - src/dashboard/tabs/drivers.py
    - tests/test_dashboard.py
decisions:
  - "Diagnostics tab replaces old RMSE scorecard with split Hard/Soft panels reading directly from BACKTESTING_DF for full display control"
  - "backtest.py rewritten to accept BACKTESTING_DF (not residuals_df) — old test updated to match new API"
  - "Soft panel explicitly labels MAPE as circular_not_validated with amber color to prevent misinterpretation"
metrics:
  duration: 199
  completed: "2026-03-26"
  tasks_completed: 2
  files_modified: 5
---

# Phase 11 Plan 04: Diagnostics Rewrite and Vintage Footer Completion Summary

**One-liner:** Split Hard/Soft diagnostics panels with real EDGAR MAPE [out-of-sample] labels, actual-vs-predicted scatter, circular_flag transparency, and vintage footers across all 5 tabs.

---

## Tasks Completed

### Task 1: Rewrite diagnostics.py and backtest.py for real backtesting metrics

**Commit:** `9f769d5`

**backtest.py — Full rewrite:**
- Replaced residuals bar chart with actual-vs-predicted scatter plot
- Filters to `actual_type == 'hard'` rows only — soft/circular rows never plotted
- `go.Scatter(mode='markers')` with `x=actual_usd`, `y=predicted_usd`
- Color by segment (COLOR_DEEP_BLUE primary, COLOR_CORAL secondary)
- y=x diagonal reference line via `fig.add_shape` with gray dashed line
- Layout: `plot_bgcolor="white"`, `paper_bgcolor="white"`, axis titles in USD billions
- Handles empty hard actuals gracefully with annotation message

**diagnostics.py — Full rewrite:**
- `build_diagnostics_layout()` now shows two-column Hard/Soft panels via `dbc.Row([dbc.Col(hard_panel, width=6), dbc.Col(soft_panel, width=6)])`
- Hard panel heading: "Validated (EDGAR actuals)" with MAPE [out-of-sample] and R² [out-of-sample] per segment
- ai_software caveat: "* C3.ai revenue only vs. full AI software segment — directional signal, not segment MAPE"
- Soft panel heading: "Cross-checked (analyst consensus)" with amber `⚠ circular_flag = True` warning badge
- Soft panel explanation: "MAPE = 0% reflects model trained on these estimates — not true out-of-sample validation"
- Actual-vs-predicted scatter chart below hard metrics
- vintage_footer("EDGAR filings 2024 | Backtesting via walk-forward CV", "") at bottom

### Task 2: Add vintage footers to segments and drivers tabs, unskip remaining tests

**Commit:** `be8b2a3`

**segments.py:**
- Added `vintage_footer` import from styles
- Appended `vintage_footer("EDGAR/Analyst Corpus", FORECASTS_DF["data_vintage"].iloc[0])` to both return paths (all-segments 2x2 grid and single-segment view)

**drivers.py:**
- Added `FORECASTS_DF` import from app
- Added `vintage_footer` import from styles
- Appended `vintage_footer("World Bank, OECD, LSEG", FORECASTS_DF["data_vintage"].iloc[0])` before return

**tests/test_dashboard.py — 3 tests unskipped:**
- `test_no_alias_columns`: asserts usd_point, usd_ci80_lower, usd_ci80_upper, usd_ci95_lower, usd_ci95_upper absent from FORECASTS_DF
- `test_no_pca_strings`: inspects source of overview, segments, diagnostics, fan_chart modules for "Composite Index" and "PCA" in non-comment lines
- `test_diagnostics_real_mape`: asserts BACKTESTING_DF has mape/actual_type columns, hard rows not empty, hard MAPE values not NaN

---

## Verification Results

```
uv run pytest tests/test_dashboard.py -q --timeout=30
18 passed in 0.34s

uv run pytest tests/test_dashboard.py tests/test_diagnostics.py tests/test_forecast_output.py tests/test_backtesting.py -q --timeout=60
51 passed, 10 warnings in 2.45s
```

- vintage_footer present in: basic.py, overview.py, segments.py, drivers.py, diagnostics.py (5/5 tabs)
- Zero non-comment usd_point references in src/dashboard/

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_backtest_chart_traces to use new BACKTESTING_DF API**
- **Found during:** Task 1 verification
- **Issue:** Existing `test_backtest_chart_traces` passed `RESIDUALS_DF` to `make_backtest_chart()`, which now expects `backtesting_df` with `actual_type` column. Test raised `KeyError: 'actual_type'`.
- **Fix:** Updated test to import `BACKTESTING_DF` instead of `RESIDUALS_DF` — matches new function signature.
- **Files modified:** tests/test_dashboard.py
- **Commit:** 9f769d5 (included in Task 1 commit)

---

## Self-Check: PASSED

- FOUND: src/dashboard/tabs/diagnostics.py
- FOUND: src/dashboard/charts/backtest.py
- FOUND: src/dashboard/tabs/segments.py
- FOUND: src/dashboard/tabs/drivers.py
- FOUND: commit 9f769d5 (Task 1)
- FOUND: commit be8b2a3 (Task 2)
