# Phase 10: Revenue Attribution and Private Company Valuation — Research

**Researched:** 2026-03-24
**Domain:** AI revenue attribution, private company valuation via comparable multiples, walk-forward backtesting
**Confidence:** HIGH (all findings grounded in direct codebase inspection + prior project research files)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Attribution Methodology**
- Method: Analyst consensus ratios — hand-curated per company from earnings calls, sell-side reports, company commentary
- Per-company fields: AI revenue estimate, attribution_method, ratio_source, uncertainty_low, uncertainty_high, vintage_date
- Storage: Separate YAML registry (like Phase 8 analyst corpus pattern), compiled to Parquet by pipeline
- Pure-play companies: Claude's discretion on whether to use pass-through with 100% ratio or skip attribution entirely
- 6 bundled companies already flagged in EDGAR output: Microsoft, Amazon, Alphabet, Meta, Salesforce, IBM

**Private Company Registry**
- Valuation method: Comparable multiples only (no DCF) — apply EV/Revenue multiples from similar public AI companies
- Multiple range: Each company gets low/mid/high valuation based on comparable public companies
- Confidence tiers: HIGH (recent funding round with known valuation), MEDIUM (revenue estimate from press + comparable multiple), LOW (revenue unknown, valuation inferred from funding)
- Scope: 15-20 major private AI companies (OpenAI, Anthropic, Databricks, xAI, Mistral, Cohere, Inflection, Scale AI, Hugging Face, etc.)
- Storage: YAML registry compiled to `private_valuations_ai.parquet`

**Backtesting Approach**
- Split: Train on pre-2022 data, evaluate on 2022-2024
- Actuals: Both EDGAR filed revenue ('hard actuals', company-level, audited) AND published analyst estimates ('soft actuals', market-level). Both reported with explicit labels
- Metrics: MAPE and R² computed separately for hard vs soft actuals
- Threshold: Claude's discretion on whether to gate or just report
- Output: `backtesting_results.parquet` feeding the Diagnostics tab

**Aggregation and Double-Counting**
- Multi-layer allocation: Companies spanning multiple value chain layers get AI revenue split by sub-segment ratios. Ratios stored in attribution YAML
- Both totals: Raw total (sum of segments, may double-count) AND adjusted total (overlap removed). Both shown in dashboard
- Overlap zones: Use the 3 overlap zones already documented in ai.yaml from Phase 8

### Claude's Discretion
- Pure-play pass-through vs skip (attribution pipeline design)
- MAPE threshold: gate vs report-only
- Which specific public AI companies to use as comparables for private company multiples
- How to handle private companies where no revenue estimate exists (funding-based inference)
- Exact sub-segment ratio values per multi-layer company
- Whether backtesting should use skforecast or custom walk-forward implementation

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MODL-02 | AI revenue attribution for 10-15 mixed-tech public companies — parameterized attribution ratios from earnings disclosures + analyst consensus, with documented uncertainty per company | Covered by Plan 10-02 via revenue_attribution.py + YAML registry pattern from market_anchors.py |
| MODL-03 | Private company valuation registry — 15-20 major private AI companies valued via comparable multiples with confidence flags and explicit uncertainty ranges | Covered by Plan 10-03 via YAML registry + comparable multiples compiled to private_valuations_ai.parquet |
| MODL-06 | Walk-forward backtesting — train on pre-2022 data, evaluate 2022-2024 against filed actuals, producing real MAPE and R² in Diagnostics tab | Covered by Plan 10-04; `compute_mape` and `compute_r2` already exist in model_eval.py; backtesting_results.parquet is the new artifact |
</phase_requirements>

---

## Summary

Phase 10 is a data enrichment phase, not a model-building phase. Three parallel workstreams: (1) build `revenue_attribution.py` that reads from a new YAML registry to produce AI revenue estimates with uncertainty for 10-15 mixed-tech public companies; (2) build `private_valuations_ai.parquet` from a separate YAML registry of 15-20 private AI companies using comparable EV/Revenue multiples; (3) activate walk-forward backtesting by wiring the existing `compute_mape` and `compute_r2` functions in `model_eval.py` against EDGAR filed actuals (hard actuals) and market anchor estimates (soft actuals), writing `backtesting_results.parquet`.

