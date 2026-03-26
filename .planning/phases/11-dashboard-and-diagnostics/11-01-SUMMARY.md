---
phase: 11-dashboard-and-diagnostics
plan: 01
subsystem: ui
tags: [plotly-dash, dash-bootstrap-components, kpi-cards, bullet-chart, confidence-indicators, fan-chart]

# Dependency graph
requires:
  - phase: 10-revenue-attribution-and-private-company-valuation
    provides: forecasts_ensemble.parquet with point_estimate_nominal, market_anchors_ai.parquet with p25/p75/median nominal columns, backtesting_results.parquet
provides:
  - build_basic_layout() in src/dashboard/tabs/basic.py — 3 KPI cards, segment bar, fan chart, consensus bullet chart
  - make_consensus_bullet_chart() in src/dashboard/charts/bullet_chart.py — grey band + diamond marker
  - vintage_footer() in src/dashboard/charts/styles.py — shared footer component
  - COLOR_CONFIDENCE_GREEN/AMBER/RED in styles.py — traffic-light color tokens
  - Basic tab wired as default landing tab (value="basic" in layout.py and callbacks.py)
  - ANCHORS_DF at startup in app.py
  - Wave 0 test scaffolds (18 tests: 14 active, 4 skipped for Plans 11-02 through 11-04)
affects:
  - 11-02 (alias removal — skipped tests will be unskipped)
  - 11-03 (revenue multiples and Normal tab updates)
  - 11-04 (diagnostics rewrite)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy imports in callbacks.py to break circular dependency (tab modules import app.py, app.py imports callbacks.py)"
    - "Confidence traffic-light: CI width ratio < 0.30 green, 0.30-0.60 amber, >= 0.60 red"
    - "nominal CI approximation: ci_nominal = ci_real * (nominal_total / real_total)"
    - "vintage_footer() shared helper from styles.py for all tab sections"

key-files:
  created:
    - src/dashboard/tabs/basic.py
    - src/dashboard/charts/bullet_chart.py
  modified:
    - src/dashboard/charts/styles.py
    - src/dashboard/app.py
    - src/dashboard/layout.py
    - src/dashboard/callbacks.py
    - tests/test_dashboard.py

key-decisions:
  - "Lazy imports in callbacks.py instead of top-level imports to break circular dependency (basic.py -> app.py -> callbacks.py -> basic.py)"
  - "Basic tab ignores mode argument entirely — build_basic_layout() always renders the Basic view regardless of Normal/Expert toggle"
  - "Confidence CI ratio computed on real_2020 USD (ci80_upper - ci80_lower) / point_estimate_real_2020 — real USD gives correct relative uncertainty even though display is nominal"
  - "Approximate nominal CIs for 2030 KPI card: scale real CIs by (nominal_total / real_total) ratio"
  - "test_basic_fan_chart_traces graph traversal fixed: elif hasattr(children, '__class__') handles single-component children (dcc.Graph in dbc.Col)"

patterns-established:
  - "Confidence traffic-light: html.Span('●') with color token, aria-label for accessibility"
  - "bullet chart: go.Bar(orientation='h', base=[p25]) + go.Scatter(mode='markers', symbol='diamond') with barmode='overlay'"
  - "Consensus chart filters estimated_flag==False to show only real analyst estimates (not bfill/ffill extrapolations)"

requirements-completed: [DASH-01, DASH-02]

# Metrics
duration: 7min
completed: 2026-03-26
---

# Phase 11 Plan 01: Basic Dashboard Tier Summary

**Basic tab with 3 KPI cards (nominal USD + confidence traffic lights), segment bar, fan chart, and analyst consensus bullet chart — wired as the default landing page**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-03-26T08:25:29Z
- **Completed:** 2026-03-26T08:32:49Z
- **Tasks:** 2
- **Files modified:** 7 (2 created, 5 modified)

## Accomplishments

- Created `build_basic_layout()` delivering a single non-scrolling screen with 3 hero KPIs, segment bar chart, growth fan chart, and analyst consensus bullet chart
- Created `make_consensus_bullet_chart()` showing grey p25-p75 consensus band with colored diamond markers (green inside range, amber outside)
- Added `vintage_footer()` shared helper and 3 confidence traffic-light color tokens to styles.py
- Wired Basic as the default landing tab (value="basic" in layout.py, lazy imports in callbacks.py to break circular dependency)
- Added ANCHORS_DF startup load in app.py
- Appended 10 Wave 0 test scaffolds (14 now active, 4 skipped for Plans 11-02 through 11-04)

