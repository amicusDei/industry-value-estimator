# Phase 11: Dashboard and Diagnostics - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the Basic dashboard tier (new tab), add analyst consensus panel and revenue multiples table, update Normal/Expert modes to show real USD (removing all pass-through aliases and composite index references), update Diagnostics tab with real backtesting metrics, and add vintage/scope labels throughout. This is the final phase of v1.1.

</domain>

<decisions>
## Implementation Decisions

### Basic Tier Layout
- **3 hero KPIs:** (1) Total AI market size (current year, nominal USD), (2) YoY growth rate (%), (3) 2030 forecast (nominal USD). Each with scope label and uncertainty range
- **Additional metrics below heroes:** Market growth rates, individual company growth, data centre construction growth rates
- **Charts:** Segment breakdown chart + growth fan chart on the same screen
- **Single non-scrolling screen** — all key information visible without scrolling
- **Currency:** Nominal USD for Basic tier (what analysts publish, more recognizable). Real 2020 USD stays in Normal/Expert
- **Uncertainty display:** Color-coded confidence indicators (green/yellow/red) next to each KPI based on how tight the uncertainty range is. Thresholds defined by Claude's discretion
- **No SHAP, no diagnostics, no methodology** on Basic tier — those live in Normal/Expert

### Analyst Consensus Panel
- **Display format:** Bullet chart — horizontal bar showing analyst range (min-max) as grey band, model estimate as colored marker. Instantly shows inside/outside consensus
- **Placement:** Both Basic and Normal tiers
- **Divergence highlighting:** Color + tooltip — marker turns amber/red when outside consensus range. Tooltip shows "Model: $X vs Consensus: $Y-$Z — divergence: +N%". Full documented rationale available in Expert mode
- **Data source:** `market_anchors_ai.parquet` analyst corpus (8 firms, scope-normalized estimates)

### Normal/Expert Cleanup
- **Revenue multiples table:** Normal mode Overview tab — context panel alongside market size summary. Shows AI pure-play (~33x), semiconductor, conglomerate (~7x) EV/Revenue multiples with source attribution and vintage date
- **Pass-through alias removal:** Delete all `usd_point`, `usd_ci80_lower` etc. aliases from `app.py`. All tabs reference `point_estimate_real_2020` directly (or renamed column if Phase 9 changed it)
- **Composite index references:** Remove any remaining references to composite index, PCA scores, or multiplier derivation from the UI
- **Diagnostics tab:** Split panels for Hard vs Soft backtesting results. Left panel: "Validated (EDGAR actuals)" with NVIDIA/Palantir MAPE. Right panel: "Cross-checked (analyst consensus)" with circular_flag warning. Uses `backtesting_results.parquet`
- **MAPE/R² labels:** Explicit [in-sample] / [out-of-sample] labels on all diagnostic metrics

### Vintage & Scope Labels
- **Prominence:** Subtle footer per section — small text below each chart/table: "Data: EDGAR Q4 2024 | Model: v1.1 | Last updated: 2026-03-26"
- **Present but not cluttering** — doesn't compete with actual data
- **Every data point has context** — no number without vintage date and scope label
- **Source attribution:** Per data source (World Bank, OECD, LSEG, EDGAR, analyst corpus) with individual vintage dates