All three workstreams follow the same YAML-registry → pandera validation → Parquet output pattern already proven in Phase 8. The value chain layer taxonomy locked in Phase 9 (chip/cloud/application/end_market in ai.yaml) provides the per-company layer assignments that determine sub-segment ratio splits for multi-layer companies. The architecture is additive: new processing modules and new YAML registries, wired into `pipeline.py` as additional steps, with no changes to existing steps.

**Primary recommendation:** Follow the market_anchors.py pattern (YAML registry → compile function → pandera schema → Parquet write) for both the attribution and private company registries. Reuse the existing `compute_mape` and `compute_r2` functions; the only new code is the data pipeline wiring and the `backtesting_results.parquet` schema.

---

## Standard Stack

### Core (already installed — no additions needed for Plans 10-01 through 10-04)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 3.0.x | DataFrame manipulation, YAML compilation, Parquet reads | Already in lock file; CoW-safe idioms required |
| pandera | 2.x | Schema validation for attribution and private valuation DataFrames | ATTRIBUTION_SCHEMA and PRIVATE_VALUATION_SCHEMA extend existing pattern in validate.py |
| pyarrow | 18.x | Parquet write with provenance metadata | Already in lock file; same pattern as save_raw_edgar() |
| PyYAML | 6.x | YAML registry loading | Already used in market_anchors.py |
| numpy | 2.x | MAPE/R² arithmetic in model_eval.py | Already in lock file |

### Supporting (already installed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| skforecast | 0.21.0 | Walk-forward backtesting wrapper for existing LightGBM/ARIMA models | Use for the walk-forward splits in Plan 10-04 rather than a custom loop; prevents fold-boundary leakage |
| edgartools | 5.25.1 | Access filed 10-K actuals for hard validation in backtesting | EDGAR data is already in `data/raw/edgar/edgar_ai_raw.parquet` from Phase 8 |
| yfinance | 1.2.0 | Cross-check EV/Revenue multiples for private company comparable selection | Use as sanity check source, not primary source |

### No New Dependencies Required

All libraries needed for Phase 10 are already in the project lock file. Phase 10 is a data pipeline extension, not a new capability domain.

---

## Architecture Patterns

### Recommended Project Structure for Phase 10 New Files

```
src/
├── processing/
│   ├── revenue_attribution.py      # NEW: Plan 10-02 — AI revenue isolation for mixed-tech companies
│   └── private_valuations.py       # NEW: Plan 10-03 — comparable multiple valuation for private companies
├── backtesting/                     # NEW package: Plan 10-04
│   ├── __init__.py
│   ├── walk_forward.py             # Walk-forward splits, model refit, forecast per fold
│   └── actuals_assembly.py         # Assembles hard actuals (EDGAR) + soft actuals (market_anchors)
├── ingestion/
│   └── pipeline.py                 # MODIFY: add attribution and backtesting steps

data/raw/
├── attribution/
│   └── ai_attribution_registry.yaml    # NEW: per-company AI revenue ratios
└── private_companies/
    └── ai_private_registry.yaml        # NEW: private company valuation inputs

data/processed/
├── revenue_attribution_ai.parquet      # NEW output from Plan 10-02
├── private_valuations_ai.parquet       # NEW output from Plan 10-03
└── backtesting_results.parquet         # NEW output from Plan 10-04

config/industries/
└── ai.yaml                             # EXTEND: add attribution_subsegment_ratios section (Plan 10-01)
```

### Pattern 1: YAML Registry → Compile Function → Pandera Schema → Parquet

This is the established project pattern (proven in market_anchors.py). Every new data layer follows it exactly.

**What:** Hand-curated YAML is the single source of truth for attribution ratios and private valuations. A compile function reads the YAML, applies logic (scope normalization, multiple application), validates with pandera, and writes Parquet.

**When to use:** For all data inputs that are hand-curated rather than fetched from an API.

