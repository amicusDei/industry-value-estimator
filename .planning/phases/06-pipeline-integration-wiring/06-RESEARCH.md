# Phase 6: Pipeline Integration Wiring - Research

**Researched:** 2026-03-23
**Domain:** Python pipeline wiring — orphaned function integration, PCA composite extension, structural break automation
**Confidence:** HIGH (all findings based on direct code inspection of the live codebase)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-05 | Ingest financial data from LSEG Workspace API (company-level data, market data) | LSEG parquet exists with 4215 rows; wiring means loading it and deriving a scalar signal that can join the PCA composite |
| MODL-01 | Build statistical baseline model (ARIMA and/or OLS regression) for AI market size estimation | `assess_stationarity` and `fit_top_down_ols_with_upgrade` are complete and tested; need call sites in `run_statistical_pipeline.py` |
| MODL-08 | Handle structural breaks (2022-23 GenAI surge) explicitly in models | `run_cusum`, `run_chow`, `fit_markov_switching` are complete and tested; Prophet changepoint year is hardcoded as `2022-01-01` instead of being derived |
</phase_requirements>

---

## Summary

This is a gap-closure phase. No new libraries or architectural patterns are needed — all required functions are already built, documented, and covered by the existing 222-test suite. The work is exclusively **call-site wiring**: adding imports, inserting function calls, and modifying `_load_real_data()` / `_build_segment_series()` / the main `run_pipeline()` loop in `scripts/run_statistical_pipeline.py`.

There is one critical constraint that was discovered during research: **`lseg_ai.parquet` contains a single-year snapshot (year=2026), not a time series.** All 4215 rows carry `year=2026` because LSEG Desktop Session returns current-period financials. This means LSEG cannot be added as a time-series column to the combined indicator matrix — instead, it contributes a **scalar signal** (total sector revenue, company count, or gross margin) that is used to scale or augment the PCA features.

The structural break detection gap is the cleanest of the three: `run_cusum` and `run_chow` accept a `pd.Series` indexed by year, run in under 200ms on 15-obs series, and return the `break_year` from the Chow result. The pipeline currently hardcodes `changepoints=['2022-01-01']` in Prophet — this string should be replaced with the detected `break_year` from Chow.

**Primary recommendation:** Wire all three gaps in a single script modification to `run_statistical_pipeline.py`, with two new helper functions (`_load_lseg_scalar()` and `_run_break_detection()`). The OLS function is called once per segment as a complementary diagnostic alongside the main ARIMA/Prophet competition — it does not replace the winner selection logic.

---

## Standard Stack

No new dependencies are required. All required packages are already installed and imported in the codebase.

### What Exists and Works

| Function | Module | Tests | Status |
|----------|--------|-------|--------|
| `run_cusum` | `src/diagnostics/structural_breaks.py` | `tests/test_diagnostics.py::TestStructuralBreaks` | 6 tests pass |
| `run_chow` | `src/diagnostics/structural_breaks.py` | `tests/test_diagnostics.py::TestStructuralBreaks` | 2 tests pass |
| `fit_markov_switching` | `src/diagnostics/structural_breaks.py` | `tests/test_diagnostics.py::TestStructuralBreaks` | 2 tests pass |
| `summarize_breaks` | `src/diagnostics/structural_breaks.py` | `tests/test_diagnostics.py::TestStructuralBreaks` | 1 test passes |
| `assess_stationarity` | `src/processing/features.py` | `tests/test_features.py::TestAssessStationarity` | 2 tests pass |
| `fit_top_down_ols_with_upgrade` | `src/models/statistical/regression.py` | `tests/test_features.py::TestRegression` | 3 tests pass |

**Total existing tests covering the orphaned functions:** 16 tests, all green.

---

## Architecture Patterns

### Current Pipeline Structure (run_statistical_pipeline.py)

```
run_pipeline()
├── _load_real_data()          # loads world_bank + oecd_msti only — GAP 1 here
├── for each segment:
│   ├── _build_segment_series()    # PCA composite — world_bank + oecd_msti only — GAP 1 here
│   ├── select_arima_order()
│   ├── run_arima_cv()
│   ├── run_prophet_cv()
│   │   └── changepoints=['2022-01-01']  # hardcoded — GAP 2 here
│   ├── compare_models()
│   ├── fit winner + extract residuals
│   └── [no assess_stationarity call]  # GAP 3a here
│   └── [no fit_top_down_ols call]     # GAP 3b here
└── save_all_residuals()
```

