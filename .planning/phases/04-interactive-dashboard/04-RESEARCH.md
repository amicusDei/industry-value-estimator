# Phase 4: Interactive Dashboard - Research

**Researched:** 2026-03-22
**Domain:** Plotly Dash 4.x, Plotly graph objects, data-driven dashboard from pre-computed Parquet artifacts
**Confidence:** HIGH (primary stack verified against PyPI and official docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Dashboard layout and navigation**
- Structure: Multi-page Dash app with 4 tabs: Overview, Segments, Drivers, Diagnostics
- Overview hero: Headline number ("AI Industry: $X.X Trillion by 2030") + full fan chart + segment breakdown table/bar chart
- Segments tab: Deep-dive per-segment fan charts and comparisons
- Drivers tab: SHAP attribution panel
- Diagnostics tab: Metrics scorecard + backtesting chart
- Filtering: Global segment dropdown at top (filters all charts on current tab, with "All segments" aggregate option), individual charts can override the global selection
- USD toggle: Radio button in header: "Real 2020 USD / Nominal USD" — all charts update simultaneously

**Chart style and interactivity**
- Color scheme: Light theme with accent colors (white background, deep blue primary, coral secondary). Professional without being stark.
- Fan chart: Dashed line for forecast + shaded forecast region background. CI bands as semi-transparent fills. Vertical dashed line at forecast origin (2024/2025).
- Hover tooltips: Compact — year + point estimate + selected CI bounds. No verbose tooltips.
- Forecast vs historical: Both dashed line AND shaded background change at forecast boundary

**Diagnostics display**
- Content: Metrics scorecard (RMSE, MAPE, R²) + backtesting chart (actual vs predicted with rolling origin). No interactive residual scatter plots.
- Scope: Comparison table showing all 4 segments side by side at top, plus per-segment backtest chart filtered by global selector below
- Backtesting chart: Interactive Plotly chart showing actual vs predicted with expanding-window backtest rolling origins highlighted

**Source attribution (DATA-07)**
- Format: Footnote below each chart — small text: "Sources: World Bank, OECD, LSEG Workspace" (or subset relevant to that chart)
- Implemented as: Plotly annotation or `html.P()` below each `dcc.Graph`

### Claude's Discretion
- Exact Plotly color hex values for the accent palette
- Chart sizing and responsive layout within each tab
- Exact Dash component hierarchy (rows, columns, cards)
- Loading states and skeleton displays
- Backtest chart specific visual treatment
- Whether to use Dash Bootstrap Components or plain Dash HTML
- SHAP visualization in Drivers tab (embed pre-generated PNG or re-render with Plotly)
- Footer content and styling

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PRES-01 | Interactive Dash dashboard with time series charts and forecast fan charts | Dash 4.0 + Plotly 6.5 fan chart pattern using go.Scatter fill='tonexty' for CI bands; dcc.Tabs for 4-tab layout; dcc.Dropdown + dcc.RadioItems for filters |
| PRES-02 | SHAP driver attribution visualization in dashboard | Pre-generated shap_summary.png at models/ai_industry/shap_summary.png; embed via base64-encoded html.Img or symlinked assets/ folder — both patterns verified |
| PRES-03 | Model diagnostics display (RMSE, MAPE, R², residual plots, backtesting results) | src/diagnostics/model_eval.py provides compute_rmse, compute_mape, compute_r2; residuals_statistical.parquet provides backtest data; html.Table or dbc.Table for scorecard |
| DATA-07 | Display data source attribution on every chart and report output | config/industries/ai.yaml has source_attribution section with display strings; implement as html.P() footnote below each dcc.Graph |
</phase_requirements>

---

## Summary

Phase 4 builds a read-only Plotly Dash dashboard that reads pre-computed artifacts from Phases 1-3 and displays them with four tabs. No model training occurs at runtime. The data layer is simple: two small Parquet files (84-row forecasts, residuals), one PNG, and one YAML config. The primary technical challenge is in Plotly figure construction — specifically the fan chart with layered CI bands — and in wiring the global segment dropdown + USD toggle to update all charts simultaneously via callbacks.

The stack decision is Dash 4.0 (released 2026-02-03, stable) and Plotly 6.5.1 (already installed in this project). Dash 4.0 has API backwards compatibility with Dash 2/3 for Python properties, but visual styling is not backwards compatible. Since this is a new app with no legacy CSS, Dash 4.0 is the correct target. Dash Bootstrap Components 2.0.4 is available for layout convenience (dbc.Row, dbc.Col, dbc.Card) but is discretionary per CONTEXT.md.

Because the dataset is small (84 rows of forecasts, ~100-200 rows of residuals), the recommended data loading pattern is module-level globals: load once at app startup, filter in callbacks without mutating. No caching layer needed for a single-process development server. The SHAP PNG should be served from a Dash `assets/` directory (symlink or copy) or encoded as base64 — the assets/ folder approach is simpler and avoids runtime encoding.

**Primary recommendation:** Use Dash 4.0 + Plotly graph objects (go.Scatter with fill='tonexty' for fan charts, fig.add_vline for forecast boundary). Load both Parquet files at module level. Wire a single pattern-callback: `(segment_dropdown, usd_toggle) -> all tab charts`. Use html.P() footnotes for DATA-07 attribution — simpler and more reliable than Plotly figure annotations.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dash | 4.0.0 | Web application framework, component tree, callback engine | Official latest stable (2026-02-03); API compatible with 2.x/3.x Python props |
| plotly | 6.5.1 | Interactive chart objects (already installed) | Already in pyproject.toml; verified installed |
| pandas | 3.0.1+ | DataFrame operations, Parquet I/O (already installed) | Already in pyproject.toml |
| pyarrow | 23.0.1+ | Parquet engine for pd.read_parquet (already installed) | Already in pyproject.toml |
| pyyaml | 6.0.3+ | Load config/industries/ai.yaml (already installed) | Already in pyproject.toml |

### Supporting (Discretionary)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dash-bootstrap-components | 2.0.4 | dbc.Row, dbc.Col, dbc.Card, dbc.Table layout primitives | Use if layout complexity warrants it; avoid if plain html.Div + inline styles suffice |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plotly graph objects (go) | Plotly Express (px) | px is faster to write but less control over multi-trace fan chart layering; use go for full CI band control |
| html.P() for attribution | Plotly figure annotation | html.P() is decoupled from figure re-renders; figure annotations are trickier to position reliably |
| Module-level data globals | dcc.Store | dcc.Store serializes to JSON (round-trip cost); globals are correct for single-process dev server with read-only data |

**Installation (new packages only):**
```bash
uv add dash dash-bootstrap-components
```

**Verified versions (as of 2026-03-22):**
- `dash`: 4.0.0 (PyPI, released 2026-02-03)
- `dash-bootstrap-components`: 2.0.4 (PyPI, released 2025-08-20)
- `plotly`: 6.5.1 (already installed, verified with `pip3 show plotly`)

---

## Architecture Patterns

### Recommended Project Structure
```
src/
└── dashboard/
    ├── __init__.py
    ├── app.py           # Dash app instantiation + data loading at module level
    ├── layout.py        # Top-level layout: header, dcc.Tabs, footer
    ├── tabs/
    │   ├── __init__.py
    │   ├── overview.py      # Overview tab layout function
    │   ├── segments.py      # Segments tab layout function
    │   ├── drivers.py       # Drivers tab layout function
    │   └── diagnostics.py   # Diagnostics tab layout function
    ├── charts/
    │   ├── __init__.py
    │   ├── fan_chart.py     # make_fan_chart(df, segment, usd_col) -> go.Figure
    │   ├── backtest.py      # make_backtest_chart(residuals_df, segment) -> go.Figure
    │   └── styles.py        # COLOR_DEEP_BLUE, COLOR_CORAL, OPACITY_CI80, OPACITY_CI95
    └── callbacks.py         # All @app.callback registrations (import after layout)

assets/                  # Dash auto-serves everything here
└── shap_summary.png     # Symlink or copy from models/ai_industry/shap_summary.png

scripts/
└── run_dashboard.py     # python scripts/run_dashboard.py (sys.path injection pattern)
```

### Pattern 1: Module-Level Data Loading

**What:** Load Parquet files and YAML config once at app startup into read-only module-level variables. Callbacks filter/slice these DataFrames without mutating them.

**When to use:** Small datasets (< 10MB) on single-process dev server. This is the official Dash recommendation for this use case.

**Example:**
```python
# src/dashboard/app.py
# Source: https://dash.plotly.com/sharing-data-between-callbacks
import pandas as pd
import yaml
from pathlib import Path
from config.settings import DATA_PROCESSED, MODELS_DIR

# Loaded once at startup — read-only globals, safe for single-process dev server
FORECASTS_DF = pd.read_parquet(DATA_PROCESSED / "forecasts_ensemble.parquet")
RESIDUALS_DF = pd.read_parquet(DATA_PROCESSED / "residuals_statistical.parquet")

with open("config/industries/ai.yaml") as f:
    AI_CONFIG = yaml.safe_load(f)

SOURCE_ATTRIBUTION = AI_CONFIG["source_attribution"]
SEGMENTS = [seg["id"] for seg in AI_CONFIG["segments"]]
SEGMENT_DISPLAY = {seg["id"]: seg["display_name"] for seg in AI_CONFIG["segments"]}
```

### Pattern 2: dcc.Tabs with Callback Content Switching

**What:** dcc.Tabs holds tab identifiers; a single callback renders the full tab layout based on which tab is active. This defers layout computation until the tab is actually visited.

**When to use:** This is the official Dash lazy-rendering pattern. Use it when tabs have independent data requirements.

**Example:**
```python
# Source: https://dash.plotly.com/dash-core-components/tabs
from dash import dcc, html, Input, Output, callback

app.layout = html.Div([
    # Global controls — visible on all tabs
    html.Div([
        dcc.Dropdown(
            id="segment-dropdown",
            options=[{"label": "All Segments", "value": "all"}] +
                    [{"label": SEGMENT_DISPLAY[s], "value": s} for s in SEGMENTS],
            value="all",
            clearable=False,
        ),
        dcc.RadioItems(
            id="usd-toggle",
            options=[
                {"label": "Real 2020 USD", "value": "point_estimate_real_2020"},
                {"label": "Nominal USD", "value": "point_estimate_nominal"},
            ],
            value="point_estimate_real_2020",
            inline=True,
        ),
    ], id="global-controls"),
    dcc.Tabs(
        id="main-tabs",
        value="overview",
        children=[
            dcc.Tab(label="Overview", value="overview"),
            dcc.Tab(label="Segments", value="segments"),
            dcc.Tab(label="Drivers", value="drivers"),
            dcc.Tab(label="Diagnostics", value="diagnostics"),
        ],
    ),
    html.Div(id="tab-content"),
])

@callback(
    Output("tab-content", "children"),
    Input("main-tabs", "value"),
    Input("segment-dropdown", "value"),
    Input("usd-toggle", "value"),
)
def render_tab(active_tab, segment, usd_col):
    if active_tab == "overview":
        return build_overview_layout(segment, usd_col)
    elif active_tab == "segments":
        return build_segments_layout(segment, usd_col)
    # ...
```

### Pattern 3: Fan Chart with Layered CI Bands

**What:** Stack three go.Scatter traces (95% band, 80% band, point line) using fill='tonexty'. Add a vertical dashed line at the forecast origin using fig.add_vline(). Use a second line segment with dash="dash" for the forecast portion.

**When to use:** Any chart displaying forecast uncertainty. This is the standard IMF/Bloomberg-style fan chart pattern verified against Plotly docs.

**Example:**
```python
# Source: https://plotly.com/python/continuous-error-bars/
import plotly.graph_objects as go

def make_fan_chart(df: pd.DataFrame, segment: str, usd_col: str) -> go.Figure:
    seg_df = df[df["segment"] == segment].sort_values("year")
    hist = seg_df[~seg_df["is_forecast"]]
    fore = seg_df[seg_df["is_forecast"]]
    forecast_origin = hist["year"].max()

    fig = go.Figure()

    # 95% CI band (widest, most transparent) — upper trace then lower with fill
    fig.add_trace(go.Scatter(
        x=list(fore["year"]) + list(fore["year"][::-1]),
        y=list(fore["ci95_upper"]) + list(fore["ci95_lower"][::-1]),
        fill="toself",
        fillcolor="rgba(30, 90, 200, 0.10)",  # deep blue, very transparent
        line=dict(color="rgba(255,255,255,0)"),
        hoverinfo="skip",
        showlegend=False,
        name="95% CI",
    ))

    # 80% CI band (narrower, slightly more opaque)
    fig.add_trace(go.Scatter(
        x=list(fore["year"]) + list(fore["year"][::-1]),
        y=list(fore["ci80_upper"]) + list(fore["ci80_lower"][::-1]),
        fill="toself",
        fillcolor="rgba(30, 90, 200, 0.20)",
        line=dict(color="rgba(255,255,255,0)"),
        hoverinfo="skip",
        showlegend=False,
        name="80% CI",
    ))

    # Historical line — solid
    fig.add_trace(go.Scatter(
        x=hist["year"], y=hist[usd_col],
        mode="lines",
        line=dict(color="#1E5AC8", width=2),
        name="Historical",
    ))

    # Forecast line — dashed
    # Bridge last historical point to first forecast point for visual continuity
    bridge_x = [hist["year"].iloc[-1]] + list(fore["year"])
    bridge_y = [hist[usd_col].iloc[-1]] + list(fore[usd_col])
    fig.add_trace(go.Scatter(
        x=bridge_x, y=bridge_y,
        mode="lines",
        line=dict(color="#1E5AC8", width=2, dash="dash"),
        name="Forecast",
    ))

    # Vertical dashed line at forecast boundary
    fig.add_vline(
        x=forecast_origin,
        line_width=1,
        line_dash="dash",
        line_color="rgba(100, 100, 100, 0.5)",
        annotation_text="Forecast",
        annotation_position="top right",
    )

    # Compact hover template
    fig.update_traces(
        hovertemplate="%{x}: %{y:.2f}T<extra></extra>",
        selector=dict(mode="lines"),
    )

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig
```

### Pattern 4: DATA-07 Attribution Footnote

**What:** Place a small html.P() element immediately below each dcc.Graph. Source strings come from config/industries/ai.yaml `source_attribution` section.

**When to use:** Every chart. Simpler than Plotly figure annotations which move with zoom/pan.

**Example:**
```python
# Source: config/industries/ai.yaml source_attribution section
def attribution_footnote(sources: list[str]) -> html.P:
    """sources: list of keys from SOURCE_ATTRIBUTION dict."""
    display_strings = [SOURCE_ATTRIBUTION[s] for s in sources]
    return html.P(
        f"Sources: {', '.join(display_strings)}",
        style={
            "fontSize": "11px",
            "color": "#888",
            "marginTop": "4px",
            "marginBottom": "0",
        }
    )

# Usage in layout:
html.Div([
    dcc.Graph(id="fan-chart-graph"),
    attribution_footnote(["world_bank", "oecd", "lseg"]),
])
```

### Pattern 5: SHAP PNG Embedding

**What:** Copy (or symlink) `models/ai_industry/shap_summary.png` into `assets/` directory. Dash auto-serves the `assets/` folder. Reference with `html.Img(src="/assets/shap_summary.png")`.

**When to use:** Pre-generated static images. No runtime encoding needed, no base64 bloat, no callback required.

**Example:**
```python
# src/dashboard/tabs/drivers.py
from dash import html

def build_drivers_layout(segment: str, usd_col: str) -> html.Div:
    return html.Div([
        html.H3("SHAP Driver Attribution"),
        html.P(
            "Feature importance from SHAP analysis — shows which variables "
            "contribute most to the forecast for the current period.",
            style={"color": "#555"},
        ),
        html.Img(
            src="/assets/shap_summary.png",
            style={"maxWidth": "100%", "height": "auto"},
        ),
        html.P(
            "Sources: World Bank, OECD, LSEG Workspace",
            style={"fontSize": "11px", "color": "#888", "marginTop": "8px"},
        ),
    ])
```

### Pattern 6: Diagnostics Metrics Scorecard

**What:** Compute RMSE/MAPE/R² from residuals_statistical.parquet at module level. Display as an html.Table (or dbc.Table) with all 4 segments side-by-side.

**Example:**
```python
# src/dashboard/app.py — compute at startup
from src.diagnostics.model_eval import compute_rmse, compute_mape, compute_r2
import numpy as np

def _compute_diagnostics(residuals_df: pd.DataFrame) -> dict:
    """Compute per-segment scorecard metrics from residuals."""
    results = {}
    for segment, grp in residuals_df.groupby("segment"):
        actual = grp["actual"].to_numpy() if "actual" in grp.columns else None
        predicted = grp["predicted"].to_numpy() if "predicted" in grp.columns else None
        residual = grp["residual"].to_numpy()
        # If only residuals available, derive from residual = actual - predicted
        # model_eval functions need actual + predicted; check column availability
        results[segment] = {
            "rmse": float(np.sqrt(np.mean(residual ** 2))),
            # mape and r2 require actual values — check residuals schema
        }
    return results

DIAGNOSTICS = _compute_diagnostics(RESIDUALS_DF)
```

**Note on residuals_statistical.parquet schema:** The parquet file was verified to exist. The exact column names (`actual`, `predicted` vs just `residual`) need to be confirmed when the file is read — the pattern above shows both scenarios.

### Anti-Patterns to Avoid
- **Calling pd.read_parquet inside callbacks:** Reads disk on every user interaction. Load at module level.
- **Modifying FORECASTS_DF inside a callback:** Not thread-safe. Always filter with boolean mask to produce a copy.
- **Storing full DataFrames in dcc.Store:** For this project's dataset size it technically works, but it's unnecessary — module-level globals are simpler and correct for a single-process dev server.
- **Using dash.page_registry (Dash Pages) instead of dcc.Tabs:** Dash Pages uses URL routing, which changes the URL on tab switch. dcc.Tabs is the correct approach for in-page tab switching with shared global controls.
- **Re-creating the Dash app instance across multiple files:** Instantiate Dash app once in app.py; import it in other modules.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CI band shading | Custom SVG overlays | go.Scatter fill='toself' or fill='tonexty' | Plotly handles coordinate transforms, zoom sync, hover |
| Forecast boundary marker | Manual annotation positioning | fig.add_vline() | Auto-scales with axis range |
| Responsive grid layout | CSS grid from scratch | dbc.Row / dbc.Col or html.Div with display:flex | DBC Bootstrap grid handles column breakpoints |
| Metrics table | Custom HTML string concat | html.Table with list comprehension or dbc.Table | Dash component tree handles escaping, re-renders cleanly |
| SHAP image delivery | Flask send_file route | Dash assets/ folder auto-serving | Built-in, zero configuration, handles MIME types |
| USD format in tooltips | String formatting in callback | Plotly hovertemplate with %{y:.2f} | Server-side; no JS needed |

**Key insight:** The Plotly graph objects API (go.Scatter, go.Figure) handles all coordinate transformations, hover, zoom, and pan automatically. Any custom rendering layer for this will be worse in every dimension.

---

## Common Pitfalls

### Pitfall 1: Dash 4.0 Visual Compatibility
**What goes wrong:** Apps styled for Dash 2/3 look different in Dash 4 because component CSS selectors changed in the redesigned core components.
**Why it happens:** Dash 4 rebuilt dcc.Tabs, dcc.Dropdown, dcc.RadioItems with new CSS classes.
**How to avoid:** This is a greenfield app — write styles targeting Dash 4 components from the start. Don't copy CSS from Dash 2/3 tutorials for component-specific selectors.
**Warning signs:** dcc.Tabs appearing with unexpected default styling.

### Pitfall 2: CI Band Trace Order
**What goes wrong:** The 80% CI band renders on top of the 95% band, making the outer band invisible.
**Why it happens:** Plotly renders traces in the order they are added; later traces paint over earlier ones.
**How to avoid:** Add widest CI band (95%) first, then 80%, then the point line. Use `fill='toself'` with semi-transparent fillcolor so stacking is visible.
**Warning signs:** Shaded region appears as a single uniform color band instead of two nested bands.

### Pitfall 3: Global Dropdown + Tab Interaction
**What goes wrong:** When the user switches tabs, the content re-renders correctly but the segment dropdown resets.
**Why it happens:** If the segment dropdown is inside the tab content (re-rendered by the callback), its value resets on every tab switch.
**How to avoid:** Place the segment dropdown and USD toggle in the layout OUTSIDE the tab content container, at the same level as `dcc.Tabs`. Their values persist because they are never re-rendered.
**Warning signs:** Dropdown value resets to "All Segments" on every tab click.

### Pitfall 4: Parquet Column Name Mismatch
**What goes wrong:** KeyError when accessing `df["point_real_2020"]` — column is actually named `point_estimate_real_2020`.
**Why it happens:** CONTEXT.md canonical_refs describe a slightly different schema than what Phase 3 actually produced. The actual Parquet columns (verified live) are: `point_estimate_real_2020`, `point_estimate_nominal` (not `point_real_2020`, `point_nominal` as the CONTEXT.md data contract suggested).
**How to avoid:** Use the verified schema below. Do not trust CONTEXT.md column names verbatim — verify against live file.
**Warning signs:** KeyError at app startup when slicing FORECASTS_DF.

**Verified actual schema of forecasts_ensemble.parquet:**
```
year                          int64
segment                      object    # values: ai_adoption, ai_hardware, ai_infrastructure, ai_software
point_estimate_real_2020    float64
point_estimate_nominal      float64
ci80_lower                  float64
ci80_upper                  float64
ci95_lower                  float64
ci95_upper                  float64
is_forecast                    bool   # False for historical, True for 2025+
data_vintage                 object   # e.g., "2024-Q4"
```
Shape: 84 rows (4 segments × 21 years: 2010–2030)
Forecast boundary: is_forecast == True for year >= 2025

### Pitfall 5: Headline "Trillion" Computation
**What goes wrong:** Headline number shows raw model units instead of a dollar figure.
**Why it happens:** The forecast values in the Parquet are the ensemble outputs — the scale depends on what unit the underlying model was trained on (proxy index vs. actual USD).
**How to avoid:** Inspect FORECASTS_DF values before building the headline. The point_estimate_real_2020 values observed were in the range -1 to +1.5 (normalized). If values are normalized, the dashboard must apply the appropriate scaling factor or note units explicitly. Coordinate with Phase 3 team about scale.
**Warning signs:** Headline number shows "AI Industry: $0.8 Trillion" which seems too low or "$-0.08 Trillion" which is nonsensical.

### Pitfall 6: SHAP PNG Path at Runtime
**What goes wrong:** `html.Img(src="/assets/shap_summary.png")` returns 404 because the assets/ folder doesn't contain the file.
**Why it happens:** The PNG lives in `models/ai_industry/` — Dash won't serve it from there.
**How to avoid:** During setup task (Wave 0), create `assets/` directory in the dashboard src folder and symlink or copy the PNG. Document the setup step in run_dashboard.py or a setup script.
**Warning signs:** Broken image icon in the Drivers tab.

---

## Code Examples

Verified patterns from official sources:

### App Entry Point (run_dashboard.py)
```python
# scripts/run_dashboard.py
# Source: Phase 02-05 sys.path injection pattern (established project convention)
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dashboard.app import app

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
```

### Vertical Dashed Line at Forecast Origin
```python
# Source: https://plotly.com/python/horizontal-vertical-shapes/
fig.add_vline(
    x=2024,  # last historical year
    line_width=1,
    line_dash="dash",
    line_color="rgba(120, 120, 120, 0.6)",
    annotation_text="Forecast Start",
    annotation_position="top right",
    annotation_font_size=10,
)
```

### Compact Hover Template
```python
# Source: https://plotly.com/python-api-reference/generated/plotly.graph_objects.Scatter.html
go.Scatter(
    x=years,
    y=values,
    hovertemplate="<b>%{x}</b><br>%{y:.2f}T USD<extra></extra>",
)
```

### Diagnostics Scorecard Table
```python
# All-segments comparison table using html.Table
def build_scorecard_table(diagnostics: dict) -> html.Table:
    segments = list(diagnostics.keys())
    header = html.Tr([html.Th("Metric")] + [html.Th(SEGMENT_DISPLAY.get(s, s)) for s in segments])
    rows = []
    for metric in ["rmse", "mape", "r2"]:
        cells = [html.Td(metric.upper())]
        for s in segments:
            val = diagnostics[s].get(metric, "N/A")
            cells.append(html.Td(f"{val:.3f}" if isinstance(val, float) else val))
        rows.append(html.Tr(cells))
    return html.Table([html.Thead(header), html.Tbody(rows)], style={"width": "100%"})
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| dash_table.DataTable | dash[ag-grid] (for complex tables) | Dash 3.3.0 deprecated DataTable | Use html.Table for simple scorecard; ag-grid only for complex interactive grids |
| Dash 2.x multi-page with dcc.Location | Dash Pages (2.5+) or dcc.Tabs | Dash 2.5 (2022) | Use dcc.Tabs for in-page tab switching (correct for this app); use Dash Pages only for URL-routed multi-page apps |
| Flask-Caching for data | Module-level globals (small data) | Always valid | For 84-row datasets, module globals are correct; caching adds complexity for no benefit |

**Deprecated/outdated:**
- `dash_table.DataTable`: Deprecated in Dash 3.3.0. Use `html.Table` for simple tables or `dag.AgGrid` from `dash[ag-grid]` for complex grids. This app needs only simple scorecards, so `html.Table` is correct.

---

## Open Questions

1. **Normalized vs. absolute forecast values**
   - What we know: `point_estimate_real_2020` values in the live Parquet range from approximately -1.2 to +1.5 (observed in data inspection). These appear to be normalized/scaled, not raw USD trillions.
   - What's unclear: What scaling factor converts these to display-ready USD values for the headline? Phase 3 ensemble may output normalized residual corrections added to statistical model outputs, not final USD market size estimates.
   - Recommendation: Implementation Wave 0 task should read the Phase 3 forecast.py `build_forecast_dataframe` docstring and confirm output units before building the headline number. If values are normalized, either (a) the dashboard needs a denormalization step, or (b) the headline should use different framing (e.g., growth index or relative comparison). This is the highest-risk open question for PRES-01.

2. **residuals_statistical.parquet column schema**
   - What we know: File exists at `data/processed/residuals_statistical.parquet`. Phase 2 context says schema is `year (int), segment (str), residual (float), model_type (str)`.
   - What's unclear: Does the file also contain `actual` and `predicted` columns needed for RMSE/MAPE/R² using `model_eval.py`? Or only `residual`?
   - Recommendation: Read the file early in Wave 0. If only `residual` column: RMSE = sqrt(mean(residual²)); MAPE and R² require actual values and cannot be computed from residuals alone — display those as "N/A" or use a different source.

3. **Global dropdown + tab re-render interaction**
   - What we know: The callback pattern that re-renders entire tab content on every segment/toggle change will re-render the full tab on every interaction, which could cause chart flicker.
   - What's unclear: Whether individual chart callbacks per-graph (finer-grained) would be better UX than one tab-level callback.
   - Recommendation: Start with one tab-level callback (simpler code, easier to debug). Switch to per-graph callbacks only if flicker is visually unacceptable during testing.

---

## Validation Architecture

nyquist_validation is enabled (no explicit false in config.json).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ |
| Config file | pyproject.toml (no explicit pytest section detected — uses defaults) |
| Quick run command | `python3 -m pytest tests/test_dashboard.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRES-01 | Fan chart figure contains CI band traces and forecast line with dash style | unit | `python3 -m pytest tests/test_dashboard.py::test_fan_chart_traces -x` | ❌ Wave 0 |
| PRES-01 | dcc.Tabs layout renders without error (all 4 tabs present) | unit | `python3 -m pytest tests/test_dashboard.py::test_layout_tabs -x` | ❌ Wave 0 |
| PRES-01 | USD toggle switches column used in chart (callback output differs by toggle value) | unit | `python3 -m pytest tests/test_dashboard.py::test_usd_toggle_callback -x` | ❌ Wave 0 |
| PRES-02 | Drivers tab layout contains html.Img with src pointing to shap_summary.png | unit | `python3 -m pytest tests/test_dashboard.py::test_drivers_shap_img -x` | ❌ Wave 0 |
| PRES-03 | Diagnostics scorecard table contains RMSE, MAPE, R² rows | unit | `python3 -m pytest tests/test_dashboard.py::test_diagnostics_scorecard -x` | ❌ Wave 0 |
| PRES-03 | Backtest chart figure contains actual and predicted traces | unit | `python3 -m pytest tests/test_dashboard.py::test_backtest_chart_traces -x` | ❌ Wave 0 |
| DATA-07 | Every chart div contains an attribution html.P() as sibling of dcc.Graph | unit | `python3 -m pytest tests/test_dashboard.py::test_attribution_footnotes -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_dashboard.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_dashboard.py` — all dashboard unit tests (7 tests listed above)
- [ ] `src/dashboard/__init__.py` — package marker
- [ ] `assets/` directory (symlink or copy `models/ai_industry/shap_summary.png`)
- [ ] Install dash: `uv add dash dash-bootstrap-components` — neither in pyproject.toml yet

---

## Sources

### Primary (HIGH confidence)
- PyPI dash 4.0.0 — version and release date verified
- PyPI dash-bootstrap-components 2.0.4 — version and release date verified
- `pip3 show plotly` — confirmed 6.5.1 installed in project environment
- https://dash.plotly.com/dash-core-components/tabs — dcc.Tabs callback pattern
- https://plotly.com/python/continuous-error-bars/ — fill='toself' and fill='tonexty' for CI bands
- https://plotly.com/python/horizontal-vertical-shapes/ — fig.add_vline() for forecast boundary
- https://dash.plotly.com/sharing-data-between-callbacks — module-level data loading pattern
- `data/processed/forecasts_ensemble.parquet` — schema verified by direct inspection (python3 -c)
- `config/industries/ai.yaml` — source_attribution section read directly

### Secondary (MEDIUM confidence)
- https://community.plotly.com/t/dash-4-0-0rc-with-refreshed-dash-core-components-now-available/94184 — Dash 4.0 API backwards compatibility claim (Python props stable, visual styling changed)
- https://dash.plotly.com/testing — callback unit testing pattern with contextvars
- https://dash.plotly.com/external-resources — assets/ folder auto-serving behavior

### Tertiary (LOW confidence)
- data inspection showing point_estimate values in ~-1 to +1.5 range: possible normalization — needs validation against Phase 3 source code

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified against PyPI, plotly confirmed installed
- Architecture: HIGH — patterns verified against official Dash docs and existing project conventions
- Parquet schema: HIGH — verified by direct file inspection
- Pitfalls: HIGH for CI ordering/tab scoping (common documented issues); MEDIUM for headline scaling (open question)
- Validation architecture: HIGH — follows established project test pattern

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (Dash 4.x is stable; DBC 2.0.4 stable)
