# Phase 5: Reports, Paper, and Portfolio - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce the final portfolio outputs: PDF reports (executive brief + full analytical), methodology paper for LinkedIn, comprehensive code docstrings, architecture guide, and a polished GitHub README. Also: run the full pipeline against real World Bank/OECD/LSEG data to replace synthetic placeholders before generating any final outputs. No new models, dashboard features, or data sources.

</domain>

<decisions>
## Implementation Decisions

### CRITICAL PREREQUISITE: Real data pipeline run
- **Before generating any reports or documentation:** Run the full ingestion + processing + statistical + ensemble pipeline against real World Bank/OECD/LSEG API data
- Replace all synthetic Parquet files with real data outputs
- Re-run `scripts/run_statistical_pipeline.py` and `scripts/run_ensemble_pipeline.py` with real data
- This requires LSEG Workspace running for the LSEG connector
- All downstream outputs (reports, screenshots, paper) must reflect real data, not synthetic placeholders

### PDF report structure (PRES-04)
- **Two versions:** Executive brief (5-8 pages, normal mode) AND full analytical report (15-25 pages, expert mode)
- **Executive brief:** Dollar headlines, fan chart, segment breakdown, key findings, data sources. Clean narrative — for executives and LinkedIn shares.
- **Full report:** Everything in the brief PLUS raw methodology, diagnostics, model parameters, assumption sensitivity notes, mathematical appendix. For technical reviewers.
- **PDF engine:** WeasyPrint (HTML/CSS to PDF) — write report as styled HTML, render to PDF. Embed Plotly charts as static PNG images.
- **Mode alignment:** Executive brief = dashboard normal mode content. Full report = dashboard expert mode content.

### LinkedIn methodology paper (PRES-05)
- **Tone and style:** Claude's discretion — user skipped this discussion. Likely a hybrid narrative + technical approach given the portfolio context.
- **Must reference:** The GitHub repo, the quant risk manager origin story (PROJECT.md), key findings with real numbers

### Code documentation (ARCH-02)
- **Docstring depth:** Tutorial-style walkthroughs — extended docstrings that teach the reader. Each domain-critical function explains the concept, why this approach was chosen over alternatives, and links to ASSUMPTIONS.md. Matches PROJECT.md's "learning resource" goal.
- **Architecture guide:** `docs/ARCHITECTURE.md` — short (1-2 pages): data flow diagram, module responsibilities, key design decisions. Points to code for details.

### README showcase (ARCH-03)
- **Hero:** Screenshot-first — dashboard screenshot at the top as the first thing someone sees when browsing the repo
- **Sections:** Comprehensive (8+): Screenshot, Description, Key Findings, Quick Start, Architecture, Data Sources, Methodology, Contributing, License
- **Badges:** Minimal — Python version + license only. No badge spam.
- **Quick-start:** Exact commands to reproduce the pipeline from scratch

### Claude's Discretion
- LinkedIn paper tone and structure (user deferred)
- Exact WeasyPrint HTML/CSS template design
- Chart export resolution and format (PNG vs SVG)
- Architecture diagram format (ASCII, Mermaid, or image)
- Docstring format (Google-style with extended explanations)
- README example output images (dashboard screenshots vs chart exports)
- Contributing section depth
- License choice (MIT, Apache 2.0, etc.)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/PROJECT.md` — Documentation as learning resource, portfolio-quality, quant risk manager origin story
- `.planning/REQUIREMENTS.md` — PRES-04, PRES-05, ARCH-02, ARCH-03 requirements
- `.planning/ROADMAP.md` — Phase 5 success criteria (4 criteria that must be TRUE)

### Existing documentation (to extend, not duplicate)
- `docs/METHODOLOGY.md` — Market boundary rationale (Phase 1) — extend for the paper
- `docs/ASSUMPTIONS.md` — Two-tier with 16 sensitivity notes (Phase 2) — reference in reports

### Pipeline scripts (to re-run with real data)
- `scripts/run_statistical_pipeline.py` — Statistical pipeline runner
- `scripts/run_ensemble_pipeline.py` — ML ensemble pipeline runner
- `scripts/run_dashboard.py` — Dashboard launcher

### Dashboard outputs (for screenshots and chart exports)
- `src/dashboard/app.py` — Dashboard data layer and app instance
- `src/dashboard/charts/fan_chart.py` — Fan chart builder (export static images for PDF)
- `data/processed/forecasts_ensemble.parquet` — Forecast data (will be replaced with real data)
- `models/ai_industry/shap_summary.png` — SHAP plot for reports

### Config
- `config/industries/ai.yaml` — Source attribution strings, value chain multiplier config

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/dashboard/charts/fan_chart.py` — `make_fan_chart()` can export static PNG via `fig.write_image()` for PDF embedding
- `src/dashboard/charts/backtest.py` — `make_backtest_chart()` for diagnostics section in report
- `src/dashboard/app.py` — `FORECASTS_DF`, `DIAGNOSTICS`, `SOURCE_ATTRIBUTION` all loadable for report generation
- `docs/METHODOLOGY.md` — 366+ lines of market boundary content for the paper
- `docs/ASSUMPTIONS.md` — 16 sensitivity notes for the full report appendix

### Established Patterns
- Parquet as data interchange
- Config-driven segment and attribution strings
- Normal/Expert mode content distinction (Phase 4)
- `scripts/` directory for runner scripts

### Integration Points
- **Input:** All `data/processed/*.parquet` files (real data after pipeline re-run)
- **Input:** `models/ai_industry/` (serialized models + SHAP plot)
- **Output:** `reports/executive_brief.pdf` and `reports/full_report.pdf`
- **Output:** `docs/methodology_paper.md` (LinkedIn-ready)
- **Output:** `docs/ARCHITECTURE.md`
- **Output:** `README.md` (project root)

</code_context>

<specifics>
## Specific Ideas

- Running real data through the pipeline before generating outputs is the single most important task — everything else depends on having defensible numbers
- The executive brief should be shareable on its own — someone who gets the PDF should understand the finding without needing the repo
- Tutorial-style docstrings make this a genuine learning resource — differentiates it from typical portfolio projects that have zero documentation
- Screenshot-first README mirrors how recruiters actually browse GitHub — visual impact in the first 2 seconds

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-reports-paper-and-portfolio*
*Context gathered: 2026-03-22*
