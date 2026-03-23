# Industry Value Estimator

## What This Is

An analyst's best friend for AI industry valuation — a data-driven tool that estimates real AI market size, attributes AI revenue within mixed-tech conglomerates, and forecasts sector growth to 2030. Features a three-tier dashboard (Basic/Normal/Expert), exportable PDF reports, and a methodology paper. Built to produce numbers that pass the sniff test against known benchmarks.

## Core Value

Be an analyst's best friend: produce AI industry valuations and growth forecasts grounded in real market data that people can actually trust and act on.

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

- [ ] Rework model from ground up — anchor on real market data (published estimates, company filings with AI revenue attribution, DCF/multiplier models for private companies)
- [ ] AI revenue attribution for mixed-tech public companies (isolate AI portion from conglomerates)
- [ ] Handle private company valuation opacity (DCF, AI value multipliers, revenue proxies)
- [ ] Backtesting and validation against known market sizes and analyst consensus
- [ ] Fix diagnostics — real actuals so MAPE, R², and other metrics compute
- [ ] Realistic forecast trajectories reflecting actual AI industry growth
- [ ] New Basic dashboard tier — total AI market cap, growth rates, expected value, segment breakdown
- [ ] Update Normal/Expert modes to reflect real model outputs

### Out of Scope

- Multiple industries beyond AI — expand later after AI model is proven (ARCH-01 extensibility is built)
- Real-time streaming data — batch processing is sufficient
- Mobile-responsive design — desktop browser is the target
- User authentication / multi-user features — personal tool
- Scenario analysis with interactive sliders — v2 feature (SCEN-01)

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
| v1.1: Ground-up model rework | v1.0 PCA composite approach produced flat/unrealistic forecasts; proxy indicators don't measure AI revenue | — Pending |
| v1.1: Real market data anchoring | Published estimates + company filings as ground truth; econometric indicators as explanatory drivers | — Pending |
| v1.1: Three-tier dashboard | Basic tier for quick market intelligence; Normal/Expert for depth | — Pending |

## Current Milestone: v1.1 Model Credibility & Usability

**Goal:** Rework the model from ground up to produce trustworthy, real-world AI valuations — and add a Basic dashboard tier that makes the output immediately useful to any analyst.

**Target features:**
- Ground-up model rebuild anchored on real market data
- AI revenue attribution for mixed-tech companies and private company valuation
- Backtesting with real actuals (working MAPE, R², diagnostics)
- Basic dashboard tier (market cap, growth rates, expected value)
- Updated Normal/Expert views with credible outputs

---
*Last updated: 2026-03-23 after v1.1 milestone started*
