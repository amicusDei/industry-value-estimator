---
phase: 11-dashboard-and-diagnostics
verified: 2026-03-26T12:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 11: Dashboard and Diagnostics — Verification Report

**Phase Goal:** The dashboard shows validated, real USD numbers across all three tiers; the Basic tier gives any analyst immediate market intelligence without requiring expertise to interpret
**Verified:** 2026-03-26
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|---------|
| 1  | Basic tab is the first and default tab in the dashboard | VERIFIED | `layout.py` line 130: `value="basic"` on `dcc.Tabs`; "Basic" is first `dcc.Tab` child |
| 2  | 3 hero KPI cards display total market size, YoY growth, and 2030 forecast in nominal USD | VERIFIED | `basic.py` lines 196-226: three `_kpi_card()` calls with labels "Total AI Market Size", "YoY Market Growth", "2030 Forecast"; all use `point_estimate_nominal` column |
| 3  | Each KPI card has a confidence traffic-light dot (green/amber/red) based on CI width ratio | VERIFIED | `_confidence_color()` in `basic.py` lines 41-58: ratio < 0.30 → green, < 0.60 → amber, else red; `html.Span("●")` with color in `_kpi_card()` |
| 4  | Analyst consensus bullet chart in both Basic and Normal tier Overview | VERIFIED | `basic.py` lines 293-316: `make_consensus_bullet_chart()` called; `overview.py` lines 181-200: `_build_consensus_panel()` injected when `mode == "normal"` |
| 5  | Revenue multiples table shows 4 rows in Normal mode Overview with source attribution | VERIFIED | `overview.py` lines 62-91: `_REVENUE_MULTIPLES` list with 4 rows; `_build_revenue_multiples_table()` appended in Normal mode; "PitchBook Q4 2025" source note present |
| 6  | No alias columns (usd_point, usd_ci80_*, usd_ci95_*) in FORECASTS_DF at runtime | VERIFIED | Alias block deleted from `app.py`; grep across entire `src/dashboard/` shows zero occurrences of `usd_point` or `usd_ci*` as column references; `test_no_alias_columns` passes |
| 7  | No PCA/Composite Index/multiplier derivation text in any dashboard UI | VERIFIED | grep across all `src/dashboard/**/*.py` returns zero matches for "PCA", "Composite Index", or "multiplier derivation"; `test_no_pca_strings` passes |
| 8  | Diagnostics tab shows split Hard/Soft panels with real MAPE and R² from backtesting_results.parquet | VERIFIED | `diagnostics.py` lines 113-185: Hard panel with "Validated (EDGAR actuals)", MAPE [out-of-sample], R², ai_software caveat; lines 188-246: Soft panel with circular_flag warning and "MAPE = 0% reflects model trained on these estimates" |
| 9  | Backtest chart shows actual vs predicted scatter for hard rows only | VERIFIED | `backtest.py` line 44: filters `actual_type == 'hard'`; `go.Scatter(x=actual_usd, y=predicted_usd)` with y=x diagonal reference line |
| 10 | Vintage footers present in all 5 tabs with data source, vintage, and model version | VERIFIED | grep confirms `vintage_footer` called in basic.py (3x), overview.py (4x), segments.py (3x), drivers.py (2x), diagnostics.py (2x); `test_vintage_footer_present` passes |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/dashboard/tabs/basic.py` | Basic tier layout with KPIs, charts, consensus panel; exports `build_basic_layout` | VERIFIED | 327 lines; `build_basic_layout()` defined; full implementation with KPI row, segment bar, fan chart, consensus panel, vintage footers |
| `src/dashboard/charts/bullet_chart.py` | Analyst consensus bullet chart; exports `make_consensus_bullet_chart` | VERIFIED | 136 lines; `make_consensus_bullet_chart()` with grey band (`rgba(180,180,180,0.4)`), diamond markers, `estimated_flag==False` filter |
| `src/dashboard/charts/styles.py` | 3 confidence color constants + `vintage_footer()` helper | VERIFIED | `COLOR_CONFIDENCE_GREEN`, `COLOR_CONFIDENCE_AMBER`, `COLOR_CONFIDENCE_RED` on lines 31-33; `vintage_footer()` on lines 39-64 |
| `src/dashboard/tabs/overview.py` | Overview with consensus panel and revenue multiples in Normal mode; PCA text removed | VERIFIED | `_REVENUE_MULTIPLES` list; `_build_consensus_panel()`, `_build_revenue_multiples_table()`; `build_overview_layout()` injects both in Normal mode |
| `src/dashboard/app.py` | No alias columns; BACKTESTING_DF and ANCHORS_DF loaded; DIAGNOSTICS from backtesting | VERIFIED | Lines 35-36: `BACKTESTING_DF` and `ANCHORS_DF` loaded; lines 46-54: DIAGNOSTICS populated from `actual_type == 'hard'` rows |
| `src/dashboard/tabs/diagnostics.py` | Split Hard/Soft panels with real backtesting metrics | VERIFIED | Full rewrite; Hard panel ("Validated (EDGAR actuals)"), Soft panel ("Cross-checked (analyst consensus)"), circular_flag badge, vintage footer |
| `src/dashboard/charts/backtest.py` | Actual vs predicted scatter using `actual_usd`/`predicted_usd` columns | VERIFIED | Full rewrite; hard-only filter; `go.Scatter`; y=x diagonal `fig.add_shape` |
| `src/dashboard/layout.py` | Basic tab first with `value="basic"` default | VERIFIED | Line 130: `value="basic"` on `dcc.Tabs`; "Basic" tab defined first in children list |
| `src/dashboard/callbacks.py` | `active_tab == "basic"` branch before "overview"; lazy imports | VERIFIED | Line 44: lazy import of `build_basic_layout`; line 51: `if active_tab == "basic"` before `elif active_tab == "overview"` |
| `tests/test_dashboard.py` | 18 tests, 0 skipped, all passing | VERIFIED | 18 tests; 0 `pytest.mark.skip` decorators; `18 passed in 0.62s` confirmed |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `src/dashboard/callbacks.py` | `src/dashboard/tabs/basic.py` | `active_tab == "basic"` branch + lazy import | VERIFIED | Line 44 lazy import; line 51 `if active_tab == "basic": return build_basic_layout(...)` |
| `src/dashboard/layout.py` | `dcc.Tabs` | `value="basic"` as default | VERIFIED | Line 130: `value="basic"` confirmed |
| `src/dashboard/tabs/basic.py` | `src/dashboard/charts/bullet_chart.py` | `from ... import make_consensus_bullet_chart` | VERIFIED | Line 23: direct import; called at line 293 |
| `src/dashboard/tabs/overview.py` | `src/dashboard/charts/bullet_chart.py` | `from ... import make_consensus_bullet_chart` | VERIFIED | Line 27: import present; called in `_build_consensus_panel()` and `_build_expert_consensus_panel()` |
| `src/dashboard/tabs/overview.py` | `market_anchors_ai.parquet` | `ANCHORS_DF` from `app.py` | VERIFIED | Line 19: `ANCHORS_DF` imported; used in `_build_consensus_panel()` and `_build_expert_consensus_panel()` |
| `src/dashboard/tabs/overview.py` | `FORECASTS_DF` | `point_estimate_real_2020` (not alias) | VERIFIED | Lines 275-288: all column references use native names `point_estimate_real_2020`, `ci80_lower`, `ci80_upper`, etc. |
| `src/dashboard/charts/fan_chart.py` | `FORECASTS_DF` | `ci80_lower` (not alias) | VERIFIED | Lines 67-70: native column names `ci80_lower`, `ci80_upper`, `ci95_lower`, `ci95_upper` |
| `src/dashboard/app.py` | `backtesting_results.parquet` | `BACKTESTING_DF` global | VERIFIED | Line 35: `BACKTESTING_DF = pd.read_parquet(DATA_PROCESSED / "backtesting_results.parquet")` |
| `src/dashboard/tabs/diagnostics.py` | `src/dashboard/app.py` | `import BACKTESTING_DF` | VERIFIED | Line 14: `from src.dashboard.app import BACKTESTING_DF, ...`; used at lines 114, 170, 188 |
| `src/dashboard/charts/backtest.py` | `backtesting_results.parquet` | `actual_usd` vs `predicted_usd` columns | VERIFIED | Lines 91, 94: `x=seg_df["actual_usd"]`, `y=seg_df["predicted_usd"]`; line 44: `actual_type == "hard"` filter |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| DASH-01 | 11-01 | Basic dashboard tier — 3 hero numbers (total AI market size, YoY growth rate, 2030 forecast), segment breakdown chart, growth fan chart on a single non-scrolling screen | SATISFIED | `basic.py`: 3 KPI cards with nominal USD; segment bar; fan chart; `overflow: "hidden"` layout container; `test_basic_tab_renders`, `test_basic_kpi_cards`, `test_basic_fan_chart_traces` all pass |
| DASH-02 | 11-01, 11-03 | Analyst consensus panel — model output vs published estimate range displayed side-by-side in Basic and Normal tiers | SATISFIED | Basic: `make_consensus_bullet_chart()` in `basic.py`; Normal Overview: `_build_consensus_panel()` in `overview.py`; `test_consensus_panel_segments`, `test_consensus_divergence_color` pass |
| DASH-03 | 11-03 | Revenue multiples reference table — EV/Revenue multiples for AI pure-plays (~33x), semiconductors, and conglomerates (~7x) with source attribution | SATISFIED | `_REVENUE_MULTIPLES` list in `overview.py` with all 4 rows; `_build_revenue_multiples_table()` with `dbc.Table`; "PitchBook Q4 2025" source note; `test_revenue_multiples_in_overview` passes |
| DASH-04 | 11-02, 11-04 | Normal/Expert modes updated — real USD figures replace composite indices, recalibrated narrative text, all existing tabs functional with new model outputs | SATISFIED | Zero alias columns in runtime; zero PCA/Composite Index text in codebase; Diagnostics shows real MAPE/R² from BACKTESTING_DF; `test_no_alias_columns`, `test_no_pca_strings`, `test_diagnostics_real_mape` pass |
| DASH-05 | 11-04 | Data vintage and methodology transparency — per-source, per-segment "last updated" timestamp and scope label displayed in UI | SATISFIED | `vintage_footer()` present in all 5 tabs (basic, overview, segments, drivers, diagnostics); `test_vintage_footer_present` passes; each call passes data-source and vintage strings |

All 5 requirements satisfied. No orphaned requirements found for Phase 11.

---

### Anti-Patterns Found

No blocker or warning anti-patterns found.

| File | Pattern | Severity | Notes |
|------|---------|----------|-------|
| — | No `return null`, `return {}`, empty handlers, TODO/FIXME, placeholder comments found in any phase-11 file | — | Clean |

---

### Human Verification Required

The following items require running the Dash application and cannot be verified programmatically:

#### 1. Single non-scrolling screen (DASH-01)

**Test:** Run the app (`uv run python -m src.dashboard.app`), navigate to the Basic tab on a 1080p or higher resolution display.
**Expected:** All content — KPI row, chart row, and consensus panel — is visible without vertical scrolling. Layout uses `overflow: "hidden"` with `height: "calc(100vh - 120px)"`.
**Why human:** CSS `overflow: hidden` and `calc()` viewport units require a live browser to evaluate pixel-level rendering.

#### 2. Confidence dot color display

**Test:** Open the Basic tab and visually inspect the three traffic-light dots (●) next to each KPI value.
**Expected:** Dots render as colored circles (green/amber/red) in the correct semantic color. Colors should match `#2ECC71`, `#F39C12`, `#E74C3C`.
**Why human:** Browser color rendering and font glyph (U+25CF) visibility cannot be verified from component trees.

