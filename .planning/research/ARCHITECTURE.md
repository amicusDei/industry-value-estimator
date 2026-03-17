# Architecture Research

**Domain:** Economic industry valuation and forecasting (hybrid statistical + ML pipeline)
**Researched:** 2026-03-17
**Confidence:** MEDIUM-HIGH

## Standard Architecture

### System Overview

The canonical architecture for this type of system is a **layered pipeline** with four distinct tiers: ingestion, processing/modeling, storage, and presentation. Data flows strictly downward — raw sources feed into normalized stores, which feed modeling, which feeds the dashboard and reports. No layer reaches backward.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                          │
│  ┌─────────────────────┐   ┌─────────────────────────────────────┐  │
│  │  Dash/Plotly         │   │  Report Generator (PDF/HTML)        │  │
│  │  Interactive         │   │  Methodology Paper Export           │  │
│  │  Dashboard           │   │                                     │  │
│  └──────────┬──────────┘   └─────────────────┬───────────────────┘  │
└─────────────┼───────────────────────────────┼───────────────────────┘
              │ reads                          │ reads
┌─────────────┼───────────────────────────────┼───────────────────────┐
│             ▼          INFERENCE LAYER       ▼                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Forecast Engine                                              │   │
│  │  - loads trained models from model registry                  │   │
│  │  - produces point estimates + confidence intervals           │   │
│  │  - runs scenario analysis (pessimistic/base/optimistic)      │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
└──────────────────────────────┼─────────────────────────────────────-┘
                               │ reads models from
┌──────────────────────────────┼──────────────────────────────────────┐
│                 MODELING LAYER                ▼                      │
│  ┌────────────────────┐  ┌───────────────────────────────────────┐  │
│  │  Statistical Layer │  │  ML Layer                             │  │
│  │  - ARIMA/SARIMA    │  │  - Gradient boosting (XGBoost/LGB)    │  │
│  │  - Prophet         │  │  - LSTM / Transformer (optional)      │  │
│  │  - OLS regression  │  │  - Ensemble combiner                  │  │
│  │  - VAR             │  │                                       │  │
│  └────────┬───────────┘  └───────────────┬───────────────────────┘  │
│           │ residuals feed ML             │                          │
│           └───────────────────────────────┘                          │
│           both read from Feature Store                               │
│                         ┌──────────────────────────────────────┐    │
│                         │  Feature Store                        │    │
│                         │  - engineered features (lags, growth  │    │
│                         │    rates, cross-sector indicators)    │    │
│                         │  - normalized, industry-tagged        │    │
│                         └──────────────┬─────────────────────-─┘    │
└──────────────────────────────────────-─┼───────────────────────────-┘
                                         │ reads from
┌────────────────────────────────────────┼────────────────────────────┐
│                     DATA LAYER         ▼                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Normalized Data Store  (data/processed/)                   │    │
│  │  - unified schema across sources                            │    │
│  │  - industry-tagged rows                                     │    │
│  └────────────────────────────────────┬────────────────────────┘    │
│                                       │ built by                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Ingestion & Normalization Pipeline                           │   │
│  │  - World Bank API connector                                   │   │
│  │  - OECD connector                                             │   │
│  │  - Eurostat connector                                         │   │
│  │  - Web scraper (company filings, market reports)              │   │
│  │  - Raw data cache (data/raw/ — immutable)                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| Ingestion connectors | Fetch raw data from public APIs and scraping targets; write to `data/raw/` | None (sources only) |
| Normalization pipeline | Clean, schema-align, deduplicate, tag by industry; write to `data/processed/` | Reads raw; writes processed |
| Feature store | Compute derived features: lags, growth rates, rolling averages, cross-sector signals | Reads processed; feeds model layers |
| Statistical layer | Baseline models — ARIMA, Prophet, OLS, VAR; produces baselines + residuals | Reads feature store; writes results + residuals |
| ML layer | Refine on residuals from statistical layer; gradient boosting primary, LSTM optional | Reads feature store + statistical residuals; writes model artifacts |
| Ensemble combiner | Weighted blend of statistical and ML outputs; produces final forecast with CI | Reads both model outputs |
| Forecast engine (inference) | Load serialized models, run forward projections, produce scenario bands | Reads model registry + feature store |
| Dashboard (Dash) | Interactive UI — charts, tables, filter controls | Reads forecast outputs |
| Report generator | Render PDF/HTML with methodology, charts, projections | Reads forecast outputs + templates |

---

## Recommended Project Structure

