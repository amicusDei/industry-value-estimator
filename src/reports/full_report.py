"""
Full analytical report PDF generator.

Generates a 15-25 page full report from real forecast data (expert mode).
Target audience: technical reviewers, quants, methodology auditors.
Content: everything in the executive brief PLUS methodology deep-dive,
model diagnostics, SHAP feature attribution, assumptions summary, and
mathematical appendix.

Functions
---------
generate_full_report : Render and export the full analytical report PDF.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _extract_tldr_from_assumptions(assumptions_path: Path) -> str:
    """
    Extract the TL;DR section from docs/ASSUMPTIONS.md.

    Parameters
    ----------
    assumptions_path : Path
        Path to ASSUMPTIONS.md.

    Returns
    -------
    str
        The TL;DR section text (between "## TL;DR" and the next "##" heading).
        Returns empty string if file or section not found.
    """
    if not assumptions_path.exists():
        return ""

    content = assumptions_path.read_text(encoding="utf-8")

    # Find TL;DR section
    match = re.search(
        r"##\s+TL;DR[^\n]*\n(.*?)(?=\n##\s|\Z)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return ""

    tldr_text = match.group(1).strip()
    return tldr_text


def generate_full_report(output_path: Path | None = None) -> Path:
    """
    Generate the full analytical report PDF from real forecast data.

    Loads the report context in expert mode (includes RMSE, model types,
    residual statistics, backtest charts), reads the ASSUMPTIONS.md TL;DR,
    renders the full_report.html Jinja2 template, and converts to PDF
    using WeasyPrint.

    Parameters
    ----------
    output_path : Path, optional
        Destination path for the PDF file. Defaults to reports/full_report.pdf
        in the project root.

    Returns
    -------
    Path
        Absolute path to the generated PDF file.

    Notes
    -----
    The generated PDF contains (15-25 pages):
    - Cover page (full analytical edition)
    - Key findings with KPI cards and global fan chart
    - Segment breakdown with per-segment fan charts and 95% CI table
    - Data sources with detailed attribution
    - Methodology deep dive: hybrid architecture, ensemble formula, value chain calibration,
      structural break modeling, CI construction
    - Model diagnostics: RMSE table, backtest residual charts per segment
    - SHAP feature attribution with interpretation notes
    - Assumptions and sensitivity (TL;DR from ASSUMPTIONS.md)
    - Mathematical appendix: AICc, inverse-RMSE weights, additive blend, CI construction,
      Chow test, PCA composite formulas

    Requires WeasyPrint and kaleido to be installed.
    """
    from jinja2 import Environment, FileSystemLoader
    from weasyprint import HTML

    from src.reports.data_context import load_report_context

    # --- Resolve paths ---
    templates_dir = _PROJECT_ROOT / "reports" / "templates"
    assumptions_path = _PROJECT_ROOT / "docs" / "ASSUMPTIONS.md"

    if output_path is None:
        output_path = _PROJECT_ROOT / "reports" / "full_report.pdf"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Load data context (expert mode) ---
    ctx = load_report_context(mode="expert")

    # --- Enrich with ASSUMPTIONS.md TL;DR ---
    ctx["assumptions_tldr"] = _extract_tldr_from_assumptions(assumptions_path)

    # --- Render template ---
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False,
    )
    template = env.get_template("full_report.html")
    rendered_html = template.render(**ctx)

    # --- Export PDF ---
    HTML(string=rendered_html, base_url=str(templates_dir)).write_pdf(str(output_path))

    return output_path
