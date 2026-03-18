---
phase: 01-data-foundation
plan: 04
subsystem: data-processing
tags: [pandas, pyarrow, parquet, deflation, interpolation, pandera, gdp-deflator]

# Dependency graph
requires:
  - phase: 01-data-foundation-01-01
    provides: pandera PROCESSED_SCHEMA, check_no_nominal_columns, config/settings.py (BASE_YEAR, DATA_PROCESSED)
  - phase: 01-data-foundation-01-02
    provides: World Bank and OECD raw ingestion patterns (column naming, DataFrame structure)
  - phase: 01-data-foundation-01-03
    provides: LSEG ingestion patterns, TRBC code config in ai.yaml
provides:
  - "src/processing/deflate.py — deflate_to_base_year, apply_deflation"
  - "src/processing/interpolate.py — interpolate_series, apply_interpolation with estimated_flag"
  - "src/processing/tag.py — apply_industry_tags, tag_lseg_by_trbc"
  - "src/processing/normalize.py — normalize_world_bank, normalize_oecd, normalize_lseg, write_processed_parquet"
  - "46 tests covering deflation arithmetic, identity, column renaming, interpolation flagging, full pipeline"
affects: [phase-02-statistical-modeling, phase-03-ml, phase-04-dashboard, phase-05-reports]

# Tech tracking
tech-stack:
  added: [pyarrow (Parquet write with schema metadata), pyarrow.parquet]
  patterns:
    - "TDD red-green cycle: tests written first (ImportError = RED), implementation makes them pass (GREEN)"
    - "Year-indexed Series for deflation lookup — year is a column in DataFrames, must be mapped to index before deflate_to_base_year"
    - "estimated_flag OR-accumulation: once a row is flagged, subsequent interpolation steps preserve the flag"
    - "Parquet provenance metadata: source, industry, base_year, fetched_at stored as schema-level bytes metadata"

key-files:
  created:
    - src/processing/deflate.py
    - src/processing/interpolate.py
    - src/processing/tag.py
    - src/processing/normalize.py
    - tests/test_deflate.py
    - tests/test_interpolate.py
    - tests/test_processing.py
  modified: []

key-decisions:
  - "apply_deflation builds year-indexed Series from year column, then .values to reset index — avoids year/positional index mismatch in deflate_to_base_year"
  - "estimated_flag uses OR accumulation across multiple interpolation calls — once flagged, always flagged"
  - "normalize_oecd raises ValueError on missing economy column rather than silently producing invalid rows"
  - "tag_lseg_by_trbc reads TRBC codes from config dynamically — zero hardcoded segment mappings in production code"
  - "write_processed_parquet embeds source/industry/base_year/fetched_at as Parquet schema metadata for downstream attribution"

patterns-established:
  - "Nominal->Real pipeline: _nominal_ suffix in columns triggers deflation, output renamed to _real_2020"
  - "Transparency flagging: every interpolated value gets estimated_flag=True — non-negotiable per CONTEXT.md"
  - "Defensive validation: normalize_oecd refuses DataFrames without economy column rather than producing corrupt output"

requirements-completed: [DATA-06, DATA-07]

# Metrics
duration: 4min
completed: 2026-03-18
---

# Phase 1 Plan 04: Data Processing Pipeline Summary

**GDP deflation to 2020 constant USD, estimated_flag interpolation, config-driven industry tagging, and Parquet output with provenance metadata — 46 tests, all green**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-18T09:16:52Z
- **Completed:** 2026-03-18T09:20:58Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Full data processing pipeline: nominal->real deflation, transparent interpolation flagging, industry/segment tagging, schema validation, Parquet write
- 46 tests covering deflation identity, arithmetic, missing base year errors, column renaming, estimated_flag transparency, end-to-end pipeline validation, provenance metadata
- DATA-07 satisfied: every processed row carries a `source` column; Parquet files embed source/industry/base_year/fetched_at as schema metadata