**Example — attribution YAML entry (follows ai_analyst_registry.yaml schema style):**
```yaml
# data/raw/attribution/ai_attribution_registry.yaml
entries:
  - company_name: "Microsoft Corporation"
    cik: "0000789019"
    value_chain_layer: "cloud"
    ai_revenue_usd_billions: 13.0        # management commentary: $13B AI annual run rate
    attribution_method: "management_commentary"
    ratio_source: "Microsoft FY2024 earnings call, Q4 2024 (Satya Nadella)"
    ratio_source_url: "https://ir.microsoft.com/..."
    vintage_date: "2024-07-30"           # date of the earnings call
    uncertainty_low: 11.0
    uncertainty_high: 16.0
    segment: "ai_infrastructure"         # maps to value_chain_layer cloud -> ai_infrastructure
    estimated_flag: false
    notes: "Azure AI + Copilot run-rate; does not separate Azure AI from total Azure"
```

**Example — private company YAML entry:**
```yaml
# data/raw/private_companies/ai_private_registry.yaml
entries:
  - company_name: "OpenAI"
    confidence_tier: "HIGH"             # recent funding round with known valuation
    last_funding_valuation_usd_billions: 157.0
    funding_date: "2024-10-01"
    estimated_arr_usd_billions: 3.4     # press estimate (The Information, Q3 2024)
    arr_source: "The Information, 2024-09"
    arr_source_url: "https://..."
    comparable_low_multiple: 25.0
    comparable_mid_multiple: 40.0
    comparable_high_multiple: 60.0
    comparable_peer_group: "ai_software_pure_play"
    implied_ev_low: 85.0
    implied_ev_mid: 136.0
    implied_ev_high: 204.0
    segment: "ai_software"
    vintage_date: "2024-10-01"
    notes: "Mid multiple anchored to funding round post-money valuation as crosscheck"
```

### Pattern 2: Revenue Attribution Function Signature (from ARCHITECTURE.md)

The `estimate_ai_revenue()` function in `revenue_attribution.py` follows the signature already documented in the project's architecture research:

```python
# src/processing/revenue_attribution.py
def estimate_ai_revenue(
    company_revenue: float,
    cik: str,
    attribution_config: dict,
    year: int,
) -> dict:
    """
    Returns:
        ai_revenue_usd: float
        attribution_method: "explicit_disclosure" | "analogue_ratio" | "management_commentary"
        ratio: float
        ratio_source: str
        uncertainty_low: float
        uncertainty_high: float
        vintage_date: str
    """
```

For pure-play companies (NVIDIA Data Center, Palantir, C3.ai), use a pass-through pattern with ratio=1.0 and attribution_method="direct_disclosure". This is the cleanest approach: it avoids a special-case branch while preserving the uniform output schema. The uncertainty bounds for pure-plays are tight (±5%) reflecting the explicit segment disclosure.

### Pattern 3: Sub-Segment Ratio Splits in ai.yaml

For multi-layer companies, sub-segment ratios are stored in ai.yaml under a new `attribution_subsegment_ratios` section (Plan 10-01 deliverable). This follows ARCH-01 config-driven extensibility:

```yaml
# config/industries/ai.yaml (new section, Plan 10-01)
attribution_subsegment_ratios:
  - cik: "0001045810"  # NVIDIA
    company_name: "NVIDIA Corporation"
    primary_layer: "chip"
    sub_segment_splits:
      ai_hardware: 0.80
      ai_infrastructure: 0.20          # data center builds count in infrastructure too
    rationale: "Nvidia GPU revenue split: ~80% direct silicon, ~20% system/infrastructure"
    vintage_date: "2026-01"
```

Both totals (raw = sum of segments, adjusted = overlap removed) use the existing `adjusted_total_method` formula already defined in ai.yaml's `market_boundary.adjusted_total_method`.

### Pattern 4: Backtesting with Hard vs Soft Actuals

The backtesting architecture assembles two distinct actuals sources and computes metrics separately, as required by the locked decisions:

```python
# src/backtesting/actuals_assembly.py
def assemble_actuals(industry_id: str) -> pd.DataFrame:
    """
    Returns DataFrame with columns:
        year, segment, actual_usd_billions, actual_type ("hard" | "soft"),
        source, source_date
    Hard actuals: from data/raw/edgar/ (EDGAR 10-K filed revenue, audited)
    Soft actuals: from data/processed/market_anchors_ai.parquet (analyst consensus)
    """
```

