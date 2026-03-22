# Phase 5: Reports, Paper, and Portfolio - Research

**Researched:** 2026-03-22
**Domain:** PDF generation (WeasyPrint), Plotly static export (kaleido), Python docstrings, GitHub README
**Confidence:** HIGH

## Summary

Phase 5 is the capstone phase: re-run the full pipeline against real data, then produce two PDF reports, a LinkedIn methodology paper, tutorial-style docstrings across all `src/` modules, an architecture guide, and a polished GitHub README. All four outputs depend on real data being in the Parquet files first — that pre-condition is the single most critical task sequencing constraint.

The PDF stack is WeasyPrint (HTML/CSS → PDF) combined with Jinja2 for templating and kaleido for embedding static Plotly chart images. None of these are in the current `pyproject.toml`. Chrome is already installed at `/Applications/Google Chrome.app` which satisfies kaleido v1's runtime requirement. WeasyPrint needs system-level Pango/Cairo libraries via Homebrew. Plotly 6.6.0 is already installed; only `kaleido` needs to be added.

The docstring work is mechanical but high-effort: every module in `src/` needs extended Google-style docstrings with domain explanations, rationale for approach choices, and links to `ASSUMPTIONS.md`. The codebase already uses a consistent docstring pattern (see `src/models/statistical/arima.py` and `src/inference/forecast.py`) that extends Google-style with design notes — that convention should be used throughout.

**Primary recommendation:** Sequence strictly: (1) real data pipeline run, (2) chart exports + report generation, (3) docstrings, (4) README. Do not generate any final outputs before real data is in place.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**CRITICAL PREREQUISITE: Real data pipeline run**
- Before generating any reports or documentation: Run the full ingestion + processing + statistical + ensemble pipeline against real World Bank/OECD/LSEG API data
- Replace all synthetic Parquet files with real data outputs
- Re-run `scripts/run_statistical_pipeline.py` and `scripts/run_ensemble_pipeline.py` with real data
- This requires LSEG Workspace running for the LSEG connector
- All downstream outputs (reports, screenshots, paper) must reflect real data, not synthetic placeholders

**PDF report structure (PRES-04)**
- Two versions: Executive brief (5-8 pages, normal mode) AND full analytical report (15-25 pages, expert mode)
- Executive brief: Dollar headlines, fan chart, segment breakdown, key findings, data sources. Clean narrative — for executives and LinkedIn shares.
- Full report: Everything in the brief PLUS raw methodology, diagnostics, model parameters, assumption sensitivity notes, mathematical appendix. For technical reviewers.
- PDF engine: WeasyPrint (HTML/CSS to PDF) — write report as styled HTML, render to PDF. Embed Plotly charts as static PNG images.
- Mode alignment: Executive brief = dashboard normal mode content. Full report = dashboard expert mode content.

**LinkedIn methodology paper (PRES-05)**
- Tone and style: Claude's discretion — user skipped this discussion. Likely a hybrid narrative + technical approach given the portfolio context.
- Must reference: The GitHub repo, the quant risk manager origin story (PROJECT.md), key findings with real numbers

**Code documentation (ARCH-02)**
- Docstring depth: Tutorial-style walkthroughs — extended docstrings that teach the reader. Each domain-critical function explains the concept, why this approach was chosen over alternatives, and links to ASSUMPTIONS.md. Matches PROJECT.md's "learning resource" goal.
- Architecture guide: `docs/ARCHITECTURE.md` — short (1-2 pages): data flow diagram, module responsibilities, key design decisions. Points to code for details.

**README showcase (ARCH-03)**
- Hero: Screenshot-first — dashboard screenshot at the top as the first thing someone sees when browsing the repo
- Sections: Comprehensive (8+): Screenshot, Description, Key Findings, Quick Start, Architecture, Data Sources, Methodology, Contributing, License
- Badges: Minimal — Python version + license only. No badge spam.
- Quick-start: Exact commands to reproduce the pipeline from scratch

