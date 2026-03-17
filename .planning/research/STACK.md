# Stack Research

**Domain:** Hybrid statistical + ML economic valuation and forecasting system (Python)
**Researched:** 2026-03-17
**Confidence:** MEDIUM-HIGH (versions verified via PyPI/official sources; library-specific recommendations from docs + community consensus)

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12 | Runtime | 3.12 is the current production-stable sweet spot — 3.13 support is still maturing across the data science ecosystem. Avoid 3.10 (EOL approaching) and avoid 3.13 until library support is universal. |
| pandas | 3.0.x | Data wrangling, time series construction | Pandas 3.0 (released January 2026) is the current major version. Copy-on-Write is now default — write idiomatic CoW-safe code from day one rather than migrating later. |
| numpy | 2.x | Numerical computation foundation | Required by all scientific Python libraries. Pandas 3.0 and scikit-learn 1.8 both target NumPy 2.x. |

### Statistical Modeling

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| statsmodels | 0.14.6 | Econometric baseline models: OLS regression, ARIMA, SARIMAX, VAR, cointegration tests | The standard for econometrics in Python — provides p-values, confidence intervals, hypothesis tests, and model summaries that scikit-learn intentionally omits. Mandatory for portfolio credibility: quants and economists expect to see statsmodels outputs. Version 0.14.6 includes pandas 3.0 compatibility fix released December 2025. |
| Prophet | 1.1.x | Additive trend + seasonality decomposition for yearly AI market data | Excels at business time series with irregular seasonality, missing data, and structural breaks — precisely the profile of AI industry revenue data (sparse, fast-growing, non-stationary). Handles outliers gracefully without manual preprocessing. |

### Machine Learning

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| scikit-learn | 1.8.0 | Pipeline management, cross-validation, baseline ML models (Ridge, ElasticNet, HistGradientBoosting), model evaluation | 1.8.0 is the current stable release (December 2025). Use as the orchestration layer — pipelines, transformers, CV splitters — with LightGBM plugged in as the estimator. Its consistent API across 100+ algorithms makes it the best choice for rapid experimentation. |
| LightGBM | 4.6.0 | Primary gradient boosting for tabular economic data | For tabular structured data at economic-model scale (hundreds to low thousands of rows), LightGBM outperforms XGBoost in training speed and memory. Natively handles missing values and categoricals. sklearn-compatible API means it plugs directly into scikit-learn pipelines. |
| shap | 0.46.x | Model interpretability — explain feature contributions to forecasts | Economic models MUST be explainable to be credible. SHAP waterfall plots and feature importance tables are the current standard for communicating "why the model said X" to non-technical stakeholders and for a methodology paper. |

### Data Collection

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| wbgapi | 1.0.x | World Bank API access | The World Bank's own recommended Python client. Modern API (replaces deprecated world_bank_data and wbdata patterns). Returns DataFrames directly. |
| eurostat | 1.0.x | Eurostat REST API access | Official Eurostat dissemination API (old SDMX API was decommissioned January 2023). The `eurostat` PyPI package was rewritten to support the new API. |
| pandasdmx | 1.x | OECD SDMX data access | OECD exposes data via SDMX; pandasdmx implements SDMX 2.1 and supports OECD as a named provider. More robust than direct HTTP calls to OECD endpoints. |
| requests | 2.32.x | HTTP for scraping company filings / supplementary sources | Standard HTTP library; use for any custom scraping not covered by the above wrappers. |
| requests-cache | 1.2.x | Cache API responses to disk during development | AI industry data sources are rate-limited. Caching prevents redundant calls during model iteration and makes development reproducible offline. |

### Visualization & Dashboard

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Plotly | 6.6.0 | Interactive charts (line, bar, scatter, confidence interval ribbons, choropleth) | 6.0 rewrote DataFrame handling via Narwhals — it now works cleanly with pandas 3.0. Produces publication-quality interactive figures that embed in Dash without extra export steps. |
| Dash | 4.0.x | Interactive web dashboard framework | The project spec explicitly calls out Dash. It integrates with Plotly natively and requires zero JavaScript. Dash 4.0 (February 2026) is the current stable release. The hooks system in recent versions simplifies lifecycle management. |

