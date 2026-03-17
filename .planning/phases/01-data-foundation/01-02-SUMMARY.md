---
phase: 01-data-foundation
plan: 02
subsystem: ingestion
tags: [wbgapi, pandasdmx, world-bank, oecd, parquet, pandera, requests-cache, sdmx]

# Dependency graph
requires:
  - phase: 01-data-foundation/01-01
    provides: config/settings.py (load_industry_config, get_all_economy_codes, DATA_RAW, DEFLATOR_INDICATOR), src/processing/validate.py (validate_raw_world_bank, validate_raw_oecd), config/industries/ai.yaml (indicator codes)

provides:
  - World Bank connector (fetch_world_bank_indicators, save_raw_world_bank) — fetches GDP, R&D, ICT indicators for all configured economies
  - OECD connector (fetch_oecd_msti, fetch_oecd_ai_patents, save_raw_oecd) — fetches MSTI and PATS_IPC G06N datasets with 30-day cache
  - Ingestion pipeline orchestrator (run_ingestion) — config-driven routing to WB and OECD connectors
  - 14 unit tests covering both connectors and pipeline with full mock isolation

affects: [01-data-foundation/01-03, processing, deflation-pipeline]

# Tech tracking
tech-stack:
  added: [wbgapi, pandasdmx, requests-cache, pyarrow, tqdm]
  patterns: [TDD-RED-GREEN-COMMIT, pandera-at-fetch-boundary, immutable-raw-parquet, provenance-metadata-in-schema, patch.object-for-module-level-mocking]

key-files:
  created:
    - src/ingestion/world_bank.py
    - src/ingestion/oecd.py
    - src/ingestion/pipeline.py
    - tests/test_ingestion.py
  modified: []

key-decisions:
  - "_sdmx_to_dataframe helper wraps pandasdmx output: to_pandas() returns pd.Series with MultiIndex, not DataFrame — must call reset_index() on Series, not on the raw result"
  - "patch.object on the pipeline module (not string path) avoids import-time bypass when mocking module-level function references"
  - "OECD fallback key: try LOCATION first, catch all exceptions, retry with COU — handles OECD SDMX API dimension name inconsistency between environments"
  - "30-day SQLite requests-cache for OECD (2592000s) stored in data/raw/oecd/.cache — OECD queries are 30s+ and data updates annually"

patterns-established:
  - "Fetch boundary validation: every connector calls validate_raw_* before returning — fail loudly rather than silently writing corrupt Parquet"
  - "Immutable raw Parquet: files include provenance metadata (source, industry, fetched_at) written once, never modified"
  - "Config-driven connectors: indicator codes, country codes, date ranges all read from industry YAML — no hardcoded values in connector logic"
  - "Mock isolation in tests: patch.object targets the module's own references to avoid mocking the wrong binding when using importlib.reload"

requirements-completed: [DATA-03, DATA-04]

# Metrics
duration: 12min
completed: 2026-03-17
---

# Phase 1 Plan 2: Ingestion Connectors Summary

**World Bank (wbgapi) and OECD (pandasdmx) connectors with mandatory deflator co-fetch, 30-day SDMX cache, pandera validation at fetch boundary, and immutable Parquet output — 14 mocked unit tests all green**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-17T15:08:19Z
- **Completed:** 2026-03-17T15:20:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- World Bank connector fetches all 8 configured indicators (GDP, deflator, R&D, ICT) for all configured economies via wbgapi, reshapes MultiIndex output to wide format, validates against WORLD_BANK_RAW_SCHEMA, writes Parquet with provenance metadata
- OECD connector fetches MSTI and PATS_IPC (G06N filter) via pandasdmx SDMX, includes fallback dimension key handling (LOCATION vs COU), caches HTTP traffic with 30-day SQLite TTL via requests-cache
- Pipeline orchestrator reads industry YAML config and routes to both connectors via tqdm progress steps, returning dict of output paths; LSEG stub included for future Phase 1-03

## Task Commits

Each task was committed atomically:

1. **Task 1: World Bank ingestion connector** - `96ccabf` (feat)
2. **Task 2: OECD connector + pipeline orchestrator** - `f35f91c` (feat)

**Plan metadata:** (docs commit — see below)

_Note: TDD tasks followed RED (tests written first, confirmed failing) then GREEN (implementation written to pass)._

