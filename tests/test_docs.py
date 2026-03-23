"""Documentation completeness tests (DATA-08, ARCH-02)."""
import ast
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


class TestDocstringCoverage:
    """ARCH-02: Every public function in src/ has a non-empty docstring."""

    @staticmethod
    def _get_public_functions(module_path: Path) -> list[tuple[str, str]]:
        """Return list of (filename, function_name) for undocumented public functions."""
        undocumented = []
        src_dir = module_path
        for py_file in sorted(src_dir.rglob("*.py")):
            if "__pycache__" in str(py_file):
                continue
            rel = py_file.relative_to(module_path.parent)
            try:
                tree = ast.parse(py_file.read_text())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("_"):
                        continue  # skip private
                    docstring = ast.get_docstring(node)
                    if not docstring or len(docstring.strip()) < 10:
                        undocumented.append((str(rel), node.name))
        return undocumented

    def test_all_public_functions_documented(self):
        src_dir = Path(__file__).parent.parent / "src"
        undocumented = self._get_public_functions(src_dir)
        if undocumented:
            msg = f"{len(undocumented)} undocumented public functions:\n"
            for filepath, func in undocumented[:20]:
                msg += f"  {filepath}::{func}\n"
            if len(undocumented) > 20:
                msg += f"  ... and {len(undocumented) - 20} more"
        assert len(undocumented) == 0, msg

    def test_module_docstrings_exist(self):
        src_dir = Path(__file__).parent.parent / "src"
        missing = []
        for py_file in sorted(src_dir.rglob("*.py")):
            if "__pycache__" in str(py_file) or py_file.name == "__init__.py":
                continue
            try:
                tree = ast.parse(py_file.read_text())
            except SyntaxError:
                continue
            docstring = ast.get_docstring(tree)
            if not docstring or len(docstring.strip()) < 10:
                rel = py_file.relative_to(src_dir.parent)
                missing.append(str(rel))
        assert len(missing) == 0, f"Modules without docstrings: {missing}"


class TestArchitectureDoc:
    """ARCH-02: docs/ARCHITECTURE.md exists with required sections."""

    @staticmethod
    def _content() -> str:
        path = Path(__file__).parent.parent / "docs" / "ARCHITECTURE.md"
        assert path.exists(), "docs/ARCHITECTURE.md must exist"
        return path.read_text()

    def test_architecture_exists(self):
        content = self._content()
        assert len(content) > 200

    def test_architecture_has_data_flow(self):
        content = self._content()
        assert "mermaid" in content.lower() or "data flow" in content.lower()

    def test_architecture_has_module_responsibilities(self):
        content = self._content()
        for module in ["ingestion", "processing", "models", "inference", "dashboard"]:
            assert module in content.lower(), f"Missing module: {module}"

    def test_architecture_has_design_decisions(self):
        content = self._content()
        assert "design" in content.lower() or "decision" in content.lower()


class TestMethodologyPaper:
    """PRES-05: docs/methodology_paper.md exists with required content."""

    @staticmethod
    def _content() -> str:
        path = Path(__file__).parent.parent / "docs" / "methodology_paper.md"
        assert path.exists(), "docs/methodology_paper.md must exist"
        return path.read_text()

    def test_paper_exists(self):
        content = self._content()
        assert len(content) > 500, "Methodology paper too short"

    def test_paper_has_github_reference(self):
        content = self._content()
        assert "github" in content.lower(), "Paper must reference GitHub repo"

    def test_paper_mentions_hybrid_model(self):
        content = self._content()
        assert "hybrid" in content.lower() or "ensemble" in content.lower()

    def test_paper_has_key_findings(self):
        content = self._content()
        assert "billion" in content.lower() or "trillion" in content.lower(), \
            "Paper must include key findings with real dollar figures"

    def test_paper_mentions_data_sources(self):
        content = self._content()
        assert "World Bank" in content
        assert "OECD" in content


class TestReadme:
    """ARCH-03: README.md exists with required sections."""

    @staticmethod
    def _content() -> str:
        path = Path(__file__).parent.parent / "README.md"
        assert path.exists(), "README.md must exist"
        return path.read_text()

    def test_readme_exists(self):
        content = self._content()
        assert len(content) > 500

    def test_readme_has_screenshot(self):
        content = self._content()
        assert "dashboard_screenshot" in content, "README must reference dashboard screenshot"

    def test_screenshot_exists(self):
        path = Path(__file__).parent.parent / "assets" / "dashboard_screenshot.png"
        assert path.exists(), "assets/dashboard_screenshot.png must exist"

    def test_readme_has_required_sections(self):
        content = self._content()
        required = ["Quick Start", "Architecture", "Data Sources", "Methodology"]
        for section in required:
            assert section.lower() in content.lower(), f"README missing section: {section}"

    def test_readme_has_reproduction_commands(self):
        content = self._content()
        assert "uv run" in content, "README must include uv run commands"

    def test_readme_has_badges(self):
        content = self._content()
        assert "python" in content.lower() and ("badge" in content.lower() or "img.shields.io" in content.lower() or "![" in content)

    def test_readme_has_license(self):
        content = self._content()
        assert "license" in content.lower()
