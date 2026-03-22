---
phase: 4
slug: interactive-dashboard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_dashboard.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_dashboard.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | PRES-01 | unit | `uv run pytest tests/test_dashboard.py::test_app_layout_has_tabs -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 0 | PRES-01 | unit | `uv run pytest tests/test_dashboard.py::test_forecast_chart_renders -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 0 | PRES-02 | unit | `uv run pytest tests/test_dashboard.py::test_shap_image_present -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 0 | PRES-03 | unit | `uv run pytest tests/test_dashboard.py::test_diagnostics_scorecard -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 0 | DATA-07 | unit | `uv run pytest tests/test_dashboard.py::test_source_attribution -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_dashboard.py` — stubs for PRES-01 (layout, charts), PRES-02 (SHAP), PRES-03 (diagnostics), DATA-07 (attribution)
- [ ] Package additions: `uv add dash dash-bootstrap-components`
- [ ] `src/dashboard/__init__.py` — new directory
- [ ] `assets/` — directory for static assets (SHAP PNG)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard visual quality | PRES-01 | Visual inspection | Run `uv run python -m src.dashboard.app` — verify fan chart renders, tabs work, colors match spec |
| Fan chart CI bands | PRES-01 | Visual rendering | Check 80%/95% bands are visible and correctly shaded |
| SHAP plot readability | PRES-02 | Visual quality | Check Drivers tab shows SHAP summary with named features |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