### Claude's Discretion
- LinkedIn paper tone and structure (user deferred)
- Exact WeasyPrint HTML/CSS template design
- Chart export resolution and format (PNG vs SVG)
- Architecture diagram format (ASCII, Mermaid, or image)
- Docstring format (Google-style with extended explanations)
- README example output images (dashboard screenshots vs chart exports)
- Contributing section depth
- License choice (MIT, Apache 2.0, etc.)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRES-04 | Exportable PDF report with analysis and projections | WeasyPrint + Jinja2 + kaleido stack; fan_chart.py already has `fig.write_image()` capability once kaleido is installed |
| PRES-05 | Methodology paper suitable for LinkedIn publication | Markdown file in `docs/`; extends existing `docs/METHODOLOGY.md` (366+ lines) |
| ARCH-02 | Comprehensive code documentation explaining every module and function for learning purposes | Google-style extended docstrings; project already uses this pattern in arima.py and forecast.py |
| ARCH-03 | Polished GitHub README with project description, data sources, setup instructions | Standard Markdown README with screenshot hero; screenshot-first pattern confirmed as portfolio best practice |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| weasyprint | 68.1 | HTML/CSS to PDF rendering | Industry standard for Python PDF generation; supports full CSS Paged Media spec including @page, page-break, headers/footers |
| jinja2 | already installed (dash dep) | HTML template rendering | De facto Python templating; separates report content from PDF generation logic |
| kaleido | 1.2.0 | Plotly figure → static PNG | Official Plotly static export library; required for embedding charts in WeasyPrint HTML |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Plotly 6.6.0 | already installed | Fan chart and backtest chart source figures | Already in project — fan_chart.py and backtest.py produce go.Figure objects |
| base64 (stdlib) | stdlib | Embed PNG bytes directly in HTML as data URIs | Avoid file system path issues when WeasyPrint renders HTML with embedded images |
| pathlib (stdlib) | stdlib | Report output path management | Already used throughout project |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WeasyPrint | ReportLab | ReportLab requires imperative drawing API — no HTML/CSS; harder to style for non-PDF-experts |
| WeasyPrint | pdfkit (wkhtmltopdf) | wkhtmltopdf is unmaintained (last release 2020); requires binary install; WeasyPrint is pure Python |
| kaleido | orca | Orca is deprecated by Plotly as of Sept 2025; kaleido is the only supported static export path |
| kaleido | matplotlib screenshots | Fan charts are Plotly-native; re-implementing in matplotlib would be re-work |
| Jinja2 | f-string HTML | f-strings don't support template inheritance, macros, or safe HTML escaping |

**Installation:**
```bash
# System dependencies for WeasyPrint (macOS)
brew install pango

# Python packages (add to pyproject.toml)
uv add weasyprint kaleido
```

**Version verification:** Versions verified against PyPI on 2026-03-22. WeasyPrint 68.1, kaleido 1.2.0.

---

## Architecture Patterns

### Recommended Project Structure

```
src/
└── reports/                  # New module — report generation
    ├── __init__.py
    ├── chart_export.py       # Export fan charts and backtest charts as PNG bytes
    ├── data_context.py       # Load forecast/diagnostics from Parquet + compute context values
    ├── executive_brief.py    # Assemble and render executive brief (5-8 pages)
    └── full_report.py        # Assemble and render full analytical report (15-25 pages)

reports/
├── templates/
│   ├── base.html             # @page rules, fonts, shared layout
│   ├── executive_brief.html  # Jinja2 template — brief content
│   └── full_report.html      # Jinja2 template — full report content
├── executive_brief.pdf       # Output
└── full_report.pdf           # Output

scripts/
└── run_reports.py            # Script runner — calls src/reports generators

docs/
├── METHODOLOGY.md            # Exists (366+ lines) — extend for paper
├── ASSUMPTIONS.md            # Exists (16 sensitivity notes) — reference in reports
├── ARCHITECTURE.md           # New — data flow diagram + module responsibilities
└── methodology_paper.md      # New — LinkedIn-ready narrative paper
```

### Pattern 1: Jinja2 + WeasyPrint Report Rendering

**What:** Render a Jinja2 HTML template with context data, then pass the resulting HTML string to WeasyPrint for PDF output.

**When to use:** All report generation — both executive brief and full report.

**Example:**
```python
# Source: https://doc.courtbouillon.org/weasyprint/stable/
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from pathlib import Path

def render_report(template_name: str, context: dict, output_path: Path) -> None:
    env = Environment(loader=FileSystemLoader("reports/templates"))
    template = env.get_template(template_name)
    html_string = template.render(**context)
    HTML(string=html_string, base_url=str(Path.cwd())).write_pdf(str(output_path))
```

### Pattern 2: Plotly Figure to Base64 PNG (kaleido v1)

