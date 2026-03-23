# Roadmap: Industry Value Estimator

## Overview

This project builds bottom-up, following the strict architectural dependency chain that the domain requires. A validated data pipeline feeds a statistical baseline, which feeds an ML correction layer, which feeds an ensemble that produces the forecast artifacts that the dashboard and reports consume. Each phase delivers a testable, verifiable capability before the next phase begins. The result is a defensible, data-driven AI industry valuation system with an interactive dashboard, exportable PDF reports, and a methodology paper ready for LinkedIn publication.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Data Foundation** - Build the validated, normalized data pipeline for all AI industry indicators (completed 2026-03-18)
- [x] **Phase 2: Statistical Baseline** - Fit interpretable econometric models and establish the baseline forecast (gap closure in progress) (completed 2026-03-22)
- [x] **Phase 3: ML Ensemble and Validation** - Train the ML refinement layer, build the ensemble, and produce forecast artifacts (completed 2026-03-22)
- [x] **Phase 4: Interactive Dashboard** - Build the Dash dashboard that reads pre-computed forecast artifacts (completed 2026-03-22)
- [x] **Phase 5: Reports, Paper, and Portfolio** - Generate PDF reports, write the methodology paper, and finalize the GitHub portfolio (completed 2026-03-23)

## Phase Details

### Phase 1: Data Foundation
**Goal**: Clean, validated, inflation-adjusted AI industry data is available as a local Parquet cache ready for modeling
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07, DATA-08, ARCH-01
**Success Criteria** (what must be TRUE):
  1. Running the ingestion pipeline produces a local Parquet cache of raw data from World Bank, OECD, and LSEG without errors
  2. All monetary series are deflated to constant-year USD and column names encode the real/nominal distinction (e.g., `revenue_usd_real_2020`)
  3. Schema validation tests run after every fetch and reject malformed API responses before they corrupt the dataset
  4. The AI industry market boundary (which sectors and activities count as "AI") is locked in a config file and every dataset row carries an industry tag
  5. A second industry can be added by dropping a new YAML file into `config/industries/` without modifying pipeline code
**Plans:** 5/5 plans complete

Plans:
- [x] 01-01-PLAN.md — Project scaffold, config, AI boundary YAML, validation schemas, METHODOLOGY.md
- [ ] 01-02-PLAN.md — World Bank and OECD ingestion connectors
- [ ] 01-03-PLAN.md — LSEG Workspace ingestion connector
- [ ] 01-04-PLAN.md — Processing pipeline (deflation, interpolation, tagging, normalization)
- [ ] 01-05-PLAN.md — Pipeline orchestrator, extensibility verification, documentation

### Phase 2: Statistical Baseline
**Goal**: Interpretable econometric models produce AI market size baselines and residuals, with documented assumptions and structural break analysis
**Depends on**: Phase 1
**Requirements**: MODL-01, MODL-06, MODL-08, MODL-09, ARCH-04
**Success Criteria** (what must be TRUE):
  1. ARIMA and/or Prophet models fit on the processed data and produce out-of-sample forecasts with documented fit metrics (RMSE, MAPE, R²)
  2. A structural break test (Chow or CUSUM) is run before model selection and the 2022–2024 GenAI surge is handled explicitly in the chosen model
  3. Temporal cross-validation uses an expanding window with no data leakage — all preprocessors are fit only on training data
  4. A documented assumptions file exists that explains every modeling decision, parameter choice, and mathematical foundation in plain language
**Plans:** 5/5 plans complete

Plans:
- [ ] 02-01-PLAN.md — Dependencies, diagnostics package (structural breaks + model eval metrics)
- [ ] 02-02-PLAN.md — Feature engineering (PCA composite, stationarity), OLS regression, temporal CV helper
- [ ] 02-03-PLAN.md — ARIMA + Prophet per-segment fitting, model comparison, residual Parquet output
- [ ] 02-04-PLAN.md — ASSUMPTIONS.md documentation with automated completeness tests
- [ ] 02-05-PLAN.md — Gap closure: pipeline runner to persist residuals_statistical.parquet

