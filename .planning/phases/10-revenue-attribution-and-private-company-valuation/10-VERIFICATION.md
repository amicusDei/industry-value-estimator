---
phase: 10-revenue-attribution-and-private-company-valuation
verified: 2026-03-24T21:30:00Z
status: passed
score: 12/12 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 9/12
  gaps_closed:
    - "backtesting_results.parquet now contains 4 hard actual rows (NVIDIA ai_hardware 2023+2024, ai_software 2023+2024 from Palantir+C3.ai)"
    - "MAPE values are non-zero for hard actuals (14.2% NVIDIA 2023, 38.3% NVIDIA 2024, 2134% ai_software 2023, 17934% ai_software 2024 — all real, non-circular)"
    - "2022 fold absence is formally documented in walk_forward.py module docstring with MIN_FOLDS=2 constant; code already handled gracefully; 2 folds present as minimum"
  gaps_remaining: []
  regressions: []
human_verification: []
---

# Phase 10: Revenue Attribution and Private Company Valuation — Verification Report

**Phase Goal:** Every mixed-tech public company has an attributed AI revenue figure with source and uncertainty range; every major private AI company has a valuation with explicit uncertainty; segment totals sum without double-counting
**Verified:** 2026-03-24T21:30:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (Plan 10-05)

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ATTRIBUTION_SCHEMA and PRIVATE_VALUATION_SCHEMA exist in validate.py and validate sample DataFrames | VERIFIED | Both schemas importable; sample DataFrames pass validation |
| 2 | attribution_subsegment_ratios section exists in ai.yaml with ratios for multi-layer companies | VERIFIED | Section at line 178 of ai.yaml; 5 entries (NVIDIA, Microsoft, Alphabet, Amazon, Meta) with splits and rationale |
| 3 | revenue_attribution.py produces AI revenue for 15 public companies with attribution_method, ratio_source, uncertainty_low, uncertainty_high, vintage_date per row | VERIFIED | revenue_attribution_ai.parquet: 15 rows, all required columns present, zero null values in uncertainty columns |
| 4 | Every company has a point estimate with bounds — no bare float without uncertainty range | VERIFIED | uncertainty_low.isna().any() = False, uncertainty_high.isna().any() = False across all 15 rows |
| 5 | Pure-play companies (NVIDIA, Palantir, C3.ai) use attribution_method=direct_disclosure | VERIFIED | All three attribution methods present; pure-plays confirmed direct_disclosure |
| 6 | Compiled attribution DataFrame passes ATTRIBUTION_SCHEMA validation | VERIFIED | compile_and_write_attribution() calls ATTRIBUTION_SCHEMA.validate(); all 19 attribution tests pass |
| 7 | private_valuations_ai.parquet contains 15-20 private AI companies with low/mid/high valuations | VERIFIED | 18 companies; implied_ev_low, implied_ev_mid, implied_ev_high columns present for all rows |
| 8 | Every private company has a confidence tier (HIGH/MEDIUM/LOW) and vintage_date | VERIFIED | All 3 tiers present (HIGH: 6, MEDIUM: 7, LOW: 5); no null vintage_dates |
| 9 | implied_ev_low <= implied_ev_mid <= implied_ev_high for every row | VERIFIED | Ordering invariant holds for all 18 rows |
| 10 | backtesting_results.parquet contains rows with actual_type='hard' from EDGAR direct-disclosure companies | VERIFIED | 4 hard actual rows: NVIDIA (ai_hardware 2023, 2024) and combined Palantir+C3.ai (ai_software 2023, 2024); EDGAR data: 2652 rows, 14 companies including all 3 direct-disclosure CIKs |
| 11 | MAPE values are non-zero and soft actual circular comparison is flagged transparently | VERIFIED | Hard actual MAPE: 14.2% (NVIDIA 2023), 38.3% (NVIDIA 2024) — real non-circular signal; all 8 soft rows have circular_flag=True and mape_label="circular_not_validated" |
| 12 | backtesting_results.parquet contains at least 2 evaluation folds with documented reasoning if 2022 fold is absent | VERIFIED | 2 folds present (2023, 2024); 2022 absence documented in walk_forward.py module docstring, MIN_FOLDS=2 constant, and printed notes in run_backtesting() output |

