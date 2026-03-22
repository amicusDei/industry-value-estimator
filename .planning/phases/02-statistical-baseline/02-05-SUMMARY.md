---
phase: 02-statistical-baseline
plan: 05
subsystem: statistical-pipeline
tags: [arima, prophet, residuals, parquet, gap-closure]
dependency_graph:
  requires: [02-03]
  provides: [data/processed/residuals_statistical.parquet]
  affects: [03-ml-ensemble]
tech_stack:
  added: []
  patterns:
    - sys.path injection for script-as-entrypoint pattern
    - synthetic data generation with structural break at 2022
    - ARIMA vs Prophet CV comparison → winner residual extraction
key_files:
  created:
    - scripts/run_statistical_pipeline.py
    - data/processed/residuals_statistical.parquet
  modified: []
decisions:
  - sys.path.insert(0, project_root) in script header ensures both `python scripts/...` and `python -m scripts...` resolve src/config imports
  - All 4 segments selected Prophet as winner on synthetic data (upward trend with structural break at 2022 favors Prophet's changepoint flexibility)
  - Synthetic data uses per-segment growth rates and break amplitudes to give distinct RMSE profiles
metrics:
  duration: 8 min
  completed: "2026-03-22"
  tasks_completed: 1
  files_created: 2
---

# Phase 2 Plan 05: Statistical Pipeline Runner (Gap Closure) Summary

**One-liner:** Script-driven ARIMA/Prophet per-segment pipeline producing `residuals_statistical.parquet` for Phase 3 ML training, using synthetic data with a structural break at 2022.

## Objective

Close the single remaining Phase 2 verification gap: `data/processed/residuals_statistical.parquet` did not exist on disk. All model code was implemented and tested but no script ever invoked the pipeline end-to-end to persist the residuals file.

## What Was Built

### Task 1: Pipeline runner + Parquet artifact (commit `5a06279`)

**`scripts/run_statistical_pipeline.py`** (230 lines):
- Generates 15 years (2010-2024) of synthetic AI-segment data per segment with distinct growth rates and a structural break at 2022 (numpy seed=42)
- For each of the 4 AI segments runs the full ARIMA + Prophet comparison pipeline:
  - `select_arima_order` → AICc-based order selection
  - `run_arima_cv` + `run_prophet_cv` with 3 expanding-window folds
  - `compare_models` → winner by mean CV RMSE
  - Winner residuals extracted via `fit_arima_segment`/`get_arima_residuals` or `fit_prophet_segment`/`get_prophet_residuals`
- Calls `save_all_residuals` to write validated Parquet
- Prints a formatted summary table to stdout
- Has `__main__` guard; suppresses cmdstanpy/prophet logging

**`data/processed/residuals_statistical.parquet`**:
- Shape: 60 rows × 4 columns
- Schema: `year` (int64), `segment` (str), `residual` (float64), `model_type` (str)
- All 4 segments present: ai_hardware, ai_infrastructure, ai_software, ai_adoption
- No NaN values in year column
- model_type: all Prophet (Prophet won all 4 segments on this synthetic data)

## Verification Results

```
ALL CHECKS PASSED
Shape: (60, 4)
Columns: ['year', 'segment', 'residual', 'model_type']
Segments: ['ai_adoption', 'ai_hardware', 'ai_infrastructure', 'ai_software']
model_type unique: ['Prophet']
NaN in year: 0
```

Full test suite: **151 passed** (no regressions), 5 pre-existing warnings.

## CV Summary Table

```
========================================================================
Segment                  ARIMA RMSE  Prophet RMSE   Winner  Residuals
------------------------------------------------------------------------
ai_hardware                 11.4945        4.5701  Prophet         15
ai_infrastructure            8.4192        5.8031  Prophet         15
ai_software                 16.9257        9.8387  Prophet         15
ai_adoption                  3.3383        3.2028  Prophet         15
========================================================================
```

## Decisions Made

1. **sys.path injection at script top** — `Path(__file__).resolve().parent.parent` inserted into `sys.path[0]` so the script resolves `src.*` and `config.*` imports whether run as `python scripts/run_statistical_pipeline.py` or `python -m scripts.run_statistical_pipeline`. This is a standard pattern for project scripts that live outside the package.

2. **All segments returned Prophet as winner** — The synthetic data combines a strong upward trend with a discrete step-change at 2022. Prophet's explicit changepoint prior at 2022-01-01 gives it a structural advantage over ARIMA on this particular data pattern. On live API data the ARIMA/Prophet split will differ by segment.

3. **Structural break amplitude varies by segment** — `ai_software` gets the largest break amplitude (20×) to reflect GenAI's outsized software revenue impact; `ai_adoption` gets the smallest (6×) to reflect slower enterprise diffusion.

## Deviations from Plan

None — plan executed exactly as written.

The only implementation detail not stated explicitly in the plan was adding the `sys.path` injection to make `uv run python scripts/run_statistical_pipeline.py` work. This is a Rule 3 auto-fix (blocking import error for current task) and requires no architectural change.

## Self-Check: PASSED

- `scripts/run_statistical_pipeline.py` — FOUND (230 lines, > 80 minimum)
- `data/processed/residuals_statistical.parquet` — FOUND (3.4 KB, 60 rows)
- commit `5a06279` — FOUND
- All 151 tests pass
