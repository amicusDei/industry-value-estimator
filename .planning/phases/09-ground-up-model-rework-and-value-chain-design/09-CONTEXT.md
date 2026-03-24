# Phase 9: Ground-Up Model Rework and Value Chain Design - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Retrain ARIMA/Prophet/LightGBM on real USD market sizes from `market_anchors_ai.parquet` (Phase 8 output), delete the PCA composite and value chain multiplier paths entirely, lock the value chain layer taxonomy in ai.yaml, and ensure forecasts produce realistic 25-40% CAGR trajectories. Dashboard gets a minimal fix so it doesn't crash — full dashboard rework is Phase 11.

</domain>

<decisions>
## Implementation Decisions

### Model Target Variable
- **Y variable:** `median_real_2020` from `market_anchors_ai.parquet` — the scope-normalized median in constant 2020 USD billions
- **Granularity:** Per-segment models (separate ARIMA/Prophet/LightGBM per hardware/infrastructure/software/adoption), same approach as v1.0. Total = sum of segment forecasts
- **Exogenous features:** Keep World Bank/OECD macro indicators (R&D spend, patents, ICT exports, GDP) as X variables. They explain WHY the market grows — SHAP drivers become meaningful against real USD
- **Confidence intervals:** Two-layer uncertainty — (1) source disagreement from p25/p75 range, AND (2) model confidence intervals from LightGBM quantile regression. Both displayed on forecasts
- **Forecast horizon:** 2025-2030

### PCA Composite Fate
- **Delete entirely** — remove the PCA composite path from `features.py` (`build_indicator_matrix`), all related imports, and any code that references composite index values
- **features.py:** Delete `build_indicator_matrix` and rebuild from scratch as a flat feature builder — output aligned macro indicator matrix (not principal components) for ARIMA exogenous regressors and LightGBM features
- **No Expert-mode comparison** — the old model is gone, not preserved as a side panel

### Value Chain Taxonomy
- **1:1 mapping** between value chain layers and market segments: chip=hardware, cloud=infrastructure, application=software, end-market=adoption
- **Multi-layer companies:** Claude's discretion on whether to use primary+secondary flags or strict single assignment — pick the approach that keeps Phase 9 simple while giving Phase 10 what it needs for attribution
- **Taxonomy locked in ai.yaml** before any attribution percentages are written (Phase 10)

### Multiplier Deletion Scope
- **Delete all multiplier code** from `app.py` (VALUE_CHAIN_MULTIPLIERS, VALUE_CHAIN_DERIVATION blocks), `data_context.py` (value_chain_multipliers computation), and `overview.py` (multiplier display)
- **Column name:** Claude's discretion — keep `point_estimate_real_2020` (zero breakage) or rename for clarity
- **ai.yaml value_chain section:** Comment out / archive as legacy documentation, not delete
- **Minimal dashboard fix in Phase 9** — delete multiplier conversion, add pass-through so dashboard renders without crashing with raw USD values. Full polish is Phase 11
- **Contract test:** Assert that `forecasts_ensemble.parquet` `point_estimate_real_2020` (or renamed column) contains values in USD billions, not index units

### Claude's Discretion
- Whether to keep column name `point_estimate_real_2020` or rename
- Primary+secondary layer flags vs strict single assignment for multi-layer companies
- Exact feature alignment approach between macro indicators and market_anchors time series
- How to handle the 9-datapoint limitation (e.g., expanding window, synthetic augmentation, regularization)
- Minimal dashboard pass-through implementation details
- Which specific macro indicators to retain vs drop as exogenous features

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/PROJECT.md` — Core value ("analyst's best friend"), v1.1 milestone goals, constraints
- `.planning/REQUIREMENTS.md` — MODL-01, MODL-04, MODL-05 requirements with acceptance criteria
- `.planning/ROADMAP.md` — Phase 9 success criteria (3 criteria that must be TRUE)

### Research findings
- `.planning/research/STACK.md` — skforecast for backtesting, existing LightGBM/Prophet/ARIMA stack
- `.planning/research/ARCHITECTURE.md` — PCA demotion approach, multiplier block removal, forecasts_ensemble.parquet schema continuity
- `.planning/research/PITFALLS.md` — Model version gating risk, pipeline routing errors during transition
- `.planning/research/SUMMARY.md` — Build order rationale, phase dependencies

### Phase 8 outputs (data foundation)
- `config/industries/ai.yaml` — Market boundary, scope mapping, EDGAR companies with value_chain_layer assignments, legacy value_chain section
- `data/processed/market_anchors_ai.parquet` — 45-row ground truth (5 segments x 9 years, p25/median/p75, nominal + real 2020 USD)
- `src/ingestion/market_anchors.py` — Pipeline that produces the ground truth Parquet
- `.planning/phases/08-data-architecture-and-ground-truth-assembly/08-CONTEXT.md` — Phase 8 decisions (multi-layer, overlap handling, reconciliation)

### Existing model code (to be modified/replaced)
- `src/processing/features.py` — `build_indicator_matrix` (PCA composite — DELETE and rebuild)
- `src/models/statistical/arima.py` — ARIMA model (retrain on USD)
- `src/models/statistical/prophet_model.py` — Prophet model (retrain on USD)
- `src/models/ml/gradient_boost.py` — LightGBM (retrain on USD)
- `src/models/ensemble.py` — Ensemble weighting (retrain on USD)
- `src/inference/forecast.py` — Forecast pipeline (remove multiplier, output USD directly)

### Multiplier code (to be deleted)
- `src/dashboard/app.py` — VALUE_CHAIN_MULTIPLIERS, VALUE_CHAIN_DERIVATION (lines 71-108)
- `src/reports/data_context.py` — value_chain_multipliers computation (lines 93-108)
- `src/dashboard/tabs/overview.py` — multiplier display references

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/models/statistical/arima.py` — ARIMA per-segment model; retrain with new Y variable, keep structure
- `src/models/statistical/prophet_model.py` — Prophet per-segment; same — retrain, keep structure
- `src/models/ml/gradient_boost.py` — LightGBM with quantile regression for CIs; retrain on USD residuals
- `src/models/ensemble.py` — Inverse-RMSE per-segment weighting; reuse with new RMSE values
- `src/processing/deflate.py` — Deflation utilities; reuse for feature alignment
- `src/inference/shap_analysis.py` — SHAP driver attribution; gains credibility when trained on real USD

### Established Patterns
- Per-segment model loop: iterate over segments, fit model, collect predictions (arima.py, prophet_model.py)
- Residual boosting: statistical baseline → LightGBM corrects residuals (ensemble.py)
- Parquet output: `forecasts_ensemble.parquet` with `point_estimate_real_2020` column read by 9 downstream files
- Config-driven: all segment definitions from ai.yaml

### Integration Points
- `market_anchors_ai.parquet` (Phase 8) → new model training Y variable
- `forecasts_ensemble.parquet` → dashboard, reports, inference (9 files consume this)
- `ai.yaml` → value chain taxonomy, segment definitions
- `src/ingestion/pipeline.py` → already wired for market_anchors + EDGAR steps

</code_context>

<specifics>
## Specific Ideas

- Two-layer uncertainty (source disagreement + model CIs) is a unique differentiator — no commercial tool shows both
- The macro indicators as exogenous drivers means SHAP now explains "R&D spending drove 30% of AI hardware growth" against real USD — much more compelling than explaining PCA component variance
- Minimal dashboard fix prevents a multi-week period where the tool is completely non-functional during Phases 9-10

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-ground-up-model-rework-and-value-chain-design*
*Context gathered: 2026-03-24*