**What:** Export a Plotly figure as PNG bytes, then base64-encode for embedding as a data URI in HTML. Avoids file system path resolution issues inside WeasyPrint.

**When to use:** Every chart embedded in the reports — fan charts, backtest chart, SHAP plot.

**Example:**
```python
# Source: https://plotly.com/python/static-image-export/
import base64
import plotly.graph_objects as go

def fig_to_data_uri(fig: go.Figure, width: int = 900, height: int = 500) -> str:
    """Export Plotly figure as a base64 PNG data URI for HTML embedding."""
    img_bytes = fig.to_image(format="png", width=width, height=height)
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"
```

Note: kaleido v1 (1.2.0) requires Chrome. Chrome is confirmed installed at `/Applications/Google Chrome.app` on this machine. The `kaleido_get_chrome` command can install a bundled Chrome if the system one is not detected.

### Pattern 3: WeasyPrint CSS Page Layout

**What:** Use CSS `@page` rule and `page-break-before`/`page-break-after` to control PDF pagination. WeasyPrint supports the full CSS Paged Media spec.

**When to use:** Report template CSS — section headers as page-break points, page margins, header/footer.

**Example:**
```css
/* Source: https://doc.courtbouillon.org/weasyprint/stable/ */
@page {
    size: A4;
    margin: 2.5cm 2cm 2cm 2cm;
    @top-center { content: "AI Industry Valuation — Confidential"; font-size: 9pt; }
    @bottom-right { content: counter(page) " / " counter(pages); font-size: 9pt; }
}
.section-break { page-break-before: always; }
```

### Pattern 4: Extended Google-Style Docstrings (Project Convention)

**What:** Module-level docstring lists what the module exports and key design notes. Function docstrings follow Google-style with Parameters/Returns, then a free-form section explaining domain concepts and alternatives considered. Links to `ASSUMPTIONS.md` where relevant.

**When to use:** All functions in `src/` — already established in `arima.py` and `forecast.py`, extend to all remaining modules.

**Example (from existing codebase):**
```python
def select_arima_order(series: pd.Series) -> tuple[int, int, int]:
    """
    Select ARIMA(p, d, q) order via AICc on a pandas Series.

    Uses pmdarima auto_arima with stepwise Hyndman-Khandakar search,
    constrained to max_p=2, max_q=2 for parsimony on short annual panels
    (N < 30). Differencing order d is detected automatically via ADF.

    Parameters
    ----------
    series : pd.Series
        Annual time series (any year-indexed or integer-indexed Series).

    Returns
    -------
    tuple[int, int, int]
        (p, d, q) order selected by AICc.
    """
```

This is NumPy-style Parameters/Returns, not Google-style Args/Returns — the project uses NumPy-style. Match this existing convention (not Google-style) for all new docstrings.

### Anti-Patterns to Avoid

- **Generating reports before real data pipeline run:** All report content (dollar figures, CI ranges, market size estimates) will be synthetic/meaningless. The prerequisite is non-negotiable.
- **Writing static chart images to disk and referencing by path:** WeasyPrint resolves paths relative to the `base_url`. Use base64 data URIs instead to guarantee portability.
- **Using `engine="kaleido"` parameter:** Deprecated in Plotly 6.x. Use `fig.to_image(format="png")` directly.
- **Screenshotting the live Dash dashboard for the README:** Use a static export of `make_fan_chart()` or a saved screenshot of the running dashboard — the dashboard is the authoritative visual artifact.
- **Writing methodology paper as a copy of METHODOLOGY.md:** The paper extends it with narrative, origin story, and key findings with real numbers — it's a different genre.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML to PDF | Custom ReportLab layout code | WeasyPrint + HTML/CSS | CSS is vastly easier to style than imperative PDF drawing; WeasyPrint handles page breaks, headers, fonts |
| Chart to PNG | matplotlib reimplementation of fan chart | `fig.to_image(format="png")` on existing Plotly figures | fan_chart.py already produces correct Plotly figures — just export |
| HTML templating | f-string concatenation | Jinja2 templates | Template inheritance, safe HTML escaping, loops for segment tables, macros for reuse |
| Page numbering | Manual counter | CSS `counter(page)` via WeasyPrint @page | CSS Paged Media handles this natively |

**Key insight:** The entire PDF generation stack (WeasyPrint + Jinja2 + kaleido) wraps around existing outputs from earlier phases. No new modeling or data work — only rendering.

