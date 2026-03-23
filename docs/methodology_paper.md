# How I Built a Data-Driven Framework to Value the AI Industry

*A methodology writeup for the AI Industry Value Estimator project*

---

How do you put a defensible price tag on the AI industry? Ask ten analysts and you will get ten different numbers — anywhere from $185 billion to $1.8 trillion depending on how they define the market, which data they use, and what assumptions they bake in. The variation is not just noise. It reflects genuine methodological choices about market boundaries, indicator selection, and model architecture. This project started with a simple question: what would it look like to do this rigorously, with full transparency about every assumption?

---

## Origin Story

The seed of this project came from a conversation with a quant risk manager who made a casual observation that struck me as deeply important: AI industry valuations are largely done "by thumb." Sell-side analysts and research firms produce headline numbers backed by proprietary models that are never published. Consensus emerges through citation loops — firms citing each other until a number like $200 billion becomes gospel. There is nothing wrong with consensus estimates. But in a sector growing this fast, with this much structural change, the absence of reproducible, open-source methodology is a real gap.

My background is in economics, which gave me an appreciation for rigorous baseline modeling, but I wanted to push further. Traditional econometric approaches — OLS regression, ARIMA time series — are interpretable and statistically grounded, but they struggle with the kind of non-linear, regime-changing dynamics that define an industry rewriting itself every eighteen months. The hypothesis driving this project: a hybrid approach, combining econometric models for interpretability with machine learning for capturing non-linear residual dynamics, should outperform either approach in isolation. That hybrid approach became the architecture of the AI Industry Value Estimator.

---

## Methodology Overview

### Data Foundation

The model draws from three independent data sources to build a multi-dimensional picture of AI industry activity. World Bank Open Data provides macroeconomic foundation — GDP, R&D expenditure as a share of GDP, high-technology exports, and ICT service exports across sixteen economies spanning the US, Europe, China, and Rest of World. OECD statistics contribute technology and innovation indicators: the Main Science and Technology Indicators (MSTI) dataset for business R&D by sector, and AI patent filings as an innovation intensity proxy. LSEG Workspace provides company-level financial data — revenue, R&D expense, and gross margins — for publicly listed firms classified under AI-relevant TRBC industry codes (semiconductors, computer hardware, internet software and services).

These three sources are not sufficient on their own. No statistical agency directly tracks "AI revenue" as a category. The approach therefore builds a *composite index* by applying Principal Component Analysis (PCA) to the full indicator set within each of four market segments — AI Hardware, AI Infrastructure, AI Software and Platforms, and AI Adoption. PCA extracts the direction of maximum variance across correlated indicators, producing a single time series per segment that captures the shared signal in the underlying data. This composite is then calibrated to USD billions using a linear anchor: the $200 billion global AI market consensus estimate for 2023 (sourced from McKinsey Global Institute, Statista, and Grand View Research, which agree within a $185–$215 billion range).

### Statistical Baseline

The composite index for each segment is modelled with two competing time series specifications: ARIMA (AutoRegressive Integrated Moving Average) and Facebook's Prophet. ARIMA is fit using AICc-based order selection — the small-sample correction is critical here, as the annual series span only fifteen data points (2010–2024). Prophet brings a practical advantage for this domain: its `changepoints` parameter allows explicit modelling of structural breaks. The 2022 generative AI surge — ChatGPT's release, the explosion of foundation model investment — represents a clear regime change that ARIMA would absorb as residual volatility. By setting `changepoints=['2022-01-01']`, Prophet's trend component captures this discontinuity explicitly.

Both models are evaluated using temporal cross-validation: the training window expands forward through time, never using future data to fit past periods. The winner by out-of-sample RMSE becomes the statistical baseline for that segment. Importantly, the pipeline extracts and stores the residuals — the gap between what the statistical model predicted and what the data actually showed — as the target for the machine learning layer.

### Machine Learning Correction

The second layer trains a LightGBM gradient boosting model on those statistical residuals. This is a deliberate design choice: rather than replacing the interpretable baseline with a black box, the ML component *corrects* it. The additive blend formula is `final_forecast = stat_prediction + lgbm_weight × lgbm_residual_correction`. The ensemble weight is derived from inverse-RMSE weighting — a model that performed better historically gets proportionally more influence in the blend.

The final output is a set of calibrated confidence intervals for each segment, derived from bootstrap resampling of the residual distribution. The 80% and 95% bands represent genuine uncertainty quantification, not just scaled standard errors. All assumptions underlying this process — from the PCA indicator weights to the CAGR extrapolation used for post-2024 features — are documented in `docs/ASSUMPTIONS.md` with explicit sensitivity notes describing the direction and magnitude of impact if each assumption is wrong.

---

## Key Findings

The model was anchored to the industry consensus of $200 billion for the global AI market in 2023. The historical composite index tracks coherently through the 2010–2023 period, rising from a baseline around $50 billion (2015 equivalent) to the $200 billion anchor, with the expected acceleration after 2020 as cloud AI infrastructure buildout began in earnest and software platform revenues surged. AI Software and Platforms emerged as the largest contributor to the composite through 2022–2023, consistent with the margin-rich nature of foundation model APIs and AI SaaS businesses. AI Infrastructure showed strong persistence in positive territory through 2023, reflecting the sustained capital expenditure on data center build-out. The 2024 data reflects known OECD and World Bank reporting lags — macro indicator series typically lag by 12–18 months — making the 2023 anchor year the most reliable headline figure from this vintage of data.

---

## What I Learned

The most valuable lesson from this project was not technical. It was the discipline of *documented assumptions*. Every modelling decision that feels obvious in isolation — "use AICc not AIC," "anchor at 2023 not 2022," "PCA with three indicators per segment" — compounds. By the time you reach the final forecast, dozens of such decisions interact. The `docs/ASSUMPTIONS.md` file in this repository records sixteen assumption classes, each with an explicit sensitivity note. Writing those notes forced me to think harder about whether I actually believed the choices I was making, or whether I was just pattern-matching to familiar methods. That discipline is what separates analysis that is defensible from analysis that is merely fluent.

The hybrid statistical-plus-ML architecture worked as intended. The LightGBM correction layer meaningfully adjusted the statistical baseline residuals in the training period. What it could not fix was data quality at the boundary — 2024 indicator data from public sources is sparse and subject to revision. This is not a failure of the model; it is a characteristic of working with lagged public data. The architecture is designed to be re-run: once 2024 indicator data is fully published (typically by late 2025), a single pipeline re-run will update all forecasts without changing any code.

---

## Try It Yourself

The full codebase, pipeline, and interactive dashboard are open source on GitHub. Clone the repo and run `uv sync` to get started; `uv run python scripts/run_dashboard.py` launches the interactive dashboard. The methodology is reproducible from scratch: the ingestion layer pulls directly from World Bank and OECD public APIs, so no proprietary data is required (LSEG data requires a Workspace subscription for the company financials layer).

If you have thoughts on the methodology — particularly the PCA composite approach or the ensemble weighting strategy — I would genuinely welcome the feedback. This is exactly the kind of project where external review is valuable. Find the repository at: **https://github.com/[your-username]/industry-value-estimator**

*The full source code, data pipeline, and ASSUMPTIONS.md are available in the repository. PDF reports (executive brief and full analytical report) are generated by `uv run python scripts/run_reports.py`.*