## Files Created/Modified
- `src/ingestion/world_bank.py` - World Bank connector: fetch_world_bank_indicators, save_raw_world_bank; mandatory DEFLATOR_INDICATOR injection; wbgapi MultiIndex reshape to wide format
- `src/ingestion/oecd.py` - OECD connector: fetch_oecd_msti, fetch_oecd_ai_patents, save_raw_oecd; _sdmx_to_dataframe helper; 30-day requests-cache; LOCATION/COU fallback
- `src/ingestion/pipeline.py` - Orchestrator: run_ingestion reads industry config and routes to WB and OECD connectors; LSEG stub for future plan
- `tests/test_ingestion.py` - 14 unit tests: TestWorldBankIngestion (6), TestOECDIngestion (5), TestIngestionPipeline (3); helper functions _make_wbgapi_mock_df, _make_sdmx_series

## Decisions Made
- `_sdmx_to_dataframe` helper: pandasdmx's `to_pandas()` returns `pd.Series` with MultiIndex — calling `reset_index()` on it directly produces the expected flat DataFrame. Initial implementation used `df.reset_index()` on the result of `to_pandas()` which caused "cannot insert X, already exists" when the mock returned a DataFrame with columns matching the index levels.
- `patch.object` for pipeline tests: the pipeline module imports connectors at module load time as local names. Using string-path `patch("src.ingestion.pipeline.fetch_oecd_msti")` is correct but `importlib.reload()` inside the patch context recreates those bindings, bypassing the patch. Using `patch.object(pipeline_mod, "fetch_oecd_msti")` patches the already-loaded module's attribute directly.
- OECD dimension key fallback: OECD SDMX API uses different dimension names across environments (stats.oecd.org uses `COU`, newer OECD.stat APIs may use `LOCATION`). Implementation tries LOCATION first with broad exception catch, then falls back to COU with rename.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pandasdmx Series reset_index handling**
- **Found during:** Task 2 (OECD tests going GREEN)
- **Issue:** `sdmx.to_pandas()` returns a `pd.Series` with a MultiIndex, not a DataFrame. Calling `reset_index()` on it works correctly for a Series but fails when a DataFrame with matching columns was accidentally returned (test mock setup issue). The production code path also needed the Series-aware helper.
- **Fix:** Added `_sdmx_to_dataframe()` helper that branches on `isinstance(raw, pd.Series)` and handles both the Series case (reset_index + rename value column) and the DataFrame case. Updated tests to use `_make_sdmx_series()` helper that correctly simulates pandasdmx output shape.
- **Files modified:** src/ingestion/oecd.py, tests/test_ingestion.py
- **Verification:** All 5 OECD tests pass after fix
- **Committed in:** f35f91c (Task 2 commit)

**2. [Rule 1 - Bug] Fixed pipeline test mock bypass caused by importlib.reload**
- **Found during:** Task 2 (TestIngestionPipeline going GREEN)
- **Issue:** Pipeline tests used `with patch("src.ingestion.pipeline.fetch_oecd_msti")` + `importlib.reload(pipeline_mod)` inside the patch context. The reload recreated the module, creating new function references that bypassed the active patches, causing real HTTP calls to OECD API.
- **Fix:** Changed all pipeline tests to import the module once (`import src.ingestion.pipeline as pipeline_mod`) and use `patch.object(pipeline_mod, "fetch_oecd_msti")` to patch the live module's attributes without reload.
- **Files modified:** tests/test_ingestion.py
- **Verification:** All 3 pipeline tests pass without live API calls
- **Committed in:** f35f91c (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both fixes required for test correctness and to prevent live API calls in unit tests. No scope creep.

## Issues Encountered
- OECD SDMX API (stats.oecd.org) returns 404 for `MSTI?detail=serieskeysonly` — this is expected; the OECD SDMX endpoint changed. The connector's try/except fallback handles this. Live integration tests will need to verify the correct working endpoint.

## Next Phase Readiness
- World Bank and OECD connectors are fully implemented and tested with mocks — ready for integration runs once live API endpoint behavior is verified
- Pipeline orchestrator is ready to route `run_ingestion("ai")` to both connectors
- LSEG connector stub exists in pipeline.py for Plan 01-03
- Blocker noted in STATE.md: live OECD SDMX endpoint needs validation (LOCATION vs COU dimension key) before first production fetch run

---
*Phase: 01-data-foundation*
*Completed: 2026-03-17*

## Self-Check: PASSED

- src/ingestion/world_bank.py: FOUND
- src/ingestion/oecd.py: FOUND
- src/ingestion/pipeline.py: FOUND
- tests/test_ingestion.py: FOUND
- .planning/phases/01-data-foundation/01-02-SUMMARY.md: FOUND
- Commit 96ccabf: FOUND
- Commit f35f91c: FOUND
