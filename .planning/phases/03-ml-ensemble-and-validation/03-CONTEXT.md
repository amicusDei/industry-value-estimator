# Phase 3: ML Ensemble and Validation - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the ML refinement layer (LightGBM on statistical residuals), ensemble combiner with per-segment weights, 2030 growth forecasts with calibrated confidence intervals, SHAP driver attribution, and serialized model artifacts. This phase produces the final AI market size estimates. Dashboard, reports, and paper are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Ensemble weighting strategy
- **Method:** Fixed weights from CV performance — weight each model proportional to its inverse CV error (e.g., if statistical RMSE=0.3 and LightGBM RMSE=0.2, LightGBM gets 60%)
- **Scope:** Per-segment weights primary (each segment gets its own blend ratio), global weights as fallback for segments with insufficient CV folds
- **LightGBM features:** Residuals only (pure residual learning) — LightGBM sees ONLY the statistical model residuals + lag features. True "residual boosting" — ML learns what statistics missed. Clean separation of responsibilities.
- **Data vintage:** Every output estimate tagged with the date of the latest data used (e.g., "AI market was $X trillion as of 2025-Q1 data"). Required by MODL-04. In DataFrame columns, not just metadata.

### Confidence interval calibration
- **Method:** Quantile regression via LightGBM — train separate models for 10th/90th percentiles (80% CI) and 2.5th/97.5th percentiles (95% CI). Directly produces interval bounds.
- **Fan shape:** Claude calibrates based on data — let the quantile regression learn natural widening from CV folds. Don't force fan shapes if the data doesn't support it.
- **No bare point forecasts:** Every forecast output includes both point estimate and interval bounds (MODL-05).

### Output units
- **Primary:** 2020 constant USD (trillions) — consistent with Phase 1 deflation base year
- **Secondary:** Reflated to nominal USD for headlines — "AI industry worth $X.X trillion (2020 USD) / $Y.Y trillion (nominal)"
- Both representations in the forecast output DataFrame

### Model serialization
- **Format:** joblib (scikit-learn standard) — fast, handles LightGBM + sklearn pipelines natively
- **Directory:** `models/ai_industry/` (already exists on disk)
- **Artifacts:** Both serialized models AND pre-computed forecast DataFrames (point estimates + intervals). Dashboard loads forecasts directly without running inference. Cache invalidated when models are retrained.

### Pipeline runner
- **Script:** `scripts/run_ensemble_pipeline.py` — single command: train LightGBM → build ensemble → forecast to 2030 → compute SHAP → serialize models → save forecasts
- Follows the pattern established by `scripts/run_statistical_pipeline.py` from Phase 2

### Claude's Discretion
- LightGBM hyperparameters (learning_rate, n_estimators, max_depth, etc.)
- Number of lag features derived from residuals
- SHAP analysis depth (summary plots vs force plots vs interaction effects)
- Exact quantile regression model configuration
- Model file naming convention within `models/ai_industry/`
- Deflation/reflation mechanics for nominal USD conversion
- Minimum CV folds threshold before falling back to global weights

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/PROJECT.md` — Project vision: hybrid statistical + ML, documentation as learning resource, portfolio-quality
- `.planning/REQUIREMENTS.md` — MODL-02, MODL-03, MODL-04, MODL-05, MODL-07 requirements mapped to this phase
- `.planning/ROADMAP.md` — Phase 3 success criteria (5 criteria that must be TRUE)

### Phase 2 outputs (model contract)
- `data/processed/residuals_statistical.parquet` — Schema: year (int), segment (str), residual (float), model_type (str). 60 rows, 4 segments, 2010-2024. This is the LightGBM training input.
- `src/models/statistical/arima.py` — `select_arima_order`, `fit_arima_segment`, `forecast_arima`, `run_arima_cv`
- `src/models/statistical/prophet_model.py` — `fit_prophet_segment`, `forecast_prophet`, `save_all_residuals`
- `src/models/statistical/regression.py` — `fit_top_down_ols_with_upgrade`, `temporal_cv_generic` (reusable for ML CV)
- `src/diagnostics/model_eval.py` — `compute_rmse`, `compute_mape`, `compute_r2`, `compute_aic_bic`, `ljung_box_test`, `compare_models`
- `scripts/run_statistical_pipeline.py` — Pattern for pipeline runner script

### Phase 1 outputs (data layer)
- `config/industries/ai.yaml` — 4 segments, base_year 2020
- `config/settings.py` — BASE_YEAR=2020, load_industry_config()

### Research findings
- `.planning/research/STACK.md` — LightGBM, scikit-learn, SHAP in stack
- `.planning/research/ARCHITECTURE.md` — FTI pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `temporal_cv_generic` in `regression.py` — callable-based expanding-window CV scaffold, directly reusable for LightGBM CV
- `compare_models` in `model_eval.py` — compares model metrics, can compare statistical vs ML vs ensemble
- `compute_rmse`, `compute_mape`, `compute_r2` — full metrics suite ready
- `save_all_residuals` in `prophet_model.py` — Parquet save pattern with schema validation
- `scripts/run_statistical_pipeline.py` — runner script pattern to follow

### Established Patterns
- Parquet storage with provenance metadata
- pandera schema validation at boundaries
- TDD: tests before implementation
- Per-segment modeling with config-driven segment list
- joblib already in uv lockfile (sklearn dependency)

### Integration Points
- **Input:** `data/processed/residuals_statistical.parquet` (Phase 2 output)
- **Output:** `models/ai_industry/` for serialized models + forecast cache
- **Output:** Forecast DataFrames consumed by Phase 4 dashboard
- **Config:** `config/industries/ai.yaml` for segment list

</code_context>

<specifics>
## Specific Ideas

- Pure residual learning (LightGBM on residuals only) creates the cleanest "hybrid" story for the methodology paper — statistics handles the trend, ML handles the noise
- Per-segment ensemble weights show that the optimal blend varies by domain — impressive nuance for the paper
- Both constant and nominal USD outputs serve different audiences: constant for academic rigor, nominal for LinkedIn/press headlines
- Data vintage tagging makes every estimate reproducible — "this was the answer with data through Q1 2025"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-ml-ensemble-and-validation*
*Context gathered: 2026-03-22*