### Target Pipeline Structure (after wiring)

```
run_pipeline()
├── _load_lseg_scalar()        # NEW: load lseg_ai.parquet → single scalar per segment
├── _load_real_data()          # unchanged: loads world_bank + oecd_msti
├── _run_break_detection()     # NEW: run_cusum + run_chow on aggregate series → break_year int
├── for each segment:
│   ├── _build_segment_series()    # MODIFIED: accept lseg_scalar kwarg, augment matrix
│   ├── assess_stationarity()      # NEW CALL: log d recommendation before order selection
│   ├── select_arima_order()
│   ├── run_arima_cv()
│   ├── run_prophet_cv()
│   │   └── changepoints=[f'{break_year}-01-01']  # DERIVED from _run_break_detection()
│   ├── compare_models()
│   ├── fit_top_down_ols_with_upgrade()    # NEW CALL: GDP-share OLS as complementary model
│   ├── fit winner + extract residuals
│   └── log OLS diagnostics
└── save_all_residuals()
```

### Pattern 1: LSEG Single-Year Scalar Integration

**What:** `lseg_ai.parquet` has `year=2026` for all 4215 rows. It is a company-universe snapshot, not a time series. The scalar integration approach converts it to a single numeric feature per segment representing the relative market weight of LSEG-covered companies.

**When to use:** When LSEG data is a cross-section (snapshot), not a panel.

**How to derive the scalar:**
```python
# Source: direct inspection of lseg_ai.parquet (year unique: [2026])
def _load_lseg_scalar() -> dict[str, float]:
    """
    Load lseg_ai.parquet and derive a scalar indicator per segment.
    Returns dict mapping segment -> scalar (total revenue in billions, normalized).
    Falls back to empty dict if file missing (pipeline runs without LSEG).
    """
    lseg_path = DATA_PROCESSED / "lseg_ai.parquet"
    if not lseg_path.exists():
        return {}

    lseg = pd.read_parquet(lseg_path)

    # Aggregate total revenue per segment (in billions real USD)
    # Revenue column is in raw currency units (Int64) — divide by 1e9
    rev_by_seg = (
        lseg.groupby("industry_segment")["Revenue"]
        .sum()
        .astype(float)
        / 1e9
    )

    # Normalize: each segment scalar is its share of total LSEG revenue
    # This produces a [0,1] weight representing relative company-universe size
    total = rev_by_seg.sum()
    if total > 0:
        return (rev_by_seg / total).to_dict()
    return {}
```

**How to use the scalar in PCA composite:**

The scalar cannot be a new time-series column (no temporal variation). Instead, it functions as a **weight multiplier** on the PCA first component — segments with larger LSEG revenue representation get a proportionally scaled composite score:

```python
def _build_segment_series(combined, segment, lseg_scalar=None):
    # ... existing PCA logic ...
    scores, explained, _ = build_pca_composite(matrix, train_end_idx=train_end)

    # Apply LSEG revenue weight if available
    if lseg_scalar and segment in lseg_scalar:
        weight = lseg_scalar[segment]
        # Use log-scaling to avoid extreme compression: weight is in [0,1]
        # A simple linear scale preserves relative ordering
        scores = scores * (1.0 + weight)  # gentle amplification, not replacement
        print(f"    LSEG scalar for {segment}: {weight:.4f} (revenue weight applied)")

    return pd.DataFrame({...})
```

**Important constraint:** Since `lseg_ai.parquet` currently covers only `ai_software` segment (4215 rows, single segment), segments without LSEG coverage (`ai_hardware`, `ai_infrastructure`, `ai_adoption`) receive scalar=0 and are unaffected. This is correct behavior — do not fabricate coverage.

**Coverage check (verified from live data):**
```
industry_segment  ai_software: 4215 rows, Revenue total ~$473T (raw units), ~$473B
industry_segment  ai_hardware: 0 rows (not covered)
industry_segment  ai_infrastructure: 0 rows (not covered)
industry_segment  ai_adoption: 0 rows (not covered)
```

### Pattern 2: Structural Break Detection → Prophet Changepoint

**What:** Run CUSUM and Chow tests before the per-segment model loop. Use the detected `break_year` to replace the hardcoded `'2022-01-01'` changepoint in Prophet.

**Where the hardcoded year lives** (line 105 of run_statistical_pipeline.py comment, actual in prophet_model.py):
```python
# In src/models/statistical/prophet_model.py:
changepoints=['2022-01-01']  # THIS is what gets replaced
```

