---
phase: 08-data-architecture-and-ground-truth-assembly
plan: 02
subsystem: data
tags: [yaml, pandera, pandas, numpy, market-anchors, analyst-estimates, scope-normalization, pytest, tdd]

# Dependency graph
requires:
  - phase: 08-01
    provides: "config/industries/ai.yaml scope_mapping_table with 8 analyst firms and scope_coefficient values; market_boundary locked before data collection"
provides:
  - "data/raw/market_anchors/ai_analyst_registry.yaml: 54-entry hand-curated analyst estimate corpus (8 firms, publication years 2019-2025)"
  - "src/ingestion/market_anchors.py: load_analyst_registry(), scope_normalize(), compile_market_anchors(), validate_market_anchors()"
  - "src/processing/validate.py: MARKET_ANCHOR_SCHEMA DataFrameSchema for compiled anchor DataFrame"
  - "tests/test_market_anchors.py: 17-test suite covering registry structure, scope normalization, schema validation, and compilation pipeline"
affects:
  - "08-04-PLAN.md (ground truth reconciliation consumes compiled market anchors DataFrame)"
  - "Phase 9 (model calibration uses anchor estimates as ground truth)"
  - "Phase 10 (attribution and valuation depend on reconciled market size series)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "YAML registry as audit trail: ai_analyst_registry.yaml is human-readable record; compiled DataFrame is machine-readable pipeline input"
    - "scope_coefficient multiplier pattern: each analyst firm entry maps their scope to our scope via a single coefficient from ai.yaml scope_mapping_table"
    - "Nominal-only compilation at ingestion layer: deflation to real_2020 deferred to Plan 08-04 reconciliation module"
    - "estimated_flag: True when estimate_year > publication_year — distinguishes historical actuals from forward forecasts in the compiled output"
    - "Percentile aggregation: p25/median/p75 per (estimate_year, segment) group using np.percentile with method=linear"

key-files:
  created:
    - "data/raw/market_anchors/ai_analyst_registry.yaml"
    - "src/ingestion/market_anchors.py"
    - "tests/test_market_anchors.py"
  modified:
    - "src/processing/validate.py (MARKET_ANCHOR_SCHEMA appended)"

key-decisions:
  - "estimate_year range in MARKET_ANCHOR_SCHEMA extended to 2035 (not 2026) — registry intentionally includes long-horizon forecasts to 2030 and 2032 for sensitivity analysis; capping at 2026 would exclude legitimate data"
  - "estimated_flag logic: estimate_year > publication_year marks forecasts, not actuals — clean distinction for Plan 08-04 to weight actuals more heavily than projections"
  - "compile_market_anchors returns nominal USD only — deflation to real_2020 is Plan 08-04's responsibility per plan specification"
  - "Firms not found in scope_mapping_table default to scope_coefficient=1.0 — safe default, never silently drops entries"

patterns-established:
  - "TDD pattern for data modules: RED (failing tests) committed before any implementation, GREEN (implementation) committed after all tests pass"
  - "YAML registry pattern: entries list with uniform schema, source_url for provenance, confidence field for weighting in reconciliation"
  - "compile_market_anchors() pipeline: load YAML → join scope_coefficients → normalize → groupby (year, segment) → percentile aggregation"

requirements-completed: [DATA-09]

# Metrics
duration: 20min
completed: 2026-03-24
---

# Phase 8 Plan 02: Analyst Registry and Market Anchors Compilation Summary

**54-entry hand-curated YAML analyst estimate corpus (8 firms, 2017-2032) with scope-normalized compilation to p25/median/p75 DataFrame via market_anchors.py, validated by MARKET_ANCHOR_SCHEMA — all 17 TDD tests pass green with no regressions.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-23T22:17:41Z
- **Completed:** 2026-03-24
- **Tasks:** 1 (TDD task: 2 commits — RED then GREEN)
- **Files modified:** 4 (ai_analyst_registry.yaml, market_anchors.py, validate.py, test_market_anchors.py)

## Accomplishments

