# Phase 10: Revenue Attribution and Private Company Valuation - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Attribute AI revenue to 10-15 mixed-tech public companies using analyst consensus ratios, build a private company valuation registry for 15-20 major private AI companies using comparable multiples, run walk-forward backtesting (train pre-2022, evaluate 2022-2024) producing real MAPE and R², and ensure segment totals sum without double-counting via sub-segment ratio splits.

</domain>

<decisions>
## Implementation Decisions

### Attribution Methodology
- **Method:** Analyst consensus ratios — hand-curated per company from earnings calls, sell-side reports, company commentary
- **Per-company fields:** AI revenue estimate, attribution_method, ratio_source, uncertainty_low, uncertainty_high, vintage_date
- **Storage:** Separate YAML registry (like Phase 8 analyst corpus pattern), compiled to Parquet by pipeline
- **Pure-play companies:** Claude's discretion on whether to use pass-through with 100% ratio or skip attribution entirely — pick the cleanest pipeline approach
- **6 bundled companies** already flagged in EDGAR output: Microsoft, Amazon, Alphabet, Meta, Salesforce, IBM

### Private Company Registry
- **Valuation method:** Comparable multiples only (no DCF) — apply EV/Revenue multiples from similar public AI companies
- **Multiple range:** Each company gets low/mid/high valuation based on comparable public companies
- **Confidence tiers:** HIGH (recent funding round with known valuation), MEDIUM (revenue estimate from press + comparable multiple), LOW (revenue unknown, valuation inferred from funding)
- **Scope:** 15-20 major private AI companies (OpenAI, Anthropic, Databricks, xAI, Mistral, Cohere, Inflection, Scale AI, Hugging Face, etc.)
- **Storage:** YAML registry compiled to `private_valuations_ai.parquet`

### Backtesting Approach
- **Split:** Train on pre-2022 data, evaluate on 2022-2024
- **Actuals:** Both EDGAR filed revenue ('hard actuals', company-level, audited) AND published analyst estimates ('soft actuals', market-level). Both reported with explicit labels
- **Metrics:** MAPE and R² computed separately for hard vs soft actuals
- **Threshold:** Claude's discretion on whether to gate or just report — pick the approach that serves an analyst's best friend
- **Output:** `backtesting_results.parquet` feeding the Diagnostics tab

### Aggregation & Double-Counting
- **Multi-layer allocation:** Companies spanning multiple value chain layers get their AI revenue split by sub-segment ratios (e.g., Nvidia: 80% hardware, 20% cloud). Ratios stored in attribution YAML
- **Both totals:** Raw total (sum of segments, may double-count) AND adjusted total (overlap removed). Both shown in dashboard with explanation — consistent with Phase 8 overlap handling decision
- **Overlap zones:** Use the 3 overlap zones already documented in ai.yaml from Phase 8

### Claude's Discretion
- Pure-play pass-through vs skip (attribution pipeline design)
- MAPE threshold: gate vs report-only
- Which specific public AI companies to use as comparables for private company multiples
- How to handle private companies where no revenue estimate exists (funding-based inference)
- Exact sub-segment ratio values per multi-layer company
- Whether backtesting should use skforecast or custom walk-forward implementation

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/PROJECT.md` — Core value, v1.1 milestone goals
- `.planning/REQUIREMENTS.md` — MODL-02, MODL-03, MODL-06 requirements
- `.planning/ROADMAP.md` — Phase 10 success criteria (3 criteria that must be TRUE)

### Research findings
- `.planning/research/STACK.md` — edgartools for EDGAR, skforecast for backtesting, numpy-financial for DCF (not used — comparable multiples only)
- `.planning/research/FEATURES.md` — Revenue attribution methodology, private company valuation approach, backtesting benchmarks
- `.planning/research/PITFALLS.md` — Double-counting across value chain, private company multiple spread (3.6x-225x), backtesting against analyst consensus ≠ real backtesting
- `.planning/research/ARCHITECTURE.md` — revenue_attribution.py and dcf_valuation.py as new processing modules, backtesting_results.parquet schema

### Phase 8 outputs (data foundation)
- `config/industries/ai.yaml` — EDGAR companies with value_chain_layer, scope mapping, overlap zones
- `src/ingestion/edgar.py` — EDGAR XBRL extraction with bundled_flag for 6 companies
- `data/processed/market_anchors_ai.parquet` — Ground truth time series
- `data/raw/market_anchors/ai_analyst_registry.yaml` — Analyst estimate corpus (pattern for new YAML registries)

### Phase 9 outputs (model rework)
- `src/inference/forecast.py` — Forecast pipeline outputting USD billions
- `data/processed/forecasts_ensemble.parquet` — USD forecasts (min 3.7B, max 405B)
- `src/models/ensemble.py` — compute_source_disagreement_columns for two-layer uncertainty
- `.planning/phases/09-ground-up-model-rework-and-value-chain-design/09-CONTEXT.md` — Model target decisions

### Prior phase context
- `.planning/phases/08-data-architecture-and-ground-truth-assembly/08-CONTEXT.md` — Market boundary, overlap handling, reconciliation decisions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ingestion/edgar.py` — EDGAR module with `bundled_flag` already set for 6 companies; `fetch_all_edgar_companies` returns DataFrame with company filings
- `src/ingestion/market_anchors.py` — YAML-to-Parquet compilation pattern; reuse for attribution and private company registries
- `src/processing/validate.py` — pandera schema validation pattern; extend with ATTRIBUTION_SCHEMA and PRIVATE_VALUATION_SCHEMA
- `src/diagnostics/model_eval.py` — Has `compute_mape` and `compute_r2` already implemented but never called with real actuals
- `data/raw/market_anchors/ai_analyst_registry.yaml` — YAML registry pattern to follow for attribution and private company data

### Established Patterns
- YAML registry → pipeline compilation → pandera validation → Parquet output
- Config-driven from ai.yaml (segments, companies, value chain layers)
- Per-segment model loop for backtesting (iterate segments, compute metrics)

### Integration Points
- `src/ingestion/edgar.py` output → `revenue_attribution.py` input (bundled companies)
- Attribution output → segment totals → model retraining loop (optional)
- `backtesting_results.parquet` → Diagnostics tab (Phase 11)
- `private_valuations_ai.parquet` → total market size calculation
- `src/ingestion/pipeline.py` — Wire new attribution and backtesting steps

</code_context>

<specifics>
## Specific Ideas

- Sub-segment ratio splits for multi-layer companies make the aggregation more defensible than the Phase 8 "allow overlap" approach — this is a refinement
- Confidence tiers on private companies (HIGH/MEDIUM/LOW) give the Basic dashboard a way to visually indicate certainty without overwhelming users
- Hard vs soft actual labels in backtesting is unique — commercial tools don't distinguish between audited and unaudited ground truth

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-revenue-attribution-and-private-company-valuation*
*Context gathered: 2026-03-24*
