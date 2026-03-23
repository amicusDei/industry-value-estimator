---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Completed 05-01-PLAN.md (real data pipeline)
last_updated: "2026-03-23T09:30:53.410Z"
last_activity: "2026-03-17 — Completed plan 01-01: project scaffold, AI industry config, pandera schemas, 26 tests"
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 20
  completed_plans: 18
  percent: 4
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-17)

**Core value:** Produce defensible, data-driven AI industry valuations and growth forecasts that go beyond rough estimates — combining econometric rigor with modern ML techniques.
**Current focus:** Phase 1 — Data Foundation

## Current Position

Phase: 1 of 5 (Data Foundation)
Plan: 1 of TBD in current phase
Status: In progress
Last activity: 2026-03-17 — Completed plan 01-01: project scaffold, AI industry config, pandera schemas, 26 tests

Progress: [░░░░░░░░░░] 4%

## Performance Metrics

**Velocity:**
- Total plans completed: 1
- Average duration: 5 min
- Total execution time: 0.08 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-data-foundation | 1 | 5 min | 5 min |

**Recent Trend:**
- Last 5 plans: 01-01 (5 min)
- Trend: —

*Updated after each plan completion*
| Phase 01-data-foundation P03 | 2 | 1 tasks | 3 files |
| Phase 01-data-foundation P02 | 12 | 2 tasks | 4 files |
| Phase 01-data-foundation P03 | 30 | 2 tasks | 3 files |
| Phase 01-data-foundation P04 | 4 | 2 tasks | 7 files |
| Phase 01-data-foundation P05 | 8 | 1 tasks | 3 files |
| Phase 02-statistical-baseline P01 | 4 | 2 tasks | 4 files |
| Phase 02-statistical-baseline P02 | 15 | 2 tasks | 5 files |
| Phase 02-statistical-baseline P03 | 3 | 2 tasks | 3 files |
| Phase 02-statistical-baseline P04 | 3 | 2 tasks | 2 files |
| Phase 02-statistical-baseline P05 | 8 | 1 tasks | 2 files |
| Phase 03-ml-ensemble-and-validation P01 | 3 | 2 tasks | 6 files |
| Phase 03-ml-ensemble-and-validation P02 | 3 | 2 tasks | 7 files |
| Phase 03-ml-ensemble-and-validation P03 | 2 | 1 tasks | 2 files |
| Phase 04-interactive-dashboard P01 | 2 | 2 tasks | 9 files |
| Phase 04-interactive-dashboard P02 | 2 | 2 tasks | 10 files |
| Phase 04-interactive-dashboard P03 | 90 | 1 tasks | 6 files |
| Phase 05-reports-paper-and-portfolio P02 | 10 | 4 tasks | 35 files |
| Phase 05-reports-paper-and-portfolio P01 | 45 | 3 tasks | 11 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 5-phase bottom-up build order matches architectural dependency chain (data → statistical → ML → dashboard → reports)
- [Roadmap]: ARCH-01 (config-driven extensibility) placed in Phase 1 so pipeline is industry-agnostic from first commit
- [Roadmap]: DATA-07 (data source attribution) placed in Phase 4 where it becomes visible in dashboard outputs
- [01-01]: pandera.pandas import used (not top-level pandera) — forward-compatible with pandera 0.30.0+ deprecation
- [01-01]: strict=False on all raw schemas — API responses include extra columns beyond required fields
- [01-01]: check_no_nominal_columns() as standalone function callable independently before full PROCESSED_SCHEMA validation
- [Phase 01-03]: Desktop Session auth config pattern: lseg-data.config.json gitignored, .example committed as template; app-key left empty
- [Phase 01-03]: TRBC codes read from config dynamically — zero hardcoded codes in lseg.py, ensures reproducibility
- [Phase 01-02]: _sdmx_to_dataframe helper: pandasdmx to_pandas() returns pd.Series with MultiIndex — reset_index() on Series to get flat DataFrame
- [Phase 01-02]: patch.object on pipeline module instead of string-path patch to avoid importlib.reload bypassing mock bindings in pipeline unit tests
- [Phase 01-02]: OECD SDMX dimension key fallback: try LOCATION first, catch exceptions, retry with COU + rename — handles API inconsistency between environments
- [Phase 01-03]: TR.TRBCIndustryCode (8-digit) used in SCREEN() expression — config stores 8-digit Industry codes, not 10-digit Activity codes (TR.TRBCActivityCode)
- [Phase 01-04]: apply_deflation builds year-indexed Series from year column, uses .values to reset index — prevents base_year lookup failure in deflate_to_base_year
- [Phase 01-04]: normalize_oecd raises ValueError on missing economy column — silent pass-through produces invalid processed rows with no clear diagnosis
- [Phase 01-04]: write_processed_parquet embeds source/industry/base_year/fetched_at as Parquet schema metadata bytes for downstream DATA-07 attribution
- [Phase 01-05]: Pipeline test uses patch.object at pipeline module level, not wbgapi library — avoids MultiIndex reshape in world_bank.py during orchestration tests
- [Phase 01-05]: run_full_pipeline uses same try/except per-source pattern as run_ingestion — consistent partial-success error isolation across full pipeline
- [Phase 02-01]: constant-only OLS for CUSUM: linear trend detrending absorbs level shifts and reduces detection power; constant-only (ddof=1) achieves p<0.05 on step-function series
- [Phase 02-01]: Markov switching minimum series length 20 obs: fewer obs cause EM non-convergence; fallback to dummy OLS for short or non-converging series
- [Phase 02-01]: AICc used in compute_aic_bic: small-N correction required (n-k-1 denominator grows materially at n<50)
- [Phase 02-02]: sklearn Pipeline enforces PCA fit-on-training-only by construction — scaler.mean_ verified in test_pca_no_leakage
- [Phase 02-02]: temporal_cv_generic accepts arbitrary callables (fit_fn/forecast_fn) not ARIMA-specific — maximizes reuse across model types in downstream plans
- [Phase 02-02]: diagnostics dict always captures OLS-layer diagnostics even when final model is WLS/GLSAR — preserves traceability for ASSUMPTIONS.md
- [Phase 02-03]: AICc (not AIC) for ARIMA order selection on short annual series (N < 30)
- [Phase 02-03]: changepoints=['2022-01-01'] anchors Prophet to GenAI surge; manual TimeSeriesSplit CV for consistent methodology with ARIMA
- [Phase 02-03]: Year-aligned residuals via original_index re-assignment; residuals Parquet schema: year (int), segment (str), residual (float), model_type (str)
- [Phase 02-statistical-baseline]: Two-tier ASSUMPTIONS.md (TL;DR + detailed appendix) mirrors academic paper style for Phase 5 methodology paper
- [Phase 02-statistical-baseline]: Every assumption accompanied by explicit sensitivity note documenting impact direction and magnitude (16 total)
- [Phase 02-05]: sys.path injection in script header resolves src/config imports for both python scripts/... and python -m scripts... invocations
- [Phase 02-05]: All 4 AI segments selected Prophet as winner on synthetic data — structural break at 2022 favors Prophet changepoint prior; split will differ on live API data
- [Phase 03-01]: libomp installed via Homebrew — LightGBM macOS dylib requires OpenMP at runtime
- [Phase 03-01]: Closure with mutable _state dict aligns feature_matrix to temporal_cv_generic y-slice API without changing the shared CV scaffold
- [Phase 03-02]: Additive blend confirmed: LightGBM corrects statistical residuals (stat_pred + lgbm_weight * correction), not a parallel full forecast
- [Phase 03-02]: 2.5% annual CAGR as inflation proxy for real-to-nominal USD conversion — upgradeable to live World Bank NY.GDP.DEFL.ZS deflator
- [Phase 03-02]: Epsilon guard (1e-10) in compute_ensemble_weights prevents division by zero; zero-RMSE model receives near-maximum weight
- [Phase 03-02]: matplotlib.use('Agg') called inside save_shap_summary_plot to keep headless-safe without forcing global backend change at import time
- [Phase 03-ml-ensemble-and-validation]: Statistical baseline RMSE = std(residuals): stat model's predicted correction of its own residuals is zero, making residual std the natural RMSE baseline for inverse-RMSE weighting
- [Phase 03-ml-ensemble-and-validation]: Forecast features use constant forward projection: last two known residuals projected flat for 2025-2030 — no-information extrapolation for mean-reverting residuals
- [Phase 04-interactive-dashboard]: uv run required for dash imports — dash/plotly in uv-managed venv, not base python3 path
- [Phase 04-interactive-dashboard]: CI bands always use real 2020 USD; usd_col param only toggles point line (historical/forecast traces)
- [Phase 04-interactive-dashboard]: MAPE and R^2 documented as N/A — residuals_statistical.parquet has only residual column, no actual/predicted
- [Phase 04-interactive-dashboard]: Forecast bridge: last historical point prepended to forecast trace x/y arrays for visual continuity at boundary
- [Phase 04-interactive-dashboard]: Tab layout builders are pure functions (segment, usd_col) → html.Div — stateless, uniform callback dispatch
- [Phase 04-interactive-dashboard]: Headline uses Forecast Index label, not USD trillions — values are normalized composite indices
- [Phase 04-interactive-dashboard]: Global controls outside tab-content to prevent state reset on tab switch (Pitfall 3)
- [Phase 04-interactive-dashboard]: Checkpoint approved after 3 rounds: normal mode USD headlines, expert mode raw indices, fan charts, SHAP, diagnostics all verified by user
- [Phase 05-02]: NumPy-style docstrings chosen for all src/ modules to match existing arima.py convention
- [Phase 05-02]: docs/ARCHITECTURE.md created with Mermaid flowchart covering full data pipeline
- [Phase 05-02]: AST-based TestDocstringCoverage enforces docstring invariant automatically on every future PR
- [Phase 05-01]: OECD PATS_IPC replaced by MSTI B_ICTS (ICT-sector BERD) as AI patent proxy — stats.oecd.org deprecated, PATS_IPC not available in new sdmx.oecd.org API
- [Phase 05-01]: Per-economy deflation fix: apply_deflation builds (economy, year) lookup map to avoid Series ambiguity with duplicate year indices across 16 economies
- [Phase 05-01]: PCA composite per segment with 3-indicator subset — hardware (exports+patents+ICT-BERD), infra (GDP+ICT-svc+BERD), software (ICT-svc+RD%+GERD), adoption (RD%+researchers+GDP)

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1]: Specific World Bank/OECD indicator codes for AI industry proxies need validation against live APIs before writing ingestion config — definitions vary 2-3x across research firms
- [Phase 3]: Ensemble weighting strategy (fixed alpha vs. stacking vs. dynamic) is an open methodology decision — must be empirically tested and documented

## Session Continuity

Last session: 2026-03-23T09:30:53.408Z
Stopped at: Completed 05-01-PLAN.md (real data pipeline)
Resume file: None