### Report Generation

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Jinja2 | 3.1.x | HTML report templates with dynamic data injection | The standard Python templating engine. Write HTML/CSS report templates; inject pandas DataFrames, Plotly figures (as static PNG via Kaleido), and narrative text. |
| WeasyPrint | 68.x | HTML+CSS to PDF conversion | Current stable is 68.1 (February 2026). Supports modern CSS layout (Flexbox, Grid) better than alternatives. Produces cleaner output than ReportLab for document-style reports with mixed text, charts, and tables. Requires Python >=3.10. |
| Kaleido | 0.2.x | Export Plotly figures to static PNG/SVG for PDF embedding | Required bridge between interactive Plotly charts and static PDF output. Without Kaleido, WeasyPrint cannot render Plotly figures. |

### Development Environment

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| uv | 0.5.x | Package manager and virtual environment | Replaces pip + venv for 2025 Python projects. Lockfile-based dependency resolution (uv.lock) makes environments reproducible. 10-100x faster than pip. Use `uv add` to manage dependencies; commit uv.lock. |
| Jupyter | 3.x (JupyterLab) | Exploratory analysis and model prototyping | The standard exploratory environment. Use notebooks for data exploration and model prototyping; graduate cleaned code to `.py` modules. Plotly 6.0 dropped support for Notebook <7.0, so use JupyterLab 4.x. |
| ruff | 0.8.x | Linting and formatting | Replaces flake8 + black + isort as a single fast tool. Portfolio code must be clean — ruff enforces it automatically. |
| pytest | 8.x | Unit tests for data pipeline and model components | Test data loading, transformation functions, and model output shapes. Portfolio projects with tests signal engineering discipline. |

---

## Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy | 1.14.x | Statistical tests, distributions, optimization | Use for hypothesis testing (Granger causality, stationarity tests beyond statsmodels), and for confidence interval calculation utilities. |
| pyarrow | 18.x | Columnar data storage (Parquet) | Cache processed datasets as Parquet files between pipeline runs. Parquet is smaller and faster than CSV for repeated reads; pandas 3.0 uses pyarrow as its default backend. |
| python-dotenv | 1.0.x | Environment variable management for API keys | Even with free APIs, some (financial data) require keys. Load from .env; never hardcode. |
| tqdm | 4.67.x | Progress bars for long data-fetch and training loops | Data ingestion across multiple World Bank/OECD indicators takes time. Progress bars keep development sane. |
| nbconvert | 7.x | Convert notebooks to HTML/PDF for publication | For the methodology writeup and GitHub portfolio: export polished notebooks directly to shareable HTML. |
| matplotlib | 3.10.x | Static publication-quality figures | Use for figures embedded in the methodology paper/writeup where interactivity is not needed. Plotly handles the dashboard; matplotlib handles print-ready charts. |
| seaborn | 0.13.x | Statistical visualization (correlation matrices, distribution plots) | Use during exploratory analysis and in the methodology writeup. Not for the dashboard. |

---

## Installation

```bash
# Initialize project with uv
uv init industry-value-estimator
cd industry-value-estimator

# Core data and modeling
uv add pandas numpy scipy statsmodels prophet scikit-learn lightgbm shap

# Data collection
uv add wbgapi eurostat pandasdmx requests requests-cache

# Visualization and dashboard
uv add plotly dash

# Report generation
uv add jinja2 weasyprint kaleido

# Storage
uv add pyarrow

# Utilities
uv add python-dotenv tqdm matplotlib seaborn

# Development dependencies
uv add --dev jupyter jupyterlab ruff pytest nbconvert

# Install all
uv sync
```

---

## Alternatives Considered

