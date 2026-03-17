# Project Research Summary

**Project:** AI Industry Economic Valuation and Forecasting System
**Domain:** Hybrid statistical + ML economic forecasting pipeline with interactive dashboard
**Researched:** 2026-03-17
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is a data-science-meets-econometrics project: a pipeline that ingests public economic data (World Bank, OECD, Eurostat), cleans and normalizes it, runs a two-stage hybrid forecasting model (statistical baseline feeding into a gradient-boosting ML refinement), and exposes results through a Plotly/Dash interactive dashboard with PDF report export. The canonical approach in this domain is a strict layered architecture — raw data flows one-way through normalization, feature engineering, statistical modeling, ML correction, ensemble combination, and finally presentation. Building any layer out of order wastes effort because each tier has hard dependencies on the one below it. The recommended stack is well-defined: Python 3.12, pandas 3.0, statsmodels 0.14.6, Prophet 1.1.x, LightGBM 4.6.0, scikit-learn 1.8.0, SHAP 0.46.x, Plotly 6.6.0, and Dash 4.0.x — with uv as the package manager.

The recommended approach is to build strictly bottom-up: data pipeline first, statistical baseline second, ML layer third, ensemble and inference fourth, dashboard and reporting last. The hybrid two-stage pattern (ARIMA/Prophet for trend and seasonality, gradient boosting on residuals for nonlinear correction) consistently outperforms either approach alone on economic time series data, and the methodology paper mandates interpretability that pure ML cannot provide. The project's core value proposition — producing "defensible" forecasts that replace "valued by thumb" estimates — depends entirely on rigorous validation (temporal train/test splits, calibrated confidence intervals, and structural break analysis). Shortcutting any of these undermines the central claim.

The key risks are concentrated in the data pipeline phase. Three pitfalls are non-negotiable to address before writing a single model: (1) market boundary definition must be locked before any API call is made — estimates vary 2-3x based on definitional choices alone; (2) all monetary series must be deflated to a common base year — nominal/real conflation is an immediate credibility killer; (3) API schema validation must be in place — the World Bank and OECD APIs have changed schemas without notice, causing silent data corruption. After the pipeline is sound, the modeling phase must enforce strict temporal validation (no data leakage) and include calibrated uncertainty intervals. Presenting point forecasts without intervals directly contradicts the project's stated purpose.

---

## Key Findings

### Recommended Stack

The stack is fully specified with verified versions. Python 3.12 is the runtime; pandas 3.0 with Copy-on-Write semantics is the data layer. Package management via uv (not pip/conda) provides lockfile reproducibility. The most important version constraint is that statsmodels must be >=0.14.6 to work with pandas 3.0 — earlier versions have an import blocker introduced in December 2025.

**Core technologies:**
- **Python 3.12**: Runtime — 3.13 ecosystem support is still maturing; 3.12 is the safe production choice
- **pandas 3.0 + NumPy 2.x**: Data wrangling — CoW is now default; write CoW-safe code from day one
- **statsmodels 0.14.6**: Econometric baseline models (OLS, ARIMA, SARIMAX, VAR) — mandatory for portfolio credibility; provides p-values and hypothesis tests that scikit-learn intentionally omits
- **Prophet 1.1.x**: Additive trend/seasonality for sparse, fast-growing, structurally-broken AI market time series — handles missing data and outliers gracefully
- **LightGBM 4.6.0**: Primary ML layer — outperforms XGBoost on small-to-medium tabular data; sklearn-compatible API
- **scikit-learn 1.8.0**: Pipeline orchestration, TimeSeriesSplit cross-validation, model evaluation
- **SHAP 0.46.x**: Feature attribution — required for methodology explainability; produces dashboard-embeddable waterfall plots
- **Plotly 6.6.0 + Dash 4.0.x**: Dashboard — Plotly 6.0+ uses Narwhals for pandas 3.0 compatibility; Dash 4.0 is current stable
- **WeasyPrint 68.x + Jinja2 3.1.x + Kaleido 0.2.x**: PDF report generation — WeasyPrint handles modern CSS layout; Kaleido bridges Plotly figures to static PNG for embedding
- **wbgapi, eurostat, pandasdmx**: Data connectors — World Bank, Eurostat, and OECD official clients respectively; avoid pandas-datareader for these sources
- **pyarrow 18.x**: Parquet storage for raw and processed data caching between pipeline runs
- **uv 0.5.x**: Package manager — 10-100x faster than pip; lockfile-based; standard for new 2026 Python projects

