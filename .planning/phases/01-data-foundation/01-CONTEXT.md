# Phase 1: Data Foundation - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the validated, normalized data pipeline that produces a Parquet cache of AI industry indicators from World Bank, OECD, and LSEG Workspace. Includes market boundary definition, AI use case taxonomy, data cleaning/normalization, schema validation, and config-driven architecture extensible to future industries. Modeling, dashboard, and reports are separate phases.

</domain>

<decisions>
## Implementation Decisions

### AI Market Boundary
- **Scope:** Broad AI value chain — everything that enables or uses AI
- **4 segments modeled separately:** AI hardware (chips/GPUs), AI infrastructure (cloud), AI software & platforms, AI adoption (enterprise)
- **Taxonomy:** Function x end-market matrix (NLP/CV/GenAI/robotics/etc. crossed with healthcare/finance/manufacturing/consumer/etc.)
- **Geographic scope:** Regional breakdown — Global aggregate + US, Europe, China, Rest of World
- **Historical period:** 2010-present (~15 years of data)
- **Double-counting:** Allow segment overlap, document and quantify the overlap range — do not force strict allocation
- **Boundary documentation:** Both a YAML config file (drives the pipeline) AND a standalone METHODOLOGY.md (explains rationale for humans / LinkedIn paper)
- **Proxy indicators for AI activity:** AI patent filings (USPTO/EPO), VC/PE investment in AI, public company AI revenue segments, R&D expenditure in ICT (OECD/World Bank)
- **Deflation base year:** 2020 constant USD for all monetary series

### LSEG Data Strategy
- **Access level:** Full LSEG Workspace (desktop terminal + API)
- **Company universe:** TRBC classification — pull all companies classified under AI-related TRBC sector codes
- **Data types to ingest:** Company financials (revenue, R&D, margins), market indices (AI/tech sector), M&A and deals (AI acquisitions, deal values), sector classifications (TRBC/GICS codes)
- **Credentials:** Gitignored config file (not environment variables)

### Data Source Priority
- **Source hierarchy by indicator type:** Macro indicators from OECD/World Bank, company-level data from LSEG, patent data from OECD — each source for what it's best at
- **Missing data handling:** Interpolate (linear or spline) and flag as estimated — preserves time series continuity while maintaining transparency
- **Storage format:** Parquet for pipeline cache (columnar, type-safe)

### Claude's Discretion
- Data pipeline update frequency (on-demand vs. quarterly — based on source cadence)
- Specific OECD/World Bank indicator codes to use
- Exact interpolation method (linear vs. spline) — pick what's most appropriate per indicator
- Column naming conventions beyond the `_real_2020` suffix pattern
- Schema validation test framework choice
- YAML config file structure for industry definitions

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/PROJECT.md` — Project vision, core value, constraints (especially: documentation depth requirement, extensibility requirement)
- `.planning/REQUIREMENTS.md` — DATA-01 through DATA-08 and ARCH-01 requirements mapped to this phase
- `.planning/ROADMAP.md` — Phase 1 success criteria (5 criteria that must be TRUE)

### Research findings
- `.planning/research/STACK.md` — Technology stack: pandas 3.0, pandasdmx for OECD, uv for dependencies, Parquet storage
- `.planning/research/ARCHITECTURE.md` — FTI pattern, Cookiecutter DS structure, industry YAML config approach
- `.planning/research/PITFALLS.md` — Market boundary definition must be locked before data collection; schema validation critical; deflation pipeline non-negotiable
- `.planning/research/FEATURES.md` — Data pipeline is root dependency; data source attribution requirements

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None yet — Phase 1 establishes the foundational patterns for the entire project

### Integration Points
- Pipeline output (Parquet cache) will be consumed by Phase 2 (statistical modeling)
- Industry YAML config will be the extensibility mechanism for all future industries
- METHODOLOGY.md will feed into Phase 5 (LinkedIn paper)

</code_context>

<specifics>
## Specific Ideas

- LSEG TRBC classification is the methodological anchor for company selection — makes the approach reproducible and defensible
- The function x end-market matrix for AI taxonomy gives rich analytical angles for the methodology paper
- Allowing overlap between segments (with flagging) mirrors how professional research firms handle it — documenting this transparently is a differentiator vs. opaque industry reports
- The quant risk manager's insight ("valued by thumb") should be addressed directly in METHODOLOGY.md

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-data-foundation*
*Context gathered: 2026-03-17*
