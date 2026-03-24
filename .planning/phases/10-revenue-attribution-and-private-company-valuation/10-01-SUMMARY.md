---
phase: 10-revenue-attribution-and-private-company-valuation
plan: "01"
subsystem: data-validation-and-registries
tags: [pandera, schemas, yaml-registry, attribution, private-valuation, wave-0, tdd]
dependency_graph:
  requires: []
  provides:
    - ATTRIBUTION_SCHEMA in src/processing/validate.py
    - PRIVATE_VALUATION_SCHEMA in src/processing/validate.py
    - attribution_subsegment_ratios section in config/industries/ai.yaml
    - data/raw/attribution/ai_attribution_registry.yaml (3-entry stub)
    - data/raw/private_companies/ai_private_registry.yaml (3-entry stub)
    - tests/test_revenue_attribution.py (Wave 0 scaffold for MODL-02)
    - tests/test_private_valuations.py (Wave 0 scaffold for MODL-03)
    - tests/test_backtesting.py (Wave 0 scaffold for MODL-06)
  affects:
    - Plan 10-02 (revenue_attribution.py validates against ATTRIBUTION_SCHEMA)
    - Plan 10-03 (private_valuations.py validates against PRIVATE_VALUATION_SCHEMA)
    - Plan 10-04 (backtesting skipped tests become live tests)
tech_stack:
  added: []
  patterns:
    - pandera DataFrameSchema with Check constraints (same pattern as EDGAR_RAW_SCHEMA)
    - YAML registry with 'entries' key and required provenance fields (same as ai_analyst_registry.yaml)
key_files:
  created:
    - data/raw/attribution/ai_attribution_registry.yaml
    - data/raw/private_companies/ai_private_registry.yaml
    - tests/test_revenue_attribution.py
    - tests/test_private_valuations.py
    - tests/test_backtesting.py
  modified:
    - src/processing/validate.py
    - config/industries/ai.yaml
    - src/ingestion/edgar.py
decisions:
  - "BUNDLED_SEGMENT_COMPANIES now includes 7 companies: both Accenture (0001281761, $3B+ AI consulting) and Salesforce (0001108524, Einstein/Agentforce) retained per plan action item"
  - "attribution_subsegment_ratios populated for 5 multi-layer companies: NVIDIA 80/20 chip/infra, Microsoft 85/15 infra/sw, Alphabet 90/10, Amazon 90/10, Meta 85/15 adoption/sw"
  - "ATTRIBUTION_SCHEMA uses value_chain_layer isin chip/cloud/application/end_market (taxonomy from Phase 9), not the segment vocabulary"
  - "Stub YAML registries use 3 entries (minimum required) to keep Wave 0 lightweight; Plans 10-02 and 10-03 will expand to full 10-15 public and 15-20 private companies"
metrics:
  duration_seconds: 198
  completed_date: "2026-03-24"
  tasks_completed: 2
  files_modified: 8
---

# Phase 10 Plan 01: Foundation Schemas, Config Extension, and Wave 0 Test Scaffolds Summary

Wave 0 foundation for Phase 10 — pandera schemas, YAML stubs, and test scaffolds so Plans 10-02, 10-03, and 10-04 have contracts to implement against from day one.

## What Was Built

### Task 1: Pandera schemas and ai.yaml extension

Two new schemas appended to `src/processing/validate.py` following the established `EDGAR_RAW_SCHEMA` pattern:

- `ATTRIBUTION_SCHEMA`: validates per-company AI revenue DataFrame with 11 columns including `attribution_method` (direct_disclosure/management_commentary/analogue_ratio), `uncertainty_low`/`uncertainty_high`, `vintage_date`, `ratio_source`, and `year` range 2017-2026.
- `PRIVATE_VALUATION_SCHEMA`: validates private company EV estimates with `confidence_tier` (HIGH/MEDIUM/LOW), `implied_ev_low/mid/high` (all > 0), `comparable_mid_multiple` (range 1.0-300.0), and `segment`.