## Task Commits

Each task was committed atomically:

1. **Task 1: bullet_chart.py, confidence colors, vintage_footer, Wave 0 test scaffolds** - `e312f83` (feat)
2. **Task 2: basic.py and wire Basic tab into layout.py + callbacks.py** - `d990100` (feat)

## Files Created/Modified

- `/Users/simonleowegner/my-project/src/dashboard/tabs/basic.py` — new; build_basic_layout() with KPI row, chart row, consensus panel
- `/Users/simonleowegner/my-project/src/dashboard/charts/bullet_chart.py` — new; make_consensus_bullet_chart() with grey band + diamond marker
- `/Users/simonleowegner/my-project/src/dashboard/charts/styles.py` — added COLOR_CONFIDENCE_GREEN/AMBER/RED and vintage_footer()
- `/Users/simonleowegner/my-project/src/dashboard/app.py` — added ANCHORS_DF = pd.read_parquet(market_anchors_ai.parquet)
- `/Users/simonleowegner/my-project/src/dashboard/layout.py` — added Basic as first dcc.Tab, changed default value to "basic"
- `/Users/simonleowegner/my-project/src/dashboard/callbacks.py` — changed to lazy imports, added "basic" branch before "overview"
- `/Users/simonleowegner/my-project/tests/test_dashboard.py` — appended 10 Wave 0 test functions; fixed fan chart graph traversal

## Decisions Made

- **Lazy imports in callbacks.py:** basic.py imports app globals (FORECASTS_DF, ANCHORS_DF), and app.py imports callbacks.py at module level. Moving tab imports inside the render_tab function body breaks the circular dependency without any architectural changes.
- **Confidence CI on real USD:** CI width ratio uses real_2020 CI columns even though Basic tier displays nominal USD. Real USD CIs correctly represent relative model uncertainty.
- **Nominal CI approximation for 2030 KPI:** `ci_nominal = ci_real * (nominal_total / real_total)` gives reasonable directional uncertainty range without requiring separate nominal CI columns in the Parquet.
- **Wave 0 test graph traversal:** `elif hasattr(children, '__class__')` (matching any Python object) replaces `elif hasattr(children, 'children')` to correctly traverse single-component children like `dcc.Graph` inside `dbc.Col`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Resolved circular import in callbacks.py**
- **Found during:** Task 2 (basic.py creation)
- **Issue:** basic.py imports from app.py; app.py imports callbacks.py; callbacks.py imported basic.py at top level — Python circular import error
- **Fix:** Changed all tab imports in callbacks.py from top-level to lazy (inside render_tab function body). Python's module cache means these are only resolved once per process.
- **Files modified:** src/dashboard/callbacks.py
- **Verification:** `uv run python -c "from src.dashboard.tabs.basic import build_basic_layout; print('OK')"` succeeds
- **Committed in:** d990100 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed test graph traversal for dbc.Col single-component children**
- **Found during:** Task 2 (test_basic_fan_chart_traces failure)
- **Issue:** `collect_graphs()` traversal used `elif hasattr(children, 'children')` which returns False for `dcc.Graph` (leaf component), causing fan chart to be missed during traversal
- **Fix:** Changed to `elif hasattr(children, '__class__')` to recursively visit any single-component child
- **Files modified:** tests/test_dashboard.py
- **Verification:** test_basic_fan_chart_traces now passes
- **Committed in:** d990100 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking circular import, 1 test traversal bug)
**Impact on plan:** Both auto-fixes necessary for correct operation. No scope creep.

## Issues Encountered

- Linter repeatedly added `@pytest.mark.skip` decorators to newly-created tests. Removed them each time — the tests are now correctly active (they depend on modules created in this plan).

## Next Phase Readiness

- Basic tab live as default landing tab — all 14 active tests pass
- Plan 11-02 can proceed: alias removal (usd_point etc.) — test_no_alias_columns and test_no_pca_strings are scaffolded and will be unskipped
- Plan 11-03 can proceed: revenue multiples table in Overview — test_revenue_multiples_in_overview is scaffolded
- Plan 11-04 can proceed: diagnostics rewrite — test_diagnostics_real_mape is scaffolded

---
*Phase: 11-dashboard-and-diagnostics*
*Completed: 2026-03-26*