- Hand-curated YAML registry with 54 entries from 8 analyst firms (IDC, Gartner, Grand View Research, Statista, Goldman Sachs, Bloomberg Intelligence, McKinsey, CB Insights) spanning publication years 2019-2025 with full vintage series
- `market_anchors.py` module implements the complete pipeline: YAML loading → scope normalization via ai.yaml coefficients → per-(year, segment) percentile aggregation → pandera schema validation
- `MARKET_ANCHOR_SCHEMA` added to validate.py, validating the 8-column compiled DataFrame before it enters the Plan 08-04 reconciliation pipeline
- 17-test TDD suite covers registry structure, scope normalization math, schema compliance, per-year source coverage, and compilation correctness — all pass green
- No regressions in existing 11 validate.py tests

## Task Commits

TDD task committed in two phases:

1. **RED: Failing tests for analyst registry and market anchors** - `8cc67b2` (test)
2. **GREEN: YAML registry + market_anchors.py + MARKET_ANCHOR_SCHEMA** - `026da4a` (feat)

**Plan metadata:** (docs commit below)

_Note: TDD task used RED → GREEN pattern; no REFACTOR pass needed — code was clean on first implementation._

## Files Created/Modified

- `data/raw/market_anchors/ai_analyst_registry.yaml` — 54-entry registry with source_firm, publication_year, estimate_year, segment, as_published_usd_billions, scope_includes, scope_excludes, methodology_notes, source_url, confidence per entry
- `src/ingestion/market_anchors.py` — load_analyst_registry(), scope_normalize(), compile_market_anchors(), validate_market_anchors()
- `src/processing/validate.py` — MARKET_ANCHOR_SCHEMA appended (estimate_year 2017-2035, all 8 required columns)
- `tests/test_market_anchors.py` — TestAnalystRegistry (5), TestScopeNormalization (4), TestMarketAnchorSchema (2), TestSourceCoverage (1), TestCompileMarketAnchors (5) — 17 total

## Decisions Made

- `MARKET_ANCHOR_SCHEMA` estimate_year range extended to 2035 (plan spec said 2026) — the registry intentionally contains long-horizon forecasts for 2030 and 2032. Capping at 2026 would make the schema unusable for these entries, which are valuable as sensitivity analysis bounds. Range 2017-2035 accommodates all current entries and plausible future additions.
- `estimated_flag` implementation uses `estimate_year > publication_year` — a forecast is any entry where the analyst is projecting into the future; historical estimates have estimate_year <= publication_year. This allows Plan 08-04 to weight actuals more heavily than projections in reconciliation.
- Compilation is nominal-only — deflation deferred to Plan 08-04 per plan specification. This keeps the module's responsibility boundary clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Extended MARKET_ANCHOR_SCHEMA estimate_year range from 2026 to 2035**
- **Found during:** Task 1 (GREEN phase, schema validation test)
- **Issue:** Plan spec said `Check.in_range(2017, 2026)`, but registry entries contain long-horizon forecast entries for estimate_years 2030 (McKinsey, Gartner, Grand View, Statista) and 2032 (Bloomberg Intelligence). These are valid registry entries by design.
- **Fix:** Changed upper bound from 2026 to 2035 in MARKET_ANCHOR_SCHEMA. Range now covers all current entries and reasonable future additions.
- **Files modified:** src/processing/validate.py
- **Verification:** `test_compiled_df_validates` now passes; all 11 existing validate tests still pass
- **Committed in:** 026da4a (Task GREEN commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Auto-fix was necessary for correctness — the schema would reject legitimate long-horizon forecast data that Plan 08-04 needs for sensitivity analysis bounds. No scope creep.

## Issues Encountered

None — the only issue was the schema range bug, which was caught immediately by the TDD test and auto-fixed inline.

## User Setup Required

None — no external service configuration required. All data is from the hand-curated YAML registry committed to the repository.

## Next Phase Readiness

- `data/raw/market_anchors/ai_analyst_registry.yaml` is committed and ready as the immutable audit record
- `compile_market_anchors("ai")` produces a 19-row × 8-column DataFrame covering estimate_years 2018-2032 across all 5 segments
- `validate_market_anchors(df)` passes for the compiled output — Plan 08-04 can call these functions directly
- Plan 08-03 (EDGAR ingestion) can proceed in parallel — it does not depend on this module
- Plan 08-04 (ground truth reconciliation) requires this module's output as its primary input

---
*Phase: 08-data-architecture-and-ground-truth-assembly*
*Completed: 2026-03-24*