The `backtesting_results.parquet` schema (from ARCHITECTURE.md):
```
year, segment, actual_usd, predicted_usd, residual_usd, model, holdout_type,
actual_type ("hard" | "soft"), mape, r2
```

The existing `compute_mape()` and `compute_r2()` functions in `src/diagnostics/model_eval.py` are already implemented and tested — they just need to be called with real actuals for the first time.

### Walk-Forward Split Logic

Pre-2022 training window, 2022-2024 evaluation. With only 8 years of anchor data (2017-2024), the walk-forward produces 3 evaluation folds:
- Fold 1: train 2017-2021, evaluate 2022
- Fold 2: train 2017-2022, evaluate 2023
- Fold 3: train 2017-2023, evaluate 2024

This is a small-sample backtesting scenario. The reported MAPE/R² must carry a caveat that 3 observations per fold is insufficient for statistical significance — this is report-only, not a gate. Use the MAPE threshold to label: <15% = "acceptable for market sizing", 15-30% = "use with caution", >30% = "directional only".

### Anti-Patterns to Avoid

- **Storing attribution percentages as bare floats in YAML without source/vintage:** Every ratio must have `ratio_source`, `vintage_date`, `uncertainty_low`, `uncertainty_high`. This is a hard design rule from PITFALLS.md Pitfall 4.
- **Applying a single revenue multiple to all private companies:** Multiple range is 3.6x–225x in the market (PITFALLS.md Pitfall 5). Low/mid/high per company is required.
- **Computing MAPE against analyst consensus and labeling it "hard validation":** Soft actuals must be explicitly labeled `actual_type="soft"` throughout the pipeline (PITFALLS.md Pitfall 6).
- **Adding attribution as a standalone script bypassing `run_full_pipeline()`:** All new steps must be wired into the `steps` list pattern in `pipeline.py` (ARCHITECTURE.md Anti-Pattern 2).
- **Writing actuals into `residuals_statistical.parquet`:** New `backtesting_results.parquet` with its own schema — do not modify existing Parquet schemas (ARCHITECTURE.md Anti-Pattern 3).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Walk-forward time series validation | Custom fold generator with manual refit loop | skforecast `backtesting_forecaster` | Custom loops commonly get fold-boundary data leakage and refit timing wrong; skforecast is purpose-built (STACK.md) |
| MAPE and R² computation | New metric functions | `compute_mape` and `compute_r2` in `src/diagnostics/model_eval.py` | Already implemented and tested in `tests/test_diagnostics.py` |
| YAML loading and parsing | Custom YAML reader | `load_analyst_registry()` pattern from `market_anchors.py` | Already battle-tested with the same registry format |
| Parquet write with provenance metadata | Ad hoc pyarrow writes | `save_raw_edgar()` pattern (pyarrow table with custom metadata dict) | Consistent provenance metadata across all pipeline artifacts |
| Schema validation | Manual column checks | pandera DataFrameSchema, extending existing patterns in `validate.py` | Fail-loud validation before write; reuses existing test infrastructure |
| Company name fuzzy matching | Custom Levenshtein | rapidfuzz `process.extractOne` (already in lock file) | Name normalization between EDGAR CIKs and YAML entries |

**Key insight:** Every problem in Phase 10 has an existing solution in the codebase. The phase is wiring and data assembly, not new capability development.

---

## Common Pitfalls

### Pitfall 1: BUNDLED_SEGMENT_COMPANIES Mismatch with YAML Registry

**What goes wrong:** `BUNDLED_SEGMENT_COMPANIES` in `edgar.py` contains 6 CIKs (Microsoft, Amazon, Alphabet, Meta, IBM, Accenture). The CONTEXT.md lists the 6 bundled companies as Microsoft, Amazon, Alphabet, Meta, Salesforce, IBM — note Salesforce replaces Accenture. The attribution YAML must cover the correct 6, and the YAML must use the same CIK strings as `BUNDLED_SEGMENT_COMPANIES` for exact-match joins.

**How to avoid:** Cross-check CIKs in the YAML against `BUNDLED_SEGMENT_COMPANIES` in `edgar.py` as part of Plan 10-01 scaffold. Note: Accenture CIK `0001281761` is in `BUNDLED_SEGMENT_COMPANIES` but CONTEXT.md lists Salesforce as bundled — resolve this discrepancy in Plan 10-01 and update `BUNDLED_SEGMENT_COMPANIES` if needed.