**Do not use:** TensorFlow/PyTorch (dataset too small — will overfit), conda, pandas <3.0, fbprophet (abandoned), scikit-learn's original GradientBoostingClassifier (orders of magnitude slower than LightGBM), pandas-datareader for OECD (OECD API changed in 2023).

See `.planning/research/STACK.md` for full alternatives analysis and version compatibility matrix.

---

### Expected Features

The project must demonstrate economic rigor (confidence intervals, documented assumptions, data attribution) alongside ML sophistication (hybrid model, SHAP explainability). The combination — rare in public portfolio projects — is the primary differentiator.

**Must have (table stakes for v1):**
- Data ingestion from World Bank and OECD APIs — without this, nothing else exists
- Data cleaning and normalization pipeline including deflation to constant-year USD
- Statistical baseline model (ARIMA or OLS) — the interpretable econometric foundation
- ML refinement model (LightGBM gradient boosting) — the layer that improves on the baseline
- Market size point estimate with units and data vintage date
- Growth forecast to 2030 with calibrated confidence intervals (80% and 95%) — point forecasts alone are statistically irresponsible
- Model diagnostics and fit metrics (RMSE, MAPE, R², backtesting) — out-of-sample only
- Interactive Dash dashboard with time series and forecast fan charts
- Exportable PDF report (WeasyPrint + Jinja2 + Kaleido)
- Documented assumptions — required for any publishable analysis
- Data source attribution in all outputs
- README with setup and data source documentation

**Should have (differentiators, add in v1.x):**
- SHAP-based driver attribution — shows which variables (R&D spend, patent filings, VC investment) drive the forecast; directly addresses the "valued by thumb" critique
- Scenario/sensitivity analysis with interactive sliders — conservative/base/optimistic; standard in professional forecasting tools, rare in portfolio projects
- Bottom-up cross-validation alongside top-down estimate — what professional market research firms do; strengthens methodological credibility
- Methodology paper / LinkedIn writeup — the content artifact that elevates the project from data exercise to published economic research
- Data freshness tracking and last-updated indicator — low effort, professional signal

**Defer (v2+):**
- Second industry (cloud computing, biotech) — build extensible architecture now, add the industry later once AI model quality is validated
- Automated model retraining on data refresh — requires scheduling infrastructure orthogonal to modeling work
- Real-time data streaming — macroeconomic data updates quarterly/annually; streaming is architectural overhead with no analytical value

See `.planning/research/FEATURES.md` for full dependency graph and prioritization matrix.

---

### Architecture Approach

The canonical architecture is a **strictly layered one-way pipeline**: ingestion connectors write to immutable raw storage; normalization reads raw and writes processed; feature engineering reads processed; statistical and ML models both read features (with ML also consuming statistical residuals); the ensemble combiner produces forecast artifacts; the dashboard and report generator both read from pre-computed forecasts. No layer reaches backward or re-trains at runtime. The architectural principle that has the most impact on long-term maintainability is industry-config-driven ingestion — every industry-specific parameter lives in `config/industries/<industry>.yaml`, making the pipeline code industry-agnostic and extension to a second industry a YAML file addition rather than a code rewrite.