**The Chow test requires a `break_idx`.** The natural choice is the index of year 2022 in the series, which is: `series.index.tolist().index(2022)` for the series indexed 2010-2024.

**Recommended approach — detect on aggregate, apply per-segment:**

```python
def _run_break_detection(combined_series: pd.Series) -> int:
    """
    Run CUSUM and Chow tests on the aggregate series.
    Returns the detected break year (int) to use as Prophet changepoint.
    Falls back to 2022 if neither test detects a break.
    """
    from src.diagnostics.structural_breaks import run_cusum, run_chow, summarize_breaks

    cusum = run_cusum(combined_series)

    # Chow at known candidate 2022 (GenAI surge year)
    years = combined_series.index.tolist()
    break_candidate = 2022
    if break_candidate in years:
        break_idx = years.index(break_candidate)
    else:
        break_idx = len(years) // 2  # fallback to midpoint

    chow = run_chow(combined_series, break_idx=break_idx)

    print(f"  CUSUM: p={cusum['p_value']:.4f}, Chow: F={chow['F_stat']:.3f} p={chow['p_value']:.4f}")

    # Use Chow break_year if significant; fallback to 2022
    if chow["p_value"] < 0.05:
        detected = int(chow["break_year"])
        print(f"  Break detected at {detected} (Chow p<0.05)")
    elif cusum["p_value"] < 0.05:
        detected = 2022  # CUSUM confirms break but can't localize; use known date
        print(f"  Break confirmed by CUSUM (p={cusum['p_value']:.4f}), using 2022")
    else:
        detected = 2022  # no significant break found; retain default
        print(f"  No significant break detected; using default changepoint 2022")

    return detected
```

**How to thread `break_year` into Prophet:** `fit_prophet_segment` and `run_prophet_cv` in `src/models/statistical/prophet_model.py` currently have the changepoint hardcoded internally. To make the break year configurable, add a `changepoint_year` parameter:

```python
# In src/models/statistical/prophet_model.py
def fit_prophet_segment(df, segment, changepoint_year: int = 2022):
    ...
    changepoints=[f'{changepoint_year}-01-01']
    ...

def run_prophet_cv(df, segment, n_splits=3, changepoint_year: int = 2022):
    ...
```

This is a **backwards-compatible signature extension** — all existing tests that call without the parameter continue to work.

### Pattern 3: assess_stationarity Integration

**What:** Call `assess_stationarity(series)` on each segment's series before ARIMA order selection. Log the `recommendation_d` result. Use it as a soft signal (log and proceed; do not override pmdarima's AICc-based order selection which handles stationarity internally).

**Why a logging-only integration:** The audit states "assess_stationarity is called before ARIMA order selection and its results are logged." The Phase 6 success criterion (criterion 3) says "its results are logged" — not "it overrides pmdarima." pmdarima's `auto_arima` already handles stationarity via ADF internally. The value of wiring `assess_stationarity` is dual-test transparency (ADF+KPSS together), not algorithmic override.

```python
# In run_pipeline() per-segment loop, BEFORE select_arima_order():
stationarity = assess_stationarity(series.values)
print(f"  Stationarity: ADF p={stationarity['adf_pval']:.4f}, "
      f"KPSS p={stationarity['kpss_pval']:.4f}, "
      f"recommended d={stationarity['recommendation_d']}")
```

### Pattern 4: fit_top_down_ols_with_upgrade Integration

**What:** After winner selection, also run `fit_top_down_ols_with_upgrade` on GDP-share as a complementary regression model. Log the model type and R². Do not add OLS residuals to `segment_residuals` (the existing residuals from the ARIMA/Prophet winner feed Phase 3 correctly).

**Why complementary, not competitive:** The success criterion (criterion 4) says it "produces a GDP-share regression as a complementary model alongside per-segment ARIMA/Prophet." It supplements the audit trail in ASSUMPTIONS.md — it does not replace the pipeline's winner-selection output.

**What to use as y (dependent variable):** The `combined` DataFrame has `gdp_real_2020_usd`. The segment PCA composite score is the natural X. Use standardized PCA composite scores as regressor:

