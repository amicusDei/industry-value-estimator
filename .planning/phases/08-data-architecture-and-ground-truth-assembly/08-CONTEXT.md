# Phase 8: Data Architecture and Ground Truth Assembly - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Lock the market boundary definition, assemble a defensible historical AI market size corpus from published analyst estimates and company filings via SEC EDGAR, and produce a reconciled ground truth time series (2017-2025) by segment. This phase produces the data foundation that all downstream phases depend on — no model code is written here.

</domain>

<decisions>
## Implementation Decisions

### Market Boundary Scope
- **Multi-layer model:** Model ALL value chain layers separately (hardware, infrastructure, software, adoption) and report each layer independently AND as a total
- **Overlap handling:** Report both overlapping values per layer, flag overlap zones, produce a separate "adjusted total" that subtracts documented overlap ranges — transparent, shows the analyst how the sausage is made
- **Full scope mapping table required:** For each analyst firm (IDC, Gartner, Grand View, Statista, etc.), document in ai.yaml + METHODOLOGY.md: what they include, what they exclude, which of our segments their number maps to, and their published figure
- **Definitions are the most important part** — user emphasized this explicitly. Boundary documentation must be thorough enough that any analyst can understand exactly what the model measures and how it compares to any published estimate

### Segment Structure
- v1.0 segments (hardware, infrastructure, software, adoption) may be kept or revised — Claude's discretion based on what best serves multi-layer reporting and analyst comparison
- Each segment must have a clear mapping to at least 2-3 published analyst category definitions

### Analyst Corpus Sourcing
- **Sources:** Free public sources (press releases, earnings transcripts, news coverage of analyst reports, Statista free tier) PLUS LSEG Workspace data and APIs (existing subscription access)
- **Source count:** 6-8 independent analyst sources minimum (IDC, Gartner, Grand View, Statista, Goldman Sachs, Bloomberg Intelligence, CB Insights, McKinsey)
- **Vintage tracking:** Full vintage series — track how estimates evolved over time (e.g., IDC's 2020 estimate as published in 2019, 2020, 2021). Enables analysis of analyst forecast accuracy itself
- **Storage:** Hand-curated YAML registry (human-readable, version-controlled, easy to review/edit) compiled to `market_anchors_ai.parquet` by the pipeline

### EDGAR Company Selection
- **Selection criteria:** Market cap leaders first, then fill gaps to ensure every value chain layer has at least 2-3 companies with filings
- **Filing approach:** Ingest whatever segment disclosures exist, flag companies where AI is bundled into larger segments (e.g., Microsoft Intelligent Cloud, Amazon AWS). Phase 10 handles the attribution math — Phase 8 just collects raw filings
- **Filing depth:** 5 years (2020-2024) — matches the period where AI revenue became meaningful in disclosures
- **Library:** edgartools (research recommendation) for 10-K/10-Q XBRL extraction

### Reconciliation Method
- **Algorithm:** Scope-normalized median — first normalize each estimate to our scope definition using the mapping table, then take median across sources per year/segment
- **Gap handling:** Linear interpolation between known data points, flagged as 'estimated' in the dataset (consistent with v1.0)
- **Output format:** Range — 25th percentile, median, 75th percentile of scope-normalized estimates per year/segment. Propagates source disagreement as uncertainty
- **Currency:** Store BOTH nominal USD and constant 2020 USD columns. Analyst estimates published in nominal; modeling uses real 2020 USD. Basic dashboard can show whichever is more intuitive

### Claude's Discretion
- Whether to revise the 4 v1.0 segments or keep them with added mappings
- Exact YAML schema for the analyst estimate registry
- Which specific XBRL tags to extract per company
- Specific 10-15 company list (guided by market cap + value chain coverage criteria)
- Interpolation method details (linear vs spline per indicator)
- How to structure the scope mapping table in ai.yaml

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/PROJECT.md` — Core value ("analyst's best friend"), v1.1 milestone goals, constraints (Python/uv, LSEG subscription, portfolio-quality)
- `.planning/REQUIREMENTS.md` — DATA-08 through DATA-11 requirements with acceptance criteria
- `.planning/ROADMAP.md` — Phase 8 success criteria (4 criteria that must be TRUE)

### Research findings
- `.planning/research/STACK.md` — edgartools 5.25.1 for EDGAR, yfinance 1.2.0 for market data, skforecast for backtesting
- `.planning/research/FEATURES.md` — Analyst estimate anchoring is non-negotiable table stake; scope definitions create 7x spread; full vintage series enables analyst accuracy analysis
- `.planning/research/ARCHITECTURE.md` — market_anchors.py as new ingestion module; market_anchors_ai.parquet schema; integration with existing pipeline
- `.planning/research/PITFALLS.md` — 7x anchor spread risk; market boundary must be locked before data collection; analyst consensus is not ground truth for backtesting
- `.planning/research/SUMMARY.md` — Synthesized findings, build order rationale

### Existing config
- `config/industries/ai.yaml` — Current market boundary config with segments, proxies, LSEG TRBC codes, value chain multiplier (to be replaced)

### Prior phase context
- `.planning/phases/01-data-foundation/01-CONTEXT.md` — v1.0 data pipeline decisions: 4 segments, overlap allowed, 2020 constant USD, Parquet cache, config-driven architecture

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ingestion/pipeline.py` — Orchestration pattern for multi-source ingestion; new market_anchors.py follows same pattern
- `src/ingestion/world_bank.py`, `src/ingestion/oecd.py`, `src/ingestion/lseg.py` — Existing ingestion modules; new EDGAR module follows same interface pattern
- `src/processing/deflate.py` — Deflation pipeline for converting nominal to real 2020 USD; reuse for analyst estimate conversion
- `src/processing/validate.py` — Schema validation with pandera; extend for new Parquet schemas
- `config/industries/ai.yaml` — Existing config structure; extend with scope mapping table and analyst registry

### Established Patterns
- Ingestion modules return validated DataFrames, written to Parquet cache in `data/` directory
- Config-driven via YAML files in `config/industries/`
- pandera schemas for data validation
- Parquet metadata embedding for source attribution (DATA-07 from v1.0)

### Integration Points
- New `market_anchors.py` ingestion module slots into `src/ingestion/`
- New `edgar.py` ingestion module slots into `src/ingestion/`
- `pipeline.py` orchestrates all ingestion modules — new modules register here
- `ai.yaml` extended with scope mapping table and analyst estimate registry path
- Output Parquet files consumed by Phase 9 (model rework) and Phase 10 (backtesting)

</code_context>

<specifics>
## Specific Ideas

- Full vintage series is a unique differentiator — tracking how analyst estimates evolved over time enables a "who predicted best" analysis that no commercial tool offers transparently
- The scope mapping table is the analytical crown jewel of this phase — it makes every downstream number defensible by showing exactly how it maps to published estimates
- LSEG access gives an edge over purely free-source approaches — company-level financial data supplements analyst estimates with actual filed revenue

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-data-architecture-and-ground-truth-assembly*
*Context gathered: 2026-03-23*