```
industry-value-estimator/
├── data/
│   ├── raw/                   # Immutable source dumps — never modify
│   │   ├── world_bank/
│   │   ├── oecd/
│   │   ├── eurostat/
│   │   └── scraped/
│   ├── interim/               # Partially transformed data
│   └── processed/             # Final canonical datasets for modeling
├── src/
│   ├── ingestion/             # One module per data source
│   │   ├── world_bank.py
│   │   ├── oecd.py
│   │   ├── eurostat.py
│   │   └── scraper.py
│   ├── processing/            # Normalization and schema alignment
│   │   ├── normalize.py       # Unified schema enforcement
│   │   ├── validate.py        # Data quality checks
│   │   └── features.py        # Feature engineering (lags, ratios, etc.)
│   ├── models/
│   │   ├── statistical/       # ARIMA, Prophet, OLS, VAR
│   │   │   ├── arima.py
│   │   │   ├── prophet_model.py
│   │   │   └── regression.py
│   │   ├── ml/                # Gradient boosting, LSTM
│   │   │   ├── gradient_boost.py
│   │   │   └── lstm.py        # Optional — add in later phase
│   │   ├── ensemble.py        # Combine statistical + ML outputs
│   │   └── evaluate.py        # RMSE, MAPE, CI coverage metrics
│   ├── inference/             # Load serialized models, produce forecasts
│   │   ├── forecast.py        # Main forecasting entry point
│   │   └── scenarios.py       # Pessimistic / base / optimistic bands
│   ├── reporting/
│   │   ├── report.py          # PDF/HTML generation
│   │   └── templates/         # Jinja2 or WeasyPrint templates
│   └── dashboard/
│       ├── app.py             # Dash app entry point
│       ├── layout.py          # Page structure
│       ├── callbacks.py       # Interactive callback logic
│       └── components/        # Reusable chart components
├── models/                    # Serialized trained models (joblib/pickle)
│   └── ai_industry/           # Industry-namespaced subdirectory
├── notebooks/                 # Exploratory analysis, methodology drafts
│   ├── 01_data_exploration.ipynb
│   ├── 02_baseline_models.ipynb
│   ├── 03_ml_layer.ipynb
│   └── 04_evaluation.ipynb
├── reports/                   # Generated outputs — not committed
│   └── .gitkeep
├── config/
│   ├── settings.py            # All tunable parameters (no hardcoding)
│   └── industries/
│       └── ai.yaml            # Per-industry config (sources, proxies, dates)
├── tests/
│   ├── test_ingestion.py
│   ├── test_processing.py
│   └── test_models.py
├── docs/                      # Methodology paper drafts, component explanations
└── pyproject.toml / requirements.txt
```

### Structure Rationale

- **`data/raw/` is immutable:** Every transformation is reproducible from source. This is the single most important rule — never overwrite raw. Enforced by convention and a README inside the folder.
- **`src/ingestion/` one file per source:** Adding a new data source means adding one file and registering it in a pipeline config. No other files change.
- **`src/models/statistical/` and `src/models/ml/` separated:** The two-layer hybrid approach needs clear ownership. Statistical models produce residuals that ML models consume. This boundary must be explicit in code.
- **`config/industries/ai.yaml`:** The extensibility mechanism. Adding a second industry means adding `config/industries/retail.yaml` with its source list, proxy variables, and date range. The ingestion pipeline reads this config and routes accordingly.
- **`models/` with industry namespacing:** `models/ai_industry/arima_2026.joblib` — no ambiguity when multiple industries exist.
- **Notebooks for exploration only:** Production logic lives in `src/`. Notebooks call `src/` modules; they do not contain pipeline logic.

---

## Architectural Patterns

### Pattern 1: Two-Stage Hybrid Forecasting (Statistical First, ML on Residuals)

**What:** Run interpretable statistical models (ARIMA, Prophet) first to capture trend and seasonality. Pass their residuals to an ML model (XGBoost, LightGBM) which learns nonlinear patterns the statistical model missed. Combine outputs via weighted ensemble.

**When to use:** Always for this project. Hybrid consistently outperforms either approach alone on economic time series. The statistical stage also provides explainability required for a methodology paper.

**Trade-offs:** Adds a dependency between model layers (ML training requires statistical outputs). Sequential execution adds runtime. Benefit: both interpretability and predictive accuracy.

**Example:**

```python
# src/models/ensemble.py
def hybrid_forecast(features_df, stat_model, ml_model, alpha=0.6):
    stat_pred = stat_model.predict(features_df)
    residuals = features_df["target"] - stat_pred
    ml_correction = ml_model.predict(features_df.assign(stat_residual=residuals))
    return alpha * stat_pred + (1 - alpha) * ml_correction
```

### Pattern 2: Industry-Config-Driven Ingestion

**What:** Each industry is declared in a YAML config file specifying its data sources, proxy variables (what to use as a proxy for AI industry GDP contribution when direct measurement is unavailable), and modeling date ranges. The ingestion pipeline is generic; industry specifics live entirely in config.

