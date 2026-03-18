"""Documentation completeness tests (DATA-08)."""
from pathlib import Path


DOCS_DIR = Path(__file__).parent.parent / "docs"


class TestMethodologyDoc:
    """Verify METHODOLOGY.md exists and has required sections."""

    def test_methodology_exists(self):
        path = DOCS_DIR / "METHODOLOGY.md"
        assert path.exists(), "docs/METHODOLOGY.md must exist"

    def test_methodology_has_market_boundary(self):
        content = (DOCS_DIR / "METHODOLOGY.md").read_text()
        assert "## Market Boundary" in content

    def test_methodology_has_data_sources(self):
        content = (DOCS_DIR / "METHODOLOGY.md").read_text()
        assert "## Data Sources" in content

    def test_methodology_has_processing_pipeline(self):
        content = (DOCS_DIR / "METHODOLOGY.md").read_text()
        assert "## Processing Pipeline" in content

    def test_methodology_mentions_deflation(self):
        content = (DOCS_DIR / "METHODOLOGY.md").read_text()
        assert "2020 constant USD" in content or "constant-year USD" in content

    def test_methodology_mentions_all_sources(self):
        content = (DOCS_DIR / "METHODOLOGY.md").read_text()
        assert "World Bank" in content
        assert "OECD" in content
        assert "LSEG" in content

    def test_methodology_explains_overlap_treatment(self):
        content = (DOCS_DIR / "METHODOLOGY.md").read_text()
        assert "overlap" in content.lower()

    def test_methodology_explains_proxy_indicators(self):
        content = (DOCS_DIR / "METHODOLOGY.md").read_text()
        assert "proxy" in content.lower() or "Proxy" in content
