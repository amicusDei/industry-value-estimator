# Phase 11: Dashboard and Diagnostics - Research

**Researched:** 2026-03-26
**Domain:** Plotly Dash dashboard — Basic tier build, analyst consensus panel, Normal/Expert cleanup, Diagnostics wiring to real backtesting metrics, vintage labels
**Confidence:** HIGH (full codebase inspection + verified Parquet schemas + test suite run)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Basic Tier Layout**
- 3 hero KPIs: (1) Total AI market size (current year, nominal USD), (2) YoY growth rate (%), (3) 2030 forecast (nominal USD). Each with scope label and uncertainty range
- Additional metrics below heroes: Market growth rates, individual company growth, data centre construction growth rates
- Charts: Segment breakdown chart + growth fan chart on the same screen
- Single non-scrolling screen — all key information visible without scrolling
- Currency: Nominal USD for Basic tier (what analysts publish, more recognizable). Real 2020 USD stays in Normal/Expert
- Uncertainty display: Color-coded confidence indicators (green/yellow/red) next to each KPI based on how tight the uncertainty range is. Thresholds defined by Claude's discretion
- No SHAP, no diagnostics, no methodology on Basic tier — those live in Normal/Expert

**Analyst Consensus Panel**
- Display format: Bullet chart — horizontal bar showing analyst range (min-max) as grey band, model estimate as colored marker. Instantly shows inside/outside consensus
- Placement: Both Basic and Normal tiers
- Divergence highlighting: Color + tooltip — marker turns amber/red when outside consensus range. Tooltip shows "Model: $X vs Consensus: $Y-$Z — divergence: +N%". Full documented rationale available in Expert mode
- Data source: `market_anchors_ai.parquet` analyst corpus (8 firms, scope-normalized estimates)

**Normal/Expert Cleanup**
- Revenue multiples table: Normal mode Overview tab — context panel alongside market size summary. Shows AI pure-play (~33x), semiconductor, conglomerate (~7x) EV/Revenue multiples with source attribution and vintage date
- Pass-through alias removal: Delete all `usd_point`, `usd_ci80_lower` etc. aliases from `app.py`. All tabs reference `point_estimate_real_2020` directly (or renamed column if Phase 9 changed it)
- Composite index references: Remove any remaining references to composite index, PCA scores, or multiplier derivation from the UI
- Diagnostics tab: Split panels for Hard vs Soft backtesting results. Left panel: "Validated (EDGAR actuals)" with NVIDIA/Palantir MAPE. Right panel: "Cross-checked (analyst consensus)" with circular_flag warning. Uses `backtesting_results.parquet`
- MAPE/R² labels: Explicit [in-sample] / [out-of-sample] labels on all diagnostic metrics

**Vintage & Scope Labels**
- Prominence: Subtle footer per section — small text below each chart/table: "Data: EDGAR Q4 2024 | Model: v1.1 | Last updated: 2026-03-26"
- Present but not cluttering — doesn't compete with actual data
- Every data point has context — no number without vintage date and scope label
- Source attribution: Per data source (World Bank, OECD, LSEG, EDGAR, analyst corpus) with individual vintage dates

### Claude's Discretion
- Exact color thresholds for confidence indicators (green/yellow/red)
- Column name strategy (keep `point_estimate_real_2020` or rename during alias cleanup)
- Exact layout positioning of consensus bullet chart within Basic tab
- How to source/display data centre construction and company growth rates on Basic tier
- Revenue multiples table data (specific companies, multiples, dates)
- Vintage footer exact format and placement per tab

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DASH-01 | Basic dashboard tier — 3 hero numbers (total AI market size, YoY growth rate, 2030 forecast), segment breakdown chart, growth fan chart on a single non-scrolling screen | `basic.py` new module; nominal USD from `point_estimate_nominal`; fan chart reused from `fan_chart.py`; segment bar from `_build_segment_bar` pattern; KPI cards via `dbc.Card` |
| DASH-02 | Analyst consensus panel — model output vs published estimate range displayed side-by-side in Basic and Normal tiers | Bullet chart component reading `market_anchors_ai.parquet` p25/p75 as range, model point as marker; placement in both `basic.py` and `overview.py` |
| DASH-03 | Revenue multiples reference table — EV/Revenue multiples for AI pure-plays (~33x), semiconductors, and conglomerates (~7x) with source attribution | Static table in `overview.py` Normal mode; data hardcoded from PitchBook Q4 2025 with vintage date (no new Parquet needed) |
| DASH-04 | Normal/Expert modes updated — real USD figures replace composite indices, recalibrated narrative text, all existing tabs functional with new model outputs | Alias columns removed from `app.py`; `overview.py` expert card PCA references removed; `fan_chart.py` `usd_mode` default clarified; `segments.py` usd_col routing verified |
| DASH-05 | Data vintage and methodology transparency — per-source, per-segment "last updated" timestamp and scope label displayed in UI | `data_vintage` column in `forecasts_ensemble.parquet` (confirmed: "2024-Q4"); scope statement in `ai.yaml` `market_boundary`; footer helper function shared across tabs |
</phase_requirements>

---

## Summary

Phase 11 is a pure dashboard/UI phase. All upstream data artifacts are confirmed present: `forecasts_ensemble.parquet` (32 rows, 2023-2030, both real and nominal columns), `backtesting_results.parquet` (12 rows, hard/soft actual_type, circular_flag column), `market_anchors_ai.parquet` (45 rows, p25/median/p75 nominal and real 2020), `revenue_attribution_ai.parquet` (15 companies), `private_valuations_ai.parquet` (18 companies). No new data pipeline work is required.

