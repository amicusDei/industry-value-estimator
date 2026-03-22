---
phase: 3
slug: ml-ensemble-and-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_ml_models.py tests/test_ensemble.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~25 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_ml_models.py tests/test_ensemble.py tests/test_forecast_output.py tests/test_shap.py tests/test_serialization.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | MODL-02 | unit | `uv run pytest tests/test_ml_models.py::TestLGBMResidualLearner -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 0 | MODL-02 | unit | `uv run pytest tests/test_ml_models.py::TestFeatureEngineering -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 0 | MODL-03 | unit | `uv run pytest tests/test_ensemble.py::TestEnsembleWeights -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 0 | MODL-03 | unit | `uv run pytest tests/test_ensemble.py::TestEnsembleCombiner -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 0 | MODL-04 | unit | `uv run pytest tests/test_forecast_output.py::test_vintage_column -x` | ❌ W0 | ⬜ pending |
| 03-01-06 | 01 | 0 | MODL-04 | unit | `uv run pytest tests/test_forecast_output.py::test_output_units -x` | ❌ W0 | ⬜ pending |
| 03-01-07 | 01 | 0 | MODL-05 | unit | `uv run pytest tests/test_forecast_output.py::test_no_bare_point_forecasts -x` | ❌ W0 | ⬜ pending |
| 03-01-08 | 01 | 0 | MODL-05 | unit | `uv run pytest tests/test_forecast_output.py::test_ci_ordering -x` | ❌ W0 | ⬜ pending |
| 03-01-09 | 01 | 0 | MODL-07 | unit | `uv run pytest tests/test_shap.py::TestSHAPValues -x` | ❌ W0 | ⬜ pending |
| 03-01-10 | 01 | 0 | MODL-07 | unit | `uv run pytest tests/test_shap.py::test_summary_plot_saves -x` | ❌ W0 | ⬜ pending |
| 03-01-11 | 01 | 0 | all | unit | `uv run pytest tests/test_serialization.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ml_models.py` — stubs for MODL-02 (LightGBM fitting, feature engineering)
- [ ] `tests/test_ensemble.py` — stubs for MODL-03 (weighting, combining)
- [ ] `tests/test_forecast_output.py` — stubs for MODL-04, MODL-05 (output schema, vintage, CI)
- [ ] `tests/test_shap.py` — stubs for MODL-07 (SHAP values, summary plot)
- [ ] `tests/test_serialization.py` — stubs for model save/load round-trip
- [ ] `src/models/ml/__init__.py` — new directory
- [ ] `src/inference/__init__.py` — new directory
- [ ] Package additions: `uv add lightgbm>=4.6.0 shap>=0.46.0`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SHAP summary plot readability | MODL-07 | Visual quality assessment | Inspect `models/ai_industry/shap_summary.png` — verify feature names visible, not "Feature 0" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 25s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
