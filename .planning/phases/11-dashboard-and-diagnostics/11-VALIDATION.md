---
phase: 11
slug: dashboard-and-diagnostics
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-26
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (existing) |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_dashboard.py -q --timeout=30` |
| **Full suite command** | `uv run pytest tests/test_dashboard.py tests/test_diagnostics.py tests/test_forecast_output.py tests/test_backtesting.py -q --timeout=60` |
| **Estimated runtime** | ~25 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_dashboard.py -q --timeout=30`
- **After every plan wave:** Run `uv run pytest tests/test_dashboard.py tests/test_diagnostics.py tests/test_forecast_output.py tests/test_backtesting.py -q --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Plan | Task | Req | Test Function | Automated Command |
|------|------|-----|---------------|-------------------|
| 11-01 | T1 | DASH-01 | `test_basic_tab_renders` | `uv run pytest tests/test_dashboard.py::test_basic_tab_renders -q` |
| 11-01 | T1 | DASH-01 | `test_basic_kpi_cards` | `uv run pytest tests/test_dashboard.py::test_basic_kpi_cards -q` |
| 11-01 | T1 | DASH-01 | `test_basic_fan_chart_traces` | `uv run pytest tests/test_dashboard.py::test_basic_fan_chart_traces -q` |
| 11-01 | T1 | DASH-02 | `test_consensus_panel_segments` | `uv run pytest tests/test_dashboard.py::test_consensus_panel_segments -q` |
| 11-01 | T1 | DASH-02 | `test_consensus_divergence_color` | `uv run pytest tests/test_dashboard.py::test_consensus_divergence_color -q` |
| 11-01 | T1 | DASH-05 | `test_vintage_footer_present` | `uv run pytest tests/test_dashboard.py::test_vintage_footer_present -q` |
| 11-02 | T1 | DASH-04 | `test_no_alias_columns` (skipped until 11-04 T2) | `uv run pytest tests/test_dashboard.py::test_no_alias_columns -q` |
| 11-02 | T2 | DASH-04 | `test_no_pca_strings` (skipped until 11-04 T2) | `uv run pytest tests/test_dashboard.py::test_no_pca_strings -q` |
| 11-02 | T2 | DASH-04 | Existing 8 tests (regression) | `uv run pytest tests/test_dashboard.py -q` |
| 11-03 | T1 | DASH-03 | `test_revenue_multiples_in_overview` | `uv run pytest tests/test_dashboard.py::test_revenue_multiples_in_overview -q` |
| 11-03 | T1 | DASH-02 | `test_consensus_panel_segments` | `uv run pytest tests/test_dashboard.py::test_consensus_panel_segments -q` |
| 11-04 | T1 | DASH-04 | `test_diagnostics_real_mape` | `uv run pytest tests/test_dashboard.py::test_diagnostics_real_mape -q` |
| 11-04 | T2 | DASH-04 | `test_no_alias_columns` (unskipped) | `uv run pytest tests/test_dashboard.py::test_no_alias_columns -q` |
| 11-04 | T2 | DASH-04 | `test_no_pca_strings` (unskipped) | `uv run pytest tests/test_dashboard.py::test_no_pca_strings -q` |
| 11-04 | T2 | DASH-05 | `test_vintage_footer_present` | `uv run pytest tests/test_dashboard.py::test_vintage_footer_present -q` |

---

## Wave 0 Requirements

Test scaffolds created in Plan 11-01 Task 1. All 10 new test functions added to existing `tests/test_dashboard.py`:

- [x] `test_basic_tab_renders` — covers DASH-01 (active from 11-01)
- [x] `test_basic_kpi_cards` — covers DASH-01 (active from 11-01)
- [x] `test_basic_fan_chart_traces` — covers DASH-01 (active from 11-01)
- [x] `test_consensus_panel_segments` — covers DASH-02 (active from 11-01)
- [x] `test_consensus_divergence_color` — covers DASH-02 (active from 11-01)
- [ ] `test_revenue_multiples_in_overview` — covers DASH-03 (skipped until 11-03)
- [ ] `test_no_alias_columns` — covers DASH-04 (skipped until 11-04)
- [ ] `test_no_pca_strings` — covers DASH-04 (skipped until 11-04)
- [ ] `test_diagnostics_real_mape` — covers DASH-04 (skipped until 11-04)
- [x] `test_vintage_footer_present` — covers DASH-05 (active from 11-01)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Basic tier fits single screen | DASH-01 | Requires visual inspection | Open Basic tab in 1920x1080 browser, verify no scrollbar |
| Color-coded confidence readable | DASH-01 | Requires visual inspection | Check green/yellow/red indicators are distinguishable |
| Bullet chart intuitive | DASH-02 | Requires visual inspection | Verify consensus range vs model marker is immediately clear |
| Dashboard loads without crash | DASH-04 | Requires running Dash server | `uv run python scripts/run_dashboard.py` — verify all tabs load |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 25s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
