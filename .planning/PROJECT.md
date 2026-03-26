# Industry Value Estimator

## What This Is

An analyst's best friend for AI industry valuation — a data-driven tool that estimates real AI market size, attributes AI revenue within mixed-tech conglomerates, and forecasts sector growth to 2030. Combines real market data from SEC EDGAR filings, analyst consensus (IDC, Gartner, Grand View Research + 5 others), and hybrid statistical/ML models (Prophet + LightGBM). Features a three-tier dashboard (Basic/Normal/Expert) with LOO cross-validation, benchmark comparisons, and honest model limitations.

## Core Value

Be an analyst's best friend: produce AI industry valuations and growth forecasts grounded in real market data that people can actually trust and act on.

## Current State (v1.1 shipped 2026-03-26)

- **Data pipeline:** 5 sources (World Bank, OECD, LSEG, SEC EDGAR, Analyst Corpus) → validated Parquet cache
- **Analyst corpus:** 100+ hand-curated estimates from 8 firms with scope normalization and vintage tracking
- **EDGAR integration:** 14 companies, 2,652 filings with XBRL revenue extraction
- **Revenue attribution:** 15 public companies with uncertainty bounds, 18 private companies with confidence tiers
- **Statistical models:** Per-segment Prophet + ARIMA with observation weighting (real 3x, interpolated 1x)
- **ML ensemble:** LightGBM residual boosting with L1/L2 regularization, early stopping, quantile CIs
- **Consensus calibration:** Configurable CAGR floors + 50/50 model/consensus blend (all params in ai.yaml)
- **Backtesting:** LOO cross-validation + EDGAR hard actuals + 3 benchmark models (naive, random walk, consensus)
- **Dashboard:** 5-tab Dash app (Basic/Overview/Segments/Drivers/Diagnostics), three-tier with loading states
- **Stats:** ~90 Python files, 16,000+ LOC, 389+ tests, ~190 commits

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
- ✓ Market boundary definition locked with analyst scope mapping — v1.1
- ✓ Published analyst estimate corpus (8 firms, vintage tracking) — v1.1
- ✓ SEC EDGAR company filings ingestion (14 companies) — v1.1
- ✓ Historical ground truth time series (2017-2025) — v1.1
- ✓ Anchored market size model replacing PCA composite — v1.1
- ✓ AI revenue attribution for 15 mixed-tech public companies — v1.1
- ✓ Private company valuation registry (18 companies, comparable multiples) — v1.1
- ✓ Value chain layer taxonomy preventing double-counting — v1.1
- ✓ Realistic forecast trajectories with consensus calibration — v1.1
- ✓ Walk-forward backtesting with real MAPE/R² — v1.1
- ✓ Basic dashboard tier (3 hero KPIs, segment chart, fan chart) — v1.1
- ✓ Analyst consensus panel (model vs published range) — v1.1
- ✓ Revenue multiples reference table — v1.1
- ✓ Normal/Expert modes updated with real USD — v1.1
- ✓ Data vintage and methodology transparency throughout — v1.1

### Active

(None — v1.1 complete. Define v1.2 requirements via `/gsd:new-milestone`)

### Out of Scope

- Multiple industries beyond AI — expand later (ARCH-01 extensibility built)
- Real-time streaming data — batch processing sufficient
- Mobile-responsive design — desktop browser target
- User authentication / multi-user features — personal tool
- Scenario analysis with interactive sliders — v2 feature (SCEN-01)
- Bottom-up cross-validation from individual company filings — requires broader EDGAR coverage

## Context

- Inspired by a conversation with a quant risk manager who noted that AI industry valuations lack rigorous methodology
- Economics background + building coding/data science skills — documentation serves dual purpose: project docs AND personal learning resource
- Portfolio/showcase project for LinkedIn and potential employers
- Passed three J.P. Morgan-standard reviews (quant model audit, code review, UX review) with targeted fixes
- GitHub: https://github.com/amicusDei/industry-value-estimator
- Python ecosystem: pandas 3.0, statsmodels, Prophet, LightGBM, SHAP, Plotly/Dash, edgartools, WeasyPrint

## Constraints

- **Tech stack**: Python (uv-managed, 131+ locked packages)
- **Data**: World Bank + OECD (public) + LSEG Workspace (subscription) + SEC EDGAR (free) + Analyst corpus (hand-curated)
- **Documentation**: Tutorial-style docstrings + ASSUMPTIONS.md + METHODOLOGY.md + ARCHITECTURE.md
- **Architecture**: Config-driven extensibility via `config/industries/` YAML files
- **Model calibration**: All constants in `ai.yaml model_calibration` section with documented sources
- **Audience**: Portfolio-quality — clean, well-structured, explainable, honest about limitations

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hybrid approach (statistical + ML) | Statistical models provide interpretable baselines; ML adds predictive power | ✓ Good — per-segment Prophet + LightGBM ensemble |
| Start with AI industry only | Focused scope prevents sprawl | ✓ Good — extensibility proven |
| Python over R | Stronger ecosystem for dashboards and production code | ✓ Good — Dash/Plotly dashboard |
| Dashboard + Reports + Paper | Triple output maximizes portfolio impact | ✓ Good — all three delivered |
| PCA composite index (v1.0) | Data-driven weights for proxy indicators | ⚠️ Replaced in v1.1 — proxy indicators don't measure AI revenue |
| Value chain multiplier (v1.0) | Converts composite index to USD market size | ⚠️ Deleted in v1.1 — replaced by direct USD model |
| Normal/Expert mode toggle | Two audiences: executives vs technical reviewers | ✓ Good — extended to three tiers (Basic/Normal/Expert) |
| Ground-up model rework (v1.1) | v1.0 PCA produced flat/unrealistic forecasts | ✓ Good — real USD anchored model with consensus calibration |
| Real market data anchoring (v1.1) | Published estimates + company filings as ground truth | ✓ Good — 8 analyst firms, EDGAR integration |
| Three-tier dashboard (v1.1) | Basic tier for quick market intelligence | ✓ Good — Basic/Normal/Expert progressive disclosure |
| LOO cross-validation (v1.1) | Non-circular backtesting for all segments | ✓ Good — beats naive, random walk, and consensus benchmarks |
| Consensus calibration (v1.1) | Model CAGR too low with 9 data points; 50/50 blend with analyst floors | ⚠️ Documented trade-off — forecasts are partly policy-driven |
| Observation weighting via duplication (v1.1) | Prophet/ARIMA don't support sample_weight; 3x real data duplication | ✓ Acceptable workaround — documented limitation |

---
*Last updated: 2026-03-26 after v1.1 milestone*
