# Phase 9: Ground-Up Model Rework and Value Chain Design - Research

**Researched:** 2026-03-24
**Domain:** Time-series model retraining on real USD anchors; value chain taxonomy; PCA/multiplier deletion; minimal dashboard pass-through
**Confidence:** HIGH (primary sources: direct codebase inspection + verified project research documents)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Model Target Variable:**
- Y variable: `median_real_2020` from `market_anchors_ai.parquet` — scope-normalized median in constant 2020 USD billions
- Granularity: Per-segment models (separate ARIMA/Prophet/LightGBM per hardware/infrastructure/software/adoption). Total = sum of segment forecasts
- Exogenous features: Keep World Bank/OECD macro indicators (R&D spend, patents, ICT exports, GDP) as X variables
- Confidence intervals: Two-layer uncertainty — (1) source disagreement from p25/p75 range, AND (2) model CIs from LightGBM quantile regression
- Forecast horizon: 2025-2030

**PCA Composite Fate:**
- Delete entirely — remove `build_indicator_matrix` PCA path from `features.py`, all related imports
- `features.py`: Delete `build_indicator_matrix` and rebuild from scratch as a flat feature builder — output aligned macro indicator matrix (not principal components)
- No Expert-mode comparison — old model is gone, not preserved as a side panel

**Value Chain Taxonomy:**
- 1:1 mapping between value chain layers and market segments: chip=hardware, cloud=infrastructure, application=software, end-market=adoption
- Multi-layer companies: Claude's discretion (see discretion section)
- Taxonomy locked in ai.yaml before any attribution percentages are written (Phase 10)

**Multiplier Deletion Scope:**
- Delete all multiplier code from `app.py` (VALUE_CHAIN_MULTIPLIERS, VALUE_CHAIN_DERIVATION blocks), `data_context.py` (value_chain_multipliers computation), and `overview.py` (multiplier display)
- Column name: Claude's discretion (see discretion section)
- ai.yaml value_chain section: Comment out / archive as legacy documentation, not delete
- Minimal dashboard fix in Phase 9 — delete multiplier conversion, add pass-through so dashboard renders without crashing with raw USD values. Full polish is Phase 11
- Contract test: Assert that `forecasts_ensemble.parquet` `point_estimate_real_2020` contains values in USD billions, not index units

### Claude's Discretion
- Whether to keep column name `point_estimate_real_2020` or rename
- Primary+secondary layer flags vs strict single assignment for multi-layer companies
- Exact feature alignment approach between macro indicators and market_anchors time series
- How to handle the 9-datapoint limitation (e.g., expanding window, synthetic augmentation, regularization)
- Minimal dashboard pass-through implementation details
- Which specific macro indicators to retain vs drop as exogenous features

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MODL-01 | ARIMA/Prophet/LightGBM retrained with real USD market sizes as target variable instead of composite index | Model retraining patterns from existing code + skforecast/statsmodels stack; market_anchors_ai.parquet is the Y source |
| MODL-04 | chip/cloud/application/end-market classification assigned per company preventing double-counting when aggregating to total market size | ai.yaml edgar_companies already has value_chain_layer; Phase 9 locks the 1:1 taxonomy and confirms every company has an assignment before Phase 10 writes attribution percentages |
| MODL-05 | Forecast trajectories reflect realistic AI growth (25-40% CAGR) with documented rationale where model diverges from consensus | Training on real USD anchors (scope-normalized IDC/Gartner/GVR data) provides the anchor gravity; CAGR verification contract test guards the range |
</phase_requirements>

---

## Summary

Phase 9 has four tightly-coupled work streams: (1) locking the value chain layer taxonomy in `ai.yaml`, (2) auditing and gating the model version interface contract, (3) retraining ARIMA and Prophet on real USD series from `market_anchors_ai.parquet`, and (4) retraining LightGBM on USD residuals and deleting the multiplier path entirely.

The highest-risk operation is the multiplier deletion. The existing codebase has multiplier logic in three files: `app.py` (lines 53-109: VALUE_CHAIN_MULTIPLIERS, VALUE_CHAIN_DERIVATION derivation, usd_* column attachment), `data_context.py` (lines 80-118: identical multiplier logic for report rendering), and `overview.py` (VALUE_CHAIN_MULTIPLIERS and VALUE_CHAIN_DERIVATION imports, usage in `_build_expert_methodology_card` and `build_overview_layout`). All three files currently use `usd_point` as the display column. After Phase 9, `point_estimate_real_2020` will be USD billions directly — the `usd_point` column concept either disappears or becomes an alias. The minimal dashboard fix is replacing `usd_point` references with `point_estimate_real_2020` in all tabs that render before Phase 11.

