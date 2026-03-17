# Industry Value Estimator

## What This Is

A hybrid statistical and machine learning model that estimates market size and forecasts growth for the AI industry — addressing the gap where emerging tech sectors are largely "valued by thumb" in economic markets. Built as a Python application with an interactive dashboard and exportable reports, designed to expand to additional industries over time.

## Core Value

Produce defensible, data-driven AI industry valuations and growth forecasts that go beyond rough estimates — combining econometric rigor with modern ML techniques.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Collect and normalize AI industry data from public sources (World Bank, OECD, Eurostat)
- [ ] Collect supplementary data via financial APIs and web scraping (company filings, market reports)
- [ ] Build statistical baseline models (time series, regression) for market size estimation
- [ ] Layer ML models (gradient boosting, neural nets) for refined forecasting
- [ ] Generate market size estimates (total revenue/GDP contribution) for AI industry
- [ ] Generate growth forecasts with confidence intervals (e.g., "AI worth $X by 2030")
- [ ] Interactive dashboard with charts and tables (Dash/Plotly)
- [ ] Exportable reports/PDFs with analysis and projections
- [ ] Comprehensive documentation explaining every component, model, and decision
- [ ] Polished GitHub repo with clean code, notebooks, and README
- [ ] Methodology paper/writeup suitable for LinkedIn publishing

### Out of Scope

- Multiple industries beyond AI — expand later after AI model is proven
- Real-time streaming data — batch processing is sufficient for v1
- Mobile app — web dashboard is the interface
- User authentication / multi-user features — personal tool
- Proprietary/paid data sources — public and free APIs only for v1

## Context

- Inspired by a conversation with a quant risk manager who noted that AI industry valuations lack rigorous methodology
- The user has an economics background and is building coding/data science skills — documentation serves dual purpose: project docs AND personal learning resource
- This is a portfolio/showcase project for LinkedIn and potential employers
- Python ecosystem: pandas, scikit-learn, statsmodels, Prophet, Plotly/Dash
- Starting with AI industry provides a focused scope; the architecture should allow adding industries later without major refactoring

## Constraints

- **Tech stack**: Python — user's chosen language, strong ecosystem for data science and econometrics
- **Data**: Public/free sources only — World Bank, OECD, Eurostat, free financial APIs
- **Documentation**: Every module, model choice, and data pipeline step must be thoroughly documented with explanations aimed at someone learning the technical implementation
- **Architecture**: Must be extensible to additional industries without rewriting core logic
- **Audience**: Code and docs should be portfolio-quality — clean, well-structured, explainable

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hybrid approach (statistical + ML) | Statistical models provide interpretable baselines; ML adds predictive power. Best of both worlds for a portfolio piece | — Pending |
| Start with AI industry only | Focused scope prevents sprawl; AI is the most interesting case given current "valued by thumb" problem | — Pending |
| Python over R | User preference; stronger ecosystem for building web dashboards and production-quality code | — Pending |
| Dashboard + Reports + Paper | Triple output maximizes portfolio impact and demonstrates end-to-end capability | — Pending |

---
*Last updated: 2026-03-17 after initialization*