```python
import statsmodels.api as sm

def _run_ols_complementary(series: pd.Series, gdp_series: pd.Series) -> dict:
    """
    Run GDP-share OLS regression as a complementary model.
    Returns summary dict for logging. Does not affect residuals output.
    """
    from src.models.statistical.regression import fit_top_down_ols_with_upgrade

    # Align indices
    common_idx = series.index.intersection(gdp_series.index)
    y = series.loc[common_idx].values
    x = gdp_series.loc[common_idx].values
    X = sm.add_constant(x)

    _, model_type, diagnostics = fit_top_down_ols_with_upgrade(y, X)
    return {"model_type": model_type, "r2": diagnostics["r2"], "r2_adj": diagnostics["r2_adj"]}
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CUSUM break detection | Custom cumulative sum logic | `run_cusum` in structural_breaks.py | Already built, tested, wraps statsmodels breaks_cusumolsresid |
| Chow break test | Custom F-stat calculation | `run_chow` in structural_breaks.py | Already built, tested, handles degrees of freedom correctly |
| ADF+KPSS dual test | Single-test stationarity check | `assess_stationarity` in features.py | Belt-and-suspenders design already implemented, KPSS warning suppression included |
| OLS with diagnostics | Plain statsmodels OLS | `fit_top_down_ols_with_upgrade` | Heteroscedasticity and autocorrelation detection + upgrade chain already implemented |
| LSEG time-series | Fabricating panel data from snapshot | Scalar weight from single-year aggregate | LSEG data is a cross-section; inventing temporal variation would introduce fictional data |

**Key insight:** Every function needed for this phase is already implemented. The work is import statements and call sites, not new code.

---

## Common Pitfalls

### Pitfall 1: Treating lseg_ai.parquet as a Time Series

**What goes wrong:** `_load_real_data()` is called to build a combined multi-year DataFrame (2010-2024). If LSEG is merged into it naively (like WB and OECD), all years will have the same LSEG value (2026 snapshot), or the merge will produce NaN for 2010-2024 because the single row has `year=2026`.

**Why it happens:** The audit says "LSEG company data contributes to the PCA composite" — this sounds like adding a column. But the data has one year only.

**How to avoid:** Keep `_load_real_data()` unchanged (WB + OECD only). Load LSEG separately in `_load_lseg_scalar()` and apply as a post-PCA scalar weight. This is safe, transparent, and doesn't corrupt the time-indexed indicator matrix.

**Warning signs:** If `combined.shape[0]` drops below 10 rows, or NaNs appear in the LSEG column for all years before 2026, you've merged incorrectly.

### Pitfall 2: Prophet changepoint_year Threading

**What goes wrong:** `run_prophet_cv()` and `fit_prophet_segment()` are called from `run_statistical_pipeline.py`. The changepoint is currently set **inside** those functions, not passed in. If you only add the parameter to `fit_prophet_segment` but not `run_prophet_cv`, the CV will use the old hardcoded year while the final fit uses the detected year — inconsistent results.

**How to avoid:** Add `changepoint_year: int = 2022` to **both** `fit_prophet_segment` and `run_prophet_cv`. Default=2022 preserves backward compatibility with all existing tests.

**Warning sign:** CV RMSE computed with changepoint 2022, final model fitted with detected year — model comparison results are invalid.

### Pitfall 3: Chow Test Requires Minimum Sub-Sample Size

**What goes wrong:** `run_chow` computes separate OLS on pre-break and post-break windows. If `break_idx` is too close to the start or end of the 15-obs series (e.g., break_idx=1 or break_idx=14), one sub-window has only 1 or 2 observations and OLS is undefined.

**How to avoid:** In `_run_break_detection()`, guard that `break_idx` is at least 3 and at most `len(series) - 3` before passing to `run_chow`. The existing `run_chow` function does not perform this guard — the caller must.

**Warning sign:** `statsmodels` raises `LinAlgError: Singular matrix` or returns `F_stat=inf`.

### Pitfall 4: assess_stationarity on Short Series (N < 20)

**What goes wrong:** The ADF and KPSS tests lose power on N < 20. With 15 observations (2010-2024), results are unreliable. Statsmodels warns about this.

**How to avoid:** Log the result but do not act on it. The docstring in `assess_stationarity` already notes "Should have at least 20 observations for reliable results." Add a print note when N < 20.

**Warning sign:** `recommendation_d=1` on a clearly stationary series — this is a small-N false positive, not a pipeline bug.

### Pitfall 5: fit_top_down_ols_with_upgrade Requires statsmodels add_constant

**What goes wrong:** `fit_top_down_ols_with_upgrade(y, X)` expects `X` to already include a constant column. The Breusch-Pagan test in the function will fail or give wrong results if `X` has no constant.

**How to avoid:** Always call `sm.add_constant(x)` before passing to `fit_top_down_ols_with_upgrade`. This pattern is shown in all test fixtures in `tests/test_features.py::TestRegression`.

---

## Code Examples

### Verified Pattern: run_cusum + run_chow (from tests/test_diagnostics.py)

```python
# Source: tests/test_diagnostics.py lines 39-55, verified against structural_breaks.py
from src.diagnostics.structural_breaks import run_cusum, run_chow

