---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Model Credibility & Usability
status: planning
stopped_at: Completed 10-05-PLAN.md
last_updated: "2026-03-24T20:53:23.920Z"
last_activity: 2026-03-23 — v1.1 roadmap created (Phases 8-11)
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 12
  completed_plans: 12
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-23)

**Core value:** Be an analyst's best friend: produce AI industry valuations and growth forecasts grounded in real market data that people can actually trust and act on.
**Current focus:** Phase 8 — Data Architecture and Ground Truth Assembly

## Current Position

Phase: 8 of 11 (Data Architecture and Ground Truth Assembly)
Plan: — (not started)
Status: Ready to plan
Last activity: 2026-03-23 — v1.1 roadmap created (Phases 8-11)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity (v1.0 history):**
- Total plans completed: 22
- Average duration: ~12 min
- Total execution time: ~4.4 hours

**By Phase (v1.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-data-foundation | 5 | 59 min | 12 min |
| 02-statistical-baseline | 5 | 33 min | 7 min |
| 03-ml-ensemble-and-validation | 3 | 8 min | 3 min |
| 04-interactive-dashboard | 3 | 94 min | 31 min |
| 05-reports-paper-and-portfolio | 4 | 85 min | 21 min |
| 06-pipeline-integration-wiring | 2 | 11 min | 6 min |

*Updated after each plan completion*
| Phase 08 P01 | 15 | 2 tasks | 3 files |
| Phase 08 P02 | 20 | 1 tasks | 4 files |
| Phase 08 P03 | 6 | 1 tasks | 5 files |
| Phase 08 P04 | 25 | 2 tasks | 5 files |
| Phase 09 P01 | 219 | 2 tasks | 5 files |
| Phase 09 P02 | 420 | 2 tasks | 4 files |
| Phase 09 P03 | 1200 | 3 tasks | 10 files |
| Phase 10 P01 | 198 | 2 tasks | 8 files |
| Phase 10 P02 | 6 | 2 tasks | 5 files |
| Phase 10 P03 | 325 | 2 tasks | 6 files |
| Phase 10 P04 | 5 | 2 tasks | 6 files |
| Phase 10-revenue-attribution-and-private-company-valuation P05 | 60 | 2 tasks | 6 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap v1.1]: Build order locked as data → model → attribution/valuation → backtesting → dashboard; nothing downstream starts until Phase 8 Parquet files exist
- [Roadmap v1.1]: Value chain layer taxonomy (MODL-04) placed in Phase 9 and must be designed before any attribution percentages are written — retrofitting is HIGH recovery cost
- [Roadmap v1.1]: PCA composite + value chain multiplier is deleted (not gated) in Phase 9; schema continuity preserved via column name, not value type
- [Roadmap v1.1]: Private company valuation (MODL-03) merged into Phase 10 with attribution — both are data enrichment that backtesting depends on; keeping them separate would create a false gate
- [Roadmap v1.1]: Walk-forward backtesting (MODL-06) placed in Phase 10 (not Phase 11) — backtesting is a data product that the dashboard consumes, not a dashboard feature
- [Roadmap v1.1]: Basic dashboard tier built last (Phase 11) — must show validated numbers; building against placeholder model output risks full rework
- [Phase 08]: Market boundary locked 2026-03-23 before data collection — prevents anchor estimate shopping
- [Phase 08]: IDC chosen as closest_analyst_match at scope_coefficient 1.0; Gartner 0.18x; McKinsey 0.25x (economic value not market size)
- [Phase 08]: 14 EDGAR companies across 4 layers (4 hardware, 4 infrastructure, 4 software, 3 adoption) with disclosure type annotations
- [Phase 08]: MARKET_ANCHOR_SCHEMA estimate_year range extended to 2035 to accommodate long-horizon forecast entries (2030, 2032) in the analyst registry
- [Phase 08]: estimated_flag = estimate_year > publication_year distinguishes actuals from forecasts for Plan 08-04 reconciliation weighting
- [Phase 08]: uv override-dependencies used to resolve edgartools vs pandasdmx/lseg-data pydantic/httpx conflicts — both libraries verified to work at runtime despite declared constraints
- [Phase 08]: BUNDLED_SEGMENT_COMPANIES set (6 CIKs) marks companies requiring Phase 10 AI revenue attribution — Microsoft, Amazon, Alphabet, Meta, IBM, Accenture
- [Phase 08]: Raw World Bank parquet used as deflator source (not processed) to get full 2010-2024 deflator coverage for market anchor deflation
- [Phase 08]: MARKET_ANCHOR_NOMINAL_SCHEMA added alongside MARKET_ANCHOR_SCHEMA to preserve backward compatibility with compile_market_anchors() callers
- [Phase 08]: Sub-segments with 2023-2024 data only use bfill/ffill for 2017-2022 extrapolation with estimated_flag=True marking
- [Phase 09]: value_chain_layer_taxonomy locked 2026-03-24 with 4 layers (chip/cloud/application/end_market) in ai.yaml — gates Phase 10 attribution
- [Phase 09]: build_pca_composite deleted from features.py — flat indicator matrix replaces PCA path in v1.1 model
- [Phase 09]: model_version: v1.1_real_data set in ai.yaml — will be used as interface gate in Plan 09-02
- [Phase 09]: market_anchors_ai.parquet column names are median_usd_billions_real_2020 (not median_real_2020) — all USD loaders use actual column names
- [Phase 09]: fit_prophet_from_anchors gracefully omits 2022 changepoint when outside training data range — prevents Prophet ValueError on sparse real-observation segments
- [Phase 09]: MACRO_FEATURE_COLS defined but fall back to residual-only features when world_bank_ai.parquet coverage < 80% in 2017-2025
- [Phase 09]: CAGR divergence documented in forecast.py: root cause is 2-obs training window per segment; 25-40% target deferred to Phase 10 data enrichment
- [Phase 09]: Forecast floor at max(last_y * 0.5, 1.5B) prevents negative USD forecasts from sparse-data Prophet extrapolation (ai_adoption 2023>2024 declining anchor)
- [Phase 10]: BUNDLED_SEGMENT_COMPANIES now 7 companies: both Accenture (AI consulting) and Salesforce (Einstein/Agentforce) included in Phase 10 attribution
- [Phase 10]: attribution_subsegment_ratios in ai.yaml: cloud hyperscalers 90/10 infra/sw split; NVIDIA 80/20 chip/infra; Meta 85/15 adoption/sw
- [Phase 10]: Registry has 15 companies not 14: ai.yaml edgar_companies has 15 CIKs (4 chip + 4 cloud including Oracle + 4 software + 3 adoption)
- [Phase 10]: Private company valuation registry: 18 companies (6 HIGH/7 MEDIUM/5 LOW) with comparable EV/ARR multiples; implied_ev ordering invariant enforced programmatically before Parquet write
- [Phase 10]: apply_comparable_multiples is a pure function for ARR re-estimation without full recompilation; pipeline Steps 8+9 both wired with try/except isolation
- [Phase 10]: MAPE labels for walk-forward backtesting are interpretive only (not gates) — 3 folds insufficient for statistical significance; hard actuals limited to DIRECT_DISCLOSURE_CIKS (NVIDIA/Palantir/C3.ai) to prevent circular validation; custom walk-forward loop over skforecast for 3-fold audibility
- [Phase 10]: edgartools API: get_facts_by_concept() is correct (not facts.query(concept) which is a 0-arg builder); C3.ai CIK corrected to 0001577526; Accenture CIK corrected to 0001467373 (10-K filer); EDGAR deduplication required before aggregation (37x duplicates from comparative-year reporting)
- [Phase 10]: Circular soft-actual MAPE transparency: circular_flag=True + mape_label=circular_not_validated exposes the limitation rather than hiding behind 0% MAPE; hard MAPE from EDGAR is non-circular but high for ai_software (C3.ai alone vs full-segment forecast)

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 8]: Market boundary definition (DATA-08) is a design decision, not a data task — must be locked before any data is collected to prevent anchor estimate shopping (Pitfall 1); requires evaluating 8-10 analyst report methodologies for definitional consistency
- [Phase 10]: Value chain layer taxonomy must exist before attribution percentages are populated — design artifact from Phase 9 gates Phase 10 work
- [Phase 10]: Private company revenue estimates (OpenAI, Anthropic) sourced from secondary press reporting; treat as wide-uncertainty inputs; validate against multiple sources before fixing config parameters

## Session Continuity

Last session: 2026-03-24T20:53:23.916Z
Stopped at: Completed 10-05-PLAN.md
Resume file: None
