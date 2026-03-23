# Architecture Research

**Domain:** AI industry valuation model — v1.1 integration patterns
**Researched:** 2026-03-23
**Confidence:** HIGH (based on direct codebase inspection + domain patterns)

---

## Standard Architecture

### System Overview: v1.0 Existing vs v1.1 Target

The existing pipeline has a clean 4-layer architecture. v1.1 adds a new data sourcing layer (market anchors + company filings) and replaces the value conversion layer. The PCA composite index + value chain multiplier approach is retired; real USD outputs come directly from the anchor-calibrated model.

```
┌─────────────────────────────────────────────────────────────────────┐
│  DATA LAYER                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ World Bank   │  │  OECD MSTI   │  │  LSEG Workspace           │  │
│  │ (macro proxy)│  │ (proxy)      │  │  (company financials)     │  │
│  └──────┬───────┘  └──────┬───────┘  └─────────────┬─────────────┘  │
│         │                 │                         │               │
│  ┌──────┴─────────────────┴─────────────────────────┴─────────────┐  │
│  │  NEW: market_anchors.py                                        │  │
│  │  ┌──────────────────┐  ┌──────────────────┐                   │  │
│  │  │ Published Market │  │ Private Company  │                   │  │
│  │  │ Estimates (YAML) │  │ Valuations (YAML)│                   │  │
│  │  └──────────────────┘  └──────────────────┘                   │  │
│  └────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│  PROCESSING LAYER  (largely preserved)                              │
│  deflate → interpolate → tag → validate → Parquet cache             │
│  NEW: revenue_attribution.py, dcf_valuation.py (in processing/)     │
├─────────────────────────────────────────────────────────────────────┤
│  MODELING LAYER                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  REPLACED: PCA composite index as Y variable                  │  │
│  │  NEW: Anchor-calibrated model                                  │  │
│  │  - Real USD market estimates as Y variable                    │  │
│  │  - Macro/proxy indicators as explanatory X variables          │  │
│  │  - ARIMA/Prophet now trained on USD values                    │  │
│  │  - LightGBM residual boosting on USD residuals                │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  NEW: src/backtesting/                                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Holdout validation, walk-forward CV, MAPE/R² with actuals   │  │
│  └───────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│  DASHBOARD LAYER                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │
│  │  Basic   │  │ Overview │  │ Segments │  │ Drivers/Diag.    │    │
│  │  (NEW)   │  │(updated) │  │(updated) │  │(fixed actuals)   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | v1.0 Status | v1.1 Action | Responsibility |
|-----------|-------------|-------------|----------------|
| `src/ingestion/pipeline.py` | EXISTS | Modify | Add market_anchors step; keep error-isolated step pattern |
| `src/ingestion/world_bank.py` | EXISTS | Preserve | Macro proxy indicators (explanatory X vars, not Y) |
| `src/ingestion/oecd.py` | EXISTS | Preserve | R&D and patent proxy indicators |
| `src/ingestion/lseg.py` | EXISTS | Extend | Add AI revenue attribution fields per company |
| `src/ingestion/market_anchors.py` | NEW | Create | Load published estimates + private company valuations from YAML |
| `src/processing/normalize.py` | EXISTS | Preserve | Deflation, interpolation, tagging pipeline |
| `src/processing/validate.py` | EXISTS | Modify | Add MARKET_ANCHOR_SCHEMA and ATTRIBUTION_SCHEMA |
| `src/processing/revenue_attribution.py` | NEW | Create | Isolate AI revenue share from conglomerate financials |
| `src/processing/dcf_valuation.py` | NEW | Create | DCF + AI value multiplier estimates for private companies |
| `src/processing/features.py` | EXISTS | Modify | PCA composite retired as primary; indicators become explanatory X variables |
| `src/models/statistical/arima.py` | EXISTS | Modify | Retrain on USD market size values (not index scores) |
| `src/models/statistical/prophet_model.py` | EXISTS | Modify | Same — fit on USD values |
| `src/models/ml/gradient_boost.py` | EXISTS | Modify | USD residuals as target; feature matrix changes |
| `src/models/ensemble.py` | EXISTS | Preserve | Inverse-RMSE weighting logic is unit-agnostic |
| `src/inference/forecast.py` | EXISTS | Modify | Remove value chain multiplier path; output natively in USD |
| `src/diagnostics/model_eval.py` | EXISTS | Modify | Activate MAPE/R² computation now that actuals exist |
| `src/backtesting/` | NEW | Create | Holdout framework, walk-forward CV, benchmark comparison |
| `src/dashboard/app.py` | EXISTS | Modify | Remove multiplier calibration block (lines 53-109); load backtesting Parquet |
| `src/dashboard/tabs/basic.py` | NEW | Create | Basic tier: total market cap KPIs, CAGR, segment bar chart |
| `src/dashboard/layout.py` | EXISTS | Modify | Add Basic tier as fifth tab in navigation |
| `src/dashboard/callbacks.py` | EXISTS | Modify | Add `elif active_tab == "basic"` routing branch |
| `src/dashboard/charts/backtest.py` | EXISTS | Replace | Rewrite to show actual vs predicted (currently only residuals) |
| `src/dashboard/tabs/diagnostics.py` | EXISTS | Modify | Wire real MAPE/R² values; update chart to actual vs predicted |
| `config/industries/ai.yaml` | EXISTS | Extend | Add market_anchors, private_company_valuations, revenue_attribution sections |

---

## Recommended Project Structure

New code fits into the existing `src/` package structure with two new top-level packages and three new processing modules.

```
src/
├── ingestion/
│   ├── pipeline.py             # MODIFY: add market_anchors step to run_full_pipeline()
│   ├── world_bank.py           # PRESERVE
│   ├── oecd.py                 # PRESERVE
│   ├── lseg.py                 # EXTEND: add AI revenue fields to fetch_company_financials()
│   └── market_anchors.py       # NEW: loads YAML anchors → Parquet (no API calls)
│
├── processing/
│   ├── normalize.py            # PRESERVE
│   ├── deflate.py              # PRESERVE
│   ├── interpolate.py          # PRESERVE
│   ├── tag.py                  # PRESERVE
│   ├── validate.py             # MODIFY: add two new pandera schemas
│   ├── features.py             # MODIFY: build_indicator_matrix preserved; PCA demoted to comparison utility
│   ├── revenue_attribution.py  # NEW: AI revenue isolation from conglomerate financials
│   └── dcf_valuation.py        # NEW: DCF + AI multiple for private companies
│
├── models/
│   ├── ensemble.py             # PRESERVE: weighting logic is unit-agnostic
│   ├── statistical/
│   │   ├── arima.py            # MODIFY: fit on USD values, not index scores
│   │   ├── prophet_model.py    # MODIFY: same
│   │   └── regression.py       # PRESERVE or extend for anchor regression
│   └── ml/
│       ├── gradient_boost.py   # MODIFY: feature matrix changes; target still residuals but USD
│       └── quantile_models.py  # PRESERVE: quantile regression logic is unit-agnostic
│
├── inference/
│   ├── forecast.py             # MODIFY: remove value chain multiplier path
│   └── shap_analysis.py        # PRESERVE: SHAP works on any LightGBM model
│
├── diagnostics/
│   ├── model_eval.py           # MODIFY: wire compute_mape/compute_r2 to backtest actuals
│   └── structural_breaks.py    # PRESERVE
│
├── backtesting/                # NEW package
│   ├── __init__.py
│   ├── holdout.py              # Holdout split + evaluation against known anchor estimates
│   ├── walk_forward.py         # Walk-forward CV across historical anchor points
│   └── benchmark_compare.py    # Compare model output vs analyst consensus ranges
│
├── dashboard/
│   ├── app.py                  # MODIFY: remove multiplier block; load backtesting_results.parquet
│   ├── layout.py               # MODIFY: add Basic tab (5th entry in dcc.Tabs)
│   ├── callbacks.py            # MODIFY: add elif active_tab == "basic" branch
│   ├── charts/
│   │   ├── fan_chart.py        # PRESERVE
│   │   ├── backtest.py         # REPLACE: actual vs predicted chart (not just residuals)
│   │   └── styles.py           # PRESERVE
│   └── tabs/
│       ├── basic.py            # NEW: Basic tier layout
│       ├── overview.py         # MODIFY: remove multiplier derivation Expert block
│       ├── segments.py         # MODIFY: USD values now native, not multiplier-converted
│       ├── drivers.py          # PRESERVE: SHAP output structure unchanged
│       └── diagnostics.py      # MODIFY: real MAPE/R²; actual vs predicted chart
│
└── reports/                    # PRESERVE (PDF content updates are downstream of this milestone)
```

### Structure Rationale

- **`src/backtesting/`** is a new top-level package, not a subfolder of `diagnostics/`, because backtesting is a pipeline-time concern (runs during model training/validation), not a dashboard display concern. Diagnostics consumes backtesting output files.
- **`src/ingestion/market_anchors.py`** is in ingestion (not processing) because it loads external reference data at the same stage as World Bank/OECD — it is a data source, not a transformation. It reads from YAML config and writes raw Parquet, matching the ingestion layer's responsibility.
- **`revenue_attribution.py` and `dcf_valuation.py`** belong in processing because they transform raw company financials into model-ready USD values — they are processing steps, not models.
- `build_pca_composite` is kept in `features.py` as a comparison path for Expert mode methodology transparency, not as the primary modeling path.

---

## Architectural Patterns

### Pattern 1: Anchor-Calibrated Regression (Replaces PCA + Multiplier)

**What:** Instead of building a dimensionless PCA composite index and multiplying to USD via a single anchor value, the new model uses published market size estimates directly as the dependent variable (Y) and treats macroeconomic/proxy indicators as explanatory variables (X). ARIMA/Prophet fit directly on the USD time series; LightGBM corrects residuals in USD units.

**When to use:** Any time you have sparse but real ground-truth observations and many correlated proxy indicators.

**Trade-offs:** Fewer observations for model fitting (published estimates typically cover 2017-2025, giving ~8 data points); the model is more transparent and auditable but more dependent on the quality of anchor inputs.

**Impact on `app.py`:** The value chain multiplier calibration block (approximately lines 53-109 in the current `app.py`) is removed entirely. Module-level globals simplify from `FORECASTS_DF` + `VALUE_CHAIN_MULTIPLIERS` + `VALUE_CHAIN_DERIVATION` to just `FORECASTS_DF` + `BACKTESTING_DF`. The `usd_point` columns that were computed as `index * multiplier` are replaced by the native model output.

```python
# v1.0 pattern (RETIRED in v1.1)
usd_point = point_estimate_real_2020 * VALUE_CHAIN_MULTIPLIERS[seg]