## Task Commits

Each task was committed atomically:

1. **Task 1: Deflation and interpolation modules** - `bb3663b` (feat)
2. **Task 2: Tagging module and full normalization pipeline** - `4e2fce3` (feat)

_Note: TDD tasks had inline fix during GREEN phase (year-index alignment bug in apply_deflation — Rule 1 auto-fix)._

## Files Created/Modified

- `src/processing/deflate.py` — deflate_to_base_year (per-series formula) + apply_deflation (DataFrame-level, renames _nominal_ -> _real_2020)
- `src/processing/interpolate.py` — interpolate_series (linear/index-based by gap size) + apply_interpolation (DataFrame-level with estimated_flag OR-accumulation)
- `src/processing/tag.py` — apply_industry_tags (adds industry_tag, industry_segment, source) + tag_lseg_by_trbc (config-driven TRBC mapping)
- `src/processing/normalize.py` — normalize_world_bank, normalize_oecd, normalize_lseg, write_processed_parquet (orchestrates full pipeline)
- `tests/test_deflate.py` — 12 tests: identity, arithmetic, missing deflator, column renaming, no-nominal check
- `tests/test_interpolate.py` — 13 tests: linear gap fill, estimated_flag transparency, large gap fallback, auto-detection
- `tests/test_processing.py` — 21 tests: tagging, World Bank pipeline, OECD pipeline, ValueError on missing economy, Parquet provenance

## Decisions Made

- `apply_deflation` builds a year-indexed pd.Series from the `year` column, calls `deflate_to_base_year`, then uses `.values` to reset the result index back to the DataFrame's positional index. Without this, `deflate_to_base_year` received a positional-indexed Series (0,1,2...) and could not find base year 2020.
- `estimated_flag` uses OR-accumulation: if a row was already flagged by a prior step, it remains flagged through all subsequent `apply_interpolation` calls.
- `normalize_oecd` raises `ValueError` on missing `economy` column — silent pass-through would produce rows failing `PROCESSED_SCHEMA` validation with no clear diagnosis.
- TRBC segment mapping reads entirely from config — no hardcoded TRBC codes in `tag.py` or `normalize.py`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed year-indexed Series alignment in apply_deflation**
- **Found during:** Task 1 (GREEN phase, test_column_renaming_nominal_to_real)
- **Issue:** `deflator_aligned` Series was built with `.values` dropping the year index. `deflate_to_base_year` looked up `base_year=2020` in index `[0,1,2,3,4]` and raised ValueError.
- **Fix:** Map year column to deflator via dict, build Series with `index=df["year"].values`, call `.values` on the deflated result to reset to positional index.
- **Files modified:** `src/processing/deflate.py`
- **Verification:** All 12 deflation tests pass including `test_deflation_base_year_identity_in_dataframe`
- **Committed in:** `bb3663b` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix was necessary for correctness — the index alignment error would have caused all DataFrame-level deflation calls to fail. No scope creep.

## Issues Encountered

- Pandera attaches `DataFrameSchema` object to `df.attrs` after validation; PyArrow cannot serialize this as JSON and emits a `UserWarning`. This is harmless — provenance metadata is stored in Parquet schema metadata (bytes keys), not in DataFrame attrs. Logged as out-of-scope (pre-existing pandera/pyarrow interaction, not introduced by this plan).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Processing pipeline complete: all ingested data can be deflated to 2020 constant USD, interpolated with transparency flags, tagged with industry/segment/source, validated against PROCESSED_SCHEMA, and written to `data/processed/` as Parquet
- Phase 2 (statistical modeling) can import from `src.processing.normalize` directly — pipeline produces validated DataFrames ready for econometric modeling
- No blockers. The pandera/pyarrow attrs warning is cosmetic and does not affect output correctness.

---
*Phase: 01-data-foundation*
*Completed: 2026-03-18*
