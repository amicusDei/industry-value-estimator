---
phase: "09"
plan: "01"
subsystem: config-and-features
tags: [taxonomy, value-chain, pca-deletion, flat-features, contract-tests]
dependency_graph:
  requires: []
  provides: [value_chain_layer_taxonomy, flat-feature-builder, contract-test-scaffold]
  affects: [09-02, 09-03, 09-04, phase-10-attribution]
tech_stack:
  added: []
  patterns: [flat-indicator-matrix, yaml-taxonomy-locking, wave-0-test-scaffolds]
key_files:
  created:
    - tests/test_contract_usd_billions.py
  modified:
    - config/industries/ai.yaml
    - tests/test_config.py
    - src/processing/features.py
    - tests/test_features.py
decisions:
  - "value_chain_layer_taxonomy locked 2026-03-24 with 4 layers (chip/cloud/application/end_market)"
  - "model_version set to v1.1_real_data in ai.yaml — gates model interface in Plan 09-02"
  - "build_pca_composite deleted (not gated) — no leakage concern after moving to real USD target"
  - "Contract test scaffold expects forecasts_ensemble.parquet in USD billions — fails until Plan 09-03"
metrics:
  duration_seconds: 219
  completed_date: "2026-03-24"
  tasks_completed: 2
  files_modified: 5
---

# Phase 9 Plan 01: Taxonomy Lock and Flat Feature Builder Summary

**One-liner:** Value chain layer taxonomy locked in ai.yaml with 4 layers (chip/cloud/application/end_market), PCA deleted from features.py, Wave 0 contract test scaffold created for USD billions output.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Lock value chain taxonomy in ai.yaml and create test scaffolds | f4ab6d5 | config/industries/ai.yaml, tests/test_config.py, tests/test_contract_usd_billions.py |
| 2 | Rebuild features.py as flat feature builder — delete PCA path entirely | fd936b0 | src/processing/features.py, tests/test_features.py |

## What Was Done

**Task 1 — Taxonomy lock and test scaffolds:**

Added `value_chain_layer_taxonomy` section to `config/industries/ai.yaml` with:
- `locked_date: "2026-03-24"` (gates Phase 10 attribution)
- 4 layers: `chip` (ai_hardware), `cloud` (ai_infrastructure), `application` (ai_software), `end_market` (ai_adoption)
- `multi_layer_policy` documenting primary-layer-wins assignment rule

Added `model_version: "v1.1_real_data"` as a top-level key — used by Plan 09-02 interface audit.

Commented out the legacy `value_chain:` section with `# LEGACY:` prefix on every line, preserving it as documentation.

Added `TestValueChainTaxonomy` class to `tests/test_config.py` with 6 tests — all pass.

Created `tests/test_contract_usd_billions.py` with 4 contract tests asserting USD billions range, plausible totals, CAGR between 15-60%, and no negatives. Tests are not skipped because the parquet file already exists from Phase 8, but they fail on the pre-Phase-9 composite-index values — this is expected Wave 0 behavior. They will pass after Plan 09-03 produces USD-unit forecasts.

**Task 2 — Flat feature builder:**

Removed from `src/processing/features.py`:
- `from sklearn.decomposition import PCA` import
- `from sklearn.pipeline import Pipeline` import
- `from sklearn.preprocessing import StandardScaler` import
- Entire `build_pca_composite` function (48 lines)

Updated module docstring to describe flat indicator matrix approach for ARIMA exogenous regressors and LightGBM features.

Updated `build_indicator_matrix` docstring to: "Build flat macro indicator matrix from long-format processed data. Output: wide matrix (n_years x n_indicators) in value_real_2020 units. No PCA reduction applied."

Deleted `TestPcaComposite` class from `tests/test_features.py` — removed tests for deleted function.

All 10 remaining feature tests pass. `build_manual_composite` and `assess_stationarity` are preserved unchanged.

## Verification Results

```
pytest tests/test_config.py tests/test_features.py -x -q
42 passed in 1.07s

python -c "import yaml; c=yaml.safe_load(open('config/industries/ai.yaml')); assert 'value_chain_layer_taxonomy' in c and c['model_version']=='v1.1_real_data'"
# OK

grep -c "build_pca_composite" src/processing/features.py
# 0

grep -c "value_chain_layer_taxonomy" config/industries/ai.yaml
# 1
```

## Deviations from Plan

None — plan executed exactly as written.

The contract test file runs rather than skips (the parquet file exists from Phase 8), and the tests fail on the pre-Phase-9 composite-index values. This is expected Wave 0 behavior: the skipif guard is `not PARQUET_PATH.exists()`, which is False because the file exists. The tests are designed to fail now and pass after Plan 09-03.

## Self-Check: PASSED

- config/industries/ai.yaml: contains value_chain_layer_taxonomy, model_version, LEGACY comments
- tests/test_config.py: contains TestValueChainTaxonomy, 32 tests pass
- tests/test_contract_usd_billions.py: created with 4 contract tests
- src/processing/features.py: no build_pca_composite, no sklearn imports
- tests/test_features.py: no TestPcaComposite, 10 tests pass
- Commits f4ab6d5 and fd936b0 exist in git log