# v1.1 pattern — no conversion needed
# point_estimate_real_2020 IS already in USD billions
# Column name preserved for schema backward compatibility
```

### Pattern 2: Revenue Attribution via Segment Disclosure + Analogue Ratios

**What:** For mixed-tech companies (e.g., Alphabet, Microsoft, IBM), AI revenue is isolated using a two-step approach:
1. **Explicit disclosures:** Companies that report AI segment revenue directly are loaded from LSEG fields configured in `ai.yaml` under `revenue_attribution.explicit_disclosure`.
2. **Analogue ratios:** For companies without explicit AI disclosure, apply an attribution ratio sourced from analyst estimates, stored as YAML in `revenue_attribution.analogue_ratios`.

**When to use:** Whenever LSEG financial data returns total company revenue for a conglomerate with mixed AI and non-AI business lines.

**Trade-offs:** Attribution ratios for non-disclosing companies introduce estimation error. The design stores ratio, source, and uncertainty band in YAML so Expert mode can surface the methodology. The `revenue_attribution.py` output always includes `attribution_method`, `ratio_source`, and `uncertainty_low/high` fields — not just a single number.

```python
# src/processing/revenue_attribution.py
def estimate_ai_revenue(
    company_revenue: float,
    ric: str,
    attribution_config: dict,
    year: int,
) -> dict:
    """
    Returns:
        ai_revenue_usd: float
        attribution_method: "explicit_disclosure" | "analogue_ratio"
        ratio: float
        ratio_source: str
        uncertainty_low: float
        uncertainty_high: float
    """
