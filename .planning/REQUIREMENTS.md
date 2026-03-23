# Requirements: Industry Value Estimator

**Defined:** 2026-03-23
**Core Value:** Be an analyst's best friend: produce AI industry valuations and growth forecasts grounded in real market data that people can actually trust and act on.

## v1.1 Requirements

Requirements for Model Credibility & Usability milestone. Each maps to roadmap phases.

### Data Foundation

- [ ] **DATA-08**: Market boundary definition locked — explicit scope definition (e.g., "AI software + services + infrastructure, ex-general IT") with documented mapping to how IDC, Gartner, and Grand View define their estimates
- [ ] **DATA-09**: Published analyst estimate corpus assembled — 10+ estimates per segment with vintage date, source firm, scope definition, and methodology notes
- [ ] **DATA-10**: Company filings ingestion via SEC EDGAR — 10-K/10-Q segment disclosures for 10-15 key public AI companies (Nvidia, Microsoft, Google, Amazon, Meta, etc.)
- [ ] **DATA-11**: Historical ground truth time series assembled — yearly AI market size by segment (2017-2025) reconciled across sources into a single defensible series

### Model & Valuation

- [ ] **MODL-01**: Anchored market size model replaces PCA composite — ARIMA/Prophet/LightGBM retrained with real USD market sizes as target variable instead of composite index
- [ ] **MODL-02**: AI revenue attribution for 10-15 mixed-tech public companies — parameterized attribution ratios from earnings disclosures + analyst consensus, with documented uncertainty per company
- [ ] **MODL-03**: Private company valuation registry — 15-20 major private AI companies (OpenAI, Anthropic, Databricks, etc.) valued via comparable multiples with confidence flags and explicit uncertainty ranges
- [ ] **MODL-04**: Value chain layer taxonomy — chip/cloud/application/end-market classification assigned per company preventing double-counting when aggregating to total market size
- [ ] **MODL-05**: Forecast trajectories reflect realistic AI growth (25-40% CAGR consistent with analyst consensus) with documented rationale where model diverges from consensus
- [ ] **MODL-06**: Walk-forward backtesting — train on pre-2022 data, evaluate 2022-2024 against filed actuals, producing real MAPE and R² in Diagnostics tab

### Dashboard & UX

- [ ] **DASH-01**: Basic dashboard tier — 3 hero numbers (total AI market size, YoY growth rate, 2030 forecast), segment breakdown chart, growth fan chart on a single non-scrolling screen
- [ ] **DASH-02**: Analyst consensus panel — model output vs published estimate range displayed side-by-side in Basic and Normal tiers
- [ ] **DASH-03**: Revenue multiples reference table — EV/Revenue multiples for AI pure-plays (~33x), semiconductors, and conglomerates (~7x) with source attribution
- [ ] **DASH-04**: Normal/Expert modes updated — real USD figures replace composite indices, recalibrated narrative text, all existing tabs functional with new model outputs
- [ ] **DASH-05**: Data vintage and methodology transparency — per-source, per-segment "last updated" timestamp and scope label displayed in UI

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Scenario Analysis

- **SCEN-01**: User can adjust key assumptions (attribution ratios, growth rates, discount rates) via interactive sliders and see forecast impact in real time

### Extended Coverage

- **PRIV-01**: Expanded private company coverage (50+ companies) beyond initial 15-20 registry
- **SUBSEC-01**: Sub-sector breakdown (NLP, computer vision, generative AI) as separate model segments — only if reliable public data sources exist

### Automation

- **AUTO-01**: Automated earnings call transcript ingestion via LLM for revenue attribution updates

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multiple industries beyond AI | Expand after AI model is proven; ARCH-01 extensibility already built |
| Real-time streaming data | Batch processing sufficient; quarterly refresh cycle matches data availability |
| Mobile-responsive design | Desktop browser is the target audience |
| User authentication / multi-user | Personal/portfolio tool |
| Single "true" market number without uncertainty | Intellectually dishonest — scope definition creates 7x spread; must show uncertainty |
| Automated LLM-based earnings parsing | Engineering complexity + hallucination risk; hand-curated attribution more credible for v1.1 |
| Live private company valuation from funding feeds | Discontinuous events, requires paid APIs (Crunchbase Pro), false precision |
| Raw data download via dashboard | LSEG data is subscription-only; would violate licensing |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-08 | — | Pending |
| DATA-09 | — | Pending |
| DATA-10 | — | Pending |
| DATA-11 | — | Pending |
| MODL-01 | — | Pending |
| MODL-02 | — | Pending |
| MODL-03 | — | Pending |
| MODL-04 | — | Pending |
| MODL-05 | — | Pending |
| MODL-06 | — | Pending |
| DASH-01 | — | Pending |
| DASH-02 | — | Pending |
| DASH-03 | — | Pending |
| DASH-04 | — | Pending |
| DASH-05 | — | Pending |

**Coverage:**
- v1.1 requirements: 15 total
- Mapped to phases: 0
- Unmapped: 15 ⚠️

---
*Requirements defined: 2026-03-23*
*Last updated: 2026-03-23 after initial definition*