**Warning signs:** Attribution YAML has entries for companies not in `BUNDLED_SEGMENT_COMPANIES`, or `BUNDLED_SEGMENT_COMPANIES` contains CIKs with no attribution YAML entry.

### Pitfall 2: Hard Actuals Coverage is Sparse for Segment-Level Backtesting

**What goes wrong:** EDGAR 10-K data exists at company level (e.g., NVIDIA Data Center revenue), not segment level (ai_hardware). Converting company-level filed revenue to segment-level actuals requires the same attribution ratios being validated. This is circular: you cannot use attribution ratios to generate the actuals that validate those same ratios.

**How to avoid:** For hard actuals, use only companies with `ai_disclosure_type: "direct"` in ai.yaml (NVIDIA, Palantir, C3.ai) — these have explicit AI segment XBRL tags and require no attribution. For companies with `bundled` or `partial` disclosure, use the analyst consensus (soft actuals) only. Label clearly which companies contribute hard vs soft actuals.

**Warning signs:** Hard actuals list includes Microsoft, Amazon, or Alphabet (all bundled companies).

### Pitfall 3: Sub-Segment Ratio Splits Creating Double-Count in `raw_total`

**What goes wrong:** If NVIDIA has sub-segment splits (80% ai_hardware, 20% ai_infrastructure), and both splits are added to their respective segment totals without tracking, the `raw_total` double-counts NVIDIA's revenue. The `adjusted_total_method` in ai.yaml already documents the overlap zones and subtraction formula. The sub-segment ratios must feed the adjusted total formula, not create new hidden overlap.

**How to avoid:** The 3 overlap zones already in ai.yaml (hardware_to_infrastructure, software_to_adoption, infrastructure_to_software) with their documented percentage ranges (20-30%, 15-25%, 10-15%) are the only subtraction applied to compute `adjusted_total`. The sub-segment ratio splits are a refinement within those zones, not an addition of new overlap categories.

### Pitfall 4: Backtesting Fold Contamination with Post-2021 Attribution Data

**What goes wrong:** Attribution ratios sourced from 2024 earnings calls (vintage_date: 2024-xx) are used as inputs to the model that is then "backtested" on 2022-2024. This is look-ahead bias: the model used 2024 attribution data to predict 2022.

**How to avoid:** For backtesting, apply only attribution vintages dated before the fold's evaluation year. The attribution YAML must store `vintage_date` per entry precisely for this reason. The backtesting fold assembler filters the attribution config to `vintage_date < fold_start_year`.

### Pitfall 5: Private Company Multiples from Stale Sources

**What goes wrong:** EV/Revenue multiples for AI pure-plays change rapidly. Multiples from 2021-2022 (50x+ era) would produce wildly inflated private company valuations when applied in 2026. The research files (PITFALLS.md) document a 3.6x–225x multiple spread across private AI companies.

**How to avoid:** Source comparables from 2025-2026 public company trading multiples (PitchBook Q4 2025 AI Comp Sheet: ~33x for pure-plays, ~7x for conglomerates). The YAML must include `comparable_vintage_date` per entry. Flag for quarterly review.

---

## Code Examples

### YAML Registry Loader Pattern (from market_anchors.py)

```python
# Source: src/ingestion/market_anchors.py load_analyst_registry()
def load_attribution_registry(registry_path: Path) -> pd.DataFrame:
    with open(registry_path, "r") as f:
        raw = yaml.safe_load(f)
    if "entries" not in raw:
        raise KeyError(f"Registry YAML at {registry_path} missing 'entries' key")
    return pd.DataFrame(raw["entries"])
```

### Pandera Schema Extension Pattern (from validate.py)