```

### Pattern 3: Private Company Valuation via DCF + AI Revenue Multiple

**What:** Private AI companies (OpenAI, Anthropic, xAI, etc.) lack market prices. The model uses a two-track approach:
1. **Revenue proxy:** Last known funding round valuation divided by prevailing AI revenue multiple (from public comps) gives implied revenue, projected forward with the segment growth rate.
2. **DCF anchor:** Where cash flow data is available from secondary sources, apply a simple DCF with terminal value based on comparable public company exit multiples.

All private valuation inputs are stored in YAML (not code), so they can be updated without model changes — consistent with the ARCH-01 config-driven extensibility principle.

**Trade-offs:** Private valuations have wide uncertainty bands (typically 30-50%). The `dcf_valuation.py` output always includes `valuation_method`, `data_freshness_date`, and `uncertainty_band_pct` fields. These surface directly in Expert mode.

```yaml
# config/industries/ai.yaml (new section)
private_company_valuations:
  - name: "OpenAI"
    segment: "ai_software"
    last_known_valuation_usd_billions: 157.0
    valuation_date: "2024-10-01"
    valuation_method: "funding_round"
    revenue_multiple_peer: "ai_software_public_median"
    uncertainty_band_pct: 40
```

### Pattern 4: Backtesting via Walk-Forward Holdout Against Known Anchors

**What:** The backtesting framework uses known historical market size estimates (from published analyst reports, stored in YAML) as "ground truth." Walk-forward validation: train on data through year T, forecast T+1 to T+3, compare against the known estimate for those years.

**When to use:** Model validation before any forecast is displayed in the dashboard. The backtesting output writes `backtesting_results.parquet` to `data/processed/`. The diagnostics tab and `model_eval.py` read from this file.

**Trade-offs:** The number of holdout points is small (AI market estimates with consensus coverage start around 2017, giving at most ~8 years). MAPE over 5-8 observations is noisy. The framework reports this limitation explicitly in the diagnostics display.

**Pipeline execution order (critical for dependency management):**
```
1. Ingest all sources including market_anchors
2. Process + revenue_attribution + dcf_valuation → processed Parquet files
3. Build indicator matrix (macro proxies as X vars)
4. Fit ARIMA/Prophet/LightGBM on anchor USD series
5. Run backtesting → write backtesting_results.parquet
6. Run full forecast → write forecasts_ensemble.parquet
7. Dashboard reads from Parquet cache at startup (no model objects at runtime)
```

---

## Data Flow

### v1.1 Pipeline Run

```
[python scripts/run_pipeline.py]
    |
    v
