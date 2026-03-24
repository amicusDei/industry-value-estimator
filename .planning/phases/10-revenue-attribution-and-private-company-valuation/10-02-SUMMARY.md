---
phase: 10-revenue-attribution-and-private-company-valuation
plan: "02"
subsystem: data-processing
tags: [revenue-attribution, yaml-registry, pandera, pyarrow, parquet, pandas, modl-02]

# Dependency graph
requires:
  - phase: 10-01
    provides: ATTRIBUTION_SCHEMA in validate.py, ai_attribution_registry.yaml stub (3 entries), test_revenue_attribution.py scaffold

provides:
  - ai_attribution_registry.yaml expanded to 15 companies (all EDGAR companies) with full provenance
  - src/processing/revenue_attribution.py with load_attribution_registry, estimate_ai_revenue, compile_and_write_attribution
  - data/processed/revenue_attribution_ai.parquet with pyarrow provenance metadata
  - pipeline.py Step 8 wired to compile_and_write_attribution()

affects:
  - 10-03-private-company-valuations
  - 11-dashboard
  - backtesting

# Tech tracking
tech-stack:
  added: []
  patterns:
    - load_attribution_registry() follows load_analyst_registry() pattern from market_anchors.py
    - compile_and_write_attribution() follows compile_and_write_market_anchors() Parquet provenance pattern
    - Pure-play CIK set (PURE_PLAY_CIKS) for O(1) direct_disclosure routing

key-files:
  created:
    - data/raw/attribution/ai_attribution_registry.yaml (expanded from 3 to 15 entries)
    - src/processing/revenue_attribution.py
    - data/processed/revenue_attribution_ai.parquet
  modified:
    - tests/test_revenue_attribution.py (unskipped + 16 new tests added)
    - tests/test_pipeline_wiring.py (TestAttributionWiring class added)

key-decisions:
  - "Registry has 15 companies not 14: ai.yaml edgar_companies list has 15 CIKs (4 chip + 4 cloud including Oracle + 4 software + 3 adoption), plan text slightly miscounted"
  - "test_attribution_step_wired_in_pipeline_module uses source-level file read instead of module import to avoid pandasdmx pydantic compatibility error on pipeline module import"

patterns-established:
  - "Pattern: attribution registry YAML named {industry_id}_attribution_registry.yaml under data/raw/attribution/"
  - "Pattern: all attribution entries require ratio_source + vintage_date + uncertainty_low + uncertainty_high (no bare float percentages)"
  - "Pattern: pure-play CIK set checked first in estimate_ai_revenue() before config-driven lookup"

requirements-completed: [MODL-02]

# Metrics
duration: 6min
completed: 2026-03-24
---

# Phase 10 Plan 02: Revenue Attribution Pipeline Summary

**Hand-curated YAML registry expanded to 15 public companies with AI revenue estimates, validated with ATTRIBUTION_SCHEMA, compiled to revenue_attribution_ai.parquet via revenue_attribution.py, and wired into pipeline.py Step 8**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-03-24T14:38:56Z
- **Completed:** 2026-03-24T14:44:28Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Expanded ai_attribution_registry.yaml from 3 stub entries to 15 full entries covering all EDGAR companies across 4 value chain layers: chip (NVIDIA, AMD, TSMC, Intel), cloud (Microsoft, Alphabet, Amazon, Oracle), application (Palantir, C3.ai, ServiceNow, Salesforce), end_market (Meta, IBM, Accenture)
- Created revenue_attribution.py with three exported functions: load_attribution_registry (follows load_analyst_registry pattern), estimate_ai_revenue (pure-play CIK routing + config-driven fallback), compile_and_write_attribution (validates against ATTRIBUTION_SCHEMA, writes Parquet with pyarrow metadata)
- All 19 revenue attribution tests pass; 2 additional wiring tests added to test_pipeline_wiring.py

## Task Commits

Each task was committed atomically:

1. **TDD RED - Failing tests** - `04c05ae` (test)
2. **Task 1: YAML registry expansion + revenue_attribution.py** - `f31b17c` (feat)
3. **Task 2: Pipeline wiring + wiring tests** - `407446c` (feat)

**Plan metadata:** [created in this commit] (docs: complete plan)

_Note: TDD task has separate test commit (RED) + implementation commit (GREEN)_

