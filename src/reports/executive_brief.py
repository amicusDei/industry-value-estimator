"""
Executive brief PDF generator.

Generates a 5-8 page executive brief PDF from real forecast data.
Target audience: executives, investors, LinkedIn readers.
Content: dollar headlines, fan charts, segment breakdown, data sources.

Functions
---------
generate_executive_brief : Render and export the executive brief PDF.
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def generate_executive_brief(output_path: Path | None = None) -> Path:
    """
    Generate the executive brief PDF from real forecast data.

    Loads the report context (forecast data, USD metrics, fan charts),
    renders the executive_brief.html Jinja2 template, and converts to PDF
    using WeasyPrint.

    Parameters
    ----------
    output_path : Path, optional
        Destination path for the PDF file. Defaults to reports/executive_brief.pdf
        in the project root.

    Returns
    -------
    Path
        Absolute path to the generated PDF file.

    Notes
    -----
    The generated PDF contains:
    - Cover page with vintage and generation date
    - Key findings with KPI cards, 80%/95% CI, global fan chart
    - Segment breakdown table with per-segment fan charts (4 charts)
    - Data sources with attribution table
    - Disclaimer with known limitations and reproducibility instructions

    Requires WeasyPrint and kaleido to be installed. Chart export uses
    kaleido v1 API (fig.to_image) — not deprecated engine="kaleido".
    """
    from jinja2 import Environment, FileSystemLoader
    from weasyprint import HTML

    from src.reports.data_context import load_report_context

    # --- Resolve paths ---
    templates_dir = _PROJECT_ROOT / "reports" / "templates"
    if output_path is None:
        output_path = _PROJECT_ROOT / "reports" / "executive_brief.pdf"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Load data context ---
    ctx = load_report_context(mode="normal")

    # --- Render template ---
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False,
    )
    template = env.get_template("executive_brief.html")
    rendered_html = template.render(**ctx)

    # --- Export PDF ---
    HTML(string=rendered_html, base_url=str(templates_dir)).write_pdf(str(output_path))

    return output_path
