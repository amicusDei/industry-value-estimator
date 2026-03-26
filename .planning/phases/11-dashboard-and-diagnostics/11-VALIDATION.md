---
phase: 11
slug: dashboard-and-diagnostics
status: draft
nyquist_compliant: false
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
| **Quick run command** | `uv run pytest tests/ -x --timeout=30` |
| **Full suite command** | `uv run pytest tests/ --timeout=60` |
| **Estimated runtime** | ~25 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --timeout=30`
- **After every plan wave:** Run `uv run pytest tests/ --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

Populated during planning — task IDs and test files will be filled by the planner to match actual plan structure.

---

## Wave 0 Requirements

Populated during planning — test scaffolds created inline by plans.

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 25s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