---

## Common Pitfalls

### Pitfall 1: WeasyPrint Missing System Dependencies
**What goes wrong:** `weasyprint` installs but crashes at render time with `OSError: cannot load library 'libpango'` or similar.
**Why it happens:** WeasyPrint wraps Pango (text layout) and Cairo (vector rendering) via CFFI. These are not Python packages — they must be installed at the OS level.
**How to avoid:** Run `brew install pango` before `uv add weasyprint`. On Apple Silicon, also ensure `brew` installs to `/opt/homebrew/lib` and that path is on `DYLD_LIBRARY_PATH` if needed.
**Warning signs:** ImportError or OSError at `from weasyprint import HTML`.

### Pitfall 2: kaleido v1 Chrome Requirement
**What goes wrong:** `fig.to_image()` raises `ValueError: Unable to find a supported browser` despite kaleido being installed.
**Why it happens:** kaleido 1.x no longer bundles Chromium — it requires a system Chrome or Chromium.
**How to avoid:** Chrome is confirmed at `/Applications/Google Chrome.app` on this machine. If kaleido can't find it automatically, run `kaleido.get_chrome_sync()` once to register the path, or run `kaleido_get_chrome` CLI to download a pinned Chromium.
**Warning signs:** Error message mentioning "Unable to find a supported browser" or "Chrome not found".

### Pitfall 3: WeasyPrint Path Resolution for Local Images
**What goes wrong:** `<img src="reports/assets/fan_chart.png">` renders as a broken image in the PDF.
**Why it happens:** WeasyPrint resolves relative paths from `base_url`, not the template file location. If `base_url` is not set correctly, local file references silently fail.
**How to avoid:** Use base64 data URIs for all chart images: `<img src="data:image/png;base64,...">`. Eliminates path resolution entirely.
**Warning signs:** Blank image boxes in PDF output.

### Pitfall 4: Real Data Not Ready When Reports Are Generated
**What goes wrong:** Reports contain synthetic index values (e.g. "Market Size: 0.47 index units") instead of dollar figures.
**Why it happens:** `forecasts_ensemble.parquet` still contains synthetic data from earlier phases. The USD conversion in `app.py` works correctly, but the underlying index values are garbage.
**How to avoid:** The first task in this phase is the real data pipeline run. Gate all downstream tasks on its completion. The `usd_point` column in `FORECASTS_DF` only makes sense after the value chain multiplier is calibrated against real anchor-year data.
**Warning signs:** Dollar figures in the $0–10B range for an industry worth $200B+, or negative values.

### Pitfall 5: Docstring Scope Underestimation
**What goes wrong:** Docstrings are added to obvious functions but missed in `__init__.py` files, pipeline orchestrators, and processing helpers.
**Why it happens:** Module-level and orchestrator-level docstrings are easy to skip.
**How to avoid:** Use a checklist-driven approach — enumerate every `.py` file in `src/` at task start and track completion per file. The modules needing work: `src/ingestion/`, `src/processing/`, `src/models/`, `src/inference/`, `src/diagnostics/`, `src/dashboard/`.
**Warning signs:** ARCH-02 verification test counts undocumented functions > 0.

### Pitfall 6: LinkedIn Paper Uses Jargon Without Explanation
**What goes wrong:** Paper reads like an internal technical memo — readers disengage.
**Why it happens:** Writing for a technical audience when LinkedIn's primary audience is mixed.
**How to avoid:** Structure as: hook (the problem), story (why a quant risk manager built this), approach (hybrid model explained simply), finding (one headline number), technical detail (brief), call-to-action (GitHub link). The paper must be readable by a non-quant.

---

## Code Examples

Verified patterns from official sources:

### WeasyPrint Basic Usage
```python
# Source: https://doc.courtbouillon.org/weasyprint/stable/
from weasyprint import HTML

# From HTML string
HTML(string="<h1>Report</h1>").write_pdf("output.pdf")

# From file with base_url for relative asset resolution
HTML(filename="report.html", base_url="/project/root").write_pdf("output.pdf")
```

### Jinja2 + WeasyPrint Full Pattern
```python
# Source: https://medium.com/@engineering_holistic_ai/using-weasyprint-and-jinja2-to-create-pdfs-from-html-and-css-267127454dbd
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from pathlib import Path

def generate_pdf(template_name: str, context: dict, output_path: str) -> None:
    env = Environment(loader=FileSystemLoader("reports/templates"))
    template = env.get_template(template_name)
    rendered = template.render(**context)
    HTML(string=rendered).write_pdf(output_path)
```