```python
# Source: src/processing/validate.py MARKET_ANCHOR_SCHEMA pattern
ATTRIBUTION_SCHEMA = DataFrameSchema(
    {
        "company_name": Column(str, nullable=False),
        "cik": Column(str, nullable=False),
        "value_chain_layer": Column(str, Check.isin(["chip", "cloud", "application", "end_market"])),
        "attribution_method": Column(str, Check.isin([
            "direct_disclosure", "management_commentary", "analogue_ratio"
        ])),
        "ai_revenue_usd_billions": Column(float, Check.greater_than_or_equal_to(0), nullable=False),
        "uncertainty_low": Column(float, Check.greater_than_or_equal_to(0), nullable=False),
        "uncertainty_high": Column(float, Check.greater_than(0), nullable=False),
        "vintage_date": Column(str, nullable=False),
        "ratio_source": Column(str, nullable=False),
        "segment": Column(str, Check.isin(["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"])),
        "year": Column(int, Check.in_range(2017, 2026)),
    },
    coerce=True,
    strict=False,
)

PRIVATE_VALUATION_SCHEMA = DataFrameSchema(
    {
        "company_name": Column(str, nullable=False),
        "confidence_tier": Column(str, Check.isin(["HIGH", "MEDIUM", "LOW"])),
        "implied_ev_low": Column(float, Check.greater_than(0)),
        "implied_ev_mid": Column(float, Check.greater_than(0)),
        "implied_ev_high": Column(float, Check.greater_than(0)),
        "segment": Column(str, Check.isin(["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"])),
        "vintage_date": Column(str, nullable=False),
        "comparable_mid_multiple": Column(float, Check.in_range(1.0, 300.0)),
    },
    coerce=True,
    strict=False,
)
```

### Parquet Write with Provenance (from edgar.py / market_anchors.py)

```python
# Source: src/ingestion/edgar.py save_raw_edgar() pattern
def write_attribution_parquet(df: pd.DataFrame, industry_id: str) -> Path:
    output_path = DATA_PROCESSED / f"revenue_attribution_{industry_id}.parquet"
    table = pa.Table.from_pandas(df, preserve_index=False)
    existing_meta = table.schema.metadata or {}
    custom_meta = {
        b"source": b"attribution_registry",
        b"industry": industry_id.encode(),
        b"fetched_at": datetime.now(tz=timezone.utc).isoformat().encode(),
    }
    table = table.replace_schema_metadata({**existing_meta, **custom_meta})
    pq.write_table(table, output_path, compression="snappy")
    return output_path
```

### Pipeline Wiring Pattern (from pipeline.py run_full_pipeline())

```python
# Source: src/ingestion/pipeline.py run_full_pipeline() steps pattern
# Add to run_full_pipeline() after Step 7 (EDGAR):

# Step 8: Revenue attribution (requires EDGAR output)
try:
    from src.processing.revenue_attribution import compile_and_write_attribution
    attribution_path = compile_and_write_attribution(industry_id)
    processed_paths["revenue_attribution"] = attribution_path
except Exception as e:
    print(f"Revenue attribution failed: {e}")

# Step 9: Private company valuations
try:
    from src.processing.private_valuations import compile_and_write_private_valuations
    private_path = compile_and_write_private_valuations(industry_id)
    processed_paths["private_valuations"] = private_path
except Exception as e:
    print(f"Private valuations failed: {e}")

# Step 10: Backtesting (requires model outputs)
try:
    from src.backtesting.walk_forward import run_backtesting
    backtest_path = run_backtesting(industry_id)
    processed_paths["backtesting_results"] = backtest_path
except Exception as e:
    print(f"Backtesting failed: {e}")
```

### Calling Existing compute_mape / compute_r2 with Real Actuals