The 9-datapoint constraint is the primary modeling challenge. `market_anchors_ai.parquet` covers 2017-2025, giving 9 annual observations per segment. ARIMA with max_p=2, max_q=2 and AICc is appropriate for this N. Prophet with an explicit changepoint at 2022 (GenAI surge) will capture the structural break. LightGBM with strong regularization (min_child_samples=3, max_depth=3, already set in existing code) is appropriate; the feature matrix shifts from residual lags to macro indicator regressors plus lag features. The two-layer uncertainty design (p25/p75 source spread as an uncertainty band independent of model CIs) is architecturally novel and requires implementing a `source_disagreement_band` calculation in the forecast pipeline.

**Primary recommendation:** Execute in strict plan order: P09-01 (taxonomy + config) → P09-02 (interface audit + model version gating) → P09-03 (ARIMA/Prophet retraining) → P09-04 (LightGBM + multiplier deletion). P09-02 must precede all model code because the interface contract test is what proves P09-03 and P09-04 are wired correctly.

---

## Standard Stack

### Core (all verified in project STACK.md)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 3.0.x | DataFrame operations; CoW-safe | Project-standard; all existing code written for it |
| statsmodels | 0.14.6 | ARIMA via ARIMA class | Existing `arima.py` uses this; 0.14.6 required for pandas 3.0 compat |
| pmdarima | latest | auto_arima AICc order selection | Existing `select_arima_order()` uses this; keep for USD retraining |
| prophet | 1.1.x | Additive trend model with structural break | Existing `prophet_model.py` uses this |
| lightgbm | 4.6.0 | Gradient boosting residual correction | Existing `gradient_boost.py` uses this |
| scikit-learn | 1.8.0 | TimeSeriesSplit, Pipeline, StandardScaler | Existing feature engineering uses this |
| pyarrow | 18.x | Parquet I/O | Project-standard for all Parquet cache operations |
| pandera | 2.x | Schema validation | Existing validate.py uses this; contract test for USD billions range |
| pydantic | 2.x | Config validation | Already in lock file per STACK.md |
| yaml | stdlib | ai.yaml config reading | Already used throughout |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | 2.x | Array math for feature engineering | Already project-standard |
| scipy | 1.14.x | Additional statistical tests if needed | Available; use for stationarity diagnostics |
| shap | 0.46.x | Feature importance after LightGBM retraining | Existing `shap_analysis.py` will gain credibility with USD Y variable |

### Installation note
No new packages required for Phase 9. All dependencies are already in the project lock file. Use `uv sync` to verify the environment is current before running retrained models.

---

## Architecture Patterns

### Recommended Execution Order (Dependency-Aware)

```
Plan 09-01: ai.yaml taxonomy lock
  - Add value_chain_layer_taxonomy section to ai.yaml
  - Comment out (archive) value_chain multiplier section
  - Confirm all 14 edgar_companies have value_chain_layer assigned
  - Write TAXONOMY.md documenting 1:1 layer-to-segment mapping rationale

Plan 09-02: Interface contract audit + model version gating
  - Add model_version flag to pipeline config or ai.yaml
  - Audit all 9 downstream consumers of forecasts_ensemble.parquet
  - Write contract test: assert point_estimate_real_2020 values are USD billions range
  - Delete multiplier blocks from app.py, data_context.py, overview.py
  - Add minimal dashboard pass-through (point_estimate_real_2020 direct to display)

Plan 09-03: ARIMA + Prophet retraining on USD series
  - Rebuild build_indicator_matrix as flat feature builder (delete PCA path)
  - Load market_anchors_ai.parquet, extract median_real_2020 per segment per year
  - Retrain ARIMA per segment on USD series
  - Retrain Prophet per segment on USD series with 2022 changepoint
  - Update residuals Parquet: residuals now in USD billions

Plan 09-04: LightGBM retraining + multiplier path deletion
  - Update feature matrix: macro indicator matrix (X) + residual lags
  - Retrain LightGBM on USD residuals from ARIMA/Prophet
  - Delete VALUE_CHAIN_MULTIPLIERS remaining references in inference/forecast.py
  - Write forecasts_ensemble.parquet with point_estimate_real_2020 in USD billions
  - Run contract test suite; verify 25-40% CAGR range; document divergence
```

### Pattern 1: Flat Feature Builder (Replaces PCA composite in features.py)

The existing `build_indicator_matrix` returns `(np.ndarray, pd.Index)` — this signature is reusable. The function must be rebuilt to return macro indicators as X variables in aligned time-series format, not PCA scores.

```python
# New build_indicator_matrix signature — same as before, different semantics
def build_indicator_matrix(
    df: pd.DataFrame,
    indicators: list[str],
    segment: str | None = None,
) -> tuple[np.ndarray, pd.Index]:
    """
    Build flat indicator matrix from long-format processed data.
    Output: wide matrix (n_years x n_indicators) in value_real_2020 units.
    No PCA reduction applied. Indicators are aligned macro X variables.
    """
```