### Phase 3: ML Ensemble and Validation
**Goal**: A hybrid statistical + ML ensemble produces the final AI market size estimates and 2030 growth forecasts with calibrated confidence intervals
**Depends on**: Phase 2
**Requirements**: MODL-02, MODL-03, MODL-04, MODL-05, MODL-07
**Success Criteria** (what must be TRUE):
  1. A LightGBM model trains on the statistical model's residuals and improves out-of-sample forecast accuracy versus the statistical baseline alone
  2. The ensemble combiner blends statistical and ML outputs with a documented, justified weighting approach and produces market size point estimates with units and data vintage date
  3. Growth forecasts to 2030 include calibrated 80% and 95% confidence intervals — no bare point forecasts are exposed as outputs
  4. SHAP values are computed and show which variables (R&D spend, patent filings, VC investment) drive the forecast
  5. Serialized model artifacts are saved to `models/ai_industry/` and can be loaded by the inference engine without re-training
**Plans:** 3/3 plans complete

Plans:
- [ ] 03-01-PLAN.md — LightGBM point estimator, feature engineering, quantile models for CI bounds
- [ ] 03-02-PLAN.md — Ensemble combiner, forecast engine with dual units and vintage, SHAP attribution
- [ ] 03-03-PLAN.md — Pipeline runner script, model serialization, integration verification

### Phase 4: Interactive Dashboard
**Goal**: A Dash dashboard displays the pre-computed forecast artifacts with interactive charts, driver attribution, and model diagnostics
**Depends on**: Phase 3
**Requirements**: PRES-01, PRES-02, PRES-03, DATA-07
**Success Criteria** (what must be TRUE):
  1. The dashboard loads in a browser and displays a time series chart and forecast fan chart with 80%/95% confidence interval bands without triggering any model re-training
  2. A SHAP driver attribution panel shows which variables contribute most to the current forecast period
  3. Model diagnostics (RMSE, MAPE, R², residual plots, backtesting results) are visible in the dashboard
  4. Every chart and table displays the data source attribution (World Bank, OECD, LSEG) so outputs are self-documenting
**Plans:** 3/3 plans complete

Plans:
- [ ] 04-01-PLAN.md — Dashboard package scaffold, data layer, chart builders (fan chart + backtest), test suite
- [ ] 04-02-PLAN.md — Tab layouts (Overview, Segments, Drivers, Diagnostics), callbacks, attribution footnotes, run script
- [ ] 04-03-PLAN.md — Visual verification checkpoint (human approval of running dashboard)

### Phase 5: Reports, Paper, and Portfolio
**Goal**: A portfolio-quality GitHub repository exists with a PDF report, methodology paper ready for LinkedIn, comprehensive code documentation, and a polished README
**Depends on**: Phase 4
**Requirements**: PRES-04, PRES-05, ARCH-02, ARCH-03
**Success Criteria** (what must be TRUE):
  1. Running the report generator produces a PDF that contains the forecast fan chart, market size estimate, confidence intervals, and data source attribution — rendered from the same forecast artifacts as the dashboard
  2. A methodology writeup exists that explains the hybrid model approach, data sources, validation strategy, and key findings in language suitable for LinkedIn publication
  3. Every module and function in `src/` has docstrings that explain what it does, why the approach was chosen, and any domain-specific concepts — readable by someone learning the implementation
  4. The GitHub README includes project description, data sources, setup instructions with the exact commands to reproduce the pipeline, and example output images
**Plans:** 4/4 plans complete

Plans:
- [ ] 05-01-PLAN.md — Install dependencies (WeasyPrint, kaleido), run full pipeline with real API data
- [ ] 05-02-PLAN.md — Tutorial-style docstrings for all src/ modules, architecture guide
- [ ] 05-03-PLAN.md — PDF report generation (executive brief + full analytical report)
- [ ] 05-04-PLAN.md — LinkedIn methodology paper, GitHub README, dashboard screenshot

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 5/5 | Complete   | 2026-03-18 |
| 2. Statistical Baseline | 5/5 | Complete   | 2026-03-22 |
| 3. ML Ensemble and Validation | 3/3 | Complete   | 2026-03-22 |
| 4. Interactive Dashboard | 3/3 | Complete   | 2026-03-22 |
| 5. Reports, Paper, and Portfolio | 4/4 | Complete   | 2026-03-23 |
