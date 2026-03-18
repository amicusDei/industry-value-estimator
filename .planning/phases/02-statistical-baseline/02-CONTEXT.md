# Phase 2: Statistical Baseline - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Build interpretable econometric models that produce AI market size baselines, residuals (for Phase 3 ML training), and documented assumptions. Includes structural break analysis for the 2022-2024 GenAI surge. Two complementary views: bottom-up proxy composite and top-down GDP share estimate. ML ensemble, dashboard, and reports are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Market size target variable
- **Two complementary measures:** bottom-up proxy composite (observed) + top-down GDP share regression (estimated)
- **Cross-validate** one against the other for defensibility
- **Per-segment modeling:** Fit separate models for each of the 4 AI segments (hardware, infrastructure, software, adoption), then aggregate. Captures different growth dynamics per segment.
- **Bottom-up composite weighting:** PCA as primary (data-driven weights), manual weights as sensitivity check. First principal component = "AI market activity index."
- **Top-down regressors:** Claude picks based on data availability and statistical significance from Phase 1 indicators (GDP, R&D/GDP, ICT exports, patent applications, researchers per million, high-tech exports)

### Model selection strategy
- **Fit both ARIMA and Prophet** on each segment, compare fit metrics, pick winner per segment. Document the comparison.
- **Top-down GDP share:** Start with OLS regression. Claude upgrades to WLS/GLS if diagnostics show heteroscedasticity or autocorrelation. Document the decision chain.
- **Fit metrics:** Extended suite — RMSE, MAPE, R², AIC/BIC, Ljung-Box residual autocorrelation test
- **Residual output:** Save residuals as explicit separate Parquet file in `data/processed/`. Phase 3 ML models train on these residuals (the "hybrid" bridge).

### Structural break handling
- **Detection:** CUSUM test to find the breakpoint date endogenously, Chow test to confirm statistical significance. Belt-and-suspenders.
- **Scope:** Aggregate first (confirm break exists), then per-segment (identify which segments drove the surge)
- **Modeling treatment:** Regime-switching model (Markov switching). Claude decides sharp vs. gradual transition based on data fit — with ~15 annual observations, sharp may be more stable.
- **All four segments** get break analysis — the GenAI surge likely hits software/infrastructure differently than hardware

### Assumptions documentation
- **Format:** Standalone `docs/ASSUMPTIONS.md` — single source of truth, easy to reference from LinkedIn paper
- **Structure:** Two-tier — practitioner summary ("TL;DR of assumptions") up front, detailed mathematical appendix below
- **Scope:** Full chain — data source assumptions, modeling assumptions, AND interpretation caveats
- **Each assumption** gets a "If this is wrong:" sensitivity note explaining impact direction and magnitude
- **Covers:** stationarity, distributional assumptions, parameter choices, cross-validation design, proxy validity arguments, TRBC universe representativeness, regulatory/market regime assumptions

### Claude's Discretion
- Specific ARIMA(p,d,q) order selection per segment
- Prophet hyperparameters (changepoint_prior_scale, seasonality)
- OLS variable selection and diagnostic-driven upgrades
- Regime-switching model specification (sharp Markov vs smooth LSTAR)
- PCA component selection criteria
- Manual weight allocation for sensitivity check
- Temporal cross-validation window sizes
- Exact structure of ASSUMPTIONS.md sections

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/PROJECT.md` — Project vision: hybrid statistical + ML approach, documentation as learning resource, portfolio-quality
- `.planning/REQUIREMENTS.md` — MODL-01, MODL-06, MODL-08, MODL-09, ARCH-04 requirements mapped to this phase
- `.planning/ROADMAP.md` — Phase 2 success criteria (4 criteria that must be TRUE)

### Phase 1 outputs (data contract)
- `src/processing/normalize.py` — Processed DataFrame schema: economy, year, indicator, value_real_2020, estimated_flag, industry_tag, source columns
- `src/processing/validate.py` — PROCESSED_SCHEMA pandera definition (the contract Phase 2 reads)
- `config/industries/ai.yaml` — 4 segments, World Bank indicators, OECD datasets, LSEG TRBC codes
- `config/settings.py` — BASE_YEAR=2020, load_industry_config(), DATA_PROCESSED path

### Research findings
- `.planning/research/STACK.md` — statsmodels, Prophet, scikit-learn in stack
- `.planning/research/ARCHITECTURE.md` — FTI pattern, Cookiecutter DS structure
- `.planning/research/PITFALLS.md` — Small N risks, structural break handling requirements

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/processing/normalize.py` — normalize_world_bank(), normalize_oecd(), normalize_lseg() produce the DataFrames this phase consumes
- `src/ingestion/pipeline.py` — run_full_pipeline() produces Parquet cache in data/processed/
- `config/settings.py` — load_industry_config() for segment definitions, BASE_YEAR for deflation reference
- `src/processing/validate.py` — PROCESSED_SCHEMA defines the input data contract

### Established Patterns
- Parquet storage with provenance metadata (source, industry, fetched_at)
- pandera schema validation at boundaries
- Config-driven industry definitions via YAML
- TDD approach (tests written before implementation in Phase 1)

### Integration Points
- **Input:** Reads from `data/processed/*.parquet` (Phase 1 output)
- **Output:** Forecast Parquet + residual Parquet in `data/models/` or `data/processed/` for Phase 3 ML training
- **Config:** Reads segment definitions from `config/industries/ai.yaml`
- **Docs:** ASSUMPTIONS.md in `docs/` alongside existing METHODOLOGY.md

</code_context>

<specifics>
## Specific Ideas

- The regime-switching approach for structural breaks is more sophisticated than a simple dummy variable — demonstrates econometric depth for the methodology paper
- PCA + manual weights comparison for the proxy composite shows robustness — a reviewer can see the results don't depend on subjective weight choices
- The two-tier ASSUMPTIONS.md (summary + appendix) mirrors academic paper style — useful for the LinkedIn writeup in Phase 5
- Residuals saved as explicit Parquet creates a clean handoff to Phase 3 ML training — the "hybrid" in the project name

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-statistical-baseline*
*Context gathered: 2026-03-18*