The key implementation challenge is the pass-through alias removal in `app.py`. Five alias columns (`usd_point`, `usd_ci80_lower`, `usd_ci80_upper`, `usd_ci95_lower`, `usd_ci95_upper`) are currently created at startup and referenced throughout `overview.py`, `fan_chart.py`, and `segments.py`. Removing these aliases requires updating every callsite in the same commit to avoid breaking the existing 8 passing dashboard tests. The safe strategy is: rename all references to `point_estimate_real_2020` (and `ci80_lower` etc.) in one pass, then delete the alias block.

The diagnostics tab rewrite is straightforward — `backtesting_results.parquet` already has the `actual_type`, `circular_flag`, `mape_label`, `mape`, and `r2` columns designed precisely for the split-panel layout. The chart in `backtest.py` needs a full rewrite: currently it reads from `residuals_statistical.parquet` (residuals only), but the new version reads from `backtesting_results.parquet` (actual vs predicted USD).

**Primary recommendation:** Build in four isolated, testable pieces: (1) Basic tier `basic.py`, (2) consensus bullet chart as a shared component, (3) alias removal + composite index cleanup in a single coordinated edit, (4) diagnostics tab and backtest chart rewrite against the new Parquet.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dash | >=4.0.0 (installed) | Component tree, callbacks, tab routing | Already the project's dashboard framework |
| dash-bootstrap-components | >=2.0.4 (installed) | KPI cards (`dbc.Card`), grid (`dbc.Row`/`dbc.Col`) | Already installed; KPI card layout requires it |
| plotly | bundled with dash | Fan chart, bullet chart, backtest chart | Fan chart already in `fan_chart.py`; bullet chart is `go.Bar` with error_x |
| pandas | >=3.0.1 (installed) | Parquet reads, DataFrame filtering | All data loaded at startup |
| pyyaml | >=6.0.3 (installed) | `ai.yaml` config for scope/vintage metadata | Already used in `app.py` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyarrow | >=23.0.1 (installed) | Parquet I/O for backtesting_results.parquet | New load in `app.py` startup |

### No New Dependencies
Zero new packages needed for Phase 11. All required libraries are already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure for Phase 11

```
src/dashboard/
├── app.py                    # MODIFY: remove 5 alias columns, add BACKTESTING_DF load, load market_anchors at startup
├── layout.py                 # MODIFY: add "basic" as first dcc.Tab; add "Basic" to mode-toggle or make Basic auto-show without mode toggle
├── callbacks.py              # MODIFY: add elif active_tab == "basic" branch
├── tabs/
│   ├── basic.py              # NEW: KPI cards + segment bar + fan chart + consensus panel, single-screen
│   ├── overview.py           # MODIFY: remove alias refs, remove PCA expert block, add consensus panel (Normal mode), add revenue multiples table (Normal mode)
│   ├── segments.py           # MODIFY: replace usd_point references with point_estimate_real_2020
│   ├── drivers.py            # MODIFY: replace usd_point if referenced (inspect)
│   └── diagnostics.py       # MODIFY: replace residuals-based scorecard with backtesting_results; split Hard/Soft panels; add in-sample/out-of-sample labels
└── charts/
    ├── fan_chart.py          # MODIFY: remove usd_point column refs from usd_mode path; update default to use point_estimate_real_2020 directly
    ├── backtest.py           # REWRITE: read backtesting_results.parquet; actual vs predicted scatter, not residuals bar
    ├── bullet_chart.py       # NEW: consensus bullet chart component (horizontal bar + marker)
    └── styles.py             # MODIFY: add confidence traffic-light colors (COLOR_GREEN, COLOR_AMBER, COLOR_RED)
```

### Pattern 1: Basic Tier — Single-Screen Non-Scrolling Layout

**What:** The Basic tab renders entirely within viewport height using CSS `height: 100vh` constraint on the outer container, with a 3-hero-KPI row at the top and two charts (segment bar + fan chart) below. `dbc.Row` / `dbc.Col` provides the two-column chart layout.

**Layout grid:**
```
┌─────────────────────────────────────────────────────┐
│  Hero KPI 1    │  Hero KPI 2    │  Hero KPI 3        │  ← dbc.Row, 3 cols
│  Total Mkt     │  YoY Growth %  │  2030 Forecast     │
├─────────────────┬───────────────────────────────────┤
│ Segment Bar     │  Fan Chart (growth fan)            │  ← dbc.Row, 2 cols (5/7 split)
│ (2030 breakdown)│                                   │
├─────────────────┴───────────────────────────────────┤
│  Analyst Consensus Bullet Chart                      │  ← full-width
│  [Consensus range: ████░░░░] [Model ▪]              │
└─────────────────────────────────────────────────────┘
```

**When to use:** This is the exclusive structure for `basic.py`. No cards expand; no methodology text; no scrolling.

**Example (KPI card):**
```python
# src/dashboard/tabs/basic.py
import dash_bootstrap_components as dbc
from dash import html

def _kpi_card(label: str, value: str, sub: str, confidence_color: str) -> dbc.Card:
    """
    confidence_color: one of '#2ECC71' (green), '#F39C12' (amber), '#E74C3C' (red)
    Set based on (ci80_upper - ci80_lower) / point as fraction of point_estimate.
    Thresholds (Claude's discretion): <0.3 → green, 0.3-0.6 → amber, >0.6 → red
    """
    return dbc.Card([
        dbc.CardBody([
            html.Div(label, style={"fontSize": "12px", "color": "#888", "marginBottom": "4px"}),
            html.Div([
                html.Span(value, style={"fontSize": "28px", "fontWeight": 700, "color": "#1A1A2E"}),
                html.Span("  ", style={"display": "inline-block", "width": "8px"}),
                html.Span("●", style={"color": confidence_color, "fontSize": "14px", "verticalAlign": "middle"}),
            ]),
            html.Div(sub, style={"fontSize": "11px", "color": "#999", "marginTop": "2px"}),
        ])
    ], style={"border": "1px solid #E8EBF0", "borderRadius": "8px", "boxShadow": "0 1px 4px rgba(0,0,0,0.06)"})
```

