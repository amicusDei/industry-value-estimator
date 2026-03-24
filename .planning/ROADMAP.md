# Roadmap: Industry Value Estimator

## Milestones

- ✅ **v1.0 MVP** — Phases 1-7 (shipped 2026-03-23) — [Archive](milestones/v1.0-ROADMAP.md)
- 🚧 **v1.1 Model Credibility & Usability** — Phases 8-11 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-7) — SHIPPED 2026-03-23</summary>

- [x] Phase 1: Data Foundation (5/5 plans) — completed 2026-03-18
- [x] Phase 2: Statistical Baseline (5/5 plans) — completed 2026-03-22
- [x] Phase 3: ML Ensemble and Validation (3/3 plans) — completed 2026-03-22
- [x] Phase 4: Interactive Dashboard (3/3 plans) — completed 2026-03-22
- [x] Phase 5: Reports, Paper, and Portfolio (4/4 plans) — completed 2026-03-23
- [x] Phase 6: Pipeline Integration Wiring (2/2 plans) — completed 2026-03-23
- [x] Phase 7: Dashboard Attribution Polish (0/0 plans, quick task) — completed 2026-03-23

</details>

### 🚧 v1.1 Model Credibility & Usability (In Progress)

**Milestone Goal:** Rework the model from ground up to produce trustworthy, real-world AI valuations anchored on actual market data — and add a Basic dashboard tier that makes output immediately useful to any analyst.

**Build order rationale:** Data foundation before model (no anchor = no credible output), value chain taxonomy before attribution (taxonomy retrofitting is HIGH recovery cost), attribution before backtesting (segment MAPE requires segment actuals), backtesting before dashboard (Basic tier must show validated numbers, not placeholders).

#### Phase 8: Data Architecture and Ground Truth Assembly

**Goal**: A locked, defensible historical AI market size series exists — with a documented boundary definition chosen before any model output is seen
**Depends on**: Phase 7 (v1.0 complete)
**Requirements**: DATA-08, DATA-09, DATA-10, DATA-11
**Success Criteria** (what must be TRUE):
  1. The market boundary definition (scope: AI software + services + infrastructure, ex-general IT) is locked in `config/industries/ai.yaml` with a documented mapping to how IDC, Gartner, and Grand View each define their estimates — written before any model run
  2. A corpus of 10+ published analyst estimates per segment exists in `market_anchors_ai.parquet` with vintage date, source firm, scope definition, and methodology notes per row
  3. 10-K/10-Q segment disclosures for 10-15 key public AI companies are ingested via SEC EDGAR and stored in a validated Parquet file
  4. A single defensible historical AI market size time series (2017-2025, by segment) exists reconciled across sources, with documented reconciliation decisions and a clear audit trail explaining why each source was accepted or discarded
**Plans**: 4 plans

Plans:
- [ ] 08-01-PLAN.md — Lock market boundary definition, scope mapping table, and EDGAR company list in ai.yaml + METHODOLOGY.md
- [ ] 08-02-PLAN.md — Create analyst estimate YAML registry (40+ entries) and market_anchors.py ingestion module
- [ ] 08-03-PLAN.md — Build EDGAR XBRL extraction module (edgartools) for 13+ AI companies
- [ ] 08-04-PLAN.md — Reconcile ground truth time series with deflation, interpolation, and pipeline integration

#### Phase 9: Ground-Up Model Rework and Value Chain Design

**Goal**: The model forecasts real USD AI market size, the PCA composite multiplier path is deleted, and the value chain layer taxonomy is locked in config before any attribution data is populated
**Depends on**: Phase 8
**Requirements**: MODL-01, MODL-04, MODL-05
**Success Criteria** (what must be TRUE):
  1. Every company in the system is assigned exactly one value chain layer (chip / cloud / application / end-market) in `ai.yaml` before any attribution percentage is written — preventing double-counting at aggregate level
  2. ARIMA, Prophet, and LightGBM are retrained with real USD billions as the Y variable; the value chain multiplier block is deleted from `inference/forecast.py` (not bridged or gated — deleted); a contract test asserts that `point_estimate_real_2020` in `forecasts_ensemble.parquet` is in USD billions
  3. Forecast trajectories are in the 25-40% CAGR range consistent with analyst consensus; the methodology documents where and why the model diverges from consensus, with explicit rationale
**Plans**: 3 plans

Plans:
- [ ] 09-01-PLAN.md — Lock value chain taxonomy in ai.yaml, rebuild features.py as flat feature builder, create contract test scaffolds
- [ ] 09-02-PLAN.md — Retrain ARIMA and Prophet on USD market anchors with two-layer uncertainty
- [ ] 09-03-PLAN.md — Retrain LightGBM, delete multiplier code, produce USD forecasts_ensemble.parquet, verify CAGR