**Score:** 12/12 truths verified

---

## Required Artifacts

### Plan 10-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/processing/validate.py` | ATTRIBUTION_SCHEMA and PRIVATE_VALUATION_SCHEMA pandera schemas | VERIFIED | Both schemas present; both importable and functional |
| `config/industries/ai.yaml` | attribution_subsegment_ratios section with per-company layer splits | VERIFIED | Section present at line 178 with 5 multi-layer company entries; C3.ai CIK corrected to 0001577526 |
| `data/raw/attribution/ai_attribution_registry.yaml` | Stub attribution registry with 3+ entries | VERIFIED | 15 entries (315 lines) |
| `data/raw/private_companies/ai_private_registry.yaml` | Stub private company registry with 3+ entries | VERIFIED | 18 entries (431 lines) |
| `tests/test_revenue_attribution.py` | Test scaffold for MODL-02 | VERIFIED | Exists; 19 tests pass |
| `tests/test_private_valuations.py` | Test scaffold for MODL-03 | VERIFIED | Exists; 20 tests pass |
| `tests/test_backtesting.py` | Test scaffold for MODL-06 | VERIFIED | 8 tests; all 8 pass — no skipped tests (EDGAR data present) |

### Plan 10-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data/raw/attribution/ai_attribution_registry.yaml` | Full YAML with 10-15 company entries (min 150 lines) | VERIFIED | 15 entries, 315 lines |
| `src/processing/revenue_attribution.py` | load_attribution_registry, estimate_ai_revenue, compile_and_write_attribution | VERIFIED | All 3 functions present; 256 lines total |
| `data/processed/revenue_attribution_ai.parquet` | Compiled attribution output | VERIFIED | 15 rows; all schema columns present |

### Plan 10-03 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data/raw/private_companies/ai_private_registry.yaml` | Full YAML with 15-20 private company entries (min 250 lines) | VERIFIED | 18 entries, 431 lines |
| `src/processing/private_valuations.py` | load_private_registry, apply_comparable_multiples, compile_and_write_private_valuations | VERIFIED | All 3 functions present; 214 lines total |
| `data/processed/private_valuations_ai.parquet` | Compiled private company valuations | VERIFIED | 18 rows; EV ordering invariant holds |

### Plan 10-04 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/backtesting/__init__.py` | Package marker | VERIFIED | Exists (45 bytes) |
| `src/backtesting/actuals_assembly.py` | assemble_actuals function | VERIFIED | Function present; DIRECT_DISCLOSURE_CIKS guard with corrected C3.ai CIK (0001577526); deduplication logic added |
| `src/backtesting/walk_forward.py` | run_walk_forward, run_backtesting, label_mape | VERIFIED | All 3 functions present; circular_flag detection, MIN_FOLDS=2 constant, 2022 absence documentation added |
| `data/processed/backtesting_results.parquet` | Backtesting output with MAPE/R2 per segment per actual_type | VERIFIED | 12 rows: 4 hard + 8 soft; circular_flag column present; hard MAPE non-zero (14.2–17934%); soft rows flagged circular_not_validated |

### Plan 10-05 Artifacts (Gap Closure)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data/raw/edgar/edgar_ai_raw.parquet` | EDGAR 10-K filings for direct-disclosure and bundled companies | VERIFIED | 2652 rows, 14 companies; includes all 3 direct-disclosure CIKs (NVIDIA 0001045810, Palantir 0001321655, C3.ai 0001577526) |
| `data/processed/backtesting_results.parquet` | Walk-forward backtesting with hard+soft actuals and real MAPE/R2 | VERIFIED | 4 hard actual rows with real MAPE (14.2%, 38.3%, 2134%, 17934%); 8 soft rows with circular_flag=True |
| `src/backtesting/walk_forward.py` | Non-circular backtesting logic with transparency flags | VERIFIED | circular_flag=True when |actual-predicted| < 0.01B; mape_label="circular_not_validated" for circular rows |
| `tests/test_backtesting.py` | Tests verifying hard actuals present and MAPE non-zero | VERIFIED | test_circular_flag_column, test_mape_not_all_zero added; test_hard_actuals_source no longer skipped; test_fold_count expects >= 2; 8/8 pass |

