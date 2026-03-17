# Feature Research

**Domain:** AI Industry Economic Valuation and Forecasting Tool
**Researched:** 2026-03-17
**Confidence:** MEDIUM-HIGH

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that anyone evaluating this tool — employer, recruiter, collaborator, or analyst — expects to see. Missing these makes the project feel unfinished or academically naive.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Data ingestion from public APIs (World Bank, OECD) | Any credible economic model must show where its data comes from. Using well-known authoritative sources is the baseline for defensibility. | MEDIUM | World Bank and OECD both have free REST APIs. wbdata and pandasdmx libraries handle this in Python. Need to handle rate limits, schema drift, and missing years. |
| Data cleaning and normalization pipeline | Raw public data has gaps, unit inconsistencies, and different base years. Users expect a documented pipeline, not raw CSVs fed straight into models. | MEDIUM | pandas is standard; must handle currency normalization (constant vs. current USD), missing value imputation, and frequency alignment (annual/quarterly). |
| Baseline statistical model (time series or regression) | Econometric credibility requires at least one interpretable statistical model. Economists expect ARIMA, OLS, or similar before ML is layered on. | MEDIUM | statsmodels for OLS/ARIMA. This is also the interpretability anchor — the model someone can reason about without a ML background. |
| Market size point estimate with units | The product's stated output. A number — "AI market worth $X in 2026" — with clear units (USD billions, constant year). | LOW | Trivial to compute once models exist. Complexity is in the model, not the output. |
| Growth forecast with confidence intervals | "AI worth $X by 2030" with a range. Confidence intervals are not optional — presenting a point forecast only is considered bad statistical practice. | MEDIUM | Statsmodels and Prophet both emit CIs natively. Must decide: 80% CI, 90% CI, or 95% CI — document the choice. |
| Interactive dashboard with charts | Plotly/Dash is the specified stack. Users expect to interact with outputs — zoom, filter by year, toggle scenarios. A static plot is insufficient. | MEDIUM | Dash is well-suited. Core charts: time series of historical data, forecast fan chart with CI bands, market segment breakdown. |
| Data source attribution in UI and reports | Every chart must show its data source. Omitting attribution undermines credibility and violates norms for publicly published economic analysis. | LOW | Simple footer/annotation on charts. Critical for LinkedIn publication and portfolio credibility. |
| Exportable PDF report | Stated in PROJECT.md requirements. Users of forecasting tools expect a shareable artifact, not just a web page. | MEDIUM | PDF export in open-source Dash requires WeasyPrint or ReportLab + a separate render step. Dash Enterprise has native PDF, but open-source requires workaround. Flag as an implementation risk. |
| Documented assumptions | Every model makes assumptions (growth drivers, data completeness, model form). Documenting them is table stakes for any published economic analysis — without this, the work cannot be critiqued or reproduced. | LOW | Markdown or docstring documentation. High value, low cost. |
| README with setup instructions | Portfolio requirement. Anyone landing on the GitHub repo expects to understand what the project does and how to run it within 60 seconds. | LOW | Standard README: project description, data sources, installation, how to run dashboard. |

---

### Differentiators (Competitive Advantage)