**Confidence thresholds (Claude's discretion):**
- GREEN: `(ci80_upper - ci80_lower) / point_estimate < 0.30` (tight range)
- AMBER: `0.30 <= fraction < 0.60`
- RED: `fraction >= 0.60` (wide, uncertain)

### Pattern 2: Analyst Consensus Bullet Chart

**What:** A horizontal bar chart where each row is a segment. A grey `error_x` band shows the analyst range (p25 to p75 from `market_anchors_ai.parquet`), and a colored `go.Bar` or `go.Scatter` marker shows the model estimate. Amber/red when outside the p25-p75 range.

**Data source mapping:**
```python
# market_anchors_ai.parquet columns used:
#   estimate_year, segment,
#   p25_usd_billions_nominal, p75_usd_billions_nominal, median_usd_billions_nominal
# forecasts_ensemble.parquet columns used:
#   year, segment, point_estimate_nominal
```

**Example (Plotly bullet chart):**
```python
# src/dashboard/charts/bullet_chart.py
import plotly.graph_objects as go
import pandas as pd

def make_consensus_bullet_chart(
    forecasts_df: pd.DataFrame,
    anchors_df: pd.DataFrame,
    year: int,
    segment_display: dict,
) -> go.Figure:
    """
    Horizontal bullet chart: analyst range (grey band) + model point (colored marker).
    Marker is amber if outside p25-p75 range, green if inside.
    """
    fig = go.Figure()
    segments = list(segment_display.keys())

    for i, seg in enumerate(segments):
        model_row = forecasts_df[(forecasts_df["year"] == year) & (forecasts_df["segment"] == seg)]
        anchor_row = anchors_df[(anchors_df["estimate_year"] == year) & (anchors_df["segment"] == seg)]

        if model_row.empty or anchor_row.empty:
            continue

        model_val = float(model_row["point_estimate_nominal"].iloc[0])
        p25 = float(anchor_row["p25_usd_billions_nominal"].iloc[0])
        p75 = float(anchor_row["p75_usd_billions_nominal"].iloc[0])
        median = float(anchor_row["median_usd_billions_nominal"].iloc[0])

        inside = p25 <= model_val <= p75
        marker_color = "#2ECC71" if inside else "#F39C12"

        # Grey consensus band
        fig.add_trace(go.Bar(
            x=[p75 - p25],
            y=[segment_display[seg]],
            base=[p25],
            orientation="h",
            marker_color="rgba(180,180,180,0.4)",
            showlegend=(i == 0),
            name="Analyst range (p25-p75)",
            hovertemplate=f"Consensus: ${p25:.0f}B–${p75:.0f}B<extra>{segment_display[seg]}</extra>",
        ))

        # Model marker
        divergence_pct = (model_val - median) / median * 100 if median > 0 else 0
        tooltip = f"Model: ${model_val:.0f}B vs Consensus: ${p25:.0f}B–${p75:.0f}B — divergence: {divergence_pct:+.1f}%"
        fig.add_trace(go.Scatter(
            x=[model_val],
            y=[segment_display[seg]],
            mode="markers",
            marker=dict(color=marker_color, size=14, symbol="diamond"),
            showlegend=(i == 0),
            name="Model estimate",
            hovertemplate=tooltip + "<extra></extra>",
        ))

    fig.update_layout(
        barmode="overlay",
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(title="USD Billions (Nominal)", gridcolor="#E8EBF0"),
        yaxis=dict(title=None),
        margin=dict(l=160, r=40, t=40, b=40),
        height=220,
    )
    return fig
```

**Note:** `market_anchors_ai.parquet` stores segment-level data, but the analyst registry (`ai_analyst_registry.yaml`) stores total-market estimates from 8 firms. The p25/p75 in the Parquet are computed percentiles across sources. For the consensus panel, use the Parquet directly — the per-segment p25/p75/median columns are ready.

**Divergence formula:**
```python
divergence_pct = (model_val - consensus_median) / consensus_median * 100
```

### Pattern 3: Alias Removal — Safe Coordinated Refactor

**What:** Remove the 5 alias columns from `app.py` startup, then update every reference in the same plan.

**Current alias block (lines 48-52 of `app.py`):**
```python
# DELETE these 5 lines:
FORECASTS_DF["usd_point"] = FORECASTS_DF["point_estimate_real_2020"]
FORECASTS_DF["usd_ci80_lower"] = FORECASTS_DF["ci80_lower"]
FORECASTS_DF["usd_ci80_upper"] = FORECASTS_DF["ci80_upper"]
FORECASTS_DF["usd_ci95_lower"] = FORECASTS_DF["ci95_lower"]
FORECASTS_DF["usd_ci95_upper"] = FORECASTS_DF["ci95_upper"]
```

**All callsites to update simultaneously:**

| File | Column replaced | New column |
|------|----------------|------------|
| `overview.py` lines 100-105 | `usd_point`, `usd_ci80_lower`, `usd_ci80_upper`, `usd_ci95_lower`, `usd_ci95_upper` | `point_estimate_real_2020`, `ci80_lower`, `ci80_upper`, `ci95_lower`, `ci95_upper` |
| `overview.py` line 323 (insights card) | `usd_point` | `point_estimate_real_2020` |
| `fan_chart.py` lines 66-77 | `usd_point`, `usd_ci80_lower/upper`, `usd_ci95_lower/upper` | direct column names |
| `segments.py` (any `usd_point` references) | `usd_point` | `point_estimate_real_2020` |

**Column name strategy (Claude's discretion):** Keep `point_estimate_real_2020` as-is. The name accurately describes what it is — no rename needed. The alias columns are the bloat; the underlying column name is correct.

### Pattern 4: Diagnostics Tab — Split Hard/Soft Panels

**What:** Replace the current "Needs actuals" scorecard with a two-panel layout driven by `backtesting_results.parquet`.

**Schema confirmed:**
```
backtesting_results.parquet columns:
  year, segment, actual_usd, predicted_usd, residual_usd, model,
  holdout_type, actual_type, mape, r2, mape_label, circular_flag
unique actual_type: ['hard', 'soft']
```

**Hard rows** (actual_type='hard', circular_flag=False): EDGAR actuals for NVIDIA and Palantir (confirmed by STATE.md: `DIRECT_DISCLOSURE_CIKS`). Palantir MAPE is real; ai_software hard MAPE is ~2134% (C3.ai alone vs full segment — expected, not a bug, as noted in STATE.md decisions).

**Soft rows** (actual_type='soft', circular_flag=True): analyst consensus used as pseudo-actuals. mape=0.0 because model was trained on these same values. Label: `circular_not_validated`.

**Layout:**
```python
# Two-column panel:
# LEFT (Hard validation):
#   "Validated (EDGAR actuals)"
#   MAPE + mape_label from hard rows
#   ai_hardware: ~14% MAPE [acceptable] — shown
#   ai_software: 2134% — shown with caveat text about single-company vs full-segment
# RIGHT (Cross-checked):
#   "Cross-checked (analyst consensus)"
#   Warning badge: circular_flag = True
#   "0% MAPE reflects model was trained on these estimates, not true out-of-sample"
```

**Backtest chart rewrite (`backtest.py`):** New function `make_backtest_chart(backtesting_df, segment)` — scatter plot of actual_usd (x) vs predicted_usd (y) for hard rows only. Diagonal y=x reference line. Each point colored by segment. Retain `make_backtest_chart` as the public function name so `diagnostics.py` callsite needs minimal change.

**New app.py load:**
```python
# Add to app.py startup (after RESIDUALS_DF load):
BACKTESTING_DF = pd.read_parquet(DATA_PROCESSED / "backtesting_results.parquet")
```

### Pattern 5: Vintage Footer Component

**What:** A shared function that renders a subtle footer string for any section. Use `data_vintage` column from `forecasts_ensemble.parquet` (confirmed value: `"2024-Q4"`) and the scope statement from `ai.yaml`.

```python
# Proposed shared helper (can live in styles.py or a new utils.py):
def vintage_footer(data_source: str, vintage: str, model_ver: str = "v1.1") -> html.P:
    """
    Render subtle footer: "Data: {source} {vintage} | Model: {model_ver} | Last updated: 2026-03-26"
    """
    from dash import html
    text = f"Data: {data_source} {vintage} | Model: {model_ver} | Last updated: 2026-03-26"
    return html.P(text, style={
        "fontSize": "11px", "color": "#AAAAAA", "marginTop": "6px",
        "marginBottom": "0", "textAlign": "right",
    })
```

**Placement guidance:**
- Fan charts: bottom-right of card, after `dcc.Graph`
- Segment bar: bottom-right of card
- KPI hero row: single footer below all three cards, not per-card
- Consensus panel: note source as "Analyst corpus (IDC, Gartner, Goldman, McKinsey, Grand View, Statista, Bloomberg, Morgan Stanley) | Latest vintage: 2025"
- Diagnostics: "EDGAR filings 2024 | Backtesting via walk-forward CV | Model: v1.1"

### Pattern 6: Additional Metrics on Basic Tier (Claude's Discretion)

**What:** Below the 3 heroes, show company growth rates and segment growth metrics.

**Data source:** `revenue_attribution_ai.parquet` provides `ai_revenue_usd_billions` + `uncertainty_low/high` for 15 companies for 2024. YoY growth rates must be computed from `forecasts_ensemble.parquet` year-over-year deltas (2023→2024).

**Display approach:** A compact horizontal row of 3-4 mini-metrics below the KPIs. No new Parquet required.

```python
# Compute from FORECASTS_DF at basic.py render time:
df_2023 = FORECASTS_DF[FORECASTS_DF["year"] == 2023]["point_estimate_nominal"].sum()
df_2024 = FORECASTS_DF[FORECASTS_DF["year"] == 2024]["point_estimate_nominal"].sum()
yoy_pct = (df_2024 - df_2023) / df_2023 * 100  # YoY market growth

# Top company from revenue_attribution_ai (already loaded at startup):
# NVIDIA $47.5B (2024), highest ai_revenue_usd_billions in the corpus
```

**Data centre construction growth:** Not available in current processed data. Use the CAGR from `forecasts_ensemble` for `ai_infrastructure` as the closest available proxy (infrastructure segment covers cloud + data centers). No fabrication needed — label it "AI Infrastructure CAGR" not "data centre construction" if infra-segment data is the source.

### Anti-Patterns to Avoid

- **Do not create a separate Dash app for the Basic tier.** The existing layout supports additional tabs. Use `dcc.Tab(label="Basic", value="basic")`.
- **Do not put the Basic tab at the end of the tab list.** It should be the FIRST tab (`value="basic"` as `main-tabs` default so it opens by default). Update `layout.py` to set `value="basic"` on the `dcc.Tabs` component.
- **Do not reference `usd_point` anywhere in the new `basic.py`.** Use `point_estimate_nominal` directly (Basic tier is nominal USD) or `point_estimate_real_2020` if needing real USD.
- **Do not present soft MAPE as a validation number.** The `circular_flag=True` rows have MAPE=0 by design. The UI must make this impossible to misread.
- **Do not strip context from hero KPIs.** Each must carry scope label, currency label, and uncertainty range even in Basic tier — PITFALLS.md Pitfall 8 documents the credibility cost of clean-but-misleading numbers.
- **Do not change `main-tabs` `value` to `"basic"` without also testing that existing callbacks for other tabs still fire** — Dash callbacks fire on any input change, so the `elif active_tab == "basic"` guard must come before the final `return build_overview_layout()` fallback.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| KPI card layout | Custom HTML `div` grid with pixel math | `dbc.Row` / `dbc.Col` with `dbc.Card` | Already used in `overview.py`; Bootstrap grid handles viewport resizing |
| Bullet chart | A new charting library | Plotly `go.Bar(orientation='h')` + `go.Scatter(mode='markers')` overlaid | Plotly is already installed; `barmode='overlay'` produces the bullet chart pattern natively |
| Confidence traffic-light | A custom CSS component | Inline `html.Span("●", style={"color": color})` | Simple and already established in the codebase style |
| Actual vs predicted chart | A custom scatter with regression line | Plotly `go.Scatter` with `mode='markers'` + `add_shape(type='line')` for y=x diagonal | Two traces, no new library |
| Vintage timestamp | Fetching from filesystem metadata | `data_vintage` column from `forecasts_ensemble.parquet` (confirmed: `"2024-Q4"` for all rows) | Already in the Parquet; no file stat needed |
| Analyst consensus range | Re-computing percentiles at runtime | `p25_usd_billions_nominal` + `p75_usd_billions_nominal` from `market_anchors_ai.parquet` | Already computed and stored |

**Key insight:** Every component needed for Phase 11 exists as either a Plotly primitive or a `dash-bootstrap-components` layout primitive. The work is wiring data to display, not building new components.

---

## Common Pitfalls

### Pitfall 1: Breaking the 8 Passing Dashboard Tests During Alias Removal

**What goes wrong:** The alias removal (deleting `usd_point` etc. from `app.py`) will break `test_tab_attribution_from_config` and any test that imports `overview.py` or `fan_chart.py` if those files still reference `usd_point`.

**Why it happens:** The alias removal touches `app.py`, `overview.py`, `fan_chart.py`, and `segments.py` — a cross-file refactor. Doing them in separate commits leaves the codebase in a broken state.

**How to avoid:** Do all alias-related edits in a single plan (11-03). After editing, run `pytest tests/test_dashboard.py -q` before committing. The test for `usd_point` aliases is implicit — if `overview.py` still contains the string `"usd_point"`, `test_tab_attribution_from_config` will catch the inconsistency via module import.

**Warning signs:** Any test error mentioning `KeyError: 'usd_point'` during tab rendering.

### Pitfall 2: Basic Tab Default Causing All Other Tests to Fail

**What goes wrong:** Setting `value="basic"` as the default on `dcc.Tabs` changes which tab is "active" at import time. If any test imports `app.py` and triggers a callback, it may now hit the `elif active_tab == "basic"` branch and call `build_basic_layout()` before that module exists.

**Why it happens:** Dash callback registration happens at import time; tests that import dashboard modules indirectly exercise the callback.

**How to avoid:** Add the `elif active_tab == "basic"` branch to `callbacks.py` before changing the default tab value in `layout.py`. The Basic tab module must exist and be importable before the tab is set as default.

### Pitfall 3: Consensus Panel With Missing Anchor Segments

**What goes wrong:** `market_anchors_ai.parquet` has 45 rows across 4 segments (ai_hardware, ai_infrastructure, ai_software, ai_adoption) and years 2017-2030 — but many of these rows are `estimated_flag=True` (bfill/ffill extrapolations). For the consensus display, using estimated/extrapolated anchors as "analyst consensus" is misleading.

**Why it happens:** The Parquet stores all years including those where no real analyst estimates exist for that segment. The `estimated_flag` column distinguishes real vs. extrapolated data.

**How to avoid:** Filter `anchors_df[anchors_df["estimated_flag"] == False]` when building the consensus panel. If no real estimate exists for the current year/segment combination, show "No consensus data" for that row rather than displaying an extrapolated range.

**Verified:** The `estimated_flag` column exists in `market_anchors_ai.parquet` (confirmed by schema inspection).

### Pitfall 4: Diagnostics Tab Loading `BACKTESTING_DF` Before It's Added to `app.py`

**What goes wrong:** `diagnostics.py` currently imports `DIAGNOSTICS` and `RESIDUALS_DF` from `app.py`. After the rewrite, it will need `BACKTESTING_DF`. If `app.py` hasn't been updated to load this Parquet and export it, the import fails at dashboard startup.

**Why it happens:** The refactor touches `app.py` (add load) and `diagnostics.py` (change what's imported) in the same plan (11-04). Order matters: `app.py` must be edited first.

**How to avoid:** In 11-04, edit `app.py` first (add `BACKTESTING_DF = pd.read_parquet(...)`), then edit `diagnostics.py` to import it. Test with `pytest tests/test_dashboard.py` to confirm the import works before proceeding.

### Pitfall 5: Expert Mode Card in Overview Still References "Raw Composite Index / PCA"

**What goes wrong:** `overview.py` lines 196-210 contain `fan_desc` mentioning "Y-axis shows the raw composite index (PCA first principal component..." and the expert card (`_build_expert_methodology_card`) references "PCA composite index", "PCA scores — negative values", "Ensemble Composition" mentioning PCA. These must all be removed/rewritten.

**Why it happens:** The expert card was written for v1.0 terminology and never fully updated in Phase 9.

**How to avoid:** In 11-03, grep for the strings "PCA", "composite index", "multiplier" in all dashboard files and remove each occurrence. Replace with v1.1 model description (anchor-calibrated USD model).

**Files to grep:**
- `overview.py`: "PCA", "composite index", "Raw composite index", "multiplier derivation"
- `fan_chart.py`: "Composite Index (PCA score)" in y_label assignment
- `segments.py`: any "PCA" or "index" references in _SEGMENT_DESCRIPTIONS or display text

### Pitfall 6: Non-Scrolling Basic Tier Breaking on Smaller Viewports

**What goes wrong:** The "single non-scrolling screen" requirement is set against a desktop browser at a standard resolution. If absolute heights are used in CSS, the layout overflows on laptops with smaller displays.

**Why it happens:** Fixed pixel heights (`height: "400px"`) for charts don't adapt to viewport.

**How to avoid:** Use percentage-based chart heights tied to viewport: `height: "calc(100vh - 320px)"` for the chart row, where 320px accounts for header + KPI row + footer. Test at 1280px and 1440px viewport widths. The REQUIREMENTS.md explicitly states "Desktop browser is the target audience; mobile-responsive design is out of scope."

---

## Code Examples

Verified patterns from official codebase inspection:

### Loading a New Parquet at `app.py` Startup
```python
# src/dashboard/app.py — add after existing RESIDUALS_DF load
BACKTESTING_DF = pd.read_parquet(DATA_PROCESSED / "backtesting_results.parquet")
ANCHORS_DF = pd.read_parquet(DATA_PROCESSED / "market_anchors_ai.parquet")
```

### Adding a New Tab in `layout.py`
```python
# src/dashboard/layout.py — add as FIRST entry in dcc.Tabs children list
dcc.Tab(
    label="Basic",
    value="basic",
    style={"padding": "10px 20px", "fontSize": "14px"},
    selected_style={"padding": "10px 20px", "fontSize": "14px", "fontWeight": 600, "borderTop": f"3px solid {COLOR_DEEP_BLUE}"},
),
# Also update dcc.Tabs value= attribute to "basic" so it opens by default
```

### Extending `callbacks.py` with Basic Tab Route
```python
# src/dashboard/callbacks.py — add BEFORE the final return
elif active_tab == "basic":
    return build_basic_layout(segment, mode)
```

### Nominal USD for Basic Tier Hero KPIs
```python
# src/dashboard/tabs/basic.py — use nominal column, not real_2020
from src.dashboard.app import FORECASTS_DF, ANCHORS_DF

df_2024 = FORECASTS_DF[FORECASTS_DF["year"] == 2024]
df_2023 = FORECASTS_DF[FORECASTS_DF["year"] == 2023]

total_2024_nominal = float(df_2024["point_estimate_nominal"].sum())  # current year nominal
yoy_growth = (total_2024_nominal / float(df_2023["point_estimate_nominal"].sum()) - 1) * 100

df_2030 = FORECASTS_DF[FORECASTS_DF["year"] == 2030]
total_2030_nominal = float(df_2030["point_estimate_nominal"].sum())
ci80_lo = float(df_2030["ci80_lower"].sum())  # Note: ci80 is in real_2020; need to check if nominal CIs exist
```

**Important CI note:** `forecasts_ensemble.parquet` has `ci80_lower`/`ci80_upper`/`ci95_lower`/`ci95_upper` but no `ci80_lower_nominal` etc. The CIs are in real 2020 USD. For uncertainty width display (confidence color traffic light), use the real-2020 CI columns — they correctly represent relative uncertainty. For the range text in the KPI card, you can either display real-2020 CIs with a "(real 2020 USD)" note, or compute approximate nominal CIs by scaling: `ci80_nominal_approx = ci80_lower * (total_2024_nominal / float(df_2024["point_estimate_real_2020"].sum()))`. Claude's discretion on which approach to use.

### Removing Alias Block (exact diff)
```python
# REMOVE these lines from app.py (currently lines 48-52):
- FORECASTS_DF["usd_point"] = FORECASTS_DF["point_estimate_real_2020"]
- FORECASTS_DF["usd_ci80_lower"] = FORECASTS_DF["ci80_lower"]
- FORECASTS_DF["usd_ci80_upper"] = FORECASTS_DF["ci80_upper"]
- FORECASTS_DF["usd_ci95_lower"] = FORECASTS_DF["ci95_lower"]
- FORECASTS_DF["usd_ci95_upper"] = FORECASTS_DF["ci95_upper"]
```

### Revenue Multiples Table (Static Data — No New Parquet)
```python
# Source: PitchBook Q4 2025 AI Public Comp Sheet and Valuation Guide
# https://pitchbook.com/news/reports/q4-2025-ai-public-comp-sheet-and-valuation-guide
# Vintage: Q4 2025

_REVENUE_MULTIPLES = [
    {"category": "AI Pure-Play", "ev_revenue": "~33x", "example": "Palantir, C3.ai, UiPath", "source": "PitchBook Q4 2025", "vintage": "2025-Q4"},
    {"category": "AI Semiconductors", "ev_revenue": "~15–25x", "example": "NVIDIA, AMD, Marvell", "source": "PitchBook Q4 2025", "vintage": "2025-Q4"},
    {"category": "Hyperscaler / Cloud", "ev_revenue": "~8–12x", "example": "Microsoft, Alphabet, Amazon", "source": "PitchBook Q4 2025", "vintage": "2025-Q4"},
    {"category": "AI Conglomerate", "ev_revenue": "~7x", "example": "IBM, Accenture, SAP", "source": "PitchBook Q4 2025", "vintage": "2025-Q4"},
]
```

### Diagnostics — Hard vs Soft Panel Split
```python
# src/dashboard/tabs/diagnostics.py — revised scorecard logic
from src.dashboard.app import BACKTESTING_DF

hard_df = BACKTESTING_DF[BACKTESTING_DF["actual_type"] == "hard"]
soft_df = BACKTESTING_DF[BACKTESTING_DF["circular_flag"] == True]

# Hard panel: show mape + mape_label per segment
# Caveat for ai_software: mape_label == 'directional_only' means C3.ai single-company vs full-segment
# Soft panel: show circular_not_validated warning prominently
```

### Vintage Footer — Data Vintage from Parquet Column
```python
# forecasts_ensemble.parquet "data_vintage" column = "2024-Q4" (confirmed for all rows)
data_vintage = FORECASTS_DF["data_vintage"].iloc[0]  # "2024-Q4"
# Display: "Data: EDGAR/Analyst Corpus 2024-Q4 | Model: v1.1"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `usd_point` alias computed via multiplier at app startup | `point_estimate_real_2020` IS USD billions directly, aliases are pass-throughs | Phase 9 (model rework) | Aliases are now dead weight — removing them simplifies all downstream code |
| Diagnostics tab: "Needs actuals" placeholder MAPE/R² | `backtesting_results.parquet` with hard/soft actual_type, MAPE, circular_flag | Phase 10 (backtesting) | Dashboard can now show real metrics; backtest chart can show actual vs predicted |
| Normal/Expert two-mode toggle | Same two modes remain; Basic tier added as a separate tab | Phase 11 | Basic tab is a new entry point; no mode toggle needed for Basic (it always shows the "Basic" view) |
| Residuals-only backtest chart | Actual vs predicted scatter (hard rows only) | Phase 11 (this phase) | Enables honest "did the model work?" visual |

**Deprecated/outdated strings to remove from dashboard:**
- "Raw Composite Index (PCA first principal component...)" — in `overview.py` expert fan chart description
- "PCA scores — negative values are valid" — in `overview.py` bar chart expert subtitle
- "PCA composite index as Y variable" — any reference in displayed UI text
- "Composite Index (PCA score)" — y-axis label in `fan_chart.py` when `usd_mode=False`

---

## Open Questions

1. **Fan chart for Basic tier: historical data only starts at 2023**
   - What we know: `forecasts_ensemble.parquet` has years 2023-2030 (all forecast, no historical). The `is_forecast` flag is presumably True for all rows. The fan chart in `fan_chart.py` splits on `is_forecast=False` for the "Historical" line.
   - What's unclear: Basic tier fan chart will show only forecast years (2023-2030) with no historical anchor line unless the anchors Parquet is joined in.
   - Recommendation: For the Basic tier fan chart, either (a) use `anchor_p25_real_2020`/`anchor_p75_real_2020` columns from `forecasts_ensemble.parquet` to draw an anchor band representing historical estimates, or (b) accept the all-forecast-only display with a note. Option (a) is more informative. Claude's discretion.

2. **Basic tier: mode toggle interaction**
   - What we know: `layout.py` has a Normal/Expert `mode-toggle`. The callback passes `mode` to all tab builders including the forthcoming `build_basic_layout`.
   - What's unclear: Should Basic tier respond to the mode toggle at all? The CONTEXT.md decisions say "No SHAP, no diagnostics, no methodology on Basic tier." If mode="expert" is set, Basic tier could either (a) ignore it and always show the Basic view, or (b) be inaccessible when Expert mode is active.
   - Recommendation: Simplest approach — `build_basic_layout` ignores the `mode` argument entirely. Basic is always Basic. Document this in the function docstring.

3. **`ai_analyst_registry.yaml` analyst count vs `market_anchors_ai.parquet`**
   - What we know: CONTEXT.md says "8 firms" for the analyst corpus. The registry YAML has entries from IDC, Gartner, McKinsey, Goldman Sachs, Grand View, Statista, Bloomberg, Morgan Stanley — which is exactly 8. The `market_anchors_ai.parquet` stores the aggregated p25/median/p75 (not individual firm estimates).
   - What's unclear: For Expert mode divergence rationale, individual firm estimates are needed. These are in the YAML, not the Parquet.
   - Recommendation: For the consensus panel tooltip (amber/red divergence), the Parquet p25/p75 is sufficient. For Expert mode "full rationale," a static text block listing the 8 firms is adequate — no need to re-parse the YAML at runtime.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (no separate pytest.ini) |
| Quick run command | `python3 -m pytest tests/test_dashboard.py -q` |
| Full suite command | `python3 -m pytest tests/test_dashboard.py tests/test_diagnostics.py tests/test_forecast_output.py tests/test_backtesting.py -q` |

**Note on test suite health:** Running the full test suite (`python3 -m pytest tests/ -q`) produces 6 collection errors (import failures in `test_revenue_attribution.py`, `test_serialization.py`, `test_validate.py` and others) that are pre-existing and unrelated to Phase 11. The 8 tests in `tests/test_dashboard.py` all pass cleanly.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | Basic tab renders without error | smoke | `pytest tests/test_dashboard.py::test_basic_tab_renders -q` | ❌ Wave 0 |
| DASH-01 | Basic tab has 3 KPI cards | unit | `pytest tests/test_dashboard.py::test_basic_kpi_cards -q` | ❌ Wave 0 |
| DASH-01 | Basic tab fan chart has forecast traces | unit | `pytest tests/test_dashboard.py::test_basic_fan_chart_traces -q` | ❌ Wave 0 |
| DASH-02 | Consensus panel renders for each segment | unit | `pytest tests/test_dashboard.py::test_consensus_panel_segments -q` | ❌ Wave 0 |
| DASH-02 | Consensus marker color amber when outside p25-p75 | unit | `pytest tests/test_dashboard.py::test_consensus_divergence_color -q` | ❌ Wave 0 |
| DASH-03 | Revenue multiples table present in Normal mode overview | unit | `pytest tests/test_dashboard.py::test_revenue_multiples_in_overview -q` | ❌ Wave 0 |
| DASH-04 | No `usd_point` column in FORECASTS_DF at startup | unit | `pytest tests/test_dashboard.py::test_no_alias_columns -q` | ❌ Wave 0 |
| DASH-04 | No PCA/composite index strings in Normal mode display | unit | `pytest tests/test_dashboard.py::test_no_pca_strings -q` | ❌ Wave 0 |
| DASH-04 | Diagnostics tab shows real MAPE from backtesting_results | unit | `pytest tests/test_dashboard.py::test_diagnostics_real_mape -q` | ❌ Wave 0 |
| DASH-05 | Each chart section contains a vintage footer | unit | `pytest tests/test_dashboard.py::test_vintage_footer_present -q` | ❌ Wave 0 |
| (regression) | Existing 8 dashboard tests still pass | regression | `pytest tests/test_dashboard.py -q` | ✅ Exists |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_dashboard.py -q`
- **Per wave merge:** `python3 -m pytest tests/test_dashboard.py tests/test_diagnostics.py tests/test_forecast_output.py tests/test_backtesting.py -q`
- **Phase gate:** Existing 8 tests pass + all Wave 0 tests pass before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_dashboard.py` — extend with Phase 11 test functions (add to existing file, don't create a new one)
  - `test_basic_tab_renders` — covers DASH-01
  - `test_basic_kpi_cards` — covers DASH-01
  - `test_basic_fan_chart_traces` — covers DASH-01
  - `test_consensus_panel_segments` — covers DASH-02
  - `test_consensus_divergence_color` — covers DASH-02
  - `test_revenue_multiples_in_overview` — covers DASH-03
  - `test_no_alias_columns` — covers DASH-04
  - `test_no_pca_strings` — covers DASH-04
  - `test_diagnostics_real_mape` — covers DASH-04
  - `test_vintage_footer_present` — covers DASH-05

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `src/dashboard/app.py`, `layout.py`, `callbacks.py`, `tabs/overview.py`, `tabs/diagnostics.py`, `tabs/segments.py`, `charts/fan_chart.py`, `charts/backtest.py` — full read 2026-03-26
- Direct Parquet schema inspection: `backtesting_results.parquet` (12 rows, 12 columns including `actual_type`, `circular_flag`, `mape_label`), `market_anchors_ai.parquet` (45 rows, confirmed `estimated_flag` column), `forecasts_ensemble.parquet` (32 rows, confirmed `point_estimate_nominal`, `data_vintage`, `anchor_p25/p75_real_2020`)
- `ai.yaml` config inspection: confirmed `source_attribution`, `market_boundary` scope statement, `value_chain_layer_taxonomy`
- `.planning/research/ARCHITECTURE.md` — Phase C dashboard build order, anti-pattern 4 (no separate Dash app)
- `.planning/research/PITFALLS.md` — Pitfall 8 (Basic tier context requirements)
- `.planning/research/FEATURES.md` — PitchBook Q4 2025 revenue multiples (33x pure-play, 7x conglomerate)
- `tests/test_dashboard.py` — 8 tests confirmed passing at 0.36s

### Secondary (MEDIUM confidence)
- PitchBook Q4 2025 AI Public Comp Sheet — revenue multiples data (~33x pure-play, ~7x conglomerate) as cited in FEATURES.md with official URL
- STATE.md Phase 10 decisions — `circular_flag=True` design decision, `DIRECT_DISCLOSURE_CIKS` for hard MAPE, `mape_label=circular_not_validated` intent

### Tertiary (LOW confidence)
None — all Phase 11 implementation details are verifiable from the codebase and data schema directly.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; all libraries confirmed installed in `pyproject.toml`
- Architecture: HIGH — full codebase inspection; all file paths confirmed; Parquet schemas verified at runtime
- Pitfalls: HIGH — grounded in actual code (alias removal risk), actual test results (8 passing, 6 collection errors), and actual data schema
- Data availability: HIGH — all 5 upstream Parquet files confirmed present with correct columns

**Research date:** 2026-03-26
**Valid until:** 2026-05-26 (stable codebase; Parquet schemas won't change unless pipeline re-runs modify them)