| Category | Recommended | Alternative | When to Use Alternative |
|----------|-------------|-------------|-------------------------|
| Package manager | uv | pip + venv | Never for new projects in 2026 — uv is strictly better |
| Package manager | uv | Poetry | Poetry is valid but slower and less actively developed than uv |
| Gradient boosting | LightGBM | XGBoost | XGBoost 3.2.0 is slightly more accurate on benchmark tasks but slower. Use XGBoost if you need GPU acceleration or are targeting a Kaggle-style benchmark evaluation |
| Gradient boosting | LightGBM | scikit-learn HistGradientBoosting | Use HistGBM for quick baselines only — LightGBM is materially faster and has better feature importance tooling |
| Dashboard | Dash | Streamlit | Streamlit is faster to prototype but less customizable for polished portfolio dashboards. Dash is more pythonic for multi-page apps with complex layouts |
| Dashboard | Dash | Panel (HoloViz) | Panel is better for very complex multi-tab scientific apps; overkill for this scope |
| PDF generation | WeasyPrint + Jinja2 | ReportLab | ReportLab gives pixel-perfect control but requires programmatic layout (no HTML/CSS). Use only if WeasyPrint cannot reproduce a required layout |
| PDF generation | WeasyPrint + Jinja2 | nbconvert | nbconvert is good for notebook-to-PDF but limited for custom-branded professional reports |
| Time series | Prophet | NeuralProphet | NeuralProphet (neural extension of Prophet) is more powerful but requires more data and more tuning. Use if Prophet residuals are poor after parameter search |
| Time series | Prophet | skforecast + ARIMA | Use if you need tighter integration with the scikit-learn pipeline API for cross-validation |
| Data access | pandasdmx | direct OECD REST API | Direct requests work but pandasdmx handles SDMX parsing, rate limiting, and multi-indicator assembly automatically |
| Linting | ruff | flake8 + black | flake8 + black is the legacy combination; ruff replaces both at 10-100x speed |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| pandas-datareader for OECD | OECD changed their API in 2023; pandas-datareader's OECD reader no longer works | pandasdmx |
| pandas-datareader for World Bank | Functional but unmaintained and less ergonomic than wbgapi | wbgapi |
| fbprophet (old package name) | Renamed to `prophet` at v1.0; fbprophet on PyPI is abandoned | prophet |
| pandas <3.0 for new projects | Copy-on-Write warnings will fill logs; string dtype inference changed — start with 3.0 clean | pandas 3.0.x |
| scikit-learn GradientBoostingClassifier/Regressor | The original (non-Histogram) GBM in sklearn is orders of magnitude slower than alternatives; it exists for legacy reasons | LightGBM or scikit-learn HistGradientBoosting |
| TensorFlow / PyTorch for this project | Neural networks require large datasets to outperform gradient boosting on tabular economic data. AI industry data has at most hundreds of annual/quarterly observations — neural nets will overfit. | LightGBM + Prophet |
| Plotly Express with pandas <3.0 | Plotly 6.x uses Narwhals, which changed the DataFrame bridge; old Plotly + new pandas combinations produce unexpected behavior | Plotly 6.6.x with pandas 3.0.x |
| FPDF / FPDF2 | Lower-quality CSS rendering than WeasyPrint; tables and charts in economic reports require proper CSS layout | WeasyPrint + Jinja2 |
| conda for environment management | conda is slower and creates conflicts with modern Python packaging. The community has largely moved to uv/pip ecosystems | uv |

---

## Stack Patterns by Variant

**If extending to additional industries (v2+):**
- Keep all data collectors behind a `DataCollector` protocol/abstract class so new industry collectors can be added without modifying core modeling code
- Store per-industry raw data in separate Parquet files under `data/raw/{industry}/`
- The modeling layer (statsmodels + LightGBM pipeline) is industry-agnostic by design — parameterize by indicator names, not hardcoded column references

**If AI market data proves too sparse for ARIMA (fewer than 30 annual observations):**
- Lean more heavily on Prophet, which handles short series with structural breaks better
- Supplement with transfer learning from related economic indicators (R&D spending, semiconductor revenue, cloud infrastructure spend) as regressors in the Prophet `add_regressor()` API

