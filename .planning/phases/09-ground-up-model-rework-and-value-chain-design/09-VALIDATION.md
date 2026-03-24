---
phase: 9
slug: ground-up-model-rework-and-value-chain-design
status: draft
nyquist_compliant: false
wave_0_complete: false
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

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | MODL-04 | unit | `uv run pytest tests/test_config.py::TestValueChainTaxonomy -x` | inline (09-01) | ⬜ pending |
| 09-02-01 | 02 | 2 | MODL-01 | unit | `uv run pytest tests/test_model_contract.py -x` | inline (09-02) | ⬜ pending |
| 09-03-01 | 03 | 3 | MODL-01, MODL-05 | unit | `uv run pytest tests/test_model_rework.py -x` | inline (09-03) | ⬜ pending |
| 09-04-01 | 04 | 4 | MODL-01, MODL-05 | unit | `uv run pytest tests/test_ensemble_usd.py tests/test_forecast_usd.py -x` | inline (09-04) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] All test files created inline by their respective plans (no separate Wave 0 stubs needed)

*Existing test infrastructure from v1.0 + Phase 8 covers framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Forecast CAGR in 25-40% range | MODL-05 | Requires running full model pipeline on real data | Run pipeline, compute CAGR from 2024-2030 forecasts, verify within range |
| Dashboard renders without crash | MODL-01 | Requires visual inspection of Dash app | Run `uv run python scripts/run_dashboard.py`, verify all tabs load |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
