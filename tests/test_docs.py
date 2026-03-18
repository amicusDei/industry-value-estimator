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


class TestAssumptionsDoc:
    """ARCH-04, MODL-09: ASSUMPTIONS.md completeness tests."""

    @staticmethod
    def _content() -> str:
        path = Path(__file__).parent.parent / "docs" / "ASSUMPTIONS.md"
        assert path.exists(), "docs/ASSUMPTIONS.md must exist"
        return path.read_text()

    def test_assumptions_md_exists(self):
        content = self._content()
        assert len(content) > 500, "ASSUMPTIONS.md too short"

    def test_assumptions_tldr(self):
        assert "## TL;DR" in self._content()

    def test_assumptions_data_source_section(self):
        assert "## Data Source Assumptions" in self._content()

    def test_assumptions_modeling_section(self):
        assert "## Modeling Assumptions" in self._content()

    def test_assumptions_cv_section(self):
        assert "## Cross-Validation Assumptions" in self._content()

    def test_assumptions_caveats_section(self):
        assert "## Interpretation Caveats" in self._content()

    def test_assumptions_appendix(self):
        assert "## Mathematical Appendix" in self._content()

    def test_assumptions_sensitivity_notes(self):
        count = self._content().count("If this is wrong")
        assert count >= 10, f"Need >= 10 sensitivity notes, found {count}"

    def test_assumptions_covers_all_models(self):
        content = self._content()
        for model in ["ARIMA", "Prophet", "Markov", "PCA"]:
            assert model in content, f"Missing model: {model}"
