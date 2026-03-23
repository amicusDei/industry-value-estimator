---
phase: 8
slug: data-architecture-and-ground-truth-assembly
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing) |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/ -x --timeout=30` |
| **Full suite command** | `uv run pytest tests/ --timeout=60` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --timeout=30`
- **After every plan wave:** Run `uv run pytest tests/ --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | DATA-08 | unit | `uv run pytest tests/test_config.py::TestMarketBoundary tests/test_config.py::TestScopeMapping -x` | inline (08-01 T2) | ⬜ pending |
| 08-02-01 | 02 | 1 | DATA-09 | unit | `uv run pytest tests/test_market_anchors.py -x` | ❌ W0 | ⬜ pending |
| 08-03-01 | 03 | 1 | DATA-10 | unit | `uv run pytest tests/test_edgar.py -x` | ❌ W0 | ⬜ pending |
| 08-04-01 | 04 | 2 | DATA-11 | unit | `uv run pytest tests/test_market_anchors.py tests/test_pipeline.py -x` | inline (08-04 T1/T2) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_config.py::TestMarketBoundary` — created inline by 08-01 Task 2 (no Wave 0 stub needed)
- [ ] `tests/test_market_anchors.py` — stubs for DATA-09 (YAML registry loading, Parquet compilation, vintage tracking)
- [ ] `tests/test_edgar.py` — stubs for DATA-10 (EDGAR XBRL extraction, bundled flag, company selection)
- [x] `tests/test_market_anchors.py` + `tests/test_pipeline.py` — DATA-11 tests created inline by 08-04 Task 1 and Task 2 (TestDeflation, TestYearCoverage, TestEstimatedFlag, TestPercentileOrder)

*Existing `tests/test_ingestion.py` covers v1.0 pipeline — new test files follow same mock pattern.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Scope mapping table correctness | DATA-08 | Requires domain judgment on analyst scope definitions | Review ai.yaml scope_mapping_table entries against published analyst methodology docs |
| Analyst estimate accuracy | DATA-09 | Published figures require manual verification against source documents | Spot-check 5 estimates against original press releases |
| EDGAR data freshness | DATA-10 | SEC EDGAR availability varies | Run live fetch for 1 company, verify filing date is within expected range |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