## Files Created/Modified

- `/Users/simonleowegner/my-project/data/raw/attribution/ai_attribution_registry.yaml` - Expanded from 3 to 15 companies with full provenance fields
- `/Users/simonleowegner/my-project/src/processing/revenue_attribution.py` - New module: load_attribution_registry, estimate_ai_revenue, compile_and_write_attribution
- `/Users/simonleowegner/my-project/data/processed/revenue_attribution_ai.parquet` - Output Parquet with 15 rows, pyarrow provenance metadata
- `/Users/simonleowegner/my-project/tests/test_revenue_attribution.py` - Unskipped compile test + 16 new tests across 5 test classes
- `/Users/simonleowegner/my-project/tests/test_pipeline_wiring.py` - Added TestAttributionWiring class (2 tests)

## Decisions Made

- **Registry has 15 companies, not 14:** The plan text says "14 EDGAR companies" but ai.yaml edgar_companies has 15 CIKs (Oracle is in the cloud/infrastructure group alongside Microsoft, Alphabet, Amazon). Registry counts 4 chip + 4 cloud + 4 software + 3 adoption = 15. Tests updated to assert 15.
- **Source-level pipeline wiring test:** test_attribution_step_wired_in_pipeline_module reads pipeline.py as text instead of importing the module, because importing pipeline.py triggers pandasdmx pydantic v1/v2 compatibility error (pre-existing environment issue). Source-level check verifies the wiring without triggering the import error.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed registry row count from 14 to 15**
- **Found during:** Task 1 (compile test)
- **Issue:** Plan stated 14 companies; actual ai.yaml edgar_companies contains 15 CIKs (Oracle included in ai_infrastructure group). Tests failed with `AssertionError: Expected 14 rows, got 15`
- **Fix:** Updated tests to assert 15 rows; YAML correctly has 15 entries matching ai.yaml
- **Files modified:** tests/test_revenue_attribution.py
- **Verification:** All 19 tests pass with 15-row assertion
- **Committed in:** f31b17c (Task 1 commit)

**2. [Rule 3 - Blocking] Fixed pipeline wiring test import error**
- **Found during:** Task 2 (test_attribution_step_wired_in_pipeline_module)
- **Issue:** `from src.ingestion import pipeline` triggers `ImportError: cannot import name 'make_generic_validator' from 'pydantic.class_validators'` (pandasdmx pydantic v1/v2 incompatibility, pre-existing)
- **Fix:** Changed test to read pipeline.py source file directly with Path.read_text() instead of importing the module
- **Files modified:** tests/test_pipeline_wiring.py
- **Verification:** Both attribution wiring tests pass
- **Committed in:** 407446c (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes were necessary for correctness and test executability. No scope creep — the deviations aligned with actual ai.yaml content.

## Issues Encountered

- Pre-existing pandasdmx/pydantic incompatibility causes `TestLsegScalar::test_lseg_scalar_applied_to_pca` to fail in test_pipeline_wiring.py. This is unrelated to Plan 10-02 work and is out of scope.

## Next Phase Readiness

- `revenue_attribution_ai.parquet` is ready for consumption by downstream phases (backtesting, dashboard)
- All 15 EDGAR companies have attribution_method, ratio_source, uncertainty_low, uncertainty_high, vintage_date
- Pure-play companies (NVIDIA/Palantir/C3.ai) correctly use direct_disclosure with tight ±5% bounds
- MODL-02 requirement complete; Plan 10-03 (private company valuations) can proceed

---
*Phase: 10-revenue-attribution-and-private-company-valuation*
*Completed: 2026-03-24*

## Self-Check: PASSED

All artifacts verified:
- FOUND: src/processing/revenue_attribution.py
- FOUND: data/raw/attribution/ai_attribution_registry.yaml
- FOUND: data/processed/revenue_attribution_ai.parquet
- FOUND: .planning/phases/10-revenue-attribution-and-private-company-valuation/10-02-SUMMARY.md
- COMMIT 04c05ae: test(10-02): add failing tests for revenue attribution module
- COMMIT f31b17c: feat(10-02): implement revenue attribution pipeline for 15 public companies
- COMMIT 407446c: feat(10-02): wire revenue attribution into pipeline.py Step 8
