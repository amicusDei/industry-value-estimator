---
phase: 5
slug: reports-paper-and-portfolio
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_reports.py tests/test_docs.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_reports.py tests/test_docs.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 0 | PRES-04 | unit | `uv run pytest tests/test_reports.py::test_pdf_generates -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 0 | PRES-04 | unit | `uv run pytest tests/test_reports.py::test_pdf_has_fan_chart -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 0 | PRES-04 | unit | `uv run pytest tests/test_reports.py::test_pdf_has_attribution -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 0 | PRES-05 | unit | `uv run pytest tests/test_docs.py::test_methodology_paper_exists -x` | ❌ W0 | ⬜ pending |
| 05-01-05 | 01 | 0 | ARCH-02 | unit | `uv run pytest tests/test_docs.py::test_all_modules_have_docstrings -x` | ❌ W0 | ⬜ pending |
| 05-01-06 | 01 | 0 | ARCH-03 | unit | `uv run pytest tests/test_docs.py::test_readme_has_sections -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_reports.py` — stubs for PRES-04 (PDF generation, chart embedding, attribution)
- [ ] `tests/test_docs.py` — add tests for PRES-05 (paper), ARCH-02 (docstrings), ARCH-03 (README)
- [ ] Package additions: `uv add weasyprint kaleido`
- [ ] System dependency: `brew install pango` (WeasyPrint macOS requirement)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PDF visual quality | PRES-04 | Layout/typography rendering | Open `reports/executive_brief.pdf` — verify charts render, text is readable |
| LinkedIn paper readability | PRES-05 | Subjective quality | Read `docs/methodology_paper.md` — verify tone, completeness, narrative flow |
| README visual appeal | ARCH-03 | Subjective quality | View README.md on GitHub — verify screenshot renders, sections are scannable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