run_full_pipeline("ai")
    |
    +---> market_anchors.py ------> data/raw/market_anchors/ai_anchors.parquet
    |                               (published estimates: IDC, Gartner, Goldman)
    |
    +---> world_bank.py + oecd.py -> data/raw/ (unchanged)
    |
    +---> lseg.py (extended) -----> data/raw/lseg/ (adds AI revenue fields)
    |
    v
processing layer
    |
    +---> revenue_attribution.py --> attaches ai_revenue_usd to company rows
    |
    +---> dcf_valuation.py --------> private company USD estimates
    |
    +---> normalize / deflate / tag / validate (unchanged)
    |
    v
data/processed/
    ├── world_bank_ai.parquet          (unchanged schema)
    ├── oecd_msti_ai.parquet           (unchanged schema)
    ├── lseg_ai.parquet                (extended: + ai_revenue_usd column)
    ├── market_anchors_ai.parquet      (NEW: year, segment, usd_billions, source)
    └── private_valuations_ai.parquet  (NEW: company, segment, usd_billions, method)
    |
    v
modeling layer
    |
    +---> Fit ARIMA/Prophet on market_anchors_ai USD series (per segment)
    +---> LightGBM fits on USD residuals using macro indicators as X features
    +---> backtesting/ --> backtesting_results.parquet  (NEW)
    +---> inference/forecast.py --> forecasts_ensemble.parquet (USD native, no multiplier)
    |
    v