Features that distinguish this project from generic "market sizing" notebooks on GitHub — and from the rough "valued by thumb" estimates the project explicitly aims to replace.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Hybrid statistical + ML ensemble | Most public forecasting projects choose one paradigm. A model that runs statsmodels ARIMA as the interpretable baseline and XGBoost/gradient boosting as the ML refinement, then reconciles outputs, is methodologically more sophisticated than either alone. | HIGH | Requires model reconciliation logic. The ensemble approach — and how the two outputs are weighted — must itself be documented as a methodology decision. |
| SHAP-based driver attribution | Showing *which variables* drive the AI market forecast (patent filings? GPU shipments? VC investment?) differentiates from black-box forecasts. SHAP values make ML predictions explainable to non-ML audiences. | MEDIUM | shap library integrates with sklearn-compatible models. Produces feature importance charts directly embeddable in the dashboard. Directly addresses the "valued by thumb" critique by showing the drivers. |
| Scenario / sensitivity analysis | Conservative / base / optimistic scenarios, or slider-based sensitivity on key assumptions (e.g., "what if AI investment grows 10% slower?"). This is standard in professional forecasting tools but rare in portfolio projects. | HIGH | Requires parameterized model inputs and Dash callbacks for interactive sliders. Adds significant dashboard complexity but dramatically increases the analytical value of outputs. |
| Bottom-up and top-down cross-validation | Running both a top-down estimate (from macro GDP/tech share) and a bottom-up estimate (from company revenue rollup, patent counts, etc.) and showing convergence — or explaining divergence — is what professional market research firms do. Showing both builds credibility. | HIGH | Requires sourcing bottom-up component data (e.g., public company filings, CB Insights-style aggregates from free sources). Adds data pipeline complexity. |
| Methodology paper / LinkedIn writeup | Publishing a structured methodology paper — not just code — elevates the project from a "data science exercise" to "economic research." This is explicitly in scope and is a genuine differentiator for the portfolio. | MEDIUM | Content work, not engineering. Requires explaining model choices in lay terms. Maps directly to the stated audience: employers and LinkedIn connections. |
| Model diagnostics and fit metrics | Displaying in-sample model fit (RMSE, MAPE, R²), residual plots, and backtesting results. Professional forecasting tools always show how well the model fits historical data. Omitting this leaves readers unable to assess forecast quality. | MEDIUM | Backtesting framework: train on pre-2020 data, evaluate on 2020-2024. Display metrics in dashboard alongside forecasts. |
| Data freshness tracking and update log | Showing when the underlying data was last fetched and whether it is current. Professional tools surface data vintage to users. | LOW | Simple metadata file updated by data fetch scripts. Small effort, professional signal. |
| Extensible industry architecture | The codebase is designed from the start to add a second industry without rewriting the pipeline. This architectural decision, if documented and visible in the code structure, demonstrates software engineering maturity beyond "data science notebook." | HIGH | Requires abstraction layer: an `IndustryModel` base class or config-driven pipeline. Most valuable as a code-quality differentiator for engineering-focused employers. |

---

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem reasonable but would harm the project given its constraints, audience, and scope.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time data streaming | Feels more impressive and "production-grade" | Adds infrastructure complexity (Kafka, websockets, or API polling loops) that distracts from the economic modeling work. Also unnecessary — macro economic data updates quarterly or annually, not in real time. Out of scope per PROJECT.md. | Scheduled batch fetch (e.g., a Python script that refreshes data weekly). Document the cadence and show the last-updated timestamp in the dashboard. |
| User authentication and multi-user support | Makes the tool feel like a real product | This is a personal portfolio tool. Adding auth (Flask-Login, OAuth) adds weeks of work with zero analytical value. Out of scope per PROJECT.md. | Document that the tool is a single-user local/deployed personal tool. If deployed publicly, a simple HTTP basic auth env var is sufficient. |
| Coverage of multiple industries simultaneously (v1) | Shows generalizability | Dilutes focus. The AI industry is the most defensible and interesting case given the "valued by thumb" problem. Getting the AI model right is more valuable than getting five industries done superficially. Out of scope per PROJECT.md. | Build with extensibility in mind (see "Extensible industry architecture" above), but don't add the second industry until the first is validated. |
| Proprietary or paid data sources | Richer data, better models | No paid data in v1 per PROJECT.md constraints. Adding paid sources also creates reproducibility problems — readers cannot run the model themselves. | Squeeze maximum signal from public sources (World Bank, OECD, Eurostat, SEC EDGAR for public company filings, USPTO patent data, USPTO for AI patent trends). Document sourcing decisions explicitly. |
| Mobile-responsive app | Broader audience | Dashboard complexity increases significantly. Plotly/Dash is primarily designed for desktop browser use. Optimizing for mobile is significant UX work with minimal portfolio payoff for this audience. Out of scope per PROJECT.md. | Ensure the Dash layout is readable on a 1280px+ desktop browser. Note the limitation in README. |
| Automated natural language report generation (LLM integration) | Trendy, sounds impressive | Introduces a dependency on an external API (OpenAI, etc.) and shifts focus from econometric rigor to prompt engineering. Reviewers may perceive it as obscuring the actual analysis. | Write the methodology paper manually — this demonstrates writing ability and domain understanding, which is a portfolio positive. |
| Live web deployment with CI/CD | Makes the project "production" | Adds DevOps scope that is orthogonal to the economic modeling work. A publicly deployed URL can also incur costs and maintenance burden. | Provide a Docker Compose file or clear local run instructions. A GitHub Actions workflow for linting/tests is sufficient CI for a portfolio project. |

---

## Feature Dependencies

