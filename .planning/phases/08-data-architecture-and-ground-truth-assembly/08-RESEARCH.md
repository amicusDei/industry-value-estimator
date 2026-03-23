# Phase 8: Data Architecture and Ground Truth Assembly - Research

**Researched:** 2026-03-23
**Domain:** AI market boundary definition, analyst estimate corpus assembly, SEC EDGAR XBRL ingestion, ground truth time series reconciliation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Market Boundary Scope:**
- Multi-layer model: Model ALL value chain layers separately (hardware, infrastructure, software, adoption) and report each layer independently AND as a total
- Overlap handling: Report both overlapping values per layer, flag overlap zones, produce a separate "adjusted total" that subtracts documented overlap ranges — transparent, shows the analyst how the sausage is made
- Full scope mapping table required: For each analyst firm (IDC, Gartner, Grand View, Statista, etc.), document in ai.yaml + METHODOLOGY.md: what they include, what they exclude, which of our segments their number maps to, and their published figure
- Definitions are the most important part — boundary documentation must be thorough enough that any analyst can understand exactly what the model measures and how it compares to any published estimate

**Segment Structure:**
- v1.0 segments (hardware, infrastructure, software, adoption) may be kept or revised — Claude's discretion based on what best serves multi-layer reporting and analyst comparison
- Each segment must have a clear mapping to at least 2-3 published analyst category definitions