dashboard reads Parquet cache at startup
```

### Dashboard Tier Data Flow (Runtime)

```
[User opens browser]
    |
    v
app.py startup
    ├── reads forecasts_ensemble.parquet   (USD billions, direct)
    ├── reads residuals_statistical.parquet
    ├── reads backtesting_results.parquet  (NEW)
    └── NO multiplier calibration block    (removed)
    |
    v
layout.py: 5 tabs rendered
    ├── Basic      -> KPI cards (total market, CAGR, segment share bar)
    ├── Overview   -> fan chart + segment table (USD native)
    ├── Segments   -> per-segment fan charts
    ├── Drivers    -> SHAP (unchanged)
    └── Diagnostics -> real MAPE/R² table + actual vs predicted chart
```

### Key Data Contract Change

The single most important schema change in v1.1:

| Column | v1.0 meaning | v1.1 meaning |
|--------|-------------|-------------|
| `point_estimate_real_2020` | Dimensionless PCA index score | USD billions (2020 constant) |
| `usd_point` | `index × VALUE_CHAIN_MULTIPLIERS[seg]` computed in app.py | Alias of `point_estimate_real_2020` (or removed) |
| `ci80_lower/upper` | Index score CI from quantile regression | USD billions CI from quantile regression |

**Recommendation:** Keep the column name `point_estimate_real_2020` in `forecasts_ensemble.parquet` for schema continuity. The values change from dimensionless index units to USD billions, but existing dashboard code that reads this column continues to work without changes — only the multiplier application block in `app.py` is removed.

---

## Integration Points

### Existing Components: Modify vs Replace vs Preserve

| Component | Action | Integration Risk | Key Notes |
|-----------|--------|-----------------|-----------|
| `src/ingestion/pipeline.py` | Modify | LOW | Add market_anchors step to `steps` list; existing error-isolation pattern applies unchanged |
| `src/processing/validate.py` | Modify | LOW | Add two new pandera schemas; existing three schemas untouched |
| `src/processing/features.py` | Modify | MEDIUM | `build_indicator_matrix` is preserved and reused — macro indicators become X variables. `build_pca_composite` becomes a comparison utility, not the primary path |
| `src/models/statistical/arima.py` | Modify | MEDIUM | Retrain on USD series; API surface unchanged but training data and units change |
| `src/models/ml/gradient_boost.py` | Modify | MEDIUM | Feature matrix changes (real indicators vs index features); target shifts to USD residuals; hyperparameters need retuning |
| `src/inference/forecast.py` | Modify | MEDIUM | Remove `reflate_to_nominal` as required step; `clip_ci_bounds` and `build_forecast_dataframe` are preserved |
| `src/dashboard/app.py` | Modify | HIGH | The multiplier calibration block (current lines 53-109) is the highest-risk deletion. Module-level globals simplify significantly. Load `backtesting_results.parquet` at startup |
| `src/dashboard/charts/backtest.py` | Replace | LOW | Currently only shows residual bars (no actuals). Complete rewrite needed; `make_backtest_chart` function signature can be preserved |
| `src/dashboard/tabs/diagnostics.py` | Modify | MEDIUM | `"N/A"` MAPE/R² become real values sourced from backtesting_results; table structure and styling unchanged |

### New Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `market_anchors.py` → processing layer | `data/raw/market_anchors/ai_anchors.parquet` | New Parquet file in existing raw layer pattern |
| `backtesting/` → `diagnostics/model_eval.py` | `data/processed/backtesting_results.parquet` | Written by pipeline, read by dashboard; no circular dependency |
| `revenue_attribution.py` → modeling | Extended `lseg_ai.parquet` with `ai_revenue_usd` column | Modeling layer reads the column; existing read paths unchanged |

### Config Extension Pattern

The YAML extension preserves ARCH-01 extensibility. New sections follow the existing list-of-dicts pattern:

```yaml
# config/industries/ai.yaml (new sections to add)