```
[Data Ingestion Pipeline]
    └──required by──> [Data Cleaning and Normalization]
                          └──required by──> [Statistical Baseline Model]
                          └──required by──> [ML Refinement Model]
                                                └──enables──> [SHAP Driver Attribution]

[Statistical Baseline Model] ──required by──> [Hybrid Ensemble]
[ML Refinement Model] ──required by──> [Hybrid Ensemble]

[Hybrid Ensemble] ──required by──> [Market Size Point Estimate]
[Hybrid Ensemble] ──required by──> [Growth Forecast with CIs]
[Hybrid Ensemble] ──required by──> [Model Diagnostics and Fit Metrics]

[Market Size Point Estimate] ──required by──> [Dashboard Charts]
[Growth Forecast with CIs] ──required by──> [Dashboard Charts]
[SHAP Driver Attribution] ──enhances──> [Dashboard Charts]

[Dashboard Charts] ──required by──> [Exportable PDF Report]
[Documented Assumptions] ──required by──> [Methodology Paper]
[Model Diagnostics and Fit Metrics] ──required by──> [Methodology Paper]

[Extensible Industry Architecture] ──enables──> [Second Industry (v2+)]

[Scenario Analysis] ──conflicts with scope of──> [v1 Launch] (defer to v1.x)
[Bottom-up Cross-validation] ──conflicts with scope of──> [v1 Launch] (defer to v1.x)
```

### Dependency Notes

- **Data Ingestion is the root dependency:** Nothing else is possible until the pipeline fetches, cleans, and normalizes data from World Bank/OECD. This is phase 1 work that blocks everything downstream.
- **Statistical model before ML model:** The hybrid approach requires a baseline to compare against. Running ARIMA/OLS first also provides interpretability that ML alone cannot.
- **SHAP requires a trained ML model:** SHAP explanations depend on a fitted gradient boosting or similar model. Cannot be added before the ML layer exists.
- **Dashboard requires finalized model outputs:** Building the dashboard on provisional model outputs wastes effort. The dashboard should be scaffolded early but finalized after the modeling pipeline stabilizes.
- **PDF export depends on dashboard layout:** PDF generation captures the rendered dashboard. The dashboard layout must be stable before investing in the PDF export mechanism.
- **Scenario analysis enhances but does not block the dashboard:** Scenarios are sliders on top of a working model. They can be added incrementally after the base dashboard is functional.

---

## MVP Definition

### Launch With (v1)

The minimum that demonstrates the core thesis: defensible, data-driven AI industry valuations using econometric rigor and ML.

- [ ] Data ingestion from World Bank and OECD APIs — without real data there is nothing to model
- [ ] Data cleaning and normalization pipeline — raw data is unusable without this
- [ ] Statistical baseline model (ARIMA or OLS regression) — the interpretable econometric foundation
- [ ] ML refinement model (gradient boosting) — the layer that improves on the statistical baseline
- [ ] Market size point estimate with units and vintage date — the headline output
- [ ] Growth forecast to 2030 with confidence intervals — the forecast output
- [ ] Model diagnostics and fit metrics — necessary to assess forecast quality; omitting is statistically irresponsible
- [ ] Documented assumptions (inline or separate doc) — required for any publishable analysis
- [ ] Interactive dashboard with time series and forecast charts — the primary user interface per PROJECT.md
- [ ] Exportable PDF report — required per PROJECT.md; flag early if open-source PDF export is blocked
- [ ] README with setup and data source documentation — portfolio minimum
- [ ] Data source attribution in all outputs — non-negotiable for published analysis

### Add After Validation (v1.x)

Add these once the v1 pipeline is working end-to-end and model outputs are validated against historical data.

- [ ] SHAP-based driver attribution in dashboard — trigger: v1 model is trained and stable; adds explanatory power
- [ ] Scenario / sensitivity analysis with interactive sliders — trigger: base dashboard is complete; high user value
- [ ] Data freshness tracking and last-updated indicator — trigger: anytime after v1 data pipeline; low effort
- [ ] Bottom-up cross-validation estimate — trigger: when suitable bottom-up data sources are identified; strengthens credibility
- [ ] Methodology paper / LinkedIn writeup — trigger: after v1 is fully functional; content work not blocked by code

### Future Consideration (v2+)

Defer until the AI industry model is validated and the architecture is proven extensible.