The `build_pca_composite` function is deleted per locked decision. The `build_manual_composite` and `assess_stationarity` functions are preserved unchanged — they are still useful for analysis.

**Test impact:** `test_features.py::TestPcaComposite` must be deleted or marked as testing a removed function. `TestBuildIndicatorMatrix` tests should continue to pass — the function signature is unchanged, only the docstring/intent changes.

### Pattern 2: Market Anchors as Y Variable

```python
# Load market_anchors_ai.parquet — this is the Phase 8 output
anchors = pd.read_parquet(DATA_PROCESSED / "market_anchors_ai.parquet")

# Extract per-segment USD series for model training
# Y variable = median_real_2020 (scope-normalized median in 2020 constant USD billions)
seg_series = (
    anchors[anchors["segment"] == segment]
    .sort_values("estimate_year")
    .set_index("estimate_year")["median_real_2020"]
)
# This is a pd.Series of length 9 (years 2017-2025), indexed by year
# Values are in USD billions — e.g., ai_hardware ~70-150B range
```

**Two-layer uncertainty implementation:**
- Layer 1 (source disagreement): `p75_real_2020 - p25_real_2020` gives the interquartile spread from source disagreement. This is a fixed band per training observation, not a model CI.
- Layer 2 (model CI): ARIMA prediction intervals + LightGBM quantile regression CIs for forecast years.
- In `forecasts_ensemble.parquet`, the `ci80_lower/upper` columns should reflect the wider of the two uncertainty sources. The source disagreement band is surfaced as a separate column or encoded in the CI bounds.

### Pattern 3: ARIMA Retraining on USD Series

The existing `fit_arima_segment` function in `arima.py` takes a `pd.Series` — no structural change needed. The caller changes: pass `seg_series` (USD billions) instead of PCA composite scores.

```python
# Retrain — same function, new input
order = select_arima_order(seg_series)  # auto-selects p,d,q for 9-obs series
results = fit_arima_segment(seg_series, order)
forecast_df = forecast_arima(results, steps=6)  # 2025-2030

# Residuals now in USD billions
resid = get_arima_residuals(results, seg_series.index)
```

**9-observation constraint:** With N=9, pmdarima `auto_arima` with `max_p=2, max_q=2` and AICc will likely select ARIMA(1,1,0) or ARIMA(0,1,1) per segment. The AICc correction is critical at this N — do not use plain AIC. The existing `select_arima_order()` already enforces this.

**Confidence intervals:** `forecast_arima(results, steps, alpha=0.05)` returns 95% prediction intervals from statsmodels. The 80% CI can be obtained with `alpha=0.20`. Both are needed for `forecasts_ensemble.parquet`.

### Pattern 4: Prophet Retraining on USD Series

The existing `fit_prophet_segment` reads from a long-format `df` and filters by segment. For Phase 9, the input source changes from the processed macro proxy DataFrame to the market anchors DataFrame.

```python
# Prepare market_anchors data in Prophet ds/y format
seg_anchors = (
    anchors[anchors["segment"] == segment]
    .sort_values("estimate_year")
    [["estimate_year", "median_real_2020"]]
    .rename(columns={"estimate_year": "ds", "median_real_2020": "y"})
)
seg_anchors["ds"] = pd.to_datetime(seg_anchors["ds"].astype(str) + "-01-01")

# Fit — same Prophet configuration, 2022 changepoint preserved
model = Prophet(
    changepoints=["2022-01-01"],
    changepoint_prior_scale=0.1,
    yearly_seasonality=False,
    weekly_seasonality=False,
    daily_seasonality=False,
)
model.fit(seg_anchors)
```

The existing `fit_prophet_segment` function filters from a long DataFrame — it will need to be either refactored to accept the anchors DataFrame directly, or a new `fit_prophet_from_anchors` function is added. Both approaches are acceptable; keep the existing function for backward compatibility in tests.

### Pattern 5: LightGBM Feature Matrix Update

The existing LightGBM in `gradient_boost.py` uses `FEATURE_COLS = ["residual_lag1", "residual_lag2", "year_norm"]` — pure residual-lag features. For Phase 9, macro indicators are added as X variables alongside the residual lags.

```python
# Updated feature matrix: residual lags + macro indicator values
FEATURE_COLS = [
    "residual_lag1",
    "residual_lag2",
    "year_norm",
    "rd_pct_gdp",           # World Bank GB.XPD.RSDV.GD.ZS
    "ict_service_exports",  # World Bank BX.GSR.CCIS.CD
    "patent_applications",  # World Bank IP.PAT.RESD
    # (include only indicators with sufficient coverage 2017-2025)
]
```