market_anchors:
  - year: 2023
    total_usd_billions: 207
    source: "IDC Worldwide AI Spending Guide 2024"
    confidence: "consensus"
  - year: 2022
    total_usd_billions: 142
    source: "Goldman Sachs AI Infrastructure Report 2023"
    confidence: "single_source"

revenue_attribution:
  explicit_disclosure:
    - ric: "MSFT.O"
      field: "azure_openai_revenue"
      coverage_years: [2023, 2024, 2025]
  analogue_ratios:
    - ric: "GOOGL.O"
      ai_revenue_ratio: 0.22
      ratio_source: "Alphabet Q4 2024 10-K analyst decomposition"
      ratio_uncertainty: 0.08

private_company_valuations:
  - name: "OpenAI"
    segment: "ai_software"
    last_known_valuation_usd_billions: 157.0
    valuation_date: "2024-10-01"
    valuation_method: "funding_round"
    revenue_multiple_peer: "ai_software_public_median"
    uncertainty_band_pct: 40
```

---

## Anti-Patterns

### Anti-Pattern 1: Recalibrating the Value Chain Multiplier Instead of Replacing It

**What people do:** Leave the PCA composite + multiplier in place but try to "better calibrate" the anchor to real market data.

**Why it's wrong:** The root problem is not the anchor value — it is that the composite index has no direct causal relationship to AI market size. Better anchoring a structurally flawed model improves numbers that still lack economic interpretability. The diagnostics tab would still show near-meaningless metrics because there are no direct actuals to compare the model against.

**Do this instead:** Replace PCA composite as the Y variable with real market size estimates. Macro indicators become X variables. The multiplier block in `app.py` is deleted, not recalibrated.

### Anti-Pattern 2: Building New Components as Standalone Scripts Outside the Pipeline

**What people do:** Build `revenue_attribution.py`, `dcf_valuation.py`, and `backtesting/` as standalone scripts called directly from the command line.

**Why it's wrong:** The existing `run_full_pipeline()` uses an error-isolated step list. Components that bypass this pattern create maintenance inconsistency and lose the guarantee that partial failures do not abort the pipeline.

**Do this instead:** Add new components as steps in the `steps` list in `run_full_pipeline()`. Each new component returns a `Path` to a written Parquet file, matching the existing pattern.

### Anti-Pattern 3: Writing Actuals into `residuals_statistical.parquet`

**What people do:** Add `actual` and `predicted` columns to the existing `residuals_statistical.parquet` to fix the diagnostics tab quickly.

**Why it's wrong:** `residuals_statistical.parquet` has a defined schema that existing code and tests read. Changing it risks breaking the Diagnostics tab, the backtest chart, and the 233 existing tests that check schema conformance.

**Do this instead:** Write a separate `backtesting_results.parquet` with its own schema (`year`, `segment`, `actual_usd`, `predicted_usd`, `residual_usd`, `model`, `holdout_type`). The diagnostics tab reads from this new file for MAPE/R² display.

### Anti-Pattern 4: Building Basic Tier as a Second Dash App Instance

**What people do:** Create a separate Dash app on a different port to keep the Basic tier "clean" and simple.

**Why it's wrong:** Two Dash instances create deployment complexity with no benefit. The existing layout already handles tier separation via tab navigation.

**Do this instead:** Add `basic` as a fifth tab value in `layout.py`. The Basic tab renders via the existing `render_tab()` callback with a new `elif active_tab == "basic"` branch. Basic tab content (KPI cards only) aggregates from the same `FORECASTS_DF` already loaded at startup — no new data load needed.

---

## Build Order (Dependency-Aware)

The correct build sequence respects data dependencies. New data must exist before models can be retrained on it; models must be retrained before the dashboard can display real diagnostics.

```
Phase A: Data Foundation
  1. Extend config/industries/ai.yaml with market_anchors + private valuations + revenue_attribution
  2. Build src/ingestion/market_anchors.py (load YAML anchors to Parquet)
  3. Extend src/processing/validate.py with new pandera schemas
  4. Build src/processing/revenue_attribution.py
  5. Build src/processing/dcf_valuation.py
  6. Wire all into src/ingestion/pipeline.py (add steps to run_full_pipeline)
  7. Run pipeline end-to-end to verify new Parquet files are written