**Major components:**
1. **Ingestion connectors** (`src/ingestion/`) — one file per source (world_bank.py, oecd.py, eurostat.py, scraper.py); fetch and cache raw data; write to immutable `data/raw/`
2. **Normalization pipeline** (`src/processing/normalize.py`, `validate.py`) — schema alignment, type coercion, deduplication, deflation to base year, industry tagging; writes to `data/processed/`
3. **Feature store** (`src/processing/features.py`) — lag features, growth rates, rolling averages, cross-sector signals; feeds both model layers
4. **Statistical layer** (`src/models/statistical/`) — ARIMA, Prophet, OLS, VAR; produces baselines and residuals for ML consumption
5. **ML layer** (`src/models/ml/gradient_boost.py`) — LightGBM trained on residuals from statistical layer; sklearn pipeline-compatible
6. **Ensemble combiner** (`src/models/ensemble.py`) — weighted blend of statistical and ML outputs; produces final forecast with confidence intervals
7. **Inference engine** (`src/inference/`) — loads serialized models, runs forward projections to 2030, produces scenario bands; runs offline and stores artifacts
8. **Dash dashboard** (`src/dashboard/`) — reads pre-computed forecast artifacts; callbacks adjust visualization, not model parameters
9. **Report generator** (`src/reporting/`) — Jinja2 templates + WeasyPrint + Kaleido; produces PDF from the same forecast artifacts as the dashboard

**Three patterns to follow from day one:**
- FTI separation (Feature/Training/Inference as distinct pipeline stages) — prevents feature logic from leaking into model files
- Industry-config-driven ingestion (YAML per industry) — the extensibility mechanism
- Pre-compute forecasts; never re-train at dashboard runtime — keeps Dash callbacks sub-second

See `.planning/research/ARCHITECTURE.md` for full component diagram, project structure, and anti-patterns.

---

### Critical Pitfalls

Eight pitfalls identified; the top five are listed here by severity and phase-of-impact. Full details in `.planning/research/PITFALLS.md`.

1. **Undefined market boundary** — "AI industry" definitions vary 2-3x across research firms (Grand View: $391B vs. Statista: $254B in 2025). Must lock down market definition (segments included/excluded, classification scheme) in a config file *before* any API call. This is a design decision, not a discovery.

2. **Nominal/real conflation** — mixing current-year and constant-year dollar values invalidates all historical comparisons. Mandatory fix: define a base year (e.g., 2020 USD), fetch World Bank GDP deflator series (NY.GDP.DEFL.ZS) alongside every nominal indicator, apply deflation as a pipeline step, and enforce a column naming convention (`revenue_usd_real_2020`). Non-negotiable for any time-series comparison.

3. **Data leakage in time series validation** — applying StandardScaler on the full dataset before splitting, or shuffling time series for cross-validation, inflates metrics and makes the methodology paper unpublishable. Use `TimeSeriesSplit` exclusively; fit all preprocessors only on training data.

4. **Structural break extrapolation** — the 2022-2024 generative AI investment surge is a structural break in the AI market series. Models trained on pre-2022 data will systematically underestimate; models that extrapolate post-2022 hypergrowth will systematically overestimate. Run Chow test or CUSUM test before model selection; tune Prophet's `changepoint_prior_scale`; build explicit scenario bands.

5. **API schema changes causing silent data corruption** — World Bank and OECD APIs have changed field names and response formats without notice. Prevention: write pandera/pydantic schema validation tests that run after every fetch; cache raw API responses with fetch timestamps; treat external data as untrusted input at the ingestion layer.

**Additional pitfalls to track:** survivorship bias in company-level data (document as limitation, cross-reference with national accounts); ML overfitting on small data (gradient boosting beats deep learning on <200 row datasets — do not add LSTM unless Prophet residuals are systematically poor); point forecasts without uncertainty (always show 80% and 95% intervals — this is the core value proposition).

---

## Implications for Roadmap

Research strongly supports a 5-phase build order that mirrors the architectural dependency chain. Each phase delivers a testable artifact before the next phase begins.

### Phase 1: Data Foundation and Pipeline