```python
# Source: src/diagnostics/model_eval.py — already implemented, just needs to be called
from src.diagnostics.model_eval import compute_mape, compute_r2

# For hard actuals (EDGAR filed revenue):
hard_mape = compute_mape(
    actual=hard_actuals_array,   # from EDGAR 10-K, direct-disclosure companies only
    predicted=predictions_array,
)
hard_r2 = compute_r2(actual=hard_actuals_array, predicted=predictions_array)

# For soft actuals (analyst consensus from market_anchors_ai.parquet):
soft_mape = compute_mape(
    actual=soft_actuals_array,
    predicted=predictions_array,
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PCA composite → value chain multiplier | USD billions direct from anchor-calibrated model | Phase 9 | `revenue_attribution.py` output goes directly into segment totals, no multiplier |
| DCF for private companies (STACK.md originally listed numpy-financial) | Comparable multiples only (CONTEXT.md locked decision) | Phase 10 CONTEXT.md | numpy-financial not needed; simpler and more defensible for sparse revenue data |
| No backtesting actuals | Hard actuals (EDGAR 10-K) + soft actuals (analyst consensus) with explicit labels | Phase 10 | `compute_mape`/`compute_r2` already implemented but never called with real actuals |
| `BUNDLED_SEGMENT_COMPANIES` flagged but no attribution | YAML registry per company with uncertainty ranges | Phase 10 | Closes the Phase 8 deferred work |

**Deprecated/outdated (from prior phases):**
- `value_chain_multiplier` path: removed in Phase 9, confirmed absent in `forecast.py`
- `build_pca_composite` as primary path: demoted to comparison utility in Phase 9
- `dcf_valuation.py` mentioned in ARCHITECTURE.md: superseded by comparable multiples decision in CONTEXT.md; skip DCF, build `private_valuations.py` instead

---

## Open Questions

1. **Salesforce vs Accenture in BUNDLED_SEGMENT_COMPANIES**
   - What we know: `BUNDLED_SEGMENT_COMPANIES` in `edgar.py` contains Accenture (CIK 0001281761). CONTEXT.md lists the 6 bundled companies as Microsoft, Amazon, Alphabet, Meta, Salesforce, IBM — Salesforce (CIK 0001108524) but not Accenture.
   - What's unclear: Whether Accenture should stay in `BUNDLED_SEGMENT_COMPANIES` or be replaced with Salesforce. Both appear in ai.yaml's `edgar_companies`.
   - Recommendation: Plan 10-01 should resolve this. Salesforce is already in ai.yaml as `ai_software/partial` disclosure type. If Salesforce AI revenue is material enough for attribution, add it to `BUNDLED_SEGMENT_COMPANIES`. Accenture's AI consulting revenue ($3B+ per FY2024) is significant and should remain. The YAML registry can cover both regardless.

2. **Backtesting with 3 folds vs skforecast usage**
   - What we know: With 8 years of anchor data (2017-2024) and pre-2022 training, the backtesting yields only 3 evaluation folds. skforecast is designed for this but reports a small-N warning.
   - What's unclear: Whether skforecast's overhead is justified for 3 folds, or whether a simple custom loop (48 lines, no leakage risk given the explicit split logic) is cleaner.
   - Recommendation: Given the CONTEXT.md explicitly lists "whether backtesting should use skforecast or custom walk-forward implementation" as Claude's discretion, use a custom walk-forward loop for Plan 10-04. With only 3 folds and an explicit pre-2022 split, there is no fold-boundary complexity that skforecast guards against. Simpler code is more auditable. Keep skforecast in the lock file for potential future use with more data.

3. **Sub-segment ratio values per multi-layer company**
   - What we know: CONTEXT.md flags the exact sub-segment ratio values as Claude's discretion. ARCHITECTURE.md's example uses NVIDIA 80% ai_hardware / 20% ai_infrastructure.
   - What's unclear: The values for other multi-layer companies (Microsoft, Alphabet, Amazon all span cloud and application layers).
   - Recommendation: Plan 10-01 should populate the `attribution_subsegment_ratios` section of ai.yaml with reasonable defaults sourced from recent earnings commentary. For cloud hyperscalers: ~90% infrastructure / 10% software. Document each with vintage_date and source.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | pytest.ini (project root, check `uv run pytest`) |
| Quick run command | `uv run pytest tests/test_validate.py tests/test_market_anchors.py -x` |
| Full suite command | `uv run pytest -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODL-02 | `revenue_attribution.py` produces AI revenue with attribution_method, ratio_source, uncertainty_low, uncertainty_high, vintage_date | unit | `uv run pytest tests/test_revenue_attribution.py -x` | ❌ Wave 0 |
| MODL-02 | `ATTRIBUTION_SCHEMA` validates compiled DataFrame (no bare float ratios, no missing vintages) | unit | `uv run pytest tests/test_validate.py::TestAttributionSchema -x` | ❌ Wave 0 |
| MODL-03 | `private_valuations_ai.parquet` contains low/mid/high EV columns with confidence_tier | unit | `uv run pytest tests/test_private_valuations.py -x` | ❌ Wave 0 |
| MODL-03 | PRIVATE_VALUATION_SCHEMA validates that implied_ev_low < implied_ev_mid < implied_ev_high | unit | `uv run pytest tests/test_validate.py::TestPrivateValuationSchema -x` | ❌ Wave 0 |
| MODL-06 | `backtesting_results.parquet` has actual_type column with values "hard" or "soft" only | unit | `uv run pytest tests/test_backtesting.py::test_actual_type_labels -x` | ❌ Wave 0 |
| MODL-06 | Hard MAPE is computed only from direct-disclosure companies (NVIDIA, Palantir, C3.ai) | unit | `uv run pytest tests/test_backtesting.py::test_hard_actuals_source -x` | ❌ Wave 0 |
| MODL-06 | `backtesting_results.parquet` schema check (year, segment, actual_usd, predicted_usd, mape, r2, actual_type) | integration | `uv run pytest tests/test_backtesting.py::test_parquet_schema -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_validate.py -x`
- **Per wave merge:** `uv run pytest -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_revenue_attribution.py` — covers MODL-02 attribution schema and compilation logic
- [ ] `tests/test_private_valuations.py` — covers MODL-03 private company registry schema and multiple application
- [ ] `tests/test_backtesting.py` — covers MODL-06 backtesting schema, hard/soft actual labels, metric computation
- [ ] `tests/test_validate.py::TestAttributionSchema` — pandera schema validation for new ATTRIBUTION_SCHEMA
- [ ] `tests/test_validate.py::TestPrivateValuationSchema` — pandera schema validation for new PRIVATE_VALUATION_SCHEMA
- [ ] `data/raw/attribution/ai_attribution_registry.yaml` — Wave 0 stub with at least 3 entries for test fixtures
- [ ] `data/raw/private_companies/ai_private_registry.yaml` — Wave 0 stub with at least 3 entries for test fixtures

