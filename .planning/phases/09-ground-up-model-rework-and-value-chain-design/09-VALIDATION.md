---
phase: 9
slug: ground-up-model-rework-and-value-chain-design
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-24
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing) |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/ -x --timeout=30` |
| **Full suite command** | `uv run pytest tests/ --timeout=60` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --timeout=30`
- **After every plan wave:** Run `uv run pytest tests/ --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Test File | Status |
|---------|------|------|-------------|-----------|-------------------|-----------|--------|
| 09-01-T1 | 01 | 1 | MODL-04 | unit | `uv run pytest tests/test_config.py::TestValueChainTaxonomy -x` | `tests/test_config.py` | pending |
| 09-01-T2 | 01 | 1 | MODL-04 | unit | `uv run pytest tests/test_features.py -x` | `tests/test_features.py` | pending |
| 09-02-T1 | 02 | 2 | MODL-01 | unit | `uv run pytest tests/test_models.py -x -k "arima"` | `tests/test_models.py` | pending |
| 09-02-T2 | 02 | 2 | MODL-01 | unit | `uv run pytest tests/test_models.py -x -k "prophet"` | `tests/test_models.py` | pending |
| 09-03-T1 | 03 | 3 | MODL-01 | unit | `uv run pytest tests/test_models.py -x -k "lgbm"` | `tests/test_models.py` | pending |
| 09-03-T2 | 03 | 3 | MODL-01, MODL-05 | integration | `grep -rn "VALUE_CHAIN_MULTIPLIERS\|VALUE_CHAIN_DERIVATION\|value_chain_multipliers" --include="*.py" src/ && exit 1 \|\| echo OK` | N/A (grep check) | pending |
| 09-03-T3 | 03 | 3 | MODL-01, MODL-05 | contract | `uv run pytest tests/test_contract_usd_billions.py -x` | `tests/test_contract_usd_billions.py` | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `tests/test_config.py` — exists (Phase 8), extended in 09-01 Task 1 with `TestValueChainTaxonomy`
- [x] `tests/test_features.py` — exists (v1.0), updated in 09-01 Task 2 (PCA tests removed)
- [x] `tests/test_models.py` — exists (v1.0), extended in 09-02 Tasks 1-2 and 09-03 Task 1
- [x] `tests/test_contract_usd_billions.py` — created in 09-01 Task 1 as Wave 0 scaffold (skipif until parquet exists)

*All test files created inline by their respective plans. No separate Wave 0 stubs needed.*
*Existing test infrastructure from v1.0 + Phase 8 covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Forecast CAGR in 25-40% range | MODL-05 | Requires running full model pipeline on real data | Run pipeline, compute CAGR from 2025-2030 forecasts, verify within range |
| Dashboard renders without crash | MODL-01 | Requires visual inspection of Dash app | Run `uv run python scripts/run_dashboard.py`, verify all tabs load |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