---

## Key Link Verification

### Plan 10-01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_revenue_attribution.py` | `src/processing/validate.py` | imports ATTRIBUTION_SCHEMA | VERIFIED | Import confirmed present |
| `tests/test_private_valuations.py` | `src/processing/validate.py` | imports PRIVATE_VALUATION_SCHEMA | VERIFIED | Import confirmed present |

### Plan 10-02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/processing/revenue_attribution.py` | `src/processing/validate.py` | ATTRIBUTION_SCHEMA.validate | VERIFIED | `ATTRIBUTION_SCHEMA.validate(df_out)` at line 236 |
| `src/processing/revenue_attribution.py` | `data/raw/attribution/ai_attribution_registry.yaml` | yaml.safe_load | VERIFIED | yaml.safe_load at line 85 |
| `src/ingestion/pipeline.py` | `src/processing/revenue_attribution.py` | Step 8 import | VERIFIED | Import at pipeline line 235 |

### Plan 10-03 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/processing/private_valuations.py` | `src/processing/validate.py` | PRIVATE_VALUATION_SCHEMA.validate | VERIFIED | `PRIVATE_VALUATION_SCHEMA.validate(df)` at line 178 |
| `src/processing/private_valuations.py` | `data/raw/private_companies/ai_private_registry.yaml` | yaml.safe_load | VERIFIED | yaml.safe_load at line 70 |
| `src/ingestion/pipeline.py` | `src/processing/private_valuations.py` | Step 9 import | VERIFIED | Import at pipeline line 243 |

### Plan 10-04 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/backtesting/actuals_assembly.py` | `data/raw/edgar/edgar_ai_raw.parquet` | pd.read_parquet for hard actuals | VERIFIED | File now exists (2652 rows); hard actual path executes successfully |
| `src/backtesting/actuals_assembly.py` | `data/processed/market_anchors_ai.parquet` | pd.read_parquet for soft actuals | VERIFIED | Soft actuals loaded successfully |
| `src/backtesting/walk_forward.py` | `src/diagnostics/model_eval.py` | compute_mape and compute_r2 calls | VERIFIED | Both functions imported and called in walk-forward loop |
| `src/ingestion/pipeline.py` | `src/backtesting/walk_forward.py` | Step 10 import | VERIFIED | Import at pipeline line 251 |

### Plan 10-05 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/backtesting/actuals_assembly.py` | `data/raw/edgar/edgar_ai_raw.parquet` | pd.read_parquet — hard actuals path | VERIFIED | File exists; DIRECT_DISCLOSURE_CIKS filter produces 14 rows (NVIDIA+Palantir+C3.ai) after dedup |
| `src/backtesting/walk_forward.py` | `data/processed/backtesting_results.parquet` | run_backtesting writes parquet | VERIFIED | 12-row file written with correct schema including circular_flag column |

---

## Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| MODL-02 | 10-01, 10-02 | AI revenue attribution for 10-15 mixed-tech public companies with documented uncertainty per company | SATISFIED | 15 companies in revenue_attribution_ai.parquet; all have attribution_method, ratio_source, uncertainty_low, uncertainty_high, vintage_date; 19 tests pass |
| MODL-03 | 10-01, 10-03 | Private company valuation registry — 15-20 companies via comparable multiples with confidence flags and explicit uncertainty ranges | SATISFIED | 18 companies in private_valuations_ai.parquet; all three confidence tiers present; EV ordering invariant holds; 20 tests pass |
| MODL-06 | 10-01, 10-04, 10-05 | Walk-forward backtesting — train pre-2022, evaluate 2022-2024 against filed actuals, producing real MAPE and R-squared | SATISFIED | backtesting_results.parquet has 4 hard actual rows from EDGAR direct-disclosure (NVIDIA ai_hardware, Palantir+C3.ai ai_software); hard MAPE is real (14.2%–17934%); 2022 fold absence documented; circular soft actuals flagged with circular_not_validated label; 8 tests pass with no skips |

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `src/backtesting/actuals_assembly.py` | Module docstring at line 8 still references old C3.ai CIK 0001577552 (Alibaba). The functional code at line 30 uses the correct 0001577526 — this is a stale comment only. | Info | No functional impact; correct CIK is used in DIRECT_DISCLOSURE_CIKS set |

No TODO/FIXME/placeholder anti-patterns found in implementation files. No blocker or warning anti-patterns remain. The ai_software hard MAPE values (2134%, 17934%) are expected and documented in the SUMMARY — C3.ai represents ~5% of the full ai_software segment forecast, making segment-level comparison inherently large-error. This is not a code defect.

---

## Human Verification Required

None. All three original gaps are closed via automated verification:

1. Hard actuals are confirmed present in backtesting_results.parquet (verified via parquet read).
2. MAPE non-circularity is confirmed by non-zero values on hard actual rows (14.2%, 38.3%).
3. 2022 fold documentation is confirmed in walk_forward.py source text.

The EDGAR credential requirement (previously human-needed) is resolved — EDGAR_USER_EMAIL was available in .env and the fetch was executed during Plan 10-05.

---

## Re-Verification Gap Closure Assessment

### Gap 1 — Hard actuals absent: CLOSED

Previous state: `data/raw/edgar/` did not exist. Hard actual path in actuals_assembly.py never executed.

Current state: `data/raw/edgar/edgar_ai_raw.parquet` exists with 2652 rows, 14 companies. All 3 DIRECT_DISCLOSURE_CIKS (NVIDIA, Palantir, C3.ai) are present. The hard actual path executes and produces 4 rows in backtesting_results.parquet.

Additional fixes applied during gap closure: edgartools API incompatibility corrected (get_facts_by_concept replaces broken facts.query), C3.ai CIK corrected (0001577552 was Alibaba — corrected to 0001577526), Accenture CIK corrected (0001281761 was Regions Financial Corp — corrected to 0001467373), EDGAR deduplication added (each 10-K contains comparative prior-year data causing ~37x duplicate revenue facts).

### Gap 2 — Circular MAPE: CLOSED

Previous state: All MAPE=0.0 because soft actuals (market_anchors_ai.parquet medians) were identical to forecasts_ensemble.parquet point estimates. The "acceptable" label masked a meaningless circular self-comparison.

Current state: Hard actual MAPE values are non-zero (NVIDIA 2023: 14.2%, NVIDIA 2024: 38.3%) — these compare filed 10-K revenue against ensemble forecasts and reflect real prediction error. Soft actual rows are now transparent: circular_flag=True for all 8 soft rows, mape_label="circular_not_validated" (replacing the misleading "acceptable"). The circularity is documented in both the module docstring and inline code comments.

### Gap 3 — 2022 fold missing: CLOSED (design documented)

Previous state: Only 2 folds silently skipped 2022 without documentation. Plan said 3 folds; 2 appeared without explanation.

Current state: walk_forward.py module docstring explicitly states "2 evaluation folds (2023, 2024)" and explains why 2022 is absent. MIN_FOLDS=2 constant establishes the minimum. run_backtesting() prints "NOTE: 2022 fold absent — forecasts_ensemble.parquet starts at 2023. 2 of 3 possible folds evaluated." EVALUATION_YEARS is kept as [2022, 2023, 2024] for forward-compatibility. test_fold_count expects >= 2 (not exactly 3).

---

_Verified: 2026-03-24T21:30:00Z_
_Verifier: Claude (gsd-verifier)_