**When to use:** From day one, even for a single industry. This is the extensibility mechanism. Building it industry-aware from the start avoids a structural rewrite when expanding.

**Trade-offs:** Adds a config schema to maintain. Indirection makes debugging slightly harder. Benefit: adding industry #2 costs a YAML file, not a code rewrite.

**Example:**

```yaml
# config/industries/ai.yaml
industry: ai
display_name: "Artificial Intelligence Industry"
sources:
  - world_bank: ["NY.GDP.MKTP.CD", "GB.XPD.RSDV.GD.ZS"]
  - oecd: ["ANBERD"]
proxies:
  - description: "R&D expenditure as share of GDP"
    variable: "GB.XPD.RSDV.GD.ZS"
date_range:
  start: "2000"
  end: "2024"
```

### Pattern 3: FTI (Feature / Training / Inference) Separation

**What:** Treat feature engineering, model training, and inference as three separately executable pipeline stages. Features are computed once and stored. Training reads stored features. Inference reads stored models and fresh features.

**When to use:** From the start. This avoids the common mistake of coupling feature engineering into the training loop, which makes reuse and debugging painful.

**Trade-offs:** Requires discipline about where feature logic lives (always in `src/processing/features.py`, never inside a model file). Adds boilerplate. Benefit: features are reused across all models; inference at dashboard time is fast.

---

## Data Flow

### End-to-End Pipeline Flow

```
[Public APIs: World Bank, OECD, Eurostat]
[Web Scraping: company filings, market reports]
    |
    | (HTTP fetch, rate-limited, cached locally)
    v
data/raw/                        <- immutable source cache
    |
    | (normalize.py: schema alignment, type coercion, dedup)
    v
data/processed/                  <- unified, industry-tagged parquet/CSV
    |
    | (features.py: lag features, growth rates, rolling windows)
    v
Feature Store (in-memory DataFrame or parquet cache)
    |
    |─────────────────────────────────|
    v                                 v
Statistical Models               ML Models
(ARIMA, Prophet, OLS)            (XGBoost/LightGBM)
    |                                 |
    | residuals ─────────────────────>|
    |                                 |
    v                                 v
                  Ensemble Combiner
                        |
                        v
              Forecast outputs (parquet)
              - point estimates by year
              - confidence intervals
              - scenario variants
                        |
               |────────|────────────|
               v                    v
         Dash Dashboard        Report Generator
         (interactive)         (PDF/HTML/paper)
```

### Key Data Flows

1. **Raw-to-processed:** Runs as a batch job triggered manually or by schedule. Reads from all source APIs, writes unified schema to `data/processed/`. Idempotent — safe to re-run.
2. **Processed-to-features:** Feature engineering reads `data/processed/`, computes derived columns, writes feature parquet (or holds in memory for small datasets). Deterministic given the same processed data.
3. **Training flow:** Reads feature store, trains statistical models, captures residuals, trains ML on residuals, serializes all models to `models/ai_industry/`.
4. **Inference flow (at dashboard load):** Loads serialized models, reads latest features, runs forward projection through 2030 horizon, returns forecast DataFrame.
5. **Dashboard callback flow:** User adjusts a filter (e.g., scenario slider) → Dash callback runs `inference/scenarios.py` → returns updated chart data → Plotly re-renders charts.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| World Bank API | REST (wbgapi Python client or direct HTTP) | Free, no auth; rate-limit to ~100 req/min |
| OECD API | SDMX REST API | Free; queries can be slow (30s+); cache aggressively |
| Eurostat | SDMX or eurostat Python package | Free; bulk download often faster than API |
| Web scraping | requests + BeautifulSoup or playwright for JS-heavy pages | Respect robots.txt; build retry/backoff |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Ingestion → Processing | File system (data/raw/ to data/processed/) | Decoupled; processing can re-run without re-fetching |
| Processing → Models | In-memory DataFrame or feature parquet | Keep features in memory for small datasets; parquet cache for larger |
| Models → Dashboard | Serialized model files + forecast parquet | Dashboard reads pre-computed forecasts; avoids training at runtime |
| Dashboard → Reports | Shared chart components | Dash callbacks and report renderer both call the same Plotly figure functions |

---

## Build Order (Phase Dependencies)

The component dependencies dictate this build order:

```
Phase 1: Data Foundation
  ingestion/ connectors + normalization pipeline
  Reason: Everything downstream depends on clean data existing.

Phase 2: Feature Engineering + Statistical Baseline
  processing/features.py + models/statistical/
  Reason: Statistical models are the interpretable baseline and produce
  residuals needed by ML. Cannot train ML without statistical residuals.

Phase 3: ML Layer + Ensemble
  models/ml/ + ensemble.py + evaluate.py
  Reason: Requires Phase 2 outputs (features + residuals).

Phase 4: Inference + Dashboard
  inference/ + dashboard/
  Reason: Requires trained models from Phase 3.

Phase 5: Reports + Methodology Paper
  reporting/ + docs/
  Reason: Requires working forecasts; summarizes all prior phases.
```