### Plotly kaleido v1 PNG Export (Plotly 6.6.0)
```python
# Source: https://plotly.com/python/static-image-export/
# fig.to_image() — new API, no engine= parameter
img_bytes: bytes = fig.to_image(format="png", width=900, height=500, scale=2)

# For multiple figures (better performance than repeated write_image calls)
import plotly.io as pio
pio.write_images([
    {"fig": fig1, "file": "chart1.png"},
    {"fig": fig2, "file": "chart2.png"},
])
```

### Base64 Image Embedding for WeasyPrint
```python
import base64

def png_to_data_uri(png_bytes: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode()

# In Jinja2 template:
# <img src="{{ fan_chart_uri }}" style="width:100%">
```

### fan_chart.py export — existing API
```python
# src/dashboard/charts/fan_chart.py — already supports this
from src.dashboard.charts.fan_chart import make_fan_chart

fig = make_fan_chart(forecasts_df, segment="all", usd_col="point_estimate_real_2020", usd_mode=True)
png_bytes = fig.to_image(format="png", width=900, height=480, scale=2)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| kaleido 0.x bundled Chromium | kaleido 1.x requires system Chrome | Sept 2025 (plotly 6.1) | Requires Chrome on machine — confirmed present at `/Applications/Google Chrome.app` |
| `fig.write_image(engine="kaleido")` | `fig.to_image(format="png")` | Plotly 6.1 | Must use new API; `engine=` parameter deprecated |
| Orca (older Plotly static export) | kaleido | 2020+ | Orca fully deprecated as of Sept 2025; kaleido is only supported path |
| pdfkit / wkhtmltopdf | WeasyPrint | ~2022 | wkhtmltopdf unmaintained; WeasyPrint is actively maintained and pure Python |

**Deprecated/outdated:**
- `plotly.io.kaleido.scope.*` configuration: use `plotly.io.defaults.*` instead
- `fig.write_image(engine="kaleido")`: use `fig.to_image(format="png")` directly
- Orca: completely deprecated, no longer supported

---

## Open Questions

1. **Value chain multiplier calibration after real data**
   - What we know: The multiplier is calibrated against a ~$200B anchor for 2023 (see `app.py`)
   - What's unclear: With real data, the index value at the anchor year may differ from synthetic data, changing all USD figures. The multiplier will re-calibrate automatically, but the resulting numbers must be sanity-checked against industry consensus.
   - Recommendation: After the real data pipeline run, verify that global AI market size at anchor year is in the $150-300B range. If wildly off, flag in the report as a known calibration limitation.

2. **Dashboard screenshot for README**
   - What we know: The README needs a hero screenshot; the dashboard runs via `uv run scripts/run_dashboard.py`
   - What's unclear: Automated screenshot capture (Selenium, Playwright) is not in the project stack. Manual screenshot may be needed.
   - Recommendation: Take a manual screenshot of the running dashboard in normal mode showing all segments, save to `assets/dashboard_screenshot.png`, reference in README. Document this as a manual step in the plan.

3. **Architecture diagram format**
   - What we know: `docs/ARCHITECTURE.md` should include a data flow diagram; CONTEXT.md leaves format to Claude's discretion.
   - What's unclear: Mermaid is GitHub-native (renders in README/docs), ASCII is universally portable, image files require maintenance.
   - Recommendation: Use Mermaid. GitHub renders it natively in `.md` files. No external tools needed.

4. **LinkedIn paper length and format**
   - What we know: Must reference GitHub repo, origin story, key findings with real numbers. Tone is Claude's discretion.
   - What's unclear: LinkedIn article optimal length (typically 800-1500 words for technical posts).
   - Recommendation: ~1000 words. Structure: opening hook, 2-paragraph origin story, 3-paragraph methodology overview, 1-paragraph findings with headline number, closing with GitHub CTA. Store as `docs/methodology_paper.md`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (no `[tool.pytest.ini_options]` section — uses defaults) |
| Quick run command | `uv run python -m pytest tests/ -x -q --tb=short` |
| Full suite command | `uv run python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRES-04 | Report generator produces a PDF file at `reports/executive_brief.pdf` | smoke | `uv run python -m pytest tests/test_reports.py::test_executive_brief_pdf_exists -x` | ❌ Wave 0 |
| PRES-04 | Executive brief PDF contains fan chart image (non-zero file size > 50KB) | smoke | `uv run python -m pytest tests/test_reports.py::test_executive_brief_has_content -x` | ❌ Wave 0 |
| PRES-04 | Full report PDF exists and is larger than executive brief | smoke | `uv run python -m pytest tests/test_reports.py::test_full_report_pdf_exists -x` | ❌ Wave 0 |
| PRES-05 | `docs/methodology_paper.md` exists and has required sections | unit | `uv run python -m pytest tests/test_docs.py::TestMethodologyPaper -x` | ❌ Wave 0 |
| ARCH-02 | All public functions in `src/` have non-empty docstrings | unit | `uv run python -m pytest tests/test_docs.py::TestDocstringCoverage -x` | ❌ Wave 0 |
| ARCH-02 | `docs/ARCHITECTURE.md` exists with required sections | unit | `uv run python -m pytest tests/test_docs.py::TestArchitectureDoc -x` | ❌ Wave 0 |
| ARCH-03 | `README.md` exists and contains required sections | unit | `uv run python -m pytest tests/test_docs.py::TestReadme -x` | ❌ Wave 0 |
| ARCH-03 | README references dashboard screenshot image that exists | unit | `uv run python -m pytest tests/test_docs.py::TestReadme::test_screenshot_exists -x` | ❌ Wave 0 |