**If the methodology paper targets academic publication (beyond LinkedIn):**
- Add `statsmodels` summary tables exported via `.summary().as_latex()` directly
- Add `matplotlib` figures saved at 300 DPI with publication-standard typefaces (set `rcParams['font.family'] = 'serif'`)

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| pandas 3.0.x | statsmodels 0.14.6+ | statsmodels 0.14.6 specifically fixes a pandas 3.0 import blocker (released Dec 2025). Do not use statsmodels <0.14.6 with pandas 3.0 |
| pandas 3.0.x | Plotly 6.6.x | Plotly 6.0+ uses Narwhals for DataFrame interop — required for pandas 3.0 compatibility |
| pandas 3.0.x | LightGBM 4.6.x | LightGBM 4.6 supports pandas 3.0. Older LightGBM versions may issue deprecation warnings on `.values` access patterns |
| Prophet 1.1.x | pandas >=3.0 | Prophet updated to support pandas >=3.0 and numpy >=2.4 per recent changelog |
| Plotly 6.x | Jupyter Notebook <7.0 | Plotly 6.0 dropped Notebook <7.0 support. Use JupyterLab 4.x or Notebook 7.x |
| WeasyPrint 68.x | Python >=3.10 | WeasyPrint requires Python 3.10+. Python 3.12 (recommended) is fully supported |
| scikit-learn 1.8.0 | Python >=3.10 | scikit-learn 1.7+ requires Python 3.10+ |

---

## Sources

- [pandas release notes — v3.0.0 (January 2026)](https://pandas.pydata.org/docs/whatsnew/v3.0.0.html) — MEDIUM confidence (official docs, version confirmed)
- [statsmodels PyPI — v0.14.6](https://pypi.org/project/statsmodels/) — HIGH confidence (PyPI official)
- [scikit-learn release history — v1.8.0](https://scikit-learn.org/stable/whats_new.html) — HIGH confidence (official docs)
- [LightGBM PyPI — v4.6.0](https://pypi.org/project/lightgbm/) — HIGH confidence (PyPI official)
- [XGBoost installation guide — v3.2.0](https://xgboost.readthedocs.io/en/stable/install.html) — HIGH confidence (official docs)
- [Plotly PyPI — v6.6.0](https://pypi.org/project/plotly/) — HIGH confidence (PyPI official)
- [Dash PyPI — v4.0.x](https://pypi.org/project/dash/) — HIGH confidence (PyPI official)
- [WeasyPrint PyPI — v68.1](https://pypi.org/project/weasyprint/) — HIGH confidence (PyPI official)
- [wbgapi World Bank blog introduction](https://blogs.worldbank.org/en/opendata/introducing-wbgapi-new-python-package-accessing-world-bank-data) — MEDIUM confidence (official World Bank source)
- [eurostat PyPI — Eurostat new dissemination API](https://pypi.org/project/eurostat/) — MEDIUM confidence (PyPI official, decommission note from community sources)
- [pandasdmx OECD SDMX support](https://pandasdmx.readthedocs.io/en/v1.0/index.html) — MEDIUM confidence (official docs)
- [uv project management guide](https://docs.astral.sh/uv/guides/projects/) — HIGH confidence (official Astral docs)
- [Plotly Dash major release blog — hooks system](https://plotly.com/blog/plotly-dash-major-release/) — MEDIUM confidence (official Plotly blog)
- [Prophet GitHub — pandas 3.0 / numpy 2.4 support](https://github.com/facebook/prophet) — MEDIUM confidence (GitHub official)
- [pandas 3.0 CoW migration guide](https://medium.com/@kaushalsinh73/pandas-3-0-copy-on-write-migration-guide-the-surprising-performance-wins-and-the-silent-footguns-f6e76db73551) — LOW confidence (community blog, cross-referenced with official release notes)

---

*Stack research for: AI Industry Economic Valuation and Forecasting System*
*Researched: 2026-03-17*
