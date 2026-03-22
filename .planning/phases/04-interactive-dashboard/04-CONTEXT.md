# Phase 4: Interactive Dashboard - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a Dash dashboard that displays the pre-computed forecast artifacts (from Phase 3) with interactive charts, SHAP driver attribution, model diagnostics, and data source attribution. Dashboard loads pre-computed Parquet and joblib files — no model re-training at runtime. PDF reports, methodology paper, and README are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Dashboard layout and navigation
- **Structure:** Multi-page Dash app with 4 tabs: Overview, Segments, Drivers, Diagnostics
- **Overview hero:** Headline number ("AI Industry: $X.X Trillion by 2030") + full fan chart + segment breakdown table/bar chart
- **Segments tab:** Deep-dive per-segment fan charts and comparisons
- **Drivers tab:** SHAP attribution panel
- **Diagnostics tab:** Metrics scorecard + backtesting chart
- **Filtering:** Global segment dropdown at top (filters all charts on current tab, with "All segments" aggregate option), individual charts can override the global selection
- **USD toggle:** Radio button in header: "Real 2020 USD / Nominal USD" — all charts update simultaneously

### Chart style and interactivity
- **Color scheme:** Light theme with accent colors (white background, deep blue primary, coral secondary). Professional without being stark.
- **Fan chart:** Dashed line for forecast + shaded forecast region background. CI bands as semi-transparent fills. Vertical dashed line at forecast origin (2024/2025).
- **Hover tooltips:** Compact — year + point estimate + selected CI bounds. No verbose tooltips.
- **Forecast vs historical:** Both dashed line AND shaded background change at forecast boundary — belt-and-suspenders visual clarity

### Diagnostics display
- **Content:** Metrics scorecard (RMSE, MAPE, R²) + backtesting chart (actual vs predicted with rolling origin). No interactive residual scatter plots.
- **Scope:** Comparison table showing all 4 segments side by side at top, plus per-segment backtest chart filtered by global selector below
- **Backtesting chart:** Interactive Plotly chart showing actual vs predicted values with the expanding-window backtest rolling origins highlighted

### Source attribution (DATA-07)
- **Format:** Footnote below each chart — small text: "Sources: World Bank, OECD, LSEG Workspace" (or subset relevant to that chart)
- **Content:** Claude decides the appropriate attribution text per chart based on what data it displays
- **Implemented as:** Plotly annotation or `html.P()` below each `dcc.Graph`

### Claude's Discretion
- Exact Plotly color hex values for the accent palette
- Chart sizing and responsive layout within each tab
- Exact Dash component hierarchy (rows, columns, cards)
- Loading states and skeleton displays
- Backtest chart specific visual treatment
- Whether to use Dash Bootstrap Components or plain Dash HTML
- SHAP visualization in Drivers tab (embed pre-generated PNG or re-render with Plotly)
- Footer content and styling

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/PROJECT.md` — Desktop-only, no mobile-responsive design, portfolio-quality
- `.planning/REQUIREMENTS.md` — PRES-01, PRES-02, PRES-03, DATA-07 requirements
- `.planning/ROADMAP.md` — Phase 4 success criteria (4 criteria that must be TRUE)

### Phase 3 outputs (data contract)
- `data/processed/forecasts_ensemble.parquet` — 84 rows, 10 columns: year, segment, point_real_2020, point_nominal, ci80_lower, ci80_upper, ci95_lower, ci95_upper, data_vintage, is_forecast
- `models/ai_industry/shap_summary.png` — Pre-generated SHAP summary plot (35KB PNG)
- `models/ai_industry/*.joblib` — 21 serialized model files (not needed at dashboard load, but available)

### Phase 1 outputs (config)
- `config/industries/ai.yaml` — `source_attribution` section with World Bank, OECD, LSEG display strings
- `config/settings.py` — `DATA_PROCESSED`, `MODELS_DIR` path constants

### Phase 2 outputs (diagnostics data)
- `src/diagnostics/model_eval.py` — `compute_rmse`, `compute_mape`, `compute_r2` for generating diagnostics metrics
- `data/processed/residuals_statistical.parquet` — residuals for backtest visualization

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config/settings.py` — `DATA_PROCESSED`, `MODELS_DIR` path constants for loading artifacts
- `config/industries/ai.yaml` — segment definitions and source attribution strings
- `src/inference/forecast.py` — `build_forecast_dataframe` schema matches dashboard needs
- `src/diagnostics/model_eval.py` — metrics functions for generating scorecard values
- `models/ai_industry/shap_summary.png` — ready to embed directly

### Established Patterns
- Parquet as the data interchange format
- Config-driven segment definitions
- pandera schema validation at boundaries

### Integration Points
- **Input:** Reads `data/processed/forecasts_ensemble.parquet` (main data source)
- **Input:** Reads `data/processed/residuals_statistical.parquet` (for backtest chart)
- **Input:** Reads `models/ai_industry/shap_summary.png` (for Drivers tab)
- **Input:** Reads `config/industries/ai.yaml` (for segment names and attribution)
- **Output:** Dash app serving on localhost (development server)

</code_context>

<specifics>
## Specific Ideas

- The headline number ("AI Industry: $X.X Trillion by 2030") should be the first thing a viewer sees — this is the "money shot" for LinkedIn/portfolio
- Fan chart with dashed forecast line + shaded region mirrors Bloomberg/IMF forecast visualizations — professional credibility
- The segment comparison on Overview immediately shows this isn't a single-number estimate — it's a structured analysis
- Compact tooltips keep the charts clean — detailed data exploration happens in the Segments and Diagnostics tabs
- Attribution footnotes satisfy DATA-07 without cluttering the visual presentation

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-interactive-dashboard*
*Context gathered: 2026-03-22*