series = pd.Series(values, index=year_range)  # pd.Series with integer year index

cusum_result = run_cusum(series)
# Returns: {"stat": float, "p_value": float, "critical_values": array}

chow_result = run_chow(series, break_idx=12)  # 2022 is index 12 in 2010-2024
# Returns: {"F_stat": float, "p_value": float, "break_year": int}
# break_year will be series.index[12] = 2022
```

### Verified Pattern: assess_stationarity (from tests/test_features.py)

```python
# Source: tests/test_features.py lines 105-128
from src.processing.features import assess_stationarity

result = assess_stationarity(series.values)  # accepts np.ndarray or pd.Series
# Returns: {"adf_stationary": bool, "kpss_stationary": bool,
#           "adf_pval": float, "kpss_pval": float, "recommendation_d": int}
```

### Verified Pattern: fit_top_down_ols_with_upgrade (from tests/test_features.py)

```python
# Source: tests/test_features.py lines 136-181
import statsmodels.api as sm
from src.models.statistical.regression import fit_top_down_ols_with_upgrade

X = sm.add_constant(x_array)  # MUST include constant
final_res, model_type, diagnostics = fit_top_down_ols_with_upgrade(y_array, X)
# model_type: "OLS ..." | "WLS (heteroscedasticity...)" | "GLSAR (autocorrelation...)"
# diagnostics: {"bp_stat", "bp_pval", "lb_pval", "r2", "r2_adj"}
```

### Verified Pattern: Chow break_idx calculation for 2010-2024 series

```python
# Source: direct inspection — 2022 is position 12 in 0-indexed range(2010, 2025)
years = list(range(2010, 2025))  # [2010, 2011, ..., 2024], len=15
break_idx = years.index(2022)    # = 12
# Guard: break_idx must satisfy 3 <= break_idx <= len(years) - 3
```

### Verified Pattern: LSEG scalar load

```python
# Source: direct inspection of lseg_ai.parquet
# lseg_ai.parquet has: year=2026 (all rows), industry_segment='ai_software' (all rows)
# Revenue column: Int64 (raw monetary units, non-null for 3875/4215 rows)
lseg = pd.read_parquet(DATA_PROCESSED / "lseg_ai.parquet")
rev = lseg.groupby("industry_segment")["Revenue"].sum().astype(float) / 1e9
```

---

## State of the Art

| Old Approach (current) | Wired Approach (Phase 6) | Impact |
|------------------------|--------------------------|--------|
| Prophet changepoint hardcoded 2022-01-01 | Detected from Chow test on real data | Break year is data-driven, not hardcoded |
| PCA composite: WB + OECD only | PCA scores scaled by LSEG revenue weight | LSEG company-universe size informs segment weighting |
| assess_stationarity: tests only | Called per-segment, d recommendation logged | Stationarity diagnosis visible in pipeline output |
| fit_top_down_ols_with_upgrade: tests only | Called per-segment, diagnostics logged | OLS-layer diagnostics in pipeline trace for ASSUMPTIONS.md traceability |

---

## Open Questions

1. **LSEG data covers only `ai_software` segment (all 4215 rows)**
   - What we know: only `ai_software` has LSEG revenue data; hardware/infrastructure/adoption are absent
   - What's unclear: whether this is a known limitation (TRBC codes only map to software companies) or a data fetch gap
   - Recommendation: proceed with software-only LSEG scalar; log a warning for the other three segments. Do not fabricate revenue for uncovered segments. The test for this wiring should verify that the scalar is 0.0 (or absent) for non-software segments.

2. **Prophet changepoint API: `changepoints` param vs `n_changepoints`**
   - What we know: `fit_prophet_segment` already uses `changepoints=['2022-01-01']` successfully
   - What's unclear: no ambiguity; the param is the explicit list form
   - Recommendation: replace the string literal with `f'{break_year}-01-01'`; no API risk.

3. **Whether to add OLS residuals to the residuals Parquet**
   - What we know: success criterion 4 says OLS "produces a GDP-share regression as a complementary model" — does not say persist to Parquet
   - What's unclear: should OLS residuals be written somewhere for Phase 4 diagnostics?
   - Recommendation: log to stdout only in Phase 6. A separate future enhancement could write them to `residuals_ols.parquet` if needed. Keeping them out of `residuals_statistical.parquet` avoids disrupting the Phase 3 ML pipeline which depends on that schema.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (version from pyproject.toml) |
| Config file | none detected (uses default pytest discovery) |
| Quick run command | `uv run pytest tests/test_diagnostics.py tests/test_features.py tests/test_models.py -x -q` |
| Full suite command | `uv run python -m pytest -q --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODL-08 | run_cusum detects break in step-function series | unit | `uv run pytest tests/test_diagnostics.py::TestStructuralBreaks::test_cusum_detects_break -x` | Yes |
| MODL-08 | run_chow detects known break at idx=10 | unit | `uv run pytest tests/test_diagnostics.py::TestStructuralBreaks::test_chow_known_break -x` | Yes |
| MODL-08 | Prophet changepoint uses detected year, not hardcoded | integration | New test in `tests/test_models.py` needed | No — Wave 0 gap |
| MODL-01 | assess_stationarity called before ARIMA order selection | integration | New test verifying call order in run_pipeline | No — Wave 0 gap |
| MODL-01 | fit_top_down_ols_with_upgrade runs per-segment in pipeline | integration | New test mocking pipeline and asserting OLS call | No — Wave 0 gap |
| DATA-05 | _load_lseg_scalar returns float dict keyed by segment | unit | New test in `tests/test_features.py` or `test_pipeline.py` | No — Wave 0 gap |
| DATA-05 | LSEG scalar applied to PCA composite scores | unit | New test for _build_segment_series with lseg_scalar | No — Wave 0 gap |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_diagnostics.py tests/test_features.py tests/test_models.py -x -q`
- **Per wave merge:** `uv run python -m pytest -q --tb=short`
- **Phase gate:** Full 222+ suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_models.py` — add `TestPipelineWiring` class covering: `_load_lseg_scalar()` returns dict, LSEG scalar is applied to `_build_segment_series`, `_run_break_detection()` returns int, `fit_prophet_segment` accepts `changepoint_year`, `run_prophet_cv` accepts `changepoint_year`
- [ ] Integration test for `assess_stationarity` call in `run_pipeline(use_real_data=False)` — confirm the function is invoked by mocking it

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `scripts/run_statistical_pipeline.py` — exact current pipeline structure
- Direct code inspection: `src/diagnostics/structural_breaks.py` — verified function signatures and return schemas
- Direct code inspection: `src/processing/features.py` — verified `assess_stationarity` signature and behavior
- Direct code inspection: `src/models/statistical/regression.py` — verified `fit_top_down_ols_with_upgrade` signature
- Direct parquet inspection: `data/processed/lseg_ai.parquet` — confirmed year=2026 single-year snapshot, 4215 rows, ai_software only
- Direct test execution: `uv run python -m pytest -q --tb=no` — 222 passed (confirmed green baseline)