- [ ] Second industry (e.g., cloud computing, biotech) — defer until AI model quality is confirmed and the extensible architecture abstraction is tested
- [ ] Automated model retraining on data refresh — defer; requires scheduling infrastructure
- [ ] Comparison view across industries — requires multi-industry data first

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Data ingestion pipeline | HIGH | MEDIUM | P1 |
| Data cleaning and normalization | HIGH | MEDIUM | P1 |
| Statistical baseline model | HIGH | MEDIUM | P1 |
| Market size point estimate | HIGH | LOW | P1 |
| Growth forecast with CIs | HIGH | MEDIUM | P1 |
| Model diagnostics and fit metrics | HIGH | MEDIUM | P1 |
| Documented assumptions | HIGH | LOW | P1 |
| Interactive dashboard (charts) | HIGH | MEDIUM | P1 |
| Exportable PDF report | HIGH | MEDIUM | P1 |
| Data source attribution | HIGH | LOW | P1 |
| README | MEDIUM | LOW | P1 |
| ML refinement model | HIGH | MEDIUM | P1 |
| SHAP driver attribution | HIGH | MEDIUM | P2 |
| Scenario / sensitivity analysis | HIGH | HIGH | P2 |
| Methodology paper | HIGH | MEDIUM | P2 |
| Data freshness tracking | LOW | LOW | P2 |
| Bottom-up cross-validation | MEDIUM | HIGH | P2 |
| Extensible industry architecture | MEDIUM | HIGH | P2 |
| Second industry (v2) | LOW | HIGH | P3 |
| Automated model retraining | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have; add when core is working
- P3: Nice to have; future consideration

---

## Competitor Feature Analysis

These are the tools and reports that do similar things — either professional market research firms or open-source econometric tools. This project is not competing with them commercially, but portfolio reviewers will compare against them implicitly.

| Feature | Professional Reports (Gartner / IDC / Grand View Research) | Open-Source Notebooks (GitHub) | This Project's Approach |
|---------|------------------------------------------------------------|-------------------------------|-------------------------|
| Data sourcing | Proprietary surveys + paid databases | Usually a single CSV, often uncited | Public APIs (World Bank, OECD) with explicit attribution |
| Methodology transparency | Opaque — "proprietary methodology" | Often absent or minimal | Full documentation: every model choice explained |
| Model type | Rarely disclosed | Usually single method (ARIMA or simple regression) | Hybrid: statistical baseline + ML refinement, both visible |
| Confidence intervals | Sometimes shown, rarely explained | Often absent | Shown prominently with explanation of what they mean |
| Interactivity | PDF reports only, no interactivity | Static Jupyter notebooks | Interactive Dash dashboard + PDF export |
| Scenario analysis | Sometimes present (3-scenario model) | Rarely present | Present in v1.x; parameterized via dashboard sliders |
| Reproducibility | Not reproducible (proprietary data) | Sometimes reproducible | Fully reproducible from public sources |
| Driver explanation | Narrative only, no quantification | Absent | SHAP values in v1.x quantify which variables drive the forecast |
| Code quality | N/A | Varies widely; often notebook-only | Portfolio-quality: modular Python, docstrings, clean structure |

---

## Sources

- [Grand View Research: AI Market Size Report](https://www.grandviewresearch.com/industry-analysis/artificial-intelligence-ai-market) — MEDIUM confidence (commercial research firm)
- [Indicio: 8 Best Econometric Forecasting Tools](https://www.indicio.com/resources/blog/econometric-forecasting-software) — MEDIUM confidence
- [Worldmetrics: Top 10 Economic Modeling Software 2026](https://worldmetrics.org/best/economic-modeling-software/) — LOW confidence (aggregator site)
- [Statista Methodology Documentation](https://www.statista.com/outlook/methodology) — HIGH confidence (official methodology page)
- [Corporate Finance Institute: Scenario vs. Sensitivity Analysis](https://corporatefinanceinstitute.com/resources/financial-modeling/scenario-analysis-vs-sensitivity-analysis/) — HIGH confidence
- [SHAP Documentation](https://shap.readthedocs.io/en/latest/) — HIGH confidence (official docs)
- [skforecast: Explainability](https://skforecast.org/0.20.1/user_guides/explainability.html) — HIGH confidence (official docs)
- [Data-Mania: Top-Down Market Sizing Guide](https://www.data-mania.com/blog/top-down-market-sizing-tam-sam-som-guide/) — MEDIUM confidence
- [Infomineo: Market Sizing Toolkit](https://infomineo.com/services/business-research/your-market-sizing-toolkit-sources-strategies-and-solutions-to-common-challenges/) — MEDIUM confidence
- [Plotly Community: PDF Export in Dash](https://community.plotly.com/t/exporting-multi-page-dash-app-to-pdf-with-entire-layout/37953) — HIGH confidence (official community forum)
- [World Bank Open Data](https://data.worldbank.org/) — HIGH confidence (primary source)
- [OECD Data Explorer](https://data-explorer.oecd.org) — HIGH confidence (primary source)

---
*Feature research for: AI Industry Economic Valuation and Forecasting Tool*
*Researched: 2026-03-17*