**Rationale:** Everything downstream has a hard dependency on clean, validated, inflation-adjusted data. This phase must be completed and verified before any modeling begins. The three most expensive pitfalls to recover from (undefined market boundary, nominal/real conflation, API schema changes) all occur here. Fix them here or pay a HIGH recovery cost later.

**Delivers:** Immutable raw data cache, normalized processed datasets in Parquet, schema validation tests, market boundary definition document, deflation pipeline, data freshness metadata.

**Addresses features:** Data ingestion from World Bank/OECD/Eurostat, data cleaning and normalization pipeline, data source attribution, data freshness tracking.

**Avoids pitfalls:** Undefined market boundary (lock definition in config before first API call), nominal/real conflation (mandatory deflation step), API schema corruption (pandera validation tests), survivorship bias in company data (document limitation at source).

**Stack:** wbgapi, eurostat, pandasdmx, requests-cache, pandas 3.0, pyarrow, python-dotenv, pydantic/pandera.

**Research flag:** NEEDS RESEARCH — specific World Bank/OECD indicator codes for AI industry proxies (R&D expenditure, patent filings, VC investment) require validation against source APIs before committing to the ingestion config.

---

### Phase 2: Statistical Baseline Modeling

**Rationale:** The interpretable statistical layer must be built before the ML layer. It provides (a) the ARIMA/Prophet residuals that the ML model trains on, (b) the explainability anchor for the methodology paper, and (c) the benchmark against which ML improvement is measured. Cannot skip this phase to "save time" — the hybrid architecture requires it as an input.

**Delivers:** Fitted ARIMA, SARIMAX, and/or Prophet models, structural break analysis (Chow test / CUSUM / Prophet changepoint review), in-sample and out-of-sample validation metrics, feature engineering module (`src/processing/features.py`).

**Addresses features:** Statistical baseline model (ARIMA/OLS), model diagnostics and fit metrics, documented assumptions.

**Avoids pitfalls:** Structural break extrapolation (Chow test before model selection, Prophet changepoint tuning), ML overfitting on small data (establish statistical baseline performance before committing to ML complexity).

**Stack:** statsmodels 0.14.6, Prophet 1.1.x, scipy 1.14.x, scikit-learn 1.8.0 TimeSeriesSplit, pandas 3.0.

**Research flag:** STANDARD PATTERNS — ARIMA and Prophet on economic time series are well-documented. Specific changepoint tuning for 2022-2024 AI investment surge may require experimentation.

---

### Phase 3: ML Layer, Ensemble, and Validation

**Rationale:** ML models consume Phase 2 residuals. The ensemble combiner requires both statistical and ML outputs. Model evaluation and backtesting require the full pipeline to be in place. This phase produces the primary forecast artifacts that all downstream phases consume.

**Delivers:** Trained LightGBM model on statistical residuals, ensemble combiner with weighted blending, SHAP feature importance calculations, serialized model artifacts (`models/ai_industry/`), backtesting report (train pre-2020, evaluate 2020-2024), market size point estimates with 80%/95% confidence intervals, 2030 growth forecast artifacts.

**Addresses features:** ML refinement model, hybrid statistical + ML ensemble, market size point estimate, growth forecast with confidence intervals, model diagnostics, SHAP driver attribution (v1.x trigger).

**Avoids pitfalls:** Data leakage (TimeSeriesSplit, scaler fitted on training data only), point forecasts without uncertainty (CI generation is part of ensemble output, not an afterthought), ML overfitting (compare LightGBM OOS performance vs. Prophet baseline before accepting the ML correction).

**Stack:** LightGBM 4.6.0, scikit-learn 1.8.0, SHAP 0.46.x, statsmodels (for quantile regression CIs), joblib for model serialization.

**Research flag:** NEEDS RESEARCH — ensemble weighting strategy (fixed alpha vs. learned weighting vs. stacking) is a methodology decision with multiple valid approaches; the choice should be documented and defended in the methodology paper.

---

### Phase 4: Inference Engine and Interactive Dashboard