---

## Anti-Patterns

### Anti-Pattern 1: Hardcoding Industry Logic in Pipeline Code

**What people do:** Write `if industry == "ai": use_source = "world_bank"` scattered through ingestion and modeling code.
**Why it's wrong:** Adding a second industry requires hunting through every file for conditionals. Quickly becomes unmaintainable.
**Do this instead:** All industry-specific parameters live in `config/industries/<industry>.yaml`. Pipeline code reads config and is industry-agnostic.

### Anti-Pattern 2: Training Models Inside the Dashboard

**What people do:** Load raw data and re-train models on each dashboard load to show "live" results.
**Why it's wrong:** Training takes seconds to minutes. Dash callbacks must respond in <1 second or the UX degrades. Also makes the dashboard stateful in ways that are hard to debug.
**Do this instead:** Train offline, serialize to disk. Dashboard loads pre-computed forecast outputs. Callback filters and re-renders charts; it does not re-train.

### Anti-Pattern 3: Skipping the Statistical Baseline

**What people do:** Jump straight to XGBoost or LSTM because they expect better accuracy.
**Why it's wrong:** ML models on economic time series with small datasets (50–100 data points) overfit easily. Statistical baselines provide interpretable benchmarks. The methodology paper requires explainability. The hybrid approach consistently wins on evaluation metrics.
**Do this instead:** Build ARIMA/Prophet baseline first, measure its error, then show how ML corrects the residuals. Document the improvement.

### Anti-Pattern 4: Mutating Raw Data

**What people do:** Run preprocessing in-place on the files in `data/raw/`.
**Why it's wrong:** Breaks reproducibility. A bug in preprocessing cannot be recovered without re-fetching from APIs.
**Do this instead:** Raw data is immutable. Every transformation writes to `data/interim/` or `data/processed/`. Re-running the full pipeline from raw must always be possible.

### Anti-Pattern 5: Monolithic Notebook as Production Code

**What people do:** One giant Jupyter notebook containing ingestion, preprocessing, modeling, and visualization.
**Why it's wrong:** Impossible to test, refactor, or extend. Cannot be imported by the dashboard. Hidden state in kernel makes reproducibility unreliable.
**Do this instead:** Notebooks are for exploration and documentation only. All logic moves to `src/` modules. Notebooks import from `src/` and demonstrate the pipeline with narrative text.

---

## Scaling Considerations

This is a personal/portfolio project, not a multi-user SaaS. Scale concerns are minimal. The relevant dimension is data volume and model complexity as industries are added.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 industry, ~100 data points | Current architecture is sufficient. In-memory DataFrames. SQLite optional. |
| 3-5 industries, thousands of rows | Add parquet caching for features. Consider DVC for data versioning. Possibly Prefect/Airflow for pipeline orchestration. |
| 10+ industries, external users | Split dashboard from model serving into separate processes. Add a lightweight API layer (FastAPI) between inference and dashboard. |

### Scaling Priorities

1. **First bottleneck:** API rate limits during ingestion (OECD is slow). Fix: aggressive local caching with freshness TTL — fetch once, re-use for weeks.
2. **Second bottleneck:** Model retraining time when adding industries. Fix: make training scripts parallelizable per industry (each industry's models train independently).

---

## Sources

- [FTI Pipeline Architecture — Hopsworks](https://www.hopsworks.ai/post/mlops-to-ml-systems-with-fti-pipelines) — Feature/Training/Inference separation pattern (MEDIUM confidence — industry standard, widely adopted)
- [Hybrid Statistical + ML Framework — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12294620/) — Dual-stage ARIMA + deep learning residual correction (HIGH confidence — peer-reviewed)
- [Bottom-Up Market Sizing Workbook Architecture — Umbrex](https://umbrex.com/resources/market-sizing-playbook/bottom-up-market-sizing-methodology/) — Scenario + sensitivity layer structure (MEDIUM confidence)
- [Cookiecutter Data Science — DrivenData](https://cookiecutter-data-science.drivendata.org/) — Canonical Python data science folder structure (HIGH confidence — community standard)
- [Top-Down vs Bottom-Up Forecasting — Forecastio](https://forecastio.ai/blog/top-down-vs-bottom-up-forecasting) — Methodology comparison informing scenario design (MEDIUM confidence)
- [Econometric + Python Forecasting Tools — MDPI](https://www.mdpi.com/2225-1146/13/4/52) — Hybrid ARIMA + ML pipeline patterns (MEDIUM confidence — peer-reviewed)

---
*Architecture research for: AI Industry Economic Valuation and Forecasting System*
*Researched: 2026-03-17*