Note: PDF generation tests (`test_reports.py`) are smoke tests that depend on kaleido and WeasyPrint being installed. They should be marked with a custom marker `pdf` to allow skipping in environments without system dependencies: `@pytest.mark.pdf`.

### Sampling Rate
- **Per task commit:** `uv run python -m pytest tests/ -x -q --tb=short`
- **Per wave merge:** `uv run python -m pytest tests/ -q`
- **Phase gate:** Full suite green (200+ tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_reports.py` — smoke tests for PRES-04 (PDF file generation)
- [ ] Add `TestMethodologyPaper` class to `tests/test_docs.py` — covers PRES-05
- [ ] Add `TestDocstringCoverage` class to `tests/test_docs.py` — covers ARCH-02
- [ ] Add `TestArchitectureDoc` class to `tests/test_docs.py` — covers ARCH-02
- [ ] Add `TestReadme` class to `tests/test_docs.py` — covers ARCH-03
- [ ] Register `pdf` marker in `conftest.py` `pytest_configure`
- [ ] Install dependencies: `uv add weasyprint kaleido` + `brew install pango`

---

## Sources

### Primary (HIGH confidence)
- WeasyPrint 68.1 official docs (https://doc.courtbouillon.org/weasyprint/stable/) — CSS @page, write_pdf API, installation
- Plotly static image export docs (https://plotly.com/python/static-image-export/) — kaleido v1 API, `to_image()` usage
- Plotly 6.1 migration guide (https://plotly.com/python/static-image-generation-changes/) — deprecation of `engine=` parameter
- Existing codebase inspection — `src/models/statistical/arima.py`, `src/inference/forecast.py` for docstring convention; `src/dashboard/charts/fan_chart.py` for chart export integration point; `pyproject.toml` for installed dependencies

### Secondary (MEDIUM confidence)
- Jinja2 + WeasyPrint pattern (https://medium.com/@engineering_holistic_ai/using-weasyprint-and-jinja2-to-create-pdfs-from-html-and-css-267127454dbd) — verified against WeasyPrint docs
- PyPI kaleido 1.2.0 (https://pypi.org/project/kaleido/) — version and Chrome requirement confirmed

### Tertiary (LOW confidence)
- README best practices for portfolio projects — synthesized from multiple WebSearch sources; specific section recommendations are judgment-based

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — WeasyPrint 68.1 and kaleido 1.2.0 verified against PyPI; plotly 6.6.0 verified in project venv; Chrome dependency confirmed present at `/Applications/Google Chrome.app`
- Architecture: HIGH — patterns derived from existing codebase structure plus official WeasyPrint/Jinja2 docs
- Pitfalls: HIGH for known issues (kaleido Chrome, WeasyPrint system deps, path resolution) — these are documented installation failure modes; MEDIUM for docstring scope underestimation (judgment-based)

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (WeasyPrint and kaleido are stable libraries; kaleido Chrome requirement is the main dependency to watch)