**Rationale:** Dashboard is built on top of finalized, serialized model artifacts. Building the dashboard before models are stable wastes layout work. The inference engine is the bridge between offline-trained models and the live dashboard — it must be separate from both training and presentation layers.

**Delivers:** Inference module that loads serialized models and runs forward projections to 2030, Dash dashboard with time series charts, forecast fan chart with CI bands, market segment breakdown, scenario selector (pessimistic/base/optimistic), methodology panel explaining market boundary.

**Addresses features:** Interactive dashboard with charts, scenario/sensitivity analysis, data source attribution in UI, real/nominal toggle, data freshness indicator.

**Avoids pitfalls:** Training at dashboard runtime (inference loads pre-computed artifacts, callbacks never re-train), forecast communication errors (fan chart with interval bands as default view, scenario toggle, hedged language throughout), overloaded dashboard (lead with ensemble forecast; individual model comparisons in secondary tab).

**Stack:** Dash 4.0.x, Plotly 6.6.0, dcc.Store for preprocessed aggregates, scattergl for high-point-count series.

**Research flag:** STANDARD PATTERNS — Dash callback architecture and Plotly fan charts are well-documented. PDF export mechanism (Phase 5 dependency) should be prototyped early to confirm WeasyPrint integration works before the dashboard layout is finalized.

---

### Phase 5: PDF Report and Methodology Paper

**Rationale:** Report generation requires a stable dashboard layout (to capture chart outputs) and complete model validation (to report defensible metrics). The methodology paper is the content artifact that makes this a published piece of economic research rather than a data science exercise. It is sequentially last but must be planned for from the start (documented assumptions, writeup-ready SHAP plots, LaTeX-exportable statsmodels summaries).

**Delivers:** WeasyPrint-rendered PDF report with methodology, charts (static PNG via Kaleido), and projections; Jinja2 HTML templates; methodology paper draft for LinkedIn publication; nbconvert-exported notebooks as supplementary material; README finalization.

**Addresses features:** Exportable PDF report, methodology paper / LinkedIn writeup, bottom-up cross-validation summary (if completed in v1.x), documented assumptions artifact.

**Avoids pitfalls:** Forecast communication in static outputs (paper uses hedged language, reports prediction intervals explicitly, includes changepoint analysis figure, documents survivorship bias limitation).

**Stack:** WeasyPrint 68.x, Jinja2 3.1.x, Kaleido 0.2.x, matplotlib 3.10.x (300 DPI for publication figures), nbconvert 7.x.

**Research flag:** STANDARD PATTERNS — WeasyPrint + Jinja2 for HTML-to-PDF is well-documented. Confirm Kaleido version compatibility with Plotly 6.6.x early (Kaleido 0.2.x has known version-pinning sensitivity).

---

### Phase Ordering Rationale

- **Data before models:** The architecture has a strict one-way data flow. No modeling work is recoverable if the upstream data contains nominal/real conflation or undefined boundaries — full retrain required.
- **Statistical before ML:** The two-stage hybrid pattern requires statistical residuals as ML training input. This is not convention; it is a hard dependency.
- **Models before dashboard:** Pre-computed artifacts are the contract between modeling and presentation. Building Dash callbacks before the forecast artifact schema is stable requires rework.
- **Reports last:** Report generation synthesizes all prior phases. The content of the methodology paper depends on having final metrics and validated forecasts.
- **Notebooks throughout:** Exploratory Jupyter notebooks run in parallel with each phase (01_data_exploration, 02_baseline_models, 03_ml_layer, 04_evaluation) but production logic always lives in `src/`.

### Research Flags

Phases needing deeper research during planning:
- **Phase 1:** Validate specific World Bank/OECD indicator codes for AI industry proxies before writing ingestion config. Confirm eurostat package works with new Eurostat dissemination API for relevant indicators.
- **Phase 3:** Decide on ensemble weighting strategy (fixed alpha, stacking, or dynamic weighting) and document rationale. Research conformal prediction intervals for gradient boosting as an alternative to quantile regression.