**Indicator selection (Claude's discretion):** With N=9 training observations and multiple features, overfitting risk is high. Apply strict feature selection: keep only indicators with <20% missing values in the 2017-2025 window and VIF < 5 to control multicollinearity. The existing `assess_stationarity` utility can be used to check indicator stationarity before inclusion. Prefer 3-4 macro indicators maximum given the 9-obs constraint.

### Pattern 6: Multiplier Deletion — Exact Code Locations

Based on direct codebase inspection, these are the precise deletion targets:

**`src/dashboard/app.py` lines 48-110 (delete entire block):**
```python
# DELETE: lines 53-109
_vc = AI_CONFIG["value_chain"]          # line 53
_anchor_year = ...                       # line 54
...                                      # lines 55-109
VALUE_CHAIN_MULTIPLIERS: dict = {}       # line 71
VALUE_CHAIN_DERIVATION: dict = {}        # line 98
# Also delete: usd_* column attachment loop (lines 82-95)
```

After deletion, `FORECASTS_DF` is used directly with `point_estimate_real_2020` as the USD column. The minimal pass-through: add `usd_point` as an alias column set equal to `point_estimate_real_2020`, so existing dashboard tabs that reference `usd_point` don't crash before Phase 11 refactors them:
```python
# Minimal pass-through — Phase 11 removes this
FORECASTS_DF["usd_point"] = FORECASTS_DF["point_estimate_real_2020"]
FORECASTS_DF["usd_ci80_lower"] = FORECASTS_DF["ci80_lower"]
FORECASTS_DF["usd_ci80_upper"] = FORECASTS_DF["ci80_upper"]
FORECASTS_DF["usd_ci95_lower"] = FORECASTS_DF["ci95_lower"]
FORECASTS_DF["usd_ci95_upper"] = FORECASTS_DF["ci95_upper"]
```

**`src/reports/data_context.py` lines 80-118 (delete multiplier computation):**
The `value_chain_multipliers` dict and `usd_*` column attachment loop (identical pattern to app.py) must be deleted. Replace with the same alias pass-through until Phase 11.

**`src/dashboard/tabs/overview.py` imports (modify):**
```python
# DELETE these two imports:
from src.dashboard.app import (
    ...
    VALUE_CHAIN_MULTIPLIERS,   # DELETE
    VALUE_CHAIN_DERIVATION,    # DELETE
    ...
)
```
The `_build_expert_methodology_card` function references both — it must be simplified to remove the multiplier derivation table. Keep the RMSE section; replace the multiplier derivation with a note that the model now outputs USD directly.

### Pattern 7: Contract Test for USD Billions Output

This is required per locked decision. The test asserts that `point_estimate_real_2020` in `forecasts_ensemble.parquet` contains values in USD billions range, not dimensionless index units.

```python
# tests/test_contract_usd_billions.py (new test file)
def test_point_estimate_is_usd_billions():
    """
    Contract test: point_estimate_real_2020 must be USD billions, not PCA index units.
    PCA scores are dimensionless, typically in range [-5, 5].
    USD billions for AI market segments (2017-2025) are in range [10, 500].
    """
    df = pd.read_parquet(DATA_PROCESSED / "forecasts_ensemble.parquet")
    # All point estimates must be positive (USD is non-negative)
    assert (df["point_estimate_real_2020"] >= 0).all(), \
        "Negative point estimates — likely still PCA index units"
    # All point estimates must be > 1.0 (even smallest AI segment in 2017 > $1B)
    assert (df["point_estimate_real_2020"] > 1.0).all(), \
        "Point estimates below $1B — likely PCA index units (bounded near 0)"
    # For historical years (2017-2025), total should be plausible AI market range
    hist = df[(df["year"] >= 2017) & (df["year"] <= 2025) & (~df["is_forecast"])]
    total_by_year = hist.groupby("year")["point_estimate_real_2020"].sum()
    assert (total_by_year > 50).all(), \
        "Total < $50B in any historical year — too low for AI market"
    assert (total_by_year < 2000).all(), \
        "Total > $2T in any historical year — too high, check units"
```

### Pattern 8: Value Chain Taxonomy in ai.yaml

The 14 `edgar_companies` in `ai.yaml` already have `value_chain_layer` assigned (verified by inspection). Phase 9's taxonomy work is:
1. Add a formal `value_chain_layer_taxonomy` section that documents the 1:1 mapping
2. Comment out the legacy `value_chain` multiplier section (archive, not delete)
3. Confirm every company has exactly one layer assigned (no null/missing)

```yaml
# config/industries/ai.yaml — ADD this section (Plan 09-01)
value_chain_layer_taxonomy:
  locked_date: "2026-03-24"
  rationale: >
    One-to-one mapping between value chain layers and market segments prevents
    double-counting in Phase 10 attribution. Every company is assigned to exactly
    one primary layer. The primary layer determines which segment's market size
    that company's AI revenue contributes to.
  layers:
    - layer_id: chip
      maps_to_segment: ai_hardware
      description: "GPU, CPU, AI accelerator manufacturers (NVIDIA, AMD, Intel, TSMC)"
    - layer_id: cloud
      maps_to_segment: ai_infrastructure
      description: "Cloud platform AI infrastructure providers (Microsoft/Azure, Alphabet/GCP, Amazon/AWS, Oracle)"
    - layer_id: application
      maps_to_segment: ai_software
      description: "AI software, platform, and SaaS companies (Salesforce, ServiceNow, Palantir, C3.ai)"
    - layer_id: end_market
      maps_to_segment: ai_adoption
      description: "Companies using AI primarily within non-AI products (Meta, IBM, Accenture)"
  multi_layer_policy: >
    Companies that span multiple layers (e.g., Microsoft sells software AND cloud infrastructure)
    are assigned to the layer where the largest share of their AI-specific revenue originates.
    For bundled-disclosure companies, assignment follows the primary_ai_segment annotation in
    edgar_companies. Secondary layer participation is noted in company notes but does not affect
    the segment attribution in Phase 10.

# LEGACY — archived, not deleted
# value_chain section below is kept as documentation of the v1.0 multiplier approach.
# It is no longer read by any pipeline code after Phase 9.
# value_chain:
#   anchor_year: 2023
#   anchor_value_usd_billions: 200
#   ...
```

### Pattern 9: CAGR Verification

MODL-05 requires forecasts in 25-40% CAGR range. This needs a verification step after retraining:

```python
# Verification calculation — run after forecasts_ensemble.parquet is written
def verify_cagr_range(df: pd.DataFrame, segments: list[str]) -> dict:
    """
    Verify per-segment and total CAGR is in 25-40% range (MODL-05).
    Returns dict of {segment: cagr_pct} for reporting.
    """
    results = {}
    for seg in segments:
        seg_df = df[df["segment"] == seg].sort_values("year")
        val_2025 = seg_df[seg_df["year"] == 2025]["point_estimate_real_2020"]
        val_2030 = seg_df[seg_df["year"] == 2030]["point_estimate_real_2020"]
        if len(val_2025) > 0 and len(val_2030) > 0:
            cagr = ((val_2030.iloc[0] / val_2025.iloc[0]) ** (1/5) - 1) * 100
            results[seg] = cagr
    return results
# If CAGR outside 25-40%: document rationale comparing to consensus sources in ai.yaml
```

### Recommended Project Structure Changes

```
src/
├── processing/
│   └── features.py        # MODIFY: delete build_pca_composite; rebuild build_indicator_matrix
│                          #         as flat feature builder (same signature, no PCA)
├── models/
│   ├── statistical/
│   │   ├── arima.py       # MODIFY: retrain on USD series (structural changes minimal)
│   │   └── prophet_model.py  # MODIFY: retrain on USD anchors (new data input path)
│   └── ml/
│       └── gradient_boost.py  # MODIFY: updated feature matrix (add macro indicators)
├── inference/
│   └── forecast.py        # MODIFY: remove usd_* column generation (these become direct)
├── dashboard/
│   ├── app.py             # MODIFY: delete VALUE_CHAIN_MULTIPLIERS block (lines 53-109);
│   │                      #         add minimal alias pass-through for usd_* columns
│   └── tabs/
│       └── overview.py    # MODIFY: remove VALUE_CHAIN_MULTIPLIERS/DERIVATION imports
│                          #         and simplify expert methodology card
├── reports/
│   └── data_context.py    # MODIFY: delete multiplier computation (lines 80-118);
│                          #         add minimal alias pass-through
config/
└── industries/
    └── ai.yaml            # MODIFY: add value_chain_layer_taxonomy section;
                           #         comment out legacy value_chain section
tests/
├── test_features.py       # MODIFY: delete TestPcaComposite class (function removed)
└── test_contract_usd_billions.py  # NEW: contract test for USD billions output
```

### Anti-Patterns to Avoid

- **Preserving PCA code "for comparison":** The locked decision is explicit — no Expert-mode comparison. Keeping dead code adds confusion and routing error risk (Pitfall 9 in PITFALLS.md).
- **Adding a conversion factor to bridge old/new units:** Do not add `multiplier=1.0` as a stub. Delete the block; the pass-through alias approach is temporary and explicitly scoped to Phase 9 only.
- **Fitting LightGBM on the full macro indicator set without selection:** With N=9 observations, using all 8 World Bank indicators plus OECD indicators will severely overfit. Select 3-4 indicators maximum with explicit justification.
- **Forgetting that `data_context.py` has an identical copy of the multiplier logic:** Both `app.py` AND `data_context.py` compute value_chain_multipliers independently. Both must be cleaned. Missing `data_context.py` will cause the PDF report generator to crash or produce wrong numbers.
- **Training ARIMA/Prophet on the interpolated rows from market_anchors:** Rows where `estimated_flag=True` and `n_sources=0` are synthetic interpolation fill — they should not be used as training observations. Filter to `estimated_flag=False` OR `n_sources > 0` rows for model training.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| AICc order selection for short series | Custom grid search | pmdarima `auto_arima(information_criterion="aicc")` | Already implemented in `select_arima_order()`; AICc handles N<30 correctly |
| Temporal cross-validation | Custom fold loop | `temporal_cv_generic` from `regression.py` + `TimeSeriesSplit` | Already implemented; prevents fold-boundary data leakage |
| Parquet schema validation | Manual column type checks | pandera `DataFrameSchema` | Already implemented in `validate.py` |
| USD/PCA unit detection | Heuristic range checks | The contract test pattern above | Explicit and testable, not heuristic |

---

## Common Pitfalls

### Pitfall 1: Training on Interpolated Anchor Rows
**What goes wrong:** `market_anchors_ai.parquet` has rows where `n_sources=0` and `estimated_flag=True` — these were filled by linear interpolation in Plan 08-04 for years with no real analyst data. Training ARIMA/Prophet on these rows treats synthetic fill as real observations. The model memorizes the interpolation line and produces mechanically smooth forecasts that happen to fall in the CAGR range but have no empirical basis.
**How to avoid:** Filter anchors to `n_sources > 0` or `estimated_flag == False` before creating the training Y series. Log a warning if fewer than 5 observations remain after filtering for any segment.
**Warning signs:** All four segments produce near-identical CAGR values; residuals are suspiciously small (the model fits the linear fill perfectly).

### Pitfall 2: Stale Multiplier References Surviving in data_context.py
**What goes wrong:** app.py multiplier block is deleted and dashboard doesn't crash. But the PDF report generator (`data_context.py`) still has the old multiplier computation. A subsequent report generation silently produces wrong numbers (0x or 1x the actual USD values depending on what the stale computation returns when `value_chain` config is absent).
**How to avoid:** Search for ALL imports of `VALUE_CHAIN_MULTIPLIERS`, `value_chain_multipliers`, `_vc`, `_anchor_year`, `_segment_shares` across the entire codebase. The grep pattern `value_chain_mult` should return zero results after Phase 9.
**Warning signs:** Dashboard renders correctly but `scripts/generate_report.py` produces numbers that differ by orders of magnitude from the dashboard.

### Pitfall 3: model_version Flag Not Implemented Before Code Changes
**What goes wrong:** The new USD model is written but there is no way to toggle between old and new at the pipeline level. During development, the researcher runs the pipeline and gets the v1.1 output but cannot easily verify that the v1.0 code path is truly inactive. A subtle import or config issue causes the old path to silently run.
**How to avoid:** Add `model_version: "v1.1_real_data"` to ai.yaml or the pipeline config at the start of Plan 09-02, before touching any model code. The assertion `assert config["model_version"] == "v1.1_real_data"` at the top of the ARIMA training script provides a hard gate.

### Pitfall 4: CAGR Out of Range Due to Unit Mismatch
**What goes wrong:** After retraining, the 2030 forecast for `ai_hardware` is 0.003 USD billions — a nonsensical number. The CAGR is -80% instead of +30%. Investigation reveals the model was trained on `p25_real_2020` (the interquartile lower bound) instead of `median_real_2020`, or the series was divided by 1000 (USD millions instead of billions) somewhere in the pipeline.
**How to avoid:** Verify the Y series values before training: print the mean and range of `median_real_2020` per segment. Expected ranges: ai_hardware ~$70-150B, ai_infrastructure ~$50-130B, ai_software ~$50-120B, ai_adoption ~$20-60B. Any segment with values < 1.0 or > 500.0 for 2017-2025 historical period indicates a unit error.

### Pitfall 5: LightGBM Residuals Computed Against Wrong Baseline
**What goes wrong:** ARIMA and Prophet are retrained on USD; their predictions are in USD. LightGBM is trained to correct residuals. But if `run_arima_cv()` or `run_prophet_cv()` returns RMSE in the old index units (because cached residuals from the previous run are being used), the LightGBM feature matrix will contain stale lag features in the wrong units.
**How to avoid:** After retraining ARIMA and Prophet, regenerate `residuals_statistical.parquet` from scratch. Do not reuse cached residuals from the v1.0 PCA run. Assert that residual values are in the expected USD billions range (abs(residual) < 50 for any segment/year) before fitting LightGBM.

### Pitfall 6: overview.py Crash After Multiplier Import Deletion
**What goes wrong:** `VALUE_CHAIN_MULTIPLIERS` and `VALUE_CHAIN_DERIVATION` are imported in `overview.py`. Deleting these from `app.py` without simultaneously updating `overview.py` causes an `ImportError` that crashes the entire dashboard on startup.
**How to avoid:** The deletion of `app.py` multiplier block and the update to `overview.py` imports must be done in the same commit. Run `pytest tests/test_dashboard.py` immediately after to confirm no import errors.

---

## Code Examples

### Example 1: Loading Market Anchors as Training Y
```python
# Source: market_anchors.py (Phase 8 output) + locked decision in CONTEXT.md
import pandas as pd
from config.settings import DATA_PROCESSED

anchors = pd.read_parquet(DATA_PROCESSED / "market_anchors_ai.parquet")

# Filter to real observations only (exclude interpolated fill rows)
real_anchors = anchors[anchors["n_sources"] > 0].copy()

# Build per-segment training series (Y variable)
def get_segment_y_series(segment: str) -> pd.Series:
    seg = (
        real_anchors[real_anchors["segment"] == segment]
        .sort_values("estimate_year")
        .set_index("estimate_year")["median_real_2020"]
    )
    return seg  # pd.Series indexed by year (int), values in USD billions
```

### Example 2: Two-Layer Uncertainty Band
```python
# Source: locked decision in CONTEXT.md — two-layer uncertainty
def get_source_disagreement_band(segment: str) -> tuple[pd.Series, pd.Series]:
    """
    Layer 1 uncertainty: source disagreement from analyst estimate spread.
    Returns (lower_band, upper_band) as pd.Series indexed by year.
    """
    seg = (
        real_anchors[real_anchors["segment"] == segment]
        .sort_values("estimate_year")
        .set_index("estimate_year")
    )
    return seg["p25_real_2020"], seg["p75_real_2020"]
```

### Example 3: Minimal Dashboard Pass-Through
```python
# src/dashboard/app.py — after multiplier block deletion
# Minimal pass-through so existing tabs render without crashing
# Phase 11 removes these alias columns and refactors all tabs to use
# point_estimate_real_2020 directly.
FORECASTS_DF["usd_point"] = FORECASTS_DF["point_estimate_real_2020"]
FORECASTS_DF["usd_ci80_lower"] = FORECASTS_DF["ci80_lower"]
FORECASTS_DF["usd_ci80_upper"] = FORECASTS_DF["ci80_upper"]
FORECASTS_DF["usd_ci95_lower"] = FORECASTS_DF["ci95_lower"]
FORECASTS_DF["usd_ci95_upper"] = FORECASTS_DF["ci95_upper"]
```

### Example 4: Rebuilt build_indicator_matrix (Flat Feature Builder)
```python
# src/processing/features.py — rebuilt function (same signature, no PCA)
def build_indicator_matrix(
    df: pd.DataFrame,
    indicators: list[str],
    segment: str | None = None,
) -> tuple[np.ndarray, pd.Index]:
    """
    Build flat macro indicator matrix from long-format processed data.

    Returns aligned indicator values as X variables for ARIMA exogenous
    regressors and LightGBM feature matrix. No PCA reduction applied.
    Indicators are raw standardized values in value_real_2020 units.
    """
    if segment is not None:
        df = df[df["industry_segment"] == segment]

    wide = df.pivot_table(
        index="year",
        columns="indicator",
        values="value_real_2020",
        aggfunc="sum",
    )

    available = [ind for ind in indicators if ind in wide.columns]
    wide = wide[available]
    wide = wide.ffill().bfill()

    return wide.values, wide.index
    # NOTE: build_pca_composite is deleted — callers that referenced it
    # should be updated to use the raw indicator matrix directly.
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PCA composite index as Y variable | Real USD anchor estimates from analyst corpus as Y variable | Phase 9 | Forecasts are interpretable as market size; SHAP drivers explain real economic causation |
| Value chain multiplier to convert index to USD | point_estimate_real_2020 IS USD billions natively | Phase 9 | Eliminates multiplier calibration debt; eliminates numeric-correctness risk |
| usd_point column derived from multiplier | usd_point = alias for point_estimate_real_2020 (Phase 9) → removed entirely (Phase 11) | Phase 9 / Phase 11 | Two-phase transition preserves dashboard stability |
| LightGBM features: residual lags only | LightGBM features: residual lags + 3-4 macro indicators | Phase 9 | SHAP now attributes growth to R&D spend and ICT exports, not just lag patterns |

**Deprecated/outdated:**
- `build_pca_composite`: Deleted in Phase 9. Not preserved anywhere.
- `VALUE_CHAIN_MULTIPLIERS` / `VALUE_CHAIN_DERIVATION`: Deleted from all three files in Phase 9.
- `value_chain` section of `ai.yaml`: Commented out as legacy documentation; pipeline no longer reads it.

---

## Open Questions

1. **Source disagreement band encoding in forecasts_ensemble.parquet**
   - What we know: Two-layer uncertainty is a locked requirement; Layer 1 = source disagreement (p25/p75 from anchors), Layer 2 = model CIs
   - What's unclear: Whether the `ci80_lower/upper` columns should encode the source disagreement band OR whether a new column (`source_band_lower/upper`) should be added to the Parquet schema
   - Recommendation: Keep ci80_lower/upper for model prediction intervals; add `anchor_p25_real_2020` and `anchor_p75_real_2020` as additional columns populated only for historical years (is_forecast=False). The dashboard can display these as a separate "source spread" band.

2. **Handling macro indicators with gaps in 2017-2025**
   - What we know: Market anchors cover 2017-2025; World Bank macro indicators may have different coverage windows
   - What's unclear: Which of the 8 World Bank indicators have complete 2017-2025 coverage for the economy aggregates needed
   - Recommendation: In Plan 09-03, print coverage statistics for each indicator in the 2017-2025 window before selecting the feature set. Require >80% non-null coverage for any indicator to be included as an exogenous feature.

3. **ARIMA exogenous regressors with 9 training observations**
   - What we know: statsmodels ARIMA supports exogenous (X) regressors via `exog` parameter; the existing `fit_arima_segment` does not pass exogenous features
   - What's unclear: Whether adding exogenous features to ARIMA is net-positive with only 9 observations (risk of overfitting a small sample)
   - Recommendation: Start with ARIMA without exogenous features (univariate). Add exogenous features only if the univariate CAGR falls outside 25-40% range and exogenous features bring it within range. Prophet `add_regressor()` is a lower-risk path for incorporating macro indicators.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | pytest.ini or pyproject.toml (existing project config) |
| Quick run command | `pytest tests/test_features.py tests/test_models.py tests/test_forecast_output.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODL-01 | ARIMA/Prophet/LightGBM produce USD billions output | integration | `pytest tests/test_contract_usd_billions.py -x` | ❌ Wave 0 |
| MODL-01 | build_indicator_matrix returns flat feature matrix, no PCA output | unit | `pytest tests/test_features.py::TestBuildIndicatorMatrix -x` | ✅ |
| MODL-01 | ARIMA retrained: forecast values > 0, not index units | unit | `pytest tests/test_models.py -x -k "arima"` | ✅ (needs update) |
| MODL-04 | All edgar_companies in ai.yaml have value_chain_layer assigned | unit | `pytest tests/test_config.py -x -k "value_chain_layer"` | ❌ Wave 0 |
| MODL-04 | value_chain_layer_taxonomy section exists in ai.yaml | unit | `pytest tests/test_config.py -x -k "taxonomy"` | ❌ Wave 0 |
| MODL-05 | CAGR 2025-2030 in 25-40% range per segment | integration | `pytest tests/test_contract_usd_billions.py::test_cagr_range -x` | ❌ Wave 0 |
| MODL-05 | forecasts_ensemble.parquet has no negative point_estimate_real_2020 | integration | `pytest tests/test_contract_usd_billions.py::test_point_estimate_is_usd_billions -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_features.py tests/test_models.py tests/test_forecast_output.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_contract_usd_billions.py` — covers MODL-01 (USD range assertion), MODL-05 (CAGR range assertion)
- [ ] `tests/test_config.py` additions — `test_value_chain_layer_taxonomy_exists`, `test_all_edgar_companies_have_layer` — covers MODL-04
- [ ] Update `tests/test_features.py` — delete `TestPcaComposite` class (build_pca_composite is removed); update `TestBuildIndicatorMatrix` docstring to reflect flat feature builder intent

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `src/processing/features.py`, `src/models/statistical/arima.py`, `src/models/statistical/prophet_model.py`, `src/models/ml/gradient_boost.py`, `src/models/ensemble.py`, `src/inference/forecast.py`, `src/dashboard/app.py`, `src/dashboard/tabs/overview.py`, `src/reports/data_context.py`, `config/industries/ai.yaml` — inspected 2026-03-24
- `.planning/research/STACK.md` — verified stack, package versions, compatibility matrix
- `.planning/research/ARCHITECTURE.md` — component modify/preserve table, data contract change documentation
- `.planning/research/PITFALLS.md` — Pitfall 2 (broken pipeline algebra), Pitfall 9 (stale PCA code), Pitfall 10 (data leakage)
- `.planning/phases/09-ground-up-model-rework-and-value-chain-design/09-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- `.planning/research/SUMMARY.md` — phase ordering rationale, research flags per phase
- `.planning/REQUIREMENTS.md` — MODL-01, MODL-04, MODL-05 acceptance criteria
- `tests/test_features.py`, `tests/test_forecast_output.py` — existing test coverage baseline

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project lock file; no new dependencies required
- Architecture patterns: HIGH — based on direct inspection of all files to be modified; exact line numbers provided
- Pitfalls: HIGH — confirmed against existing code; specific import and variable names identified
- Taxonomy/config: HIGH — ai.yaml inspected directly; all 14 edgar_companies confirmed to have value_chain_layer

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (30 days; stack is stable)
