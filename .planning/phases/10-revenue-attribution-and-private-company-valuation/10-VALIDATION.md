---
phase: 10
slug: revenue-attribution-and-private-company-valuation
status: active
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-24
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (existing) |
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

| Plan | Task | Test Command | Requirement |
|------|------|-------------|-------------|
| 10-01 T1 | Add pandera schemas + ai.yaml subsegment ratios | `uv run python -c "from src.processing.validate import ATTRIBUTION_SCHEMA, PRIVATE_VALUATION_SCHEMA; print('OK')"` | MODL-02, MODL-03 |
| 10-01 T2 | Create stub YAMLs + test scaffolds | `uv run pytest tests/test_revenue_attribution.py tests/test_private_valuations.py tests/test_backtesting.py -v --timeout=30` | MODL-02, MODL-03, MODL-06 |
| 10-02 T1 | Attribution YAML + revenue_attribution.py | `uv run pytest tests/test_revenue_attribution.py -v --timeout=30` | MODL-02 |
| 10-02 T2 | Wire attribution into pipeline.py | `uv run pytest tests/test_pipeline_wiring.py -v -k "attribution" --timeout=30` | MODL-02 |
| 10-03 T1 | Private YAML + private_valuations.py | `uv run pytest tests/test_private_valuations.py -v --timeout=30` | MODL-03 |
| 10-03 T2 | Wire private valuations into pipeline.py | `uv run pytest tests/test_pipeline_wiring.py -v -k "private" --timeout=30` | MODL-03 |
| 10-04 T1 | Actuals assembly + walk_forward.py | `uv run pytest tests/test_backtesting.py -v --timeout=60` | MODL-06 |
| 10-04 T2 | Wire backtesting into pipeline.py | `uv run pytest tests/test_pipeline_wiring.py tests/test_backtesting.py -v --timeout=60` | MODL-06 |

---

## Wave 0 Requirements

Plan 10-01 creates all Wave 0 scaffolding:

- [x] `src/processing/validate.py` — ATTRIBUTION_SCHEMA and PRIVATE_VALUATION_SCHEMA added (Plan 10-01 T1)
- [x] `config/industries/ai.yaml` — attribution_subsegment_ratios section added (Plan 10-01 T1)
- [x] `data/raw/attribution/ai_attribution_registry.yaml` — 3-entry stub (Plan 10-01 T2)
- [x] `data/raw/private_companies/ai_private_registry.yaml` — 3-entry stub (Plan 10-01 T2)
- [x] `tests/test_revenue_attribution.py` — test scaffold with passing schema tests + skipped compile tests (Plan 10-01 T2)
- [x] `tests/test_private_valuations.py` — test scaffold with passing schema tests + skipped compile tests (Plan 10-01 T2)
- [x] `tests/test_backtesting.py` — test scaffold with all-skipped tests (Plan 10-01 T2)

All `MISSING` references in verification commands are resolved by Plan 10-01 Wave 0 tasks.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Attribution ratios defensibility | MODL-02 | Requires domain judgment on analyst sources | Review 3 attribution ratios against original earnings call quotes |
| Private company revenue accuracy | MODL-03 | Revenue estimates are from press reports | Cross-check 3 private company ARR figures against recent news |
| Backtesting MAPE reasonableness | MODL-06 | Requires domain judgment | Review MAPE values — <15% acceptable, 15-30% use with caution, >30% directional only |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (planner sign-off 2026-03-24)