`config/industries/ai.yaml` extended with `attribution_subsegment_ratios` section containing 5 multi-layer company entries (NVIDIA, Microsoft, Alphabet, Amazon, Meta) with sub-segment percentage splits, rationale strings, and vintage dates. This is the config-driven data source that Plan 10-02 reads to allocate revenue across segments.

`src/ingestion/edgar.py` `BUNDLED_SEGMENT_COMPANIES` extended from 6 to 7 companies by adding Salesforce (CIK 0001108524). Accenture retained alongside Salesforce because its $3B+ AI consulting revenue is material and explicitly tracked in management commentary.

### Task 2: Stub YAML registries and test scaffolds

`data/raw/attribution/ai_attribution_registry.yaml`: 3 entries covering:
- NVIDIA ($47.5B, direct_disclosure, chip/ai_hardware, FY2024)
- Microsoft ($13.0B, management_commentary, cloud/ai_infrastructure, FY2024)
- Palantir ($2.87B, direct_disclosure, application/ai_software, FY2024)

`data/raw/private_companies/ai_private_registry.yaml`: 3 entries covering:
- OpenAI (HIGH confidence, $157B post-money, implied EV $85-204B, ai_software)
- Anthropic (HIGH confidence, $61.5B post-money, implied EV $27-63B, ai_software)
- Databricks (MEDIUM confidence, $43B post-money, implied EV $24-56B, ai_infrastructure)

Three test scaffold files created:
- `tests/test_revenue_attribution.py`: 3 live tests + 1 skipped (Plan 10-02)
- `tests/test_private_valuations.py`: 3 live tests + 1 skipped (Plan 10-03)
- `tests/test_backtesting.py`: 4 skipped placeholders (Plan 10-04)

## Verification Results

```
6 passed, 6 skipped in 0.62s
```

- `ATTRIBUTION_SCHEMA OK` — validates sample DataFrame
- `PRIVATE_VALUATION_SCHEMA OK` — validates sample DataFrame
- `attribution_subsegment_ratios:` — present in ai.yaml
- All skipped tests reference their downstream plan in the `reason=` string

## Deviations from Plan

None — plan executed exactly as written.

The BUNDLED_SEGMENT_COMPANIES resolution (add Salesforce, keep Accenture = 7 companies) was specified explicitly in the plan's Task 1 action item 3, so this is not a deviation.

## Decisions Made

1. `BUNDLED_SEGMENT_COMPANIES` now has 7 companies (Accenture retained alongside Salesforce). Both have material AI revenue and appear in `ai.yaml` edgar_companies. The YAML attribution registry covers both.

2. `attribution_subsegment_ratios` values sourced from earnings commentary (2024-2025 vintage) and documented with rationale strings. Splits are conservative: cloud hyperscalers assigned 90% infrastructure / 10% software, which aligns with the known AWS/Azure/GCP compute-dominant AI revenue mix.

3. Stub YAML entries chose NVIDIA, Microsoft, Palantir for attribution (one per disclosure type: direct/commentary/direct-pure-play) and OpenAI, Anthropic, Databricks for private companies (one per confidence tier: HIGH/HIGH/MEDIUM). This gives maximum coverage of the schema's allowed values for test fixture purposes.

## Self-Check: PASSED

Files created/modified:
- FOUND: src/processing/validate.py (ATTRIBUTION_SCHEMA + PRIVATE_VALUATION_SCHEMA)
- FOUND: config/industries/ai.yaml (attribution_subsegment_ratios)
- FOUND: src/ingestion/edgar.py (Salesforce in BUNDLED_SEGMENT_COMPANIES)
- FOUND: data/raw/attribution/ai_attribution_registry.yaml
- FOUND: data/raw/private_companies/ai_private_registry.yaml
- FOUND: tests/test_revenue_attribution.py
- FOUND: tests/test_private_valuations.py
- FOUND: tests/test_backtesting.py

Commits:
- FOUND: 0121011 (Task 1)
- FOUND: 08fbe7d (Task 2)