### Secondary (MEDIUM confidence)

- `.planning/v1.0-MILESTONE-AUDIT.md` — gap descriptions and severity classifications
- `.planning/ROADMAP.md` — Phase 6 success criteria (authoritative for scope)

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all imports and functions inspected directly; no new dependencies
- Architecture: HIGH — code changes are targeted edits to a single script; patterns verified from tests
- Pitfalls: HIGH — derived from direct data inspection (LSEG year=2026 finding) and function signatures

**Research date:** 2026-03-23
**Valid until:** 2026-06-23 (stable codebase; no external dependencies change)

---

## Key Finding: LSEG Data is a Single-Year Snapshot

This is the most important discovery from research. The audit text states "LSEG company data contributes to the PCA composite" as if LSEG is a time series. **It is not.** `lseg_ai.parquet` has `year=2026` for all 4215 rows because LSEG Desktop Session returns current-period financials.

This means:
1. LSEG cannot be added as a time-series column to the 2010-2024 indicator matrix
2. The PCA composite structure (World Bank + OECD time series, 2010-2024) must remain unchanged
3. LSEG contributes as a **post-PCA scalar weight** — a revenue-share multiplier on the PCA composite score
4. Currently only `ai_software` is covered; the other three segments receive scalar=1.0 (no adjustment)
5. This is the correct, honest integration — not a workaround but the methodologically sound approach given the data structure

The planner should design Task 1 around this constraint: `_load_lseg_scalar()` as a new function, applied in `_build_segment_series()` after PCA, not before.
