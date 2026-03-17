# Requirements: Industry Value Estimator

**Defined:** 2026-03-17
**Core Value:** Produce defensible, data-driven AI industry valuations and growth forecasts that go beyond rough estimates — combining econometric rigor with modern ML techniques.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Pipeline

- [x] **DATA-01**: Define AI industry market boundary (what sectors, companies, and activities count as "AI")
- [x] **DATA-02**: Define AI use cases taxonomy for structuring the analysis
- [ ] **DATA-03**: Ingest economic data from World Bank API (GDP, R&D expenditure, ICT indicators)
- [ ] **DATA-04**: Ingest economic data from OECD API (technology indicators, patent data)
- [x] **DATA-05**: Ingest financial data from LSEG Workspace API (company-level data, market data)
- [ ] **DATA-06**: Clean and normalize all data (currency conversion to constant USD, missing value handling, frequency alignment)
- [ ] **DATA-07**: Display data source attribution on every chart and report output
- [x] **DATA-08**: Comprehensive documentation explaining each data source, why it was chosen, and how it's processed

### Modeling

- [ ] **MODL-01**: Build statistical baseline model (ARIMA and/or OLS regression) for AI market size estimation
- [ ] **MODL-02**: Build ML refinement model (LightGBM) trained on statistical model residuals
- [ ] **MODL-03**: Create hybrid ensemble combining statistical and ML outputs with documented weighting
- [ ] **MODL-04**: Generate market size point estimates with units and vintage date
- [ ] **MODL-05**: Generate growth forecasts with calibrated confidence intervals (80%/95%)
- [ ] **MODL-06**: Implement temporal cross-validation (expanding window, no data leakage)
- [ ] **MODL-07**: Compute SHAP values showing which variables drive forecasts
- [ ] **MODL-08**: Handle structural breaks (2022-23 GenAI surge) explicitly in models
- [ ] **MODL-09**: Document all model assumptions, choices, and mathematical foundations

### Presentation

- [ ] **PRES-01**: Interactive Dash dashboard with time series charts and forecast fan charts
- [ ] **PRES-02**: SHAP driver attribution visualization in dashboard
- [ ] **PRES-03**: Model diagnostics display (RMSE, MAPE, R², residual plots, backtesting results)
- [ ] **PRES-04**: Exportable PDF report with analysis and projections
- [ ] **PRES-05**: Methodology paper suitable for LinkedIn publication

### Architecture & Documentation

- [x] **ARCH-01**: Config-driven extensible pipeline (add new industries via config, not code rewrite)
- [ ] **ARCH-02**: Comprehensive code documentation explaining every module and function for learning purposes
- [ ] **ARCH-03**: Polished GitHub README with project description, data sources, setup instructions
- [ ] **ARCH-04**: Documented assumptions file explaining all modeling decisions and their rationale

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Scenarios & Sensitivity

- **SCEN-01**: Scenario / sensitivity analysis with interactive sliders (conservative/base/optimistic)

### Cross-Validation

- **BOTT-01**: Bottom-up cross-validation estimate from company filings and patent rollups

### Data Management

- **FRES-01**: Data freshness tracking and last-updated indicator in dashboard

### Industry Expansion

- **IND2-01**: Second industry coverage (cloud computing, biotech, or similar)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-time data streaming | Macro economic data updates quarterly/annually; batch processing is sufficient |
| User authentication / multi-user | Personal portfolio tool; no multi-user needs |
| Mobile-responsive design | Desktop browser is the target audience |
| LLM-generated reports | Shifts focus from econometric rigor to prompt engineering; undermines credibility |
| CI/CD deployment pipeline | Docker + local instructions sufficient for portfolio project |
| Proprietary/paid data (beyond LSEG) | LSEG access provided; no additional paid sources for v1 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 1 | Complete |
| DATA-06 | Phase 1 | Pending |
| DATA-07 | Phase 4 | Pending |
| DATA-08 | Phase 1 | Pending |
| MODL-01 | Phase 2 | Pending |
| MODL-02 | Phase 3 | Pending |
| MODL-03 | Phase 3 | Pending |
| MODL-04 | Phase 3 | Pending |
| MODL-05 | Phase 3 | Pending |
| MODL-06 | Phase 2 | Pending |
| MODL-07 | Phase 3 | Pending |
| MODL-08 | Phase 2 | Pending |
| MODL-09 | Phase 2 | Pending |
| PRES-01 | Phase 4 | Pending |
| PRES-02 | Phase 4 | Pending |
| PRES-03 | Phase 4 | Pending |
| PRES-04 | Phase 5 | Pending |
| PRES-05 | Phase 5 | Pending |
| ARCH-01 | Phase 1 | Pending |
| ARCH-02 | Phase 5 | Pending |
| ARCH-03 | Phase 5 | Pending |
| ARCH-04 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-17*
*Last updated: 2026-03-17 after roadmap creation — all 26 requirements mapped*