Phases with standard, well-documented patterns:
- **Phase 2:** ARIMA/Prophet on economic time series — established methodology with extensive documentation.
- **Phase 4:** Dash 4.0.x callback architecture — official documentation is comprehensive and current.
- **Phase 5:** WeasyPrint + Jinja2 — mature combination with good examples; prototype PDF export early as a risk mitigation step.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All library versions verified via PyPI and official docs. Compatibility matrix explicitly validated (statsmodels 0.14.6 + pandas 3.0 fix is a documented release note). One caveat: Kaleido/Plotly 6.6.x compatibility should be verified in a spike before relying on PDF export. |
| Features | MEDIUM-HIGH | Must-have features are well-grounded in econometric and data science practice. Differentiator features (SHAP, scenarios) have clear precedent. The bottom-up/top-down cross-validation complexity depends on data availability that cannot be fully assessed without API exploration. |
| Architecture | MEDIUM-HIGH | FTI pipeline and hybrid statistical+ML pattern are supported by peer-reviewed literature (PMC and MDPI sources). The specific ensemble weighting approach is a design decision that requires empirical validation during Phase 3. |
| Pitfalls | HIGH | Critical pitfalls are verified across multiple primary and peer-reviewed sources. The data leakage pitfall has specific arXiv citation (arXiv:2512.06932). Market boundary definitional variance is confirmed by comparing published 2025 market estimates across major research firms. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **AI industry proxy indicators:** The specific World Bank and OECD indicator codes that best proxy for AI industry GDP contribution (R&D expenditure, patent filings, ICT sector revenue, semiconductor shipments) need empirical validation against actual API availability during Phase 1. Some candidate indicators may not have sufficient historical coverage (pre-2010).
- **Bottom-up data availability:** Free data sources for bottom-up company revenue aggregation (beyond SEC EDGAR for US public companies) are uncertain. Crunchbase free tier has limited historical depth. This risk should be flagged in the Phase 1 data design document.
- **Ensemble weighting calibration:** The `alpha` parameter in the hybrid ensemble (`alpha * stat_pred + (1-alpha) * ml_correction`) is a methodology decision. Research suggests hybrid consistently wins but does not prescribe a weighting method. Treat as an empirical decision in Phase 3 with documented rationale.
- **WeasyPrint/Kaleido integration:** PDF export with embedded Plotly charts via Kaleido is a known complexity point (cited in Plotly community forum). Run a spike in Phase 4 before building the full reporting pipeline in Phase 5.

---

## Sources

### Primary (HIGH confidence)
- PyPI official pages — statsmodels 0.14.6, scikit-learn 1.8.0, LightGBM 4.6.0, Plotly 6.6.0, Dash 4.0.x, WeasyPrint 68.1
- pandas official release notes — v3.0.0 (CoW semantics, January 2026)
- Astral uv official docs — project management and lockfile guide
- SHAP official documentation — feature attribution API
- Facebook Prophet official docs — cross-validation, changepoint tuning, diagnostics
- World Bank Open Data — primary data source
- OECD Data Explorer — primary data source
- Cookiecutter Data Science (DrivenData) — canonical project structure
- arXiv:2512.06932 — time series data leakage in LSTM evaluation

### Secondary (MEDIUM confidence)
- PMC 12294620 — hybrid statistical + deep learning residual correction framework
- MDPI 2225-1146/13/4/52 — econometric + Python forecasting pipeline patterns
- Hopsworks FTI pipeline pattern — Feature/Training/Inference separation
- Grand View Research / Statista AI market estimates — used to validate market boundary definitional variance
- Plotly community forum — PDF export implementation patterns
- World Bank blog — wbgapi introduction and usage

### Tertiary (LOW confidence)
- Medium: pandas 3.0 CoW migration guide — cross-referenced against official release notes; use official docs as authoritative source
- Worldmetrics: Top 10 Economic Modeling Software 2026 — aggregator site; do not rely for decisions

---
*Research completed: 2026-03-17*
*Ready for roadmap: yes*
