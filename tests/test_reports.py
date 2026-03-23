"""
PDF report generation tests (PRES-04).

Tests verify that both PDF reports exist and have non-trivial size.
Run with: uv run python -m pytest tests/test_reports.py -m pdf -x -q
"""
import pytest
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent / "reports"


@pytest.mark.pdf
class TestExecutiveBrief:
    def test_executive_brief_pdf_exists(self):
        assert (REPORTS_DIR / "executive_brief.pdf").exists()

    def test_executive_brief_has_content(self):
        pdf = REPORTS_DIR / "executive_brief.pdf"
        assert pdf.stat().st_size > 50_000, "Executive brief PDF too small (< 50KB)"


@pytest.mark.pdf
class TestFullReport:
    def test_full_report_pdf_exists(self):
        assert (REPORTS_DIR / "full_report.pdf").exists()

    def test_full_report_larger_than_brief(self):
        brief = REPORTS_DIR / "executive_brief.pdf"
        full = REPORTS_DIR / "full_report.pdf"
        assert full.stat().st_size > brief.stat().st_size, "Full report should be larger than executive brief"