### Claude's Discretion
- Exact color thresholds for confidence indicators (green/yellow/red)
- Column name strategy (keep `point_estimate_real_2020` or rename during alias cleanup)
- Exact layout positioning of consensus bullet chart within Basic tab
- How to source/display data centre construction and company growth rates on Basic tier
- Revenue multiples table data (specific companies, multiples, dates)
- Vintage footer exact format and placement per tab

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/PROJECT.md` — Core value, v1.1 goals, three-tier dashboard requirement
- `.planning/REQUIREMENTS.md` — DASH-01 through DASH-05 requirements
- `.planning/ROADMAP.md` — Phase 11 success criteria (5 criteria)

### Research findings
- `.planning/research/FEATURES.md` — Basic dashboard design: Z-pattern, 3-5 KPIs max, PitchBook as reference
- `.planning/research/ARCHITECTURE.md` — Basic tier needs zero new libraries, dcc.Store for tier state
- `.planning/research/PITFALLS.md` — Basic dashboard UX pitfalls, context requirements

### Upstream data (Phases 8-10)
- `data/processed/market_anchors_ai.parquet` — Ground truth (p25/median/p75, nominal + real 2020 USD)
- `data/processed/forecasts_ensemble.parquet` — USD forecasts with CIs
- `data/processed/revenue_attribution_ai.parquet` — 15 companies with attribution + uncertainty
- `data/processed/private_valuations_ai.parquet` — 18 companies with comparable multiples
- `data/processed/backtesting_results.parquet` — Hard/soft MAPE/R² with actual_type labels
- `data/raw/market_anchors/ai_analyst_registry.yaml` — 54 analyst estimates (consensus source)
- `config/industries/ai.yaml` — Segments, scope mapping, vintage metadata

### Existing dashboard code (to be modified)
- `src/dashboard/app.py` — Pass-through aliases to remove, tier toggle to add
- `src/dashboard/layout.py` — Add Basic tab, modify tier toggle
- `src/dashboard/callbacks.py` — Add Basic tier callbacks
- `src/dashboard/tabs/overview.py` — Add consensus panel + multiples table to Normal mode
- `src/dashboard/tabs/diagnostics.py` — Replace placeholder metrics with real backtesting
- `src/dashboard/tabs/segments.py` — Update for real USD
- `src/dashboard/tabs/drivers.py` — Update SHAP for real USD
- `src/dashboard/charts/fan_chart.py` — Remove alias references

### Prior phase context
- `.planning/phases/09-ground-up-model-rework-and-value-chain-design/09-CONTEXT.md` — Minimal dashboard fix, pass-through aliases, column naming decisions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/dashboard/tabs/overview.py` — Existing Overview tab with Normal/Expert mode toggle. Add consensus panel and multiples table here
- `src/dashboard/charts/fan_chart.py` — Fan chart component already handles CI bands. Reuse for Basic tier growth chart
- `src/dashboard/charts/styles.py` — Shared chart styles. Extend with Basic tier color scheme
- `src/dashboard/layout.py` — Tab layout with dcc.Tabs. Add Basic as first tab
- `src/dashboard/callbacks.py` — Callback routing. Extend with Basic tier callbacks
- `dash-bootstrap-components` — Already installed, use for KPI cards and layout grid

### Established Patterns
- Tab layout builders are pure functions: `(segment, usd_col) → html.Div` — stateless, uniform callback dispatch
- Normal/Expert toggle via `dcc.Store` — extend with Basic/Normal/Expert three-way toggle
- `FORECASTS_DF` loaded at module startup in `app.py` — Basic tier reads the same DataFrame

### Integration Points
- `app.py` FORECASTS_DF → all tabs consume this (including new Basic tab)
- `backtesting_results.parquet` → Diagnostics tab (new data source)
- `market_anchors_ai.parquet` → Consensus panel (analyst estimate range)
- `revenue_attribution_ai.parquet` → Overview tab (company growth context)
- `private_valuations_ai.parquet` → Overview tab (optional context in Normal mode)

</code_context>

<specifics>
## Specific Ideas

- Basic tier should feel like opening Bloomberg or PitchBook — immediate market intelligence, not a research tool
- Color-coded confidence (green/yellow/red) gives a traffic-light feel that even non-analysts understand
- Bullet chart for consensus is compact and immediately shows "are we in the range?" without reading numbers
- Split Hard/Soft panels in Diagnostics makes the distinction impossible to miss — most tools hide their validation methodology

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-dashboard-and-diagnostics*
*Context gathered: 2026-03-26*