**Analyst Corpus Sourcing:**
- Sources: Free public sources (press releases, earnings transcripts, news coverage of analyst reports, Statista free tier) PLUS LSEG Workspace data and APIs (existing subscription access)
- Source count: 6-8 independent analyst sources minimum (IDC, Gartner, Grand View, Statista, Goldman Sachs, Bloomberg Intelligence, CB Insights, McKinsey)
- Vintage tracking: Full vintage series — track how estimates evolved over time (e.g., IDC's 2020 estimate as published in 2019, 2020, 2021). Enables analysis of analyst forecast accuracy itself
- Storage: Hand-curated YAML registry (human-readable, version-controlled, easy to review/edit) compiled to `market_anchors_ai.parquet` by the pipeline

**EDGAR Company Selection:**
- Selection criteria: Market cap leaders first, then fill gaps to ensure every value chain layer has at least 2-3 companies with filings
- Filing approach: Ingest whatever segment disclosures exist, flag companies where AI is bundled into larger segments (e.g., Microsoft Intelligent Cloud, Amazon AWS). Phase 10 handles the attribution math — Phase 8 just collects raw filings
- Filing depth: 5 years (2020-2024) — matches the period where AI revenue became meaningful in disclosures
- Library: edgartools (research recommendation) for 10-K/10-Q XBRL extraction

**Reconciliation Method:**
- Algorithm: Scope-normalized median — first normalize each estimate to our scope definition using the mapping table, then take median across sources per year/segment
- Gap handling: Linear interpolation between known data points, flagged as 'estimated' in the dataset (consistent with v1.0)
- Output format: Range — 25th percentile, median, 75th percentile of scope-normalized estimates per year/segment. Propagates source disagreement as uncertainty
- Currency: Store BOTH nominal USD and constant 2020 USD columns. Analyst estimates published in nominal; modeling uses real 2020 USD. Basic dashboard can show whichever is more intuitive

### Claude's Discretion
- Whether to revise the 4 v1.0 segments or keep them with added mappings
- Exact YAML schema for the analyst estimate registry
- Which specific XBRL tags to extract per company
- Specific 10-15 company list (guided by market cap + value chain coverage criteria)
- Interpolation method details (linear vs spline per indicator)
- How to structure the scope mapping table in ai.yaml

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-08 | Market boundary definition locked — explicit scope definition with documented mapping to how IDC, Gartner, and Grand View define their estimates | Scope mapping table pattern documented in Architecture Patterns section; ai.yaml extension schema provided |
| DATA-09 | Published analyst estimate corpus assembled — 10+ estimates per segment with vintage date, source firm, scope definition, and methodology notes | YAML registry schema, edgartools-independent pipeline pattern, and source list documented in Standard Stack and Code Examples |
| DATA-10 | Company filings ingestion via SEC EDGAR — 10-K/10-Q segment disclosures for 10-15 key public AI companies | edgartools 5.25.1 API patterns, XBRL concept names, company list guidance, and edgar.py module interface documented |
| DATA-11 | Historical ground truth time series assembled — yearly AI market size by segment (2017-2025) reconciled across sources into a single defensible series | Reconciliation algorithm, output schema, pandera validation, and audit trail pattern documented |
</phase_requirements>

---

## Summary

Phase 8 is an economic research and data engineering phase, not a modeling phase. Its job is to produce two locked, defensible artifacts before any model code in Phase 9 can run: (1) a market boundary definition that is documented in `config/industries/ai.yaml` and `docs/METHODOLOGY.md` before any data collection happens, and (2) a reconciled historical AI market size series in `data/processed/market_anchors_ai.parquet` with a complete audit trail.

The central challenge is definitional heterogeneity. Published AI market size estimates for 2025 range from approximately $254 billion (Grand View Research — AI software narrow scope) to $1.76 trillion (Gartner — all AI-adjacent infrastructure spending). This is not disagreement about facts; it is disagreement about what "the AI market" means. Every data collection task in this phase must start from the locked boundary definition, not the other way around. The scope-normalized median reconciliation algorithm cannot work unless scope normalization coefficients have been pre-computed from the mapping table in ai.yaml.

The EDGAR ingestion component (Plan 08-03) is technically independent and straightforward: edgartools 5.25.1 handles XBRL extraction directly. Phase 8 only collects raw segment disclosure filings; revenue attribution math is deferred to Phase 10. The output is `edgar_ai_companies.parquet` with raw XBRL revenue fields per company per period, with a `bundled_flag` column marking rows where AI revenue is embedded in a larger segment (e.g., Microsoft Azure, Amazon AWS). This avoids a scope decision that belongs in Phase 10.

The critical sequencing constraint for all four plans: the market boundary definition (Plan 08-01) must be committed to `config/industries/ai.yaml` before any analyst estimates are entered into the YAML registry (Plan 08-02) or any reconciliation logic is written (Plan 08-04). This is the sole prevention for Pitfall 1 (anchor estimate shopping).

**Primary recommendation:** Lock the scope mapping table in ai.yaml first, write a single `METHODOLOGY.md` section documenting why the chosen scope was selected over alternatives, then collect data. Never touch the boundary definition after Plan 08-01 is complete.

---

## Standard Stack

### Core (Phase 8 specific)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| edgartools | 5.25.1 | SEC EDGAR 10-K/10-Q XBRL ingestion — extracts segment revenue tags as typed DataFrames | Only Python-native library that converts EDGAR XBRL to DataFrames without an API key; enforces SEC's 10 req/s rate limit automatically; active weekly releases (5.25.1, March 19, 2026) |
| pyarrow | 23.0.1 | Parquet I/O with embedded schema metadata | Already in lock file (pyproject.toml); project standard for all Parquet writes with provenance metadata |
| pandera | 0.30.0 | DataFrame schema validation at ingestion boundaries | Already in lock file; project standard — existing PROCESSED_SCHEMA pattern extended with two new schemas |
| pyyaml | 6.0.3 | YAML registry read/write for analyst estimate corpus | Already in lock file; project config infrastructure already uses pyyaml |
| requests-cache | 1.3.1 | HTTP caching for edgartools and any supplementary web fetches | Already in lock file; prevents redundant EDGAR calls during development |

### Already in Lock File (no action needed)

| Library | Version | Purpose |
|---------|---------|---------|
| pandas | 3.0.1 | DataFrame manipulation; CoW-safe patterns required |
| scipy | 1.17.1 | `scipy.stats.percentileofscore`, `np.percentile` for 25th/75th/median reconciliation |
| python-dotenv | 1.2.2 | Environment variable management (LSEG credentials) |

### New Dependencies (must add)

| Library | Version | Purpose | Why Needed |
|---------|---------|---------|------------|
| edgartools | 5.25.1 | SEC EDGAR XBRL extraction | Not in pyproject.toml; Phase 8 is the first phase to use EDGAR |

**Installation (only new dependency):**
```bash
uv add "edgartools>=5.25.1"
uv sync
```

**Verify edgartools not already installed before adding:**
```bash
uv tree | grep edgartools
```

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| edgartools | sec-api.io Python client | Requires paid subscription for more than 100 API calls/month; edgartools is zero cost with the same XBRL coverage |
| edgartools | direct EDGAR REST API (data.sec.gov) | Works but requires manual XBRL namespace parsing, rate limit management, and CIK lookup; edgartools handles all three |
| Hand-curated YAML registry | Automated web scraping of analyst reports | Analyst reports are paywalled PDFs; scraping produces noisy, unverified data; hand curation is more credible for a methodology paper |
| scipy percentile for reconciliation | numpy percentile | Both valid; scipy.stats functions are more explicit about interpolation method — use `np.percentile` with `method='linear'` for consistency with v1.0 interpolation approach |

---

## Architecture Patterns

### Recommended Project Structure (Phase 8 additions only)

Phase 8 adds two new files and extends three existing ones. No new packages or directories are created in `src/`.

```
src/ingestion/
├── market_anchors.py       # NEW: loads YAML analyst registry → market_anchors_ai.parquet
└── edgar.py                # NEW: edgartools XBRL extraction → edgar_ai_companies.parquet

config/industries/
└── ai.yaml                 # EXTEND: add market_boundary, scope_mapping, and edgar_companies sections

data/raw/
├── market_anchors/         # NEW directory: ai_analyst_registry.yaml (hand-curated source)
└── edgar/                  # NEW directory: raw XBRL parquet per company

data/processed/
├── market_anchors_ai.parquet    # NEW: reconciled ground truth time series
└── edgar_ai_companies.parquet   # NEW: raw XBRL segment filings

docs/
└── METHODOLOGY.md          # NEW: scope mapping narrative — written in Plan 08-01

tests/
├── test_market_anchors.py  # NEW: validates market_anchors.py logic
└── test_edgar.py           # NEW: validates edgar.py ingestion logic
```

### Pattern 1: Analyst Estimate YAML Registry Schema

**What:** Hand-curated YAML file where each entry is one published estimate from one source for one year and one segment. The pipeline compiles this YAML to Parquet; the YAML is the human-readable audit record.

**When to use:** For all published analyst estimates (IDC, Gartner, Grand View, Goldman Sachs, McKinsey, etc.). Never store analyst estimates directly in code or as inline config values.

**Schema rationale:** `publication_year` tracks vintage (when the estimate was published, not the year estimated). `as_published_usd_billions` is nominal; deflation to real_2020 is done by the pipeline at compile time using the existing `deflate.py` module. `scope_segment_mapping` links each source's category to the project's segment IDs — this is what enables scope normalization.

```yaml
# data/raw/market_anchors/ai_analyst_registry.yaml

entries:
  - source_firm: "IDC"
    report_name: "Worldwide AI Spending Guide 2024"
    publication_year: 2024
    estimate_year: 2023        # The year being estimated
    segment: "total"           # total | ai_hardware | ai_infrastructure | ai_software | ai_adoption
    as_published_usd_billions: 207.0
    currency: "nominal_usd"
    scope_includes: "enterprise AI software, IT infrastructure, and services"
    scope_excludes: "consumer AI applications, general IT not AI-specific"
    scope_segment_mapping:
      # Which of our 4 segments does this estimate cover, and what fraction?
      ai_hardware: 0.0         # IDC excludes hardware in this guide
      ai_infrastructure: 0.40
      ai_software: 0.35
      ai_adoption: 0.25
    methodology_notes: "Vendor survey + secondary research. Narrow enterprise definition."
    source_url: "https://www.idc.com/..."
    confidence: "high"         # high | medium | low

  - source_firm: "Gartner"
    report_name: "Worldwide AI Spending Forecast 2025"
    publication_year: 2025
    estimate_year: 2025
    segment: "total"
    as_published_usd_billions: 1500.0
    currency: "nominal_usd"
    scope_includes: "all AI-related technology spending including infrastructure"
    scope_excludes: "nothing explicitly excluded — broadest definition"
    scope_segment_mapping:
      ai_hardware: 0.35
      ai_infrastructure: 0.30
      ai_software: 0.20
      ai_adoption: 0.15
    methodology_notes: "Includes all AI-adjacent spend; broadest definition. Not comparable to IDC without normalization."
    source_url: "https://www.gartner.com/..."
    confidence: "high"
```

### Pattern 2: market_anchors.py Module Interface

**What:** An ingestion module that reads the YAML registry, deflates nominal values to real 2020 USD, and writes `market_anchors_ai.parquet`. Follows the exact same interface as `world_bank.py` and `oecd.py` — returns a validated DataFrame, writes to `data/processed/`.

**When to use:** Called from `pipeline.py` as a new step in `run_full_pipeline()`.

```python
# src/ingestion/market_anchors.py

import yaml
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from datetime import datetime, timezone

from config.settings import DATA_RAW, DATA_PROCESSED


def load_analyst_registry(registry_path: Path) -> pd.DataFrame:
    """
    Load and compile the hand-curated analyst estimate YAML registry into a DataFrame.

    Returns DataFrame with columns:
        source_firm, report_name, publication_year, estimate_year, segment,
        as_published_usd_billions (nominal), currency, scope_includes, scope_excludes,
        scope_segment_mapping (dict), methodology_notes, source_url, confidence
    """
    with open(registry_path) as f:
        data = yaml.safe_load(f)
    return pd.DataFrame(data["entries"])


def compile_market_anchors(industry_id: str = "ai") -> Path:
    """
    Compile analyst registry YAML to market_anchors_{industry_id}.parquet.

    Steps:
    1. Load YAML registry from data/raw/market_anchors/{industry_id}_analyst_registry.yaml
    2. Expand scope_segment_mapping rows to one row per (estimate_year, segment)
    3. Deflate as_published_usd_billions to real_2020 using existing deflate_to_base_year()
    4. Add 25th/median/75th percentile columns per (estimate_year, segment) group
    5. Write to data/processed/market_anchors_{industry_id}.parquet with provenance metadata

    Returns Path to written Parquet file.
    """
    ...


def validate_market_anchors(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate compiled market anchors against MARKET_ANCHOR_SCHEMA (pandera).
    Called after compile_market_anchors, before writing to processed layer.
    """
    ...
```

### Pattern 3: edgar.py Module Interface

**What:** An ingestion module that uses edgartools to fetch 10-K/10-Q XBRL segment revenue for a configured list of AI companies. Each company is fetched by CIK (from config), and results are written to `edgar_ai_companies.parquet`. A `bundled_flag` column marks companies where AI revenue is embedded in a larger segment.

**When to use:** Called from `pipeline.py` as a new step. Runs after market_anchors step.

**Important scoping note:** Phase 8 collects raw XBRL filings only. The `bundled_flag` is a boolean indicator that signals to Phase 10 that this row requires attribution math — Phase 8 does not attempt to estimate AI-specific revenue from bundled segments.

```python
# src/ingestion/edgar.py

from edgar import Company, set_identity
import pandas as pd
from pathlib import Path


def set_edgar_identity(email: str) -> None:
    """
    Set the SEC EDGAR user agent identity (required by SEC rules).
    Call once before any EDGAR fetch.
    edgartools enforces SEC's 10 req/s rate limit internally.

    Source: https://edgartools.readthedocs.io/
    """
    set_identity(email)


def fetch_company_filings(
    cik: str,
    company_name: str,
    form_types: list[str],
    start_year: int,
    end_year: int,
    xbrl_concepts: list[str],
) -> pd.DataFrame:
    """
    Fetch XBRL segment revenue data for a single company.

    Parameters
    ----------
    cik : str
        SEC CIK number (10-digit, zero-padded). From edgar_companies config.
    company_name : str
        Human-readable name for logging and output.
    form_types : list[str]
        ["10-K", "10-Q"] — both annual and quarterly filings.
    start_year : int
        First year to fetch (inclusive). Phase 8: 2020.
    end_year : int
        Last year to fetch (inclusive). Phase 8: 2024.
    xbrl_concepts : list[str]
        XBRL concept names to extract. See XBRL_CONCEPTS constant below.

    Returns
    -------
    pd.DataFrame
        One row per (company, period, form_type, xbrl_concept).
        Columns: cik, company_name, period_end, form_type, xbrl_concept, value_usd,
                 value_unit, bundled_flag, segment_label
    """
    ...


# Standard XBRL concepts to extract for AI company revenue
XBRL_CONCEPTS = [
    "us-gaap:Revenues",
    "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
    "us-gaap:SegmentReportingInformationRevenue",
    "us-gaap:SalesRevenueNet",
]

# Companies where AI revenue is bundled into a larger segment (require Phase 10 attribution)
BUNDLED_SEGMENT_COMPANIES = {
    "0000789019",  # Microsoft — AI in Azure/M365 segments
    "0001018724",  # Amazon — AI in AWS segment
    "0001652044",  # Alphabet — AI in Google Cloud and Search
    "0001326801",  # Meta — AI enhances ad revenue but not separately disclosed
    "0000051143",  # IBM — AI in Consulting and Software segments
}
```

### Pattern 4: ai.yaml Extension — Market Boundary Section

**What:** The `config/industries/ai.yaml` file is extended with three new top-level sections. The `market_boundary` section is the locked definition. The `scope_mapping_table` section maps each analyst firm to our segments. The `edgar_companies` section lists the 10-15 companies to ingest.

**When to use:** Written first in Plan 08-01, before any data collection. Never modified after Plan 08-01 is merged.

```yaml
# config/industries/ai.yaml — new sections to add after existing content

# ============================================================
# MARKET BOUNDARY DEFINITION (locked in Plan 08-01)
# DO NOT MODIFY after initial commit — changing this invalidates
# all downstream reconciliation decisions.
# ============================================================
market_boundary:
  definition_locked: "2026-03-XX"   # date of commit
  scope_statement: >
    AI software platforms, AI infrastructure (cloud compute dedicated to AI workloads,
    AI-specific hardware), and AI services/consulting. Excludes: general IT infrastructure
    not dedicated to AI workloads, AI-enabled consumer products where AI is embedded
    (e.g., smartphone cameras), and general enterprise software with AI features added.
  closest_analyst_match: "IDC Worldwide AI Spending Guide (enterprise narrow scope)"
  rationale: >
    IDC's enterprise-narrow definition is chosen over Gartner's broad definition because
    it excludes general IT infrastructure overlap and is the definition most commonly
    cited in financial analysis contexts. Gartner's $1.5T estimate is documented in the
    scope_mapping_table with its adjustment coefficient.
  overlap_zones:
    - hardware_to_infrastructure: "GPU revenue counted in ai_hardware and again as cloud
        infrastructure cost — documented range: 20-30% of ai_infrastructure is hardware passthrough"
    - software_to_adoption: "Enterprise AI SaaS licenses counted in ai_software and again
        as enterprise deployment spend — documented range: 15-25% of ai_adoption"

scope_mapping_table:
  # For each analyst firm: scope match coefficient, what they include/exclude,
  # which segments their total maps to, and published figure per available year.
  - firm: "IDC"
    report_series: "Worldwide AI Spending Guide"
    scope_alignment: "close"   # close | partial | broad
    scope_coefficient: 1.0     # multiplier to normalize to our scope (1.0 = no adjustment needed)
    includes: "enterprise AI software, infrastructure, services"
    excludes: "consumer AI, general IT"
    segment_coverage: ["ai_infrastructure", "ai_software", "ai_adoption"]
    known_estimates:
      - year: 2023
        as_published_usd_billions: 207.0
        publication_year: 2024

  - firm: "Gartner"
    report_series: "Worldwide AI Spending Forecast"
    scope_alignment: "broad"
    scope_coefficient: 0.18    # Gartner's $1.5T → our ~$270B equivalent (broad-to-narrow adjustment)
    includes: "all AI-adjacent technology spending"
    excludes: "nothing explicitly"
    segment_coverage: ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]
    known_estimates:
      - year: 2025
        as_published_usd_billions: 1500.0
        publication_year: 2025

edgar_companies:
  - name: "NVIDIA Corporation"
    cik: "0001045810"
    ticker: "NVDA"
    value_chain_layer: "ai_hardware"
    ai_disclosure_type: "direct"   # direct | bundled | partial
    primary_ai_segment: "Data Center"
    notes: "Data Center segment ~91% AI revenue in FY2026; most direct AI hardware disclosure"

  - name: "Microsoft Corporation"
    cik: "0000789019"
    ticker: "MSFT"
    value_chain_layer: "ai_infrastructure"
    ai_disclosure_type: "bundled"
    primary_ai_segment: "Intelligent Cloud (Azure)"
    bundled_in: "Intelligent Cloud revenue — Azure AI portion requires Phase 10 attribution"
    notes: "Reports $13B AI annual run rate in management commentary; not a separate XBRL segment"

  - name: "Alphabet Inc."
    cik: "0001652044"
    ticker: "GOOGL"
    value_chain_layer: "ai_infrastructure"
    ai_disclosure_type: "bundled"
    primary_ai_segment: "Google Cloud"
    bundled_in: "Google Cloud revenue — AI portion requires Phase 10 attribution"

  - name: "Amazon.com Inc."
    cik: "0001018724"
    ticker: "AMZN"
    value_chain_layer: "ai_infrastructure"
    ai_disclosure_type: "bundled"
    primary_ai_segment: "AWS"
    bundled_in: "AWS revenue — AI portion requires Phase 10 attribution"

  - name: "Meta Platforms Inc."
    cik: "0001326801"
    ticker: "META"
    value_chain_layer: "ai_adoption"
    ai_disclosure_type: "bundled"
    primary_ai_segment: "Family of Apps (ad revenue)"
    bundled_in: "Ad revenue enhancement — requires Phase 10 attribution"

  - name: "Advanced Micro Devices Inc."
    cik: "0000002488"
    ticker: "AMD"
    value_chain_layer: "ai_hardware"
    ai_disclosure_type: "partial"
    primary_ai_segment: "Data Center"
    notes: "Data Center segment includes AI GPUs but also EPYC server CPUs"

  - name: "Salesforce Inc."
    cik: "0001108524"
    ticker: "CRM"
    value_chain_layer: "ai_software"
    ai_disclosure_type: "partial"
    primary_ai_segment: "Platform and Other (Agentforce)"
    notes: "Einstein AI and Agentforce revenue disclosed in earnings commentary; partial XBRL"

  - name: "ServiceNow Inc."
    cik: "0001373715"
    ticker: "NOW"
    value_chain_layer: "ai_software"
    ai_disclosure_type: "partial"
    primary_ai_segment: "Subscription revenues"
    notes: "AI products embedded in platform subscription; growing explicit disclosure"

  - name: "Palantir Technologies Inc."
    cik: "0001321655"
    ticker: "PLTR"
    value_chain_layer: "ai_software"
    ai_disclosure_type: "direct"
    primary_ai_segment: "Commercial (AIP platform)"
    notes: "AI Platform (AIP) revenue growing; most explicit pure-play software AI disclosure"

  - name: "C3.ai Inc."
    cik: "0001577552"
    ticker: "AI"
    value_chain_layer: "ai_software"
    ai_disclosure_type: "direct"
    primary_ai_segment: "Subscription and professional services"
    notes: "AI pure-play; 100% of revenue is AI — clearest segment anchor"
```

### Pattern 5: Reconciliation Algorithm (Plan 08-04)

**What:** Scope-normalized median reconciliation. Each estimate is first adjusted to our scope definition using the `scope_coefficient` from the mapping table, then the distribution (25th, 50th, 75th percentile) is computed per (year, segment) group.

**When to use:** Applied in `market_anchors.py::compile_market_anchors()` after all estimates are loaded.

```python
# src/ingestion/market_anchors.py — reconciliation logic

import numpy as np
import pandas as pd


def scope_normalize(
    as_published_usd_billions: float,
    scope_coefficient: float,
) -> float:
    """
    Adjust a published estimate to our scope definition.
    scope_coefficient = our_scope / their_scope.
    e.g., Gartner $1500B × 0.18 = $270B in our scope.
    """
    return as_published_usd_billions * scope_coefficient


def reconcile_by_segment_year(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute 25th/median/75th percentile of scope-normalized estimates
    per (estimate_year, segment) group.

    Input df must have columns:
        estimate_year, segment, scope_normalized_usd_billions, source_firm, confidence

    Returns df with columns:
        estimate_year, segment,
        p25_usd_billions, median_usd_billions, p75_usd_billions,
        n_sources, source_list

    Uses np.percentile with method='linear' (consistent with v1.0 interpolation approach).
    """
    records = []
    for (year, segment), group in df.groupby(["estimate_year", "segment"]):
        values = group["scope_normalized_usd_billions"].dropna().values
        if len(values) == 0:
            continue
        records.append({
            "estimate_year": year,
            "segment": segment,
            "p25_usd_billions_nominal": float(np.percentile(values, 25, method="linear")),
            "median_usd_billions_nominal": float(np.percentile(values, 50, method="linear")),
            "p75_usd_billions_nominal": float(np.percentile(values, 75, method="linear")),
            "n_sources": len(values),
            "source_list": "|".join(sorted(group["source_firm"].tolist())),
            "estimated_flag": False,   # real observations
        })
    return pd.DataFrame(records)


def interpolate_gaps(df: pd.DataFrame, full_year_range: range) -> pd.DataFrame:
    """
    Linear interpolation for years with no analyst estimate coverage.
    Fills gaps in (segment, year) combinations using adjacent real data points.
    Sets estimated_flag=True for all interpolated rows.
    Consistent with v1.0 interpolate.py approach.
    """
    ...
```

### Pattern 6: Pipeline Integration

**What:** The two new ingestion modules are added as steps in `run_full_pipeline()` in `pipeline.py`. The existing error-isolated try/except pattern applies unchanged.

```python
# src/ingestion/pipeline.py — addition to run_full_pipeline()

# Step N: Ingest market anchors (YAML registry → Parquet)
try:
    from src.ingestion.market_anchors import compile_market_anchors, validate_market_anchors
    anchors_path = compile_market_anchors(industry_id)
    processed_paths["market_anchors"] = anchors_path
except Exception as e:
    print(f"Market anchors compilation failed: {e}")

# Step N+1: Ingest EDGAR company filings
try:
    from src.ingestion.edgar import fetch_all_edgar_companies, save_raw_edgar
    edgar_df = fetch_all_edgar_companies(config)
    save_raw_edgar(edgar_df, industry_id)
    edgar_processed = normalize_edgar(edgar_df, config)
    edgar_path = write_processed_parquet(
        edgar_processed,
        f"edgar_{industry_id}_companies.parquet",
        source="edgar",
        industry_id=industry_id,
    )
    processed_paths["edgar"] = edgar_path
except Exception as e:
    print(f"EDGAR ingestion failed: {e}")
```

### Pattern 7: Pandera Schema Extensions

**What:** Two new pandera schemas are added to `validate.py`. The PROCESSED_SCHEMA's `source` column `Check.isin` list must be updated to include `"market_anchors"` and `"edgar"`.

```python
# src/processing/validate.py — new schemas to add

MARKET_ANCHOR_SCHEMA = DataFrameSchema(
    {
        "estimate_year": Column(int, Check.in_range(2017, 2026)),
        "segment": Column(
            str,
            Check.isin(["total", "ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]),
        ),
        "p25_usd_billions_nominal": Column(float, Check.greater_than(0), nullable=False),
        "median_usd_billions_nominal": Column(float, Check.greater_than(0), nullable=False),
        "p75_usd_billions_nominal": Column(float, Check.greater_than(0), nullable=False),
        "p25_usd_billions_real_2020": Column(float, Check.greater_than(0), nullable=False),
        "median_usd_billions_real_2020": Column(float, Check.greater_than(0), nullable=False),
        "p75_usd_billions_real_2020": Column(float, Check.greater_than(0), nullable=False),
        "n_sources": Column(int, Check.greater_than_or_equal_to(1)),
        "source_list": Column(str, nullable=False),
        "estimated_flag": Column(bool, nullable=False),
    },
    coerce=True,
    strict=False,
)


EDGAR_RAW_SCHEMA = DataFrameSchema(
    {
        "cik": Column(str, nullable=False),
        "company_name": Column(str, nullable=False),
        "period_end": Column(str, nullable=False),   # YYYY-MM-DD string from edgartools
        "form_type": Column(str, Check.isin(["10-K", "10-Q"])),
        "xbrl_concept": Column(str, nullable=False),
        "value_usd": Column(float, nullable=True),   # nullable: some filings lack segment tags
        "bundled_flag": Column(bool, nullable=False),
        "value_chain_layer": Column(
            str,
            Check.isin(["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]),
        ),
    },
    coerce=True,
    strict=False,
)
```

### Anti-Patterns to Avoid

- **Collecting analyst estimates before locking the boundary definition:** The boundary definition is not configuration for the data collection step — it IS the first deliverable. Any analyst estimate collected without a locked boundary definition is contaminated by anchor shopping risk.
- **Storing scope coefficients as calculated values in code:** Scope coefficients belong in `ai.yaml` `scope_mapping_table`, not in Python code. They are editorial decisions with documented rationale, not computed values.
- **Treating `bundled_flag=True` rows as requiring Phase 8 resolution:** Phase 8 collects the raw filing data and sets the flag. The attribution math happens in Phase 10. Adding partial attribution estimates in Phase 8 pre-empts Phase 10 design decisions.
- **Using edgartools `Company.get_filings()` without setting user identity first:** SEC requires a user-agent email header. `set_identity(email)` must be called before any EDGAR fetch or requests will be rejected with 403.
- **Writing analyst estimates directly as floats in ai.yaml without vintage metadata:** Every estimate in the YAML registry must have `publication_year`, `estimate_year`, `source_url`, and `methodology_notes`. Bare floats with no provenance are never acceptable (documented in project's technical debt patterns).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| EDGAR XBRL parsing and rate limiting | Custom data.sec.gov REST scraper | edgartools 5.25.1 | EDGAR XBRL has namespaces, company-specific tag variations, and filing schema changes across years; edgartools handles all of these; also auto-enforces 10 req/s SEC limit |
| Parquet metadata embedding | Custom metadata tracking via sidecar JSON | `pa.Table.replace_schema_metadata()` | Project already uses this pattern in `world_bank.py`; consistent provenance metadata without extra files |
| DataFrame schema validation | `assert` statements or custom validation functions | pandera DataFrameSchema | Project already has 3 schemas in `validate.py`; pandera produces human-readable error messages that match the existing pattern |
| Nominal-to-real deflation for analyst estimates | Custom deflation logic in market_anchors.py | `src/processing/deflate.py::apply_deflation()` | The deflate module is already tested (233 passing tests includes deflation tests); re-using it is correct; re-implementing it introduces inconsistency |
| CSV/JSON for analyst registry | Flat files | Hand-curated YAML + pipeline compilation to Parquet | YAML is human-readable for editorial review; Parquet is machine-readable for pipeline; the two-file approach matches the project's existing config-driven architecture |
| Gap filling with custom interpolation | Custom interpolation implementation | `src/processing/interpolate.py` extended | Already implemented and tested for v1.0 data gaps; same linear interpolation logic applies to analyst estimate gaps; wrap with `estimated_flag=True` |

**Key insight:** This phase is primarily editorial and research work, not engineering. The engineering is a thin wrapper around existing project infrastructure. Every ingestion module follows the same interface (`fetch_X() → validate → write_processed_parquet()`), every YAML uses the same config-driven pattern, and every Parquet file uses the same provenance metadata embedding. The novel work is the economic analysis: evaluating analyst methodologies, deciding scope coefficients, and writing the METHODOLOGY.md rationale.

---

## Common Pitfalls

### Pitfall 1: Anchor Estimate Shopping
**What goes wrong:** Analyst estimates for AI market size range from ~$254B (Grand View narrow scope) to $1.76T (Gartner broad) for the same year. Collecting data before locking the boundary definition produces a corpus biased toward whichever estimates make the model output look plausible.
**Why it happens:** Multiple credible sources exist; the temptation is to start with data collection and decide on scope later.
**How to avoid:** Plan 08-01 must be a separate committed deliverable (ai.yaml `market_boundary` section + METHODOLOGY.md) before any analyst estimates are entered in Plan 08-02. Write a CI check: if `market_boundary.definition_locked` is not present in ai.yaml, the pipeline build fails.
**Warning signs:** Plan 08-02 work starts before Plan 08-01 is merged; `scope_coefficient` values in the registry are derived from model output rather than analytical comparison of source methodologies.

### Pitfall 2: Nominal/Real Conflation
**What goes wrong:** Analyst estimates are published in nominal USD for their publication year. If these are stored without deflation and downstream code treats them as real 2020 USD, a 2017 estimate of $20B (nominal) is compared directly to a 2023 estimate of $200B (nominal), inflating apparent CAGR.
**Why it happens:** The deflation step is easy to forget when the data appears to be "just a number from a report."
**How to avoid:** Follow the existing project convention: store the `as_published_usd_billions` column (nominal), run `apply_deflation()` from `deflate.py` during `compile_market_anchors()`, and produce both `_nominal` and `_real_2020` output columns. The `check_no_nominal_columns()` guard in `validate_processed()` catches any nominal columns reaching the processed layer.
**Warning signs:** Column named `usd_billions` without `_nominal` or `_real_2020` suffix in any intermediate DataFrame.

### Pitfall 3: edgartools Identity Not Set
**What goes wrong:** `edgar.Company()` calls succeed locally but return 403 errors in fresh environments because `set_identity()` was not called.
**Why it happens:** The SEC requires a `User-Agent: name email` header for all EDGAR API calls. edgartools documents this but it is easy to miss in development where a cached session may have been established.
**How to avoid:** `set_identity(os.environ["EDGAR_USER_EMAIL"])` must be the first call in `edgar.py` before any `Company()` instantiation. Store `EDGAR_USER_EMAIL` in `.env` and load with `python-dotenv`.
**Warning signs:** Tests pass locally but fail in CI with 403; `EDGAR_USER_EMAIL` not in `.env.example`.

### Pitfall 4: XBRL Tag Inconsistency Across Companies and Years
**What goes wrong:** Some companies use `us-gaap:Revenues`, others use `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`. Companies sometimes change XBRL tags between fiscal years after accounting standard changes. A rigid tag extraction that only looks for one concept will silently produce NaN rows for companies using an alternative concept.
**Why it happens:** XBRL is a reporting standard, not a uniform schema — companies have discretion in tag choice within the standard.
**How to avoid:** Extract all concepts in the `XBRL_CONCEPTS` list per company; for each company/period, keep the first non-null value across concepts in priority order. Log which concept was used for each company/period in a `xbrl_concept_used` column — this creates the audit trail for why some companies have revenue from a different tag.
**Warning signs:** `value_usd` column has more NaN than expected; no `xbrl_concept_used` column in output.

### Pitfall 5: Scope Coefficient Precision Illusion
**What goes wrong:** Assigning `scope_coefficient: 0.18` to Gartner implies that exactly 18% of Gartner's estimate is in our scope. But this coefficient is itself an estimate with uncertainty — different analysts decompose the Gartner total differently.
**Why it happens:** The YAML schema encourages a single float value; there is no explicit uncertainty field for scope coefficients.
**How to avoid:** Add `scope_coefficient_range: [low, high]` to the scope_mapping_table entries for any firm with `scope_alignment: "broad"` or `"partial"`. The reconciliation algorithm should produce a sensitivity output showing how the final percentile estimates change when scope coefficients are varied across their ranges. Document this sensitivity in METHODOLOGY.md.
**Warning signs:** A single scope_coefficient float with no range for broad-scope firms; no sensitivity analysis in METHODOLOGY.md.

---

## Code Examples

Verified patterns from official sources and existing project code:

### edgartools — Basic Company Filing Fetch
```python
# Source: https://edgartools.readthedocs.io/
from edgar import Company, set_identity

set_identity("your.name@email.com")   # Required; SEC User-Agent header

company = Company("0001045810")       # NVIDIA by CIK
filings = company.get_filings(form="10-K")
filing = filings[0]                    # Most recent 10-K

# Access XBRL financial statements
xbrl = filing.xbrl()
revenues = xbrl.facts.query("us-gaap:Revenues")  # Returns DataFrame
```

### edgartools — Segment Revenue Extraction
```python
# Source: edgartools documentation — XBRL concept query
from edgar import Company, set_identity

set_identity("your.name@email.com")

company = Company("0001045810")  # NVIDIA
filings = company.get_filings(form="10-K", date="2020-01-01:2025-01-01")

records = []
for filing in filings:
    try:
        xbrl = filing.xbrl()
        # Try primary revenue concepts in priority order
        for concept in [
            "us-gaap:Revenues",
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            "us-gaap:SegmentReportingInformationRevenue",
        ]:
            facts = xbrl.facts.query(concept)
            if facts is not None and len(facts) > 0:
                for _, row in facts.iterrows():
                    records.append({
                        "cik": company.cik,
                        "period_end": str(row.get("period", "")),
                        "form_type": filing.form,
                        "xbrl_concept": concept,
                        "value_usd": row.get("value"),
                        "xbrl_concept_used": concept,
                    })
                break  # Use first matching concept
    except Exception as e:
        print(f"XBRL extraction failed for {filing}: {e}")
        # Continue to next filing — do not abort pipeline
```

### Parquet Write with Provenance Metadata (existing project pattern)
```python
# Source: src/ingestion/world_bank.py (existing pattern — replicate for new modules)
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime, timezone

table = pa.Table.from_pandas(df, preserve_index=False)
existing_meta = table.schema.metadata or {}
custom_meta = {
    b"source": b"market_anchors",
    b"industry": industry_id.encode(),
    b"fetched_at": datetime.now(tz=timezone.utc).isoformat().encode(),
    b"registry_path": registry_path.as_posix().encode(),
}
table = table.replace_schema_metadata({**existing_meta, **custom_meta})
pq.write_table(table, output_path, compression="snappy")
```

### Pandera Schema Validation (existing project pattern)
```python
# Source: src/processing/validate.py (existing pattern — replicate for new schemas)
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check

MARKET_ANCHOR_SCHEMA = DataFrameSchema(
    {
        "estimate_year": Column(int, Check.in_range(2017, 2026)),
        "segment": Column(str, Check.isin(["total", "ai_hardware", ...])),
        "median_usd_billions_real_2020": Column(float, Check.greater_than(0)),
        "estimated_flag": Column(bool, nullable=False),
    },
    coerce=True,
    strict=False,
)

def validate_market_anchors(df):
    return MARKET_ANCHOR_SCHEMA.validate(df)
```

### Scope-Normalized Median Reconciliation
```python
# src/ingestion/market_anchors.py — reconciliation core
import numpy as np
import pandas as pd


def reconcile_estimates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Scope-normalize and compute percentile distribution per (estimate_year, segment).
    df must contain: estimate_year, segment, as_published_usd_billions, scope_coefficient
    """
    df = df.copy()
    df["scope_normalized_usd_billions"] = (
        df["as_published_usd_billions"] * df["scope_coefficient"]
    )

    records = []
    for (year, segment), group in df.groupby(["estimate_year", "segment"]):
        vals = group["scope_normalized_usd_billions"].dropna().values
        if len(vals) == 0:
            continue
        records.append({
            "estimate_year": year,
            "segment": segment,
            "p25_usd_billions_nominal": float(np.percentile(vals, 25, method="linear")),
            "median_usd_billions_nominal": float(np.percentile(vals, 50, method="linear")),
            "p75_usd_billions_nominal": float(np.percentile(vals, 75, method="linear")),
            "n_sources": len(vals),
            "source_list": "|".join(sorted(group["source_firm"].tolist())),
            "estimated_flag": False,
        })
    return pd.DataFrame(records)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| v1.0 value chain multiplier (PCA index × single anchor) | Multi-source scope-normalized median reconciliation with uncertainty range | Phase 8 (this phase) | Replaces single-point anchor with defensible distribution; enables uncertainty propagation to Phase 9 model |
| Single anchor value in ai.yaml | Full vintage series YAML registry compiled to Parquet | Phase 8 | Enables analyst forecast accuracy analysis as a feature; captures how estimates evolved over time |
| No EDGAR data in pipeline | edgartools XBRL extraction to Parquet | Phase 8 | Provides company-level raw revenue data that Phase 10 attribution uses as primary source |
| PROCESSED_SCHEMA with 3 sources (world_bank, oecd, lseg) | PROCESSED_SCHEMA extended with market_anchors and edgar | Phase 8 | Pipeline validation covers all new data sources |

**Deprecated/outdated:**
- `value_chain` section in ai.yaml (the `anchor_year`, `anchor_value_usd_billions`, `multiplier_method`, `segment_anchor_shares`, `usd_floor_billions` keys): Replaced entirely by the new `market_boundary` + `scope_mapping_table` + analyst YAML registry approach. Do NOT delete this section in Phase 8 — deletion happens in Phase 9 when the model rework is complete.

---

## Open Questions

1. **Scope coefficient for Grand View Research and McKinsey**
   - What we know: Grand View Research reports AI market at $244B-$390B for 2025 (narrow-to-medium software scope); McKinsey reports at different scopes in different papers.
   - What's unclear: Whether Grand View's scope is close enough to IDC's enterprise narrow scope to warrant `scope_coefficient ≈ 1.0` or whether adjustment is needed.
   - Recommendation: During Plan 08-01 scope mapping work, compare Grand View's "AI market" methodology description directly against IDC's. If scope definitions overlap >80%, use coefficient 0.95-1.05. If there is a systematic inclusion difference (e.g., Grand View includes AI-enhanced consumer software), calibrate the coefficient explicitly with a documented rationale line in METHODOLOGY.md.

2. **LSEG TRBC code coverage for edgar_companies**
   - What we know: Existing ai.yaml has LSEG TRBC codes for hardware and internet software. Some edgar_companies (Palantir, ServiceNow, C3.ai) may not be in the existing LSEG pull.
   - What's unclear: Whether extending the LSEG TRBC list to cover these companies is in scope for Phase 8 or deferred to Phase 10 (when LSEG data is attributed).
   - Recommendation: Phase 8 scope — add TRBC codes for new edgar_companies to ai.yaml `lseg.trbc_codes` section so the existing LSEG ingestion covers them. This is one YAML change, not a new module.

3. **EDGAR CIK accuracy for international AI companies (Baidu, TSMC)**
   - What we know: The CONTEXT.md company selection criteria says "market cap leaders first, then fill gaps per value chain layer." Baidu and TSMC are relevant for ai_hardware (TSMC manufactures AI chips) and ai_software/adoption (Baidu AI Cloud).
   - What's unclear: Baidu and TSMC file 20-F (foreign private issuer) not 10-K. edgartools supports 20-F; the `form_types` list in edgar.py must include "20-F" for these companies.
   - Recommendation: Include TSMC (ai_hardware coverage) and Baidu (China regional coverage) with `form_types: ["20-F"]`. Check that edgartools XBRL extraction works for 20-F filings — the XBRL concepts are the same standard but filing structure differs slightly.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (no separate pytest.ini) |
| Quick run command | `uv run pytest tests/test_market_anchors.py tests/test_edgar.py -v` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-08 | ai.yaml contains `market_boundary.definition_locked` key | unit | `uv run pytest tests/test_config.py::TestMarketBoundary -x` | ❌ Wave 0 |
| DATA-08 | scope_mapping_table has entries for IDC, Gartner, Grand View | unit | `uv run pytest tests/test_config.py::TestScopeMapping -x` | ❌ Wave 0 |
| DATA-09 | YAML registry has 10+ entries across years 2017-2025 | unit | `uv run pytest tests/test_market_anchors.py::TestAnalystRegistry -x` | ❌ Wave 0 |
| DATA-09 | market_anchors_ai.parquet passes MARKET_ANCHOR_SCHEMA validation | unit | `uv run pytest tests/test_market_anchors.py::TestMarketAnchorSchema -x` | ❌ Wave 0 |
| DATA-09 | All Parquet rows have source_list with 3+ sources per year | unit | `uv run pytest tests/test_market_anchors.py::TestSourceCoverage -x` | ❌ Wave 0 |
| DATA-09 | No nominal columns in market_anchors_ai.parquet | unit | `uv run pytest tests/test_market_anchors.py::TestNoNominalColumns -x` | ❌ Wave 0 |
| DATA-10 | edgar_ai_companies.parquet passes EDGAR_RAW_SCHEMA validation | unit | `uv run pytest tests/test_edgar.py::TestEdgarSchema -x` | ❌ Wave 0 |
| DATA-10 | edgar output has rows for all 10+ configured companies | unit | `uv run pytest tests/test_edgar.py::TestCompanyCoverage -x` | ❌ Wave 0 |
| DATA-10 | bundled_flag correctly set per BUNDLED_SEGMENT_COMPANIES list | unit | `uv run pytest tests/test_edgar.py::TestBundledFlag -x` | ❌ Wave 0 |
| DATA-11 | Reconciled series covers 2017-2025 without gaps after interpolation | unit | `uv run pytest tests/test_market_anchors.py::TestYearCoverage -x` | ❌ Wave 0 |
| DATA-11 | estimated_flag=True for all interpolated years | unit | `uv run pytest tests/test_market_anchors.py::TestEstimatedFlag -x` | ❌ Wave 0 |
| DATA-11 | p25 <= median <= p75 for all (year, segment) rows | unit | `uv run pytest tests/test_market_anchors.py::TestPercentileOrder -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_market_anchors.py tests/test_edgar.py tests/test_config.py -q`
- **Per wave merge:** `uv run pytest -q` (full 233-test suite + new tests)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_market_anchors.py` — covers DATA-09 and DATA-11 requirements (YAML registry loading, scope normalization, reconciliation, deflation, gap filling, schema validation)
- [ ] `tests/test_edgar.py` — covers DATA-10 requirements (edgartools interface, company coverage, bundled_flag, schema validation) — uses mocked edgartools calls to avoid live EDGAR access in CI
- [ ] `tests/test_config.py` extension — add `TestMarketBoundary` and `TestScopeMapping` test classes for DATA-08 (ai.yaml structural validation for new sections)
- [ ] `data/raw/market_anchors/` directory creation — `market_anchors.py` and `edgar.py` write here; directory must exist before first pipeline run

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `src/ingestion/pipeline.py`, `src/processing/validate.py`, `src/processing/deflate.py`, `config/industries/ai.yaml`, `pyproject.toml`, `tests/` (233 passing tests) — 2026-03-23
- `.planning/research/STACK.md` — edgartools 5.25.1 verified via PyPI official; all version compatibility confirmed
- `.planning/research/ARCHITECTURE.md` — component responsibility table, build order, integration points
- `.planning/research/PITFALLS.md` — all 12 pitfalls with prevention strategies; anchor shopping and boundary inconsistency as HIGH recovery cost
- `.planning/research/FEATURES.md` — feature dependency tree confirming ground truth corpus as critical path
- [edgartools PyPI v5.25.1, March 19, 2026](https://pypi.org/project/edgartools/) — current version confirmed
- [edgartools documentation](https://edgartools.readthedocs.io/) — `set_identity()`, Company API, XBRL concept extraction
- [pandera documentation](https://pandera.readthedocs.io/) — DataFrameSchema API used in existing project

### Secondary (MEDIUM confidence)
- `.planning/research/SUMMARY.md` — Phase 8 build order rationale, research flag for ground truth assembly
- [Gartner: Worldwide AI Spending $1.5T 2025](https://www.gartner.com/en/newsroom/press-releases/2025-09-17-gartner-says-worldwide-ai-spending-will-total-1-point-5-trillion-in-2025) — broad scope anchor reference (scope_coefficient derivation)
- [Grand View Research: AI Market 2025](https://www.grandviewresearch.com/industry-analysis/artificial-intelligence-ai-market) — narrow scope anchor for comparison
- [IDC: AI Infrastructure $758B by 2029](https://my.idc.com/getdoc.jsp?containerId=prUS53894425) — IDC scope definition reference
- [Bloomberg: AI Circular Deals 2026](https://www.bloomberg.com/graphics/2026-ai-circular-deals/) — double-counting risk across value chain layers

### Tertiary (LOW confidence — needs validation during implementation)
- Specific scope_coefficient values (e.g., 0.18 for Gartner → our scope): derivable from published report methodology sections but must be independently verified during Plan 08-01 scope mapping work
- Foreign private issuer (20-F) XBRL coverage in edgartools: documented as supported but not verified for specific TSMC/Baidu cases

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages either already in lock file or verified via PyPI (edgartools 5.25.1 active as of March 19, 2026)
- Architecture patterns: HIGH — all patterns follow existing project conventions verified via codebase inspection; edgartools API verified via official docs
- Pitfalls: HIGH — carried from PITFALLS.md with HIGH research confidence; directly applicable to Phase 8 scope

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (edgartools releases weekly; pyproject.toml pin at >=5.25.1 handles patch updates)