Phase B: Model Rework (requires Phase A Parquet files)
  8. Modify src/processing/features.py (indicators become X variable matrix)
  9. Modify src/models/statistical/arima.py + prophet_model.py (fit on USD series)
  10. Modify src/models/ml/gradient_boost.py (USD residuals, updated feature matrix)
  11. Build src/backtesting/holdout.py + walk_forward.py + benchmark_compare.py
  12. Wire backtesting into pipeline run (writes backtesting_results.parquet)
  13. Modify src/inference/forecast.py (remove multiplier path; USD native output)
  14. Modify src/diagnostics/model_eval.py (activate MAPE/R² with backtesting actuals)

Phase C: Dashboard (requires Phase B Parquet outputs)
  15. Modify src/dashboard/app.py (remove multiplier calibration block; load backtesting data)
  16. Build src/dashboard/tabs/basic.py (Basic tier KPI cards)
  17. Modify src/dashboard/layout.py (add Basic tab as 5th tab)
  18. Modify src/dashboard/callbacks.py (route basic tab)
  19. Replace src/dashboard/charts/backtest.py (actual vs predicted chart)
  20. Modify src/dashboard/tabs/diagnostics.py (real metrics display)
  21. Modify src/dashboard/tabs/overview.py (remove multiplier derivation Expert block)
  22. Modify src/dashboard/tabs/segments.py (USD native, no post-hoc conversion)
```

**Critical dependency:** Steps 8-14 cannot be validated end-to-end until Phase A is complete and a pipeline run has written `market_anchors_ai.parquet` with real USD anchor observations. Plan to run the pipeline after Phase A before starting Phase B.

---

## Scaling Considerations

This is a personal portfolio tool with a single user. Scale is not a concern. The relevant considerations are data volume and pipeline run time as more anchors are added.

| Concern | Current | v1.1 Impact |
|---------|---------|-------------|
| Pipeline run time | Minutes (API fetches dominate) | Slightly longer; market_anchors.py loads from YAML (instant); backtesting adds ~30s |
| Parquet cache size | ~10 MB | Adds ~2 MB for new anchor/backtesting/private valuation files |
| Dashboard startup time | Under 2s | Unchanged; backtesting Parquet is small |
| Model training time | Under 30s | Slightly longer due to walk-forward CV |

---

## Sources

- Direct codebase inspection: `src/` package (75 Python files, inspected 2026-03-23) — HIGH confidence
- [AI Startup Valuation Multiples 2026, Qubit Capital](https://qubit.capital/blog/ai-startup-valuation-multiples) — revenue multiple ranges for private company comparable analysis (MEDIUM confidence)
- [AI Business Valuation Model 2026, FE International](https://www.feinternational.com/blog/ai-business-valuation-model-2026) — DCF + revenue multiples framework for AI companies (MEDIUM confidence)
- [AI Valuation Multiples Q1 2026, Finro](https://www.finrofca.com/news/ai-valuation-multiples-q1-2026-update) — current private market multiple dispersion (MEDIUM confidence)
- [Backtesting forecasting models, Towards Data Science](https://towardsdatascience.com/putting-your-forecasting-model-to-the-test-a-guide-to-backtesting-24567d377fb5/) — walk-forward holdout validation pattern (HIGH confidence — standard practice)
- [Backtesting ML models for time series, Machine Learning Mastery](https://machinelearningmastery.com/backtest-machine-learning-models-time-series-forecasting/) — train/validation/holdout split for time series (HIGH confidence)

---

*Architecture research for: AI Industry Value Estimator v1.1 integration*
*Researched: 2026-03-23*
