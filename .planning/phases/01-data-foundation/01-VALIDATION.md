---
phase: 1
slug: data-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | None — Wave 0 creates `pyproject.toml [tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/ -x -q -m "not integration"` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds (excluding integration) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q -m "not integration"`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 0 | DATA-01 | unit | `pytest tests/test_config.py::test_ai_config_schema -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 0 | DATA-02 | unit | `pytest tests/test_processing.py::test_industry_tagging -x` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 0 | DATA-03 | unit (mocked) | `pytest tests/test_ingestion.py::test_world_bank_fetch -x` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 0 | DATA-04 | unit (mocked) | `pytest tests/test_ingestion.py::test_oecd_fetch -x` | ❌ W0 | ⬜ pending |
| 01-01-05 | 01 | 0 | DATA-05 | integration | `pytest tests/test_ingestion.py::test_lseg_fetch -x -m integration` | ❌ W0 | ⬜ pending |
| 01-01-06 | 01 | 0 | DATA-06 | unit | `pytest tests/test_deflate.py::test_no_nominal_in_processed -x` | ❌ W0 | ⬜ pending |
| 01-01-07 | 01 | 0 | DATA-06 | unit | `pytest tests/test_deflate.py::test_deflation_base_year_identity -x` | ❌ W0 | ⬜ pending |
| 01-01-08 | 01 | 0 | DATA-06 | unit | `pytest tests/test_interpolate.py::test_estimated_flag_set -x` | ❌ W0 | ⬜ pending |
| 01-01-09 | 01 | 0 | DATA-08 | unit | `pytest tests/test_docs.py::test_methodology_md_exists -x` | ❌ W0 | ⬜ pending |
| 01-01-10 | 01 | 0 | ARCH-01 | integration | `pytest tests/test_pipeline.py::test_second_industry_yaml -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_config.py` — stubs for DATA-01: YAML schema validation
- [ ] `tests/test_ingestion.py` — stubs for DATA-03, DATA-04, DATA-05 (mocked + integration)
- [ ] `tests/test_deflate.py` — stubs for DATA-06 deflation arithmetic
- [ ] `tests/test_interpolate.py` — stubs for DATA-06 estimated_flag
- [ ] `tests/test_processing.py` — stubs for DATA-02 industry tagging
- [ ] `tests/test_docs.py` — stubs for DATA-08 METHODOLOGY.md presence
- [ ] `tests/test_pipeline.py` — stubs for ARCH-01 second-industry YAML test
- [ ] `tests/fixtures/` — sample raw API responses for offline/mocked tests
- [ ] `pyproject.toml [tool.pytest.ini_options]` — configure test markers (integration)
- [ ] Framework install: `uv add --dev pytest` (ensure in pyproject.toml dev deps)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LSEG Workspace connectivity | DATA-05 | Requires LSEG Workspace running on local machine | 1. Open LSEG Workspace 2. Run `pytest tests/test_ingestion.py::test_lseg_fetch -x -m integration` 3. Verify DataFrame returned |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
