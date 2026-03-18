---
phase: 02-statistical-baseline
plan: 03
subsystem: statistical-models
tags: [arima, prophet, time-series, temporal-cv, residuals, parquet, tdd]
dependency_graph:
  requires: [02-01, 02-02]
  provides: [src/models/statistical/arima.py, src/models/statistical/prophet_model.py, data/processed/residuals_statistical.parquet]
  affects: [phase-03-ml-training]
tech_stack:
  added: [pmdarima.auto_arima, prophet.Prophet, statsmodels.tsa.arima.model.ARIMA, pyarrow.parquet]
  patterns: [AICc-order-selection, explicit-changepoint, year-indexed-residuals, manual-prophet-cv, tdd-red-green]
key_files:
  created:
    - src/models/statistical/arima.py
    - src/models/statistical/prophet_model.py
    - tests/test_models.py
  modified: []
decisions:
  - "AICc (not AIC) used in pmdarima auto_arima for all ARIMA order selection — critical for N < 30 annual obs"
  - "max_p=2, max_q=2 parsimony constraint prevents overfitting on short AI segment series"
  - "changepoints=['2022-01-01'] explicitly anchors Prophet to GenAI surge — avoids spurious fragmentation from default 25-changepoint prior"
  - "Prophet CV uses manual TimeSeriesSplit refits, not Prophet's built-in cross_validation — consistent CV methodology across ARIMA and Prophet"
  - "Residuals year-aligned via original_index re-assignment — prevents Phase 3 feature matrix join misalignment (positional index drift)"
  - "pandas 3.0 StringDtype ('str') accepted as valid string dtype in test assertion alongside object and 'string'"
metrics:
  duration: 3 min
  completed: "2026-03-18"
  tasks_completed: 2
  files_created: 3
---

# Phase 2 Plan 3: ARIMA and Prophet Statistical Models Summary

**One-liner:** ARIMA(p,d,q) with AICc order selection (max_p=2, max_q=2) and Prophet with explicit 2022 changepoint fitted per AI segment, compared via temporal CV, residuals saved to year-indexed Parquet for Phase 3 ML.

---

## What Was Built

### Task 1: ARIMA Module (`src/models/statistical/arima.py`)

Five public functions:

- **`select_arima_order(series)`** — pmdarima `auto_arima` with `information_criterion="aicc"`, `max_p=2`, `max_q=2`, `seasonal=False`. Returns `(p, d, q)` tuple.
- **`fit_arima_segment(series, order)`** — statsmodels `ARIMA(series, order=order).fit()`. Returns `ARIMAResultsWrapper`.
- **`forecast_arima(results, steps, alpha=0.05)`** — `get_forecast(steps).summary_frame(alpha)`. Returns DataFrame with `mean`, `mean_ci_lower`, `mean_ci_upper`.
- **`get_arima_residuals(results, original_index)`** — Extracts `.resid` and re-aligns index to `original_index[:len(resid)]`. Prevents year offset drift between statistical and ML layers.
- **`run_arima_cv(series, order, n_splits=3)`** — Delegates to `temporal_cv_generic` with ARIMA fit/forecast callables. Returns list of fold dicts with `rmse` and `mape`.

### Task 2: Prophet Module (`src/models/statistical/prophet_model.py`)

Five public functions:

- **`fit_prophet_segment(df, segment)`** — Filters, aggregates, converts year to datetime, fits `Prophet(changepoints=["2022-01-01"], changepoint_prior_scale=0.1, yearly_seasonality=False, ...)`.
- **`forecast_prophet(model, periods)`** — `make_future_dataframe(periods, freq="YS")` + `predict()`. Returns full forecast DataFrame.
- **`get_prophet_residuals(model, df_segment)`** — In-sample residuals indexed by `ds.dt.year` as integers. Returns `pd.Series` with integer year index.
- **`run_prophet_cv(df, segment, n_splits=3)`** — Manual `TimeSeriesSplit` refits per fold. Handles 2022 changepoint presence check per fold. Returns fold dicts with `rmse` and `mape`.
- **`save_all_residuals(segment_residuals, output_path)`** — Concatenates all segments, enforces schema (`year` int, `segment` str, `residual` float, `model_type` str), validates no NaN years, writes snappy Parquet via pyarrow.

### Tests (`tests/test_models.py`)

11 tests across 3 classes:

- `TestARIMA` (5 tests): order selection, fitting, forecasting, year-aligned residuals, CV fold structure
- `TestProphet` (4 tests): fitting, forecast yhat column, integer-year residuals, CV fold structure
- `TestResiduals` (2 tests): Parquet schema validation, year alignment in output file

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `predicted_mean.values` fails when training data is numpy array**
- **Found during:** Task 1 GREEN (test_arima_cv)
- **Issue:** `temporal_cv_generic` passes `series.values` (numpy array) to `fit_fn`. When the ARIMA model is trained on a numpy array, `get_forecast().predicted_mean` returns a numpy array, not a pandas Series — calling `.values` on it fails with `AttributeError`.
- **Fix:** Changed `forecast_fn` to use `np.asarray(pm)` instead of `pm.values`, normalising both Series and ndarray to ndarray.
- **Files modified:** `src/models/statistical/arima.py`
- **Commit:** 7cd4f49

**2. [Rule 1 - Bug] Test dtype assertion too narrow for pandas 3.0 StringDtype**
- **Found during:** Task 2 GREEN (test_residuals_schema)
- **Issue:** pandas 3.0 returns `StringDtype(na_value=nan)` displayed as `"str"` for string columns read from Parquet, not `object` or `"string"`. The test assertion `== object or str(...) == "string"` failed.
- **Fix:** Updated assertion to `str(dtype) in ("object", "string", "str") or dtype == object`.
- **Files modified:** `tests/test_models.py`
- **Commit:** 59d0c84

---

## Test Results

```
142 passed, 5 warnings in 8.18s
```

Full suite: no regressions. All pre-existing tests pass.

---

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| AICc for ARIMA order selection | Standard correction for small N — AIC over-penalises with N < 30 annual obs |
| max_p=2, max_q=2 | Parsimony constraint prevents selecting ARIMA(2,1,2) over ARIMA(1,1,1) when both fit similarly |
| `changepoints=["2022-01-01"]` | Explicit GenAI anchor prevents default 25-changepoint prior from fragmenting the 2022 trend shift |
| Manual Prophet CV | Keeps CV methodology symmetric with ARIMA; Prophet's built-in cross_validation has minimum-horizon constraints incompatible with 15-year annual data |
| Year-aligned residuals | `original_index[:len(resid)]` re-assignment ensures Phase 3 ML joins residuals correctly by year, not by positional offset |
| pandas 3.0 StringDtype handling | Forward-compatible dtype check in test assertion |

---

## Phase 3 Contract

`data/processed/residuals_statistical.parquet` schema:

| Column | Type | Description |
|--------|------|-------------|
| year | int | Calendar year (e.g. 2010–2024) |
| segment | str | AI segment name (e.g. "ai_software") |
| residual | float | Statistical model residual (actual - fitted) |
| model_type | str | "ARIMA" or "Prophet" — winning model per segment |

Phase 3 ML training loads this file and uses it as the residual target for stacked/hybrid model training.

## Self-Check: PASSED

- arima.py: FOUND
- prophet_model.py: FOUND
- test_models.py: FOUND
- Commit 2e0e3e1 (RED tests): FOUND
- Commit 7cd4f49 (ARIMA impl): FOUND
- Commit 59d0c84 (Prophet impl): FOUND