---

## Sources

### Primary (HIGH confidence)

- Direct codebase inspection: `src/ingestion/edgar.py`, `src/ingestion/market_anchors.py`, `src/processing/validate.py`, `src/diagnostics/model_eval.py`, `src/ingestion/pipeline.py`, `config/industries/ai.yaml` — all Phase 8-9 outputs inspected 2026-03-24
- `.planning/research/ARCHITECTURE.md` — revenue_attribution.py and dcf_valuation.py patterns documented; backtesting_results.parquet schema defined
- `.planning/research/STACK.md` — v1.1 stack verified; skforecast 0.21.0 and edgartools 5.25.1 confirmed in lock file
- `.planning/research/PITFALLS.md` — Pitfalls 3-7 directly applicable to this phase; hard/soft actual distinction, double-counting, multiple spread
- `.planning/phases/10-revenue-attribution-and-private-company-valuation/10-CONTEXT.md` — locked decisions constrain implementation choices

### Secondary (MEDIUM confidence)

- `.planning/research/FEATURES.md` — AI revenue attribution methodology and private company valuation section; PitchBook Q4 2025 AI Comp Sheet (~33x EV/Revenue for pure-plays, ~7x for conglomerates)
- `tests/test_diagnostics.py` — confirms `compute_mape` and `compute_r2` are already tested at unit level
- `tests/test_contract_usd_billions.py` — confirms forecasts_ensemble.parquet schema and CAGR test infrastructure

### Tertiary (LOW confidence — not verified against external source in this research session)

- NVIDIA FY2026 Data Center ~91% AI GPU share: cited in ai.yaml notes field (company-level, not independently verified in this session)
- PitchBook 33x AI pure-play multiple: from FEATURES.md citing official PitchBook Q4 2025 report (HIGH via FEATURES.md, but not re-verified in this session)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in lock file, no new installations
- Architecture: HIGH — YAML registry pattern used verbatim from market_anchors.py; pipeline wiring follows existing steps pattern
- Pitfalls: HIGH — grounded in PITFALLS.md (prior research with source citations) + direct codebase inspection revealing the BUNDLED_SEGMENT_COMPANIES discrepancy
- Backtesting: MEDIUM — skforecast vs custom loop is discretionary; small-N limitation is documented but the specific MAPE thresholds are judgment calls

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (30 days, stable domain — private company multiples may shift but the implementation pattern is stable)
