---
phase: 2
slug: statistical-baseline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pyproject.toml [tool.pytest.ini_options] (from Phase 1) |
| **Quick run command** | `uv run pytest tests/test_models.py tests/test_diagnostics.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_models.py tests/test_diagnostics.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | MODL-01 | unit | `uv run pytest tests/test_models.py::test_arima_fits -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 0 | MODL-01 | unit | `uv run pytest tests/test_models.py::test_prophet_fits -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 0 | MODL-01 | unit | `uv run pytest tests/test_models.py::test_ols_fits -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 0 | MODL-01 | unit | `uv run pytest tests/test_models.py::test_residuals_schema -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 0 | MODL-06 | unit | `uv run pytest tests/test_models.py::test_cv_no_leakage -x` | ❌ W0 | ⬜ pending |
| 02-01-06 | 01 | 0 | MODL-06 | unit | `uv run pytest tests/test_models.py::test_pca_fit_train_only -x` | ❌ W0 | ⬜ pending |
| 02-01-07 | 01 | 0 | MODL-08 | unit | `uv run pytest tests/test_diagnostics.py::test_cusum_output_shape -x` | ❌ W0 | ⬜ pending |
| 02-01-08 | 01 | 0 | MODL-08 | unit | `uv run pytest tests/test_diagnostics.py::test_chow_known_break -x` | ❌ W0 | ⬜ pending |
| 02-01-09 | 01 | 0 | MODL-08 | unit | `uv run pytest tests/test_diagnostics.py::test_markov_fallback -x` | ❌ W0 | ⬜ pending |
| 02-01-10 | 01 | 0 | MODL-09 | unit | `uv run pytest tests/test_docs.py::test_assumptions_md_exists -x` | ❌ W0 | ⬜ pending |
| 02-01-11 | 01 | 0 | ARCH-04 | unit | `uv run pytest tests/test_docs.py::test_assumptions_tldr -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_models.py` — stubs for MODL-01 (ARIMA, Prophet, OLS fit), MODL-06 (CV, PCA leakage)
- [ ] `tests/test_diagnostics.py` — stubs for MODL-08 (CUSUM, Chow, Markov fallback)
- [ ] `tests/test_docs.py` — add test_assumptions_md_exists, test_assumptions_tldr to existing file
- [ ] Framework install: `uv add statsmodels prophet scikit-learn pmdarima`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ASSUMPTIONS.md readability | MODL-09 | Subjective quality assessment | Read docs/ASSUMPTIONS.md — verify TL;DR is accessible to non-technical reader, appendix has math foundations |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