#### 3. Revenue multiples table readability

**Test:** Switch to Overview tab in Normal mode. Scroll to the EV/Revenue Reference Multiples card.
**Expected:** Table rows are legible, alternating row clarity visible, `~33x` through `~7x` values are immediately scannable.
**Why human:** Visual table formatting and readability require a rendered browser.

---

### Gaps Summary

No gaps found. All 10 observable truths are verified, all 9 artifacts are substantive and wired, all 10 key links are connected, and all 5 requirements (DASH-01 through DASH-05) are satisfied.

**Test suite result:** `18 passed, 0 failed, 0 skipped` in 0.62s.

**Commit provenance:** All phase-11 commits verified in git log:
- `e312f83` — feat(11-01): bullet_chart.py, confidence colors, vintage_footer, Wave 0 scaffolds
- `d990100` — feat(11-01): basic.py wired as default tab
- `a9715e2` — feat(11-02): alias removal from app.py, BACKTESTING_DF load
- `4c77bb5` — feat(11-02): all callsites updated, PCA text removed
- `c9addd4` — feat(11-03): consensus panel and revenue multiples table
- `0d7c2fd` — feat(11-03): test_revenue_multiples_in_overview unskipped
- `9f769d5` — feat(11-04): diagnostics.py and backtest.py rewritten
- `be8b2a3` — feat(11-04): vintage footers in segments/drivers, remaining tests unskipped

---

_Verified: 2026-03-26_
_Verifier: Claude (gsd-verifier)_
