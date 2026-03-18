---
phase: 01-data-foundation
plan: "03"
subsystem: ingestion
tags: [lseg, lseg-data, parquet, trbc, pandera, pyarrow]

# Dependency graph
requires:
  - phase: 01-01
    provides: pandera LSEG_RAW_SCHEMA, validate_raw_lseg, config.settings DATA_RAW, load_industry_config

provides:
  - LSEG Workspace Desktop Session connector (open/close session)
  - fetch_lseg_companies — TRBC-driven company universe discovery
  - fetch_company_financials — batched financial field fetch for RIC list
  - save_raw_lseg — Parquet writer with provenance metadata to data/raw/lseg/
  - lseg-data.config.json.example template for Desktop Session auth

affects: [01-05, processing, models]

# Tech tracking
tech-stack:
  added: [lseg-data, pyarrow, pyarrow.parquet]
  patterns:
    - TRBC screening expression built dynamically from config (not hardcoded)
    - Batched API fetch (100 RICs per batch) to respect rate limits
    - Parquet output with embedded provenance metadata (source, industry, fetched_at)
    - Desktop Session auth — no API key needed, flows through open Workspace app

key-files:
  created:
    - src/ingestion/lseg.py
    - tests/test_ingestion_lseg.py
    - lseg-data.config.json.example
  modified: []

key-decisions:
  - "Desktop Session auth via lseg-data.config.json (gitignored) — app-key left empty, authentication flows through open Workspace"
  - "TRBC codes dynamically read from config['lseg']['trbc_codes'] — zero hardcoded codes in lseg.py"
  - "Batch size of 100 RICs per get_data() call to stay within LSEG API limits"
  - "Integration tests marked @pytest.mark.integration — excluded from default test run, require live Workspace"
  - "TR.TRBCIndustryCode (8-digit) used in SCREEN() expression instead of TR.TRBCActivityCode (10-digit) — config stores 8-digit Industry codes, Activity codes are 10-digit and at a different hierarchy level"

patterns-established:
  - "Config-driven screening: lseg.py reads TRBC codes from industry config, not source code"
  - "Validate immediately: every API response passed through validate_raw_lseg before return"
  - "Provenance metadata embedded in Parquet schema metadata (not columns)"

requirements-completed: [DATA-05]

# Metrics
duration: ~30min
completed: 2026-03-18
---

# Phase 1 Plan 03: LSEG Workspace Connector Summary

**LSEG Workspace connector using Desktop Session auth, TRBC-based AI company universe discovery, and batched financial data fetch written to Parquet with provenance metadata — integration tests verified with live Workspace (2 passed in 6.69s)**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-03-17T15:08:28Z
- **Completed:** 2026-03-18
- **Tasks:** 2 (Task 1: TDD connector build; Task 2: human-verify checkpoint approved)
- **Files modified:** 3

## Accomplishments

- LSEG Workspace connector authenticates via Desktop Session (no separate API key)
- Company universe built by screening TRBC codes from config/industries/ai.yaml — zero hardcoded codes in source
- Financial data fetched in batches of 100 RICs with pandera validation after every fetch
- Raw data written to data/raw/lseg/ as Parquet with embedded source/industry/timestamp metadata
- All 5 mocked unit tests pass; both integration tests verified with live Workspace (test_lseg_session_opens PASSED, test_full_lseg_fetch PASSED — 6.69s); company universe populated

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for LSEG connector** - `4032144` (test)
2. **Task 1 (GREEN): LSEG connector implementation** - `216289d` (feat)
3. **Deviation fix: TR.TRBCIndustryCode for 8-digit screening** - `67cbb95` (fix)

_Note: TDD tasks have separate test and implementation commits. The TRBC field fix was a deviation committed separately during integration verification._

## Files Created/Modified

- `src/ingestion/lseg.py` — LSEG Workspace connector: open/close session, fetch companies by TRBC, fetch financials, save Parquet
- `tests/test_ingestion_lseg.py` — 5 unit tests (mocked), 2 integration tests (@pytest.mark.integration)
- `lseg-data.config.json.example` — Desktop Session config template (app-key left empty)

## Decisions Made

- Desktop Session auth config file pattern: `lseg-data.config.json` is gitignored, `.example` committed as template
- TRBC codes read from config via `config["lseg"]["trbc_codes"]` — ensures reproducibility when codes change
- Batch size of 100 chosen based on typical LSEG API per-request limits documented in RESEARCH.md
- Integration tests excluded from default pytest run via `-m "not integration"` marker

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TRBC screening field: TR.TRBCActivityCode → TR.TRBCIndustryCode**

- **Found during:** Task 2 (human-verify checkpoint — integration test run revealed empty or incorrect company universe)
- **Issue:** The SCREEN() expression used `TR.TRBCActivityCode=="{code}"` but config/industries/ai.yaml stores 8-digit TRBC Industry codes (e.g., `57201010`). `TR.TRBCActivityCode` maps to 10-digit Activity codes — the wrong TRBC hierarchy level — causing the company universe fetch to return wrong or empty results
- **Fix:** Changed screening expression in `fetch_lseg_companies` to use `TR.TRBCIndustryCode` which correctly matches 8-digit codes
- **Files modified:** `src/ingestion/lseg.py`
- **Verification:** Integration tests passed — `test_lseg_session_opens PASSED`, `test_full_lseg_fetch PASSED` (2 passed in 6.69s); company universe populated
- **Committed in:** `67cbb95`

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix was essential for correct company universe discovery. Without it, the SCREEN() expression would silently match Activity-level codes (10-digit) while config provides Industry-level codes (8-digit), yielding an empty universe. No scope creep.

## Issues Encountered

None beyond the TRBC field mismatch documented above.

## User Setup Required

**External service requires manual configuration before integration tests can pass:**

1. Ensure LSEG Workspace desktop application is open and logged in on this machine
2. Copy `lseg-data.config.json.example` to `lseg-data.config.json` in project root
3. Verify connectivity: `uv run pytest tests/test_ingestion_lseg.py -v -m integration`
4. Expected: session opens successfully, company universe returns >0 companies

## Next Phase Readiness

- LSEG connector is production-ready: config-driven, validated, Parquet output with provenance
- Company universe discovery verified against live LSEG Workspace — both integration tests pass
- Parquet output at data/raw/lseg/ is the stable input for downstream statistical processing in 01-05
- Phase 1 data foundation complete — LSEG, World Bank, and OECD connectors all operational

---
*Phase: 01-data-foundation*
*Completed: 2026-03-18*

## Self-Check: PASSED

- src/ingestion/lseg.py: FOUND
- tests/test_ingestion_lseg.py: FOUND
- lseg-data.config.json.example: FOUND
- Commit 4032144 (test RED): FOUND
- Commit 216289d (feat GREEN): FOUND
- Commit 67cbb95 (fix TRBC field): FOUND
- Integration tests verified: test_lseg_session_opens PASSED, test_full_lseg_fetch PASSED (2 passed in 6.69s)
