# Industry Value Estimator

## What This Is

A hybrid statistical and machine learning system that estimates AI industry market size and forecasts growth to 2030 — combining World Bank, OECD, and LSEG data with ARIMA/Prophet baselines and LightGBM ensemble refinement. Features an interactive Dash dashboard with Normal/Expert modes, exportable PDF reports, and a methodology paper for LinkedIn.

## Core Value

Produce defensible, data-driven AI industry valuations and growth forecasts that go beyond rough estimates — combining econometric rigor with modern ML techniques.

## Current State (v1.0 shipped 2026-03-23)

- **Data pipeline:** 3 sources (World Bank, OECD MSTI, LSEG Workspace) → validated Parquet cache in 2020 constant USD
- **Statistical models:** Per-segment ARIMA/Prophet with structural break detection (CUSUM/Chow), PCA composite index
- **ML ensemble:** LightGBM residual boosting with quantile regression CIs (80%/95%), inverse-RMSE per-segment weighting
- **Dashboard:** 4-tab Dash app (Overview/Segments/Drivers/Diagnostics), Normal/Expert modes, value chain multiplier
- **Portfolio:** 2 PDF reports (executive brief + full analytical), LinkedIn methodology paper, tutorial docstrings, polished README
- **Stats:** 75 Python files, 11,398 LOC, 233 tests, 119 commits

## Requirements

### Validated

- ✓ Collect and normalize AI industry data from World Bank, OECD, LSEG — v1.0
- ✓ Build statistical baseline models (ARIMA, Prophet, OLS regression) — v1.0
- ✓ Layer ML model (LightGBM) for refined forecasting — v1.0
- ✓ Generate market size estimates with units and data vintage date — v1.0
- ✓ Generate growth forecasts with calibrated 80%/95% confidence intervals — v1.0
- ✓ SHAP driver attribution showing which variables drive forecasts — v1.0
- ✓ Interactive Dash dashboard with fan charts and model diagnostics — v1.0
- ✓ Exportable PDF reports (executive brief + full analytical) — v1.0
- ✓ Comprehensive tutorial-style documentation — v1.0
- ✓ Polished GitHub repo with README, architecture guide, methodology paper — v1.0

### Active

(None — v1.0 complete. Define v1.1 requirements via `/gsd:new-milestone`)

### Out of Scope

- Multiple industries beyond AI — expand later after AI model is proven (ARCH-01 extensibility is built)
- Real-time streaming data — batch processing is sufficient
- Mobile-responsive design — desktop browser is the target
- User authentication / multi-user features — personal tool
- Scenario analysis with interactive sliders — v2 feature (SCEN-01)
- Bottom-up cross-validation from company filings — v2 feature (BOTT-01)

## Context

- Inspired by a conversation with a quant risk manager who noted that AI industry valuations lack rigorous methodology
- Economics background + building coding/data science skills — documentation serves dual purpose: project docs AND personal learning resource
- Portfolio/showcase project for LinkedIn and potential employers
- GitHub: https://github.com/amicusDei/industry-value-estimator
- Python ecosystem: pandas 3.0, statsmodels, Prophet, LightGBM, SHAP, Plotly/Dash, WeasyPrint

## Constraints

- **Tech stack**: Python (uv-managed, 131 locked packages)
- **Data**: World Bank + OECD (public) + LSEG Workspace (subscription)
- **Documentation**: Tutorial-style docstrings + ASSUMPTIONS.md + METHODOLOGY.md + ARCHITECTURE.md
- **Architecture**: Config-driven extensibility via `config/industries/` YAML files
- **Audience**: Portfolio-quality — clean, well-structured, explainable

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hybrid approach (statistical + ML) | Statistical models provide interpretable baselines; ML adds predictive power | ✓ Good — per-segment ARIMA/Prophet + LightGBM ensemble works well |
| Start with AI industry only | Focused scope prevents sprawl | ✓ Good — extensibility proven with dummy industry test |
| Python over R | Stronger ecosystem for dashboards and production code | ✓ Good — Dash/Plotly dashboard works smoothly |
| Dashboard + Reports + Paper | Triple output maximizes portfolio impact | ✓ Good — all three delivered |
| PCA composite index | Data-driven weights for proxy indicators | ✓ Good — with manual weights sensitivity check |
| Quantile regression for CIs | Directly produces interval bounds without distributional assumptions | ✓ Good — 80%/95% intervals |
| Value chain multiplier | Converts composite index to USD market size | ⚠️ Revisit — calibration depends on anchor estimate accuracy |
| Normal/Expert mode toggle | Two audiences: executives vs technical reviewers | ✓ Good — clean separation of content depth |

---
*Last updated: 2026-03-23 after v1.0 milestone*