#### Phase 10: Revenue Attribution and Private Company Valuation

**Goal**: Every mixed-tech public company has an attributed AI revenue figure with source and uncertainty range; every major private AI company has a valuation with explicit uncertainty; segment totals sum without double-counting
**Depends on**: Phase 9 (value chain taxonomy must exist before attribution)
**Requirements**: MODL-02, MODL-03, MODL-06
**Success Criteria** (what must be TRUE):
  1. `revenue_attribution.py` produces AI revenue figures for 10-15 mixed-tech public companies (Microsoft, Alphabet, Amazon, Meta, Salesforce, IBM, etc.); every output row carries `attribution_method`, `ratio_source`, `uncertainty_low`, `uncertainty_high`, and `vintage_date` — no company has a point estimate without bounds
  2. A private company registry covers 15-20 major private AI companies (OpenAI, Anthropic, Databricks, xAI, Mistral, etc.) with DCF and comparable-multiple valuations, explicit uncertainty bands, and vintage dates stored per company in `private_valuations_ai.parquet`
  3. Walk-forward backtesting runs on pre-2022 training data and evaluates 2022-2024 against filed company revenue actuals; real MAPE and R² values appear in `backtesting_results.parquet` — labeled explicitly as hard (filed actuals) vs. soft (analyst consensus) validation
**Plans**: 4 plans

Plans:
- [ ] 10-01-PLAN.md — Pandera schemas, ai.yaml subsegment ratios, stub YAML registries, and test scaffolds (Wave 0)
- [ ] 10-02-PLAN.md — Public company AI revenue attribution (14 companies) with revenue_attribution.py and pipeline wiring
- [ ] 10-03-PLAN.md — Private company valuation registry (18 companies) with private_valuations.py and pipeline wiring
- [ ] 10-04-PLAN.md — Walk-forward backtesting with hard/soft actuals, MAPE/R2, and pipeline wiring

#### Phase 11: Dashboard and Diagnostics

**Goal**: The dashboard shows validated, real USD numbers across all three tiers; the Basic tier gives any analyst immediate market intelligence without requiring expertise to interpret
**Depends on**: Phase 10 (dashboard must display validated model outputs, not placeholders)
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):
  1. A Basic dashboard tab exists on a single non-scrolling screen with 3 hero KPIs (total AI market size, YoY growth rate, 2030 forecast) — each carrying a scope label, vintage date, and uncertainty range — plus a segment breakdown chart and growth fan chart; no number is presented without context
  2. An analyst consensus panel appears in Basic and Normal tiers showing model output alongside the published estimate range, making it immediately visible whether the model is inside or outside analyst consensus
  3. A revenue multiples reference table exists showing EV/Revenue multiples for AI pure-plays (~33x), semiconductors, and conglomerates (~7x) with source attribution and vintage date
  4. Normal and Expert modes display real USD figures throughout; all composite index references and multiplier derivation blocks are removed from the UI; the Diagnostics tab shows real out-of-sample MAPE and R² with explicit [in-sample] / [out-of-sample] labels
  5. Every data source and segment in the UI carries a per-source, per-segment "last updated" timestamp and scope label — no data point is presented without vintage date
**Plans**: TBD

Plans:
- [ ] 11-01: Basic dashboard tier (basic.py, KPI cards, fan chart)
- [ ] 11-02: Analyst consensus panel and revenue multiples table
- [ ] 11-03: Normal/Expert mode updates and multiplier block removal
- [ ] 11-04: Data vintage display and diagnostics tab real metrics

## Progress

**Execution Order:**
Phases execute in numeric order: 8 → 9 → 10 → 11

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Foundation | v1.0 | 5/5 | Complete | 2026-03-18 |
| 2. Statistical Baseline | v1.0 | 5/5 | Complete | 2026-03-22 |
| 3. ML Ensemble and Validation | v1.0 | 3/3 | Complete | 2026-03-22 |
| 4. Interactive Dashboard | v1.0 | 3/3 | Complete | 2026-03-22 |
| 5. Reports, Paper, and Portfolio | v1.0 | 4/4 | Complete | 2026-03-23 |
| 6. Pipeline Integration Wiring | v1.0 | 2/2 | Complete | 2026-03-23 |
| 7. Dashboard Attribution Polish | v1.0 | 0/0 | Complete | 2026-03-23 |
| 8. Data Architecture and Ground Truth Assembly | 4/4 | Complete   | 2026-03-24 | - |
| 9. Ground-Up Model Rework and Value Chain Design | 3/3 | Complete   | 2026-03-24 | - |
| 10. Revenue Attribution and Private Company Valuation | 3/4 | In Progress|  | - |
| 11. Dashboard and Diagnostics | v1.1 | 0/4 | Not started | - |
