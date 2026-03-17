# Phase 1: Data Foundation - Research

**Researched:** 2026-03-17
**Domain:** Data ingestion pipeline, schema validation, Parquet caching, config-driven industry architecture
**Confidence:** HIGH (core stack verified via PyPI; patterns drawn from `.planning/research/` which was pre-researched; API-specific details verified via WebFetch)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**AI Market Boundary**
- Scope: Broad AI value chain — everything that enables or uses AI
- 4 segments modeled separately: AI hardware (chips/GPUs), AI infrastructure (cloud), AI software & platforms, AI adoption (enterprise)
- Taxonomy: Function x end-market matrix (NLP/CV/GenAI/robotics/etc. crossed with healthcare/finance/manufacturing/consumer/etc.)
- Geographic scope: Regional breakdown — Global aggregate + US, Europe, China, Rest of World
- Historical period: 2010-present (~15 years of data)
- Double-counting: Allow segment overlap, document and quantify the overlap range — do not force strict allocation
- Boundary documentation: Both a YAML config file (drives the pipeline) AND a standalone METHODOLOGY.md (explains rationale for humans / LinkedIn paper)
- Proxy indicators for AI activity: AI patent filings (USPTO/EPO), VC/PE investment in AI, public company AI revenue segments, R&D expenditure in ICT (OECD/World Bank)
- Deflation base year: 2020 constant USD for all monetary series

**LSEG Data Strategy**
- Access level: Full LSEG Workspace (desktop terminal + API)
- Company universe: TRBC classification — pull all companies classified under AI-related TRBC sector codes
- Data types to ingest: Company financials (revenue, R&D, margins), market indices (AI/tech sector), M&A and deals (AI acquisitions, deal values), sector classifications (TRBC/GICS codes)
- Credentials: Gitignored config file (not environment variables)

**Data Source Priority**
- Source hierarchy by indicator type: Macro indicators from OECD/World Bank, company-level data from LSEG, patent data from OECD — each source for what it's best at
- Missing data handling: Interpolate (linear or spline) and flag as estimated — preserves time series continuity while maintaining transparency
- Storage format: Parquet for pipeline cache (columnar, type-safe)

### Claude's Discretion
- Data pipeline update frequency (on-demand vs. quarterly — based on source cadence)
- Specific OECD/World Bank indicator codes to use
- Exact interpolation method (linear vs. spline) — pick what's most appropriate per indicator
- Column naming conventions beyond the `_real_2020` suffix pattern
- Schema validation test framework choice
- YAML config file structure for industry definitions

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-01 | Define AI industry market boundary (what sectors, companies, and activities count as "AI") | YAML config pattern; 4-segment locked; boundary locked in config/industries/ai.yaml before any API call |
| DATA-02 | Define AI use cases taxonomy for structuring the analysis | Function x end-market matrix goes in config; each row carries industry_tag and segment columns |
| DATA-03 | Ingest economic data from World Bank API (GDP, R&D expenditure, ICT indicators) | wbgapi 1.0.14; specific indicator codes documented in Standard Stack section |
| DATA-04 | Ingest economic data from OECD API (technology indicators, patent data) | pandasdmx 1.10.0 with SDMX provider 'OECD'; key datasets: MSTI, PATS_IPC |
| DATA-05 | Ingest financial data from LSEG Workspace API (company-level data, market data) | lseg-data 2.1.1; Desktop Session via ld.open_session(); credentials in gitignored lseg-data.config.json |
| DATA-06 | Clean and normalize all data (currency conversion to constant USD, missing value handling, frequency alignment) | Deflation via NY.GDP.DEFL.ZS (World Bank); column naming convention documented; interpolation strategy documented |
| DATA-07 | Display data source attribution on every chart and report output | Phase 4 deliverable — pipeline must attach source metadata to every Parquet row/file for downstream use |
| DATA-08 | Comprehensive documentation explaining each data source, why it was chosen, and how it's processed | METHODOLOGY.md + inline docstrings; dual audience: pipeline driver + LinkedIn paper |
| ARCH-01 | Config-driven extensible pipeline (add new industries via config, not code rewrite) | YAML config in config/industries/; pipeline reads config and is industry-agnostic from first commit |
</phase_requirements>

---

## Summary

Phase 1 builds the foundational data layer on which all subsequent phases depend. The goal is a local Parquet cache of clean, validated, deflated AI industry data from three source families: World Bank macro indicators (via wbgapi), OECD technology and patent indicators (via pandasdmx SDMX), and LSEG company-level financial data (via lseg-data Desktop Session). Every row carries an industry tag; all monetary series are deflated to 2020 constant USD; schema validation tests run at the ingestion boundary to reject malformed responses before they corrupt downstream modeling.

The architecture is config-driven from day one. The AI industry definition — 4 segments, proxy indicators, geographic scope, date range — lives entirely in `config/industries/ai.yaml`. Pipeline code is industry-agnostic: it reads the config and routes accordingly. Adding a second industry in a future phase requires dropping a new YAML file with no code changes.

The two critical non-negotiables for this phase are (1) deflation applied as a mandatory pipeline step before any data reaches the processed layer, and (2) schema validation tests at every fetch boundary. Both are enforced by the column naming convention (`_real_2020` suffix) and by pandera DataFrameSchema checks that run after each API call.

**Primary recommendation:** Write `config/industries/ai.yaml` and `src/processing/validate.py` (pandera schemas) before writing any ingestion code. The boundary definition and the validation contract must exist before data collection begins — this is the single most important sequencing decision of the entire phase.

---

## Standard Stack

### Core (Phase 1 specific)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| wbgapi | 1.0.14 | World Bank API — fetch GDP, R&D, deflator, ICT indicators as DataFrames | World Bank's own recommended Python client; modern API; returns DataFrames directly; replaces deprecated wbdata and pandas-datareader patterns |
| pandasdmx | 1.10.0 | OECD SDMX data access — technology indicators, patent data | OECD exposes data via SDMX 2.1; pandasdmx handles SDMX parsing, rate limiting, and multi-indicator assembly; listed as OECD provider in docs |
| lseg-data | 2.1.1 | LSEG Workspace API — company financials, TRBC classifications, M&A deals | Official LSEG Data Library for Python; Desktop Session authenticates via open Workspace app with no extra credentials |
| pandera | 0.30.0 | DataFrame schema validation — enforce types, ranges, null rules after every fetch | Production/Stable; validates pandas DataFrames with object-based or class-based API; both declarative and decorator patterns; integrates cleanly into pipeline |
| pyarrow | 23.0.1 | Parquet read/write — columnar cache for processed data | pandas 3.0 default backend; Parquet is smaller and faster than CSV for repeated reads; type-safe storage with schema preservation |
| requests-cache | 1.3.1 | Cache raw API responses to disk during development | OECD API is slow (30s+ queries); World Bank rate-limits at ~100 req/min; caching prevents redundant calls during iteration; sub-millisecond cached response |
| pyyaml | 6.x | Parse industry config YAML files | Standard Python YAML parser; reads config/industries/ai.yaml into dict for pipeline routing |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandas | 3.0.x | Core data wrangling, time series alignment, deflation arithmetic | All data processing; use CoW-safe patterns from day one |
| numpy | 2.x | Interpolation, numerical operations | Linear/spline interpolation for missing values; scipy.interpolate.CubicSpline for spline |
| scipy | 1.14.x | Spline interpolation for irregular time series gaps | Use CubicSpline for smooth interpolation on series with sparse gaps; use linear (pandas interpolate) for dense series |
| tqdm | 4.67.x | Progress bars for multi-indicator fetch loops | OECD and World Bank fetches iterate over many indicators; progress bars essential for development sanity |
| python-dotenv | 1.0.x | Load any supplementary environment config | Fallback for credentials not covered by lseg-data config file approach |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pandasdmx | direct OECD REST API requests | Direct requests work but require manual SDMX parsing; pandasdmx handles dimension codes, pagination, and rate limiting automatically |
| pandera | pydantic + manual type checks | Pydantic validates Python objects; pandera validates DataFrames natively with statistical checks (ranges, distributions) that pydantic cannot express |
| pandera | great_expectations | Great Expectations is a full data quality platform — heavy overhead for a pipeline this size; pandera is lightweight and idiomatic |
| pyyaml | python-box or dynaconf | pyyaml is sufficient for static config; more complex libraries add indirection without benefit at this scale |

**Installation:**
```bash
uv add wbgapi pandasdmx lseg-data pandera pyarrow requests-cache pyyaml scipy tqdm
```

**Version verification (confirmed 2026-03-17):**

| Package | Version | Source |
|---------|---------|--------|
| wbgapi | 1.0.14 | PyPI (released 2026-02-27) |
| pandasdmx | 1.10.0 | PyPI |
| lseg-data | 2.1.1 | PyPI (released 2025-04-04) |
| pandera | 0.30.0 | PyPI (released 2026-03-16) |
| pyarrow | 23.0.1 | PyPI (released 2026-02-16) |
| requests-cache | 1.3.1 | PyPI (released 2026-03-04) |

---

## Architecture Patterns

### Recommended Project Structure (Phase 1 scope)

```
industry-value-estimator/
├── config/
│   ├── settings.py                  # Global parameters (base year, geographic scope)
│   └── industries/
│       └── ai.yaml                  # AI market boundary — written FIRST before any code
├── data/
│   ├── raw/                         # Immutable — never modify after write
│   │   ├── world_bank/              # Raw wbgapi responses as parquet
│   │   ├── oecd/                    # Raw pandasdmx responses as parquet
│   │   └── lseg/                    # Raw LSEG company data as parquet
│   ├── interim/                     # Partially transformed (deflation applied, not yet tagged)
│   └── processed/                   # Final canonical Parquet cache — what Phase 2 reads
├── src/
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── world_bank.py            # wbgapi connector
│   │   ├── oecd.py                  # pandasdmx/OECD connector
│   │   ├── lseg.py                  # lseg-data connector
│   │   └── pipeline.py              # Orchestrator: reads config, routes to connectors
│   └── processing/
│       ├── __init__.py
│       ├── normalize.py             # Schema alignment, column naming, type coercion
│       ├── deflate.py               # Inflation adjustment — standalone module
│       ├── interpolate.py           # Missing value handling with flagging
│       ├── tag.py                   # Apply industry_segment and industry_tag columns
│       └── validate.py              # pandera schemas — one schema per source
├── tests/
│   ├── test_ingestion.py            # Unit tests for each connector (mock API calls)
│   ├── test_validate.py             # Schema validation tests with deliberately bad input
│   ├── test_deflate.py              # Deflation arithmetic tests
│   └── fixtures/                   # Sample raw API responses for offline testing
├── docs/
│   └── METHODOLOGY.md              # Human-readable market boundary explanation
└── notebooks/
    └── 01_data_exploration.ipynb    # Exploratory validation of fetched data
```

### Pattern 1: Industry Config YAML — Write First

**What:** All AI market boundary decisions live in `config/industries/ai.yaml`. The ingestion pipeline reads this file at startup and routes accordingly. The file is the single source of truth for what counts as AI, which indicators to fetch, and what geographic/time scope applies.

**When to use:** Before writing any connector code. The config file is the constraint that shapes every downstream decision.

**Example:**
```yaml
# config/industries/ai.yaml
# Source: Locked decisions from Phase 1 CONTEXT.md
industry: ai
display_name: "Artificial Intelligence Industry"
base_year: 2020                      # Deflation base year — 2020 constant USD

# 4 locked segments (modeled separately, overlap allowed and documented)
segments:
  - id: ai_hardware
    display_name: "AI Hardware (chips, GPUs, specialized silicon)"
    overlap_note: "GPU revenue counted here AND in cloud infrastructure — document range"
  - id: ai_infrastructure
    display_name: "AI Infrastructure (cloud compute, data centers)"
  - id: ai_software
    display_name: "AI Software & Platforms (foundation models, AI SaaS)"
  - id: ai_adoption
    display_name: "AI Adoption (enterprise AI deployment)"

# Geographic scope
regions:
  - id: global
  - id: us
  - id: europe
  - id: china
  - id: row            # Rest of World

# Historical range
date_range:
  start: "2010"
  end: "2025"          # Update to current year at fetch time

# Proxy indicators — what to use when direct AI revenue is unmeasurable
proxies:
  - id: rd_ict_pct_gdp
    description: "R&D expenditure in ICT as % of GDP (OECD ANBERD proxy)"
    source: oecd
    dataset: ANBERD
  - id: ai_patent_filings
    description: "AI patent applications (USPTO/EPO via OECD PATS_IPC)"
    source: oecd
    dataset: PATS_IPC
  - id: vc_ai_investment
    description: "VC/PE investment in AI companies (OECD/Crunchbase proxy)"
    source: oecd
    dataset: VC_INVEST
  - id: public_co_ai_revenue
    description: "Revenue of TRBC-classified AI companies (LSEG)"
    source: lseg
    trbc_codes: ["57201010", "57201020", "57201030"]  # AI-related TRBC codes to verify

# World Bank indicators to fetch (alongside AI proxies)
world_bank:
  indicators:
    - code: NY.GDP.MKTP.CD
      name: gdp_current_usd
      unit: current_usd
      use_for: macro_denominator
    - code: NY.GDP.DEFL.ZS
      name: gdp_deflator_index
      unit: index_2015_100
      use_for: deflation          # CRITICAL — fetch alongside every nominal series
    - code: GB.XPD.RSDV.GD.ZS
      name: rd_pct_gdp
      unit: pct_gdp
      use_for: proxy_rd
    - code: TX.VAL.TECH.CD
      name: hightech_exports_current_usd
      unit: current_usd
      use_for: proxy_tech_intensity
    - code: IP.PAT.RESD
      name: patent_applications_residents
      unit: count
      use_for: proxy_innovation
    - code: BX.GSR.CCIS.CD
      name: ict_service_exports_current_usd
      unit: current_usd
      use_for: proxy_ict

# OECD indicators to fetch
oecd:
  datasets:
    - id: MSTI
      name: main_science_tech_indicators
      use_for: rd_expenditure_by_sector
    - id: PATS_IPC
      name: patent_filings_by_ipc_class
      use_for: ai_patent_proxy
      ipc_filter: "G06N"           # IPC class G06N = Computing/calculating by methods
```

### Pattern 2: Deflation as Mandatory Pipeline Step

**What:** Deflation is never optional. Every nominal monetary column is deflated to 2020 constant USD in a dedicated `deflate.py` module before the data reaches `data/processed/`. Column naming enforces this: nominal columns have `_nominal_YYYY` suffix, real columns have `_real_2020` suffix.

**When to use:** In the `interim -> processed` transition. Raw data is stored nominal; processed data is always real.

**Example:**
```python
# src/processing/deflate.py
import pandas as pd

def deflate_to_base_year(
    nominal_series: pd.Series,
    deflator_series: pd.Series,
    base_year: int = 2020,
    nominal_col_name: str = "",
) -> pd.Series:
    """
    Convert a nominal USD series to constant base_year USD.

    Parameters
    ----------
    nominal_series : pd.Series
        Values in current USD, indexed by year.
    deflator_series : pd.Series
        World Bank NY.GDP.DEFL.ZS index (2015=100 by default).
        Must share the same year index as nominal_series.
    base_year : int
        Target constant year (project standard: 2020).
    nominal_col_name : str
        Original column name — used only for error messages.

    Returns
    -------
    pd.Series
        Values in constant base_year USD.
    """
    base_deflator = deflator_series.loc[base_year]
    if pd.isna(base_deflator):
        raise ValueError(
            f"Deflator missing for base year {base_year}. "
            f"Cannot deflate {nominal_col_name}."
        )
    return nominal_series * (base_deflator / deflator_series)


def apply_deflation(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Apply deflation to all nominal columns specified in config.
    Renames columns from _nominal_YYYY to _real_2020.
    Raises if deflator column is missing.
    """
    base_year = config["base_year"]  # 2020
    deflator_col = "gdp_deflator_index"

    if deflator_col not in df.columns:
        raise RuntimeError(
            "GDP deflator column missing from DataFrame. "
            "Fetch NY.GDP.DEFL.ZS before running deflation."
        )

    result = df.copy()
    nominal_cols = [c for c in df.columns if "_nominal_" in c]
    for col in nominal_cols:
        real_col = col.replace("_nominal_", f"_real_{base_year}_")
        result[real_col] = deflate_to_base_year(
            df[col], df[deflator_col], base_year=base_year, nominal_col_name=col
        )
        result.drop(columns=[col], inplace=True)

    return result
```

### Pattern 3: Pandera Schema Validation at Fetch Boundary

**What:** A pandera DataFrameSchema (or DataFrameModel) is defined for each data source. Validation runs immediately after a fetch, before the data is written to `data/raw/`. A schema mismatch raises an exception — the pipeline fails loudly rather than silently writing corrupt data.

**When to use:** At the ingestion layer, immediately after any API call returns a DataFrame.

**Example:**
```python
# src/processing/validate.py
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check

# Schema for World Bank DataFrame returned by wbgapi
WORLD_BANK_RAW_SCHEMA = DataFrameSchema(
    {
        "year": Column(int, Check.in_range(2000, 2030)),
        "economy": Column(str, nullable=False),
        "NY.GDP.MKTP.CD": Column(float, Check.ge(0), nullable=True),   # nullable: some countries/years missing
        "NY.GDP.DEFL.ZS": Column(float, Check.in_range(1, 1000), nullable=True),
        "GB.XPD.RSDV.GD.ZS": Column(float, Check.in_range(0, 20), nullable=True),
    },
    coerce=True,
    strict=False,   # allow extra columns from API
)

def validate_world_bank(df: pd.DataFrame) -> pd.DataFrame:
    """Validate raw World Bank fetch. Raises SchemaError on failure."""
    return WORLD_BANK_RAW_SCHEMA.validate(df)
```

### Pattern 4: LSEG Desktop Session Authentication

**What:** LSEG Data Library for Python (lseg-data) authenticates via the Desktop Session when LSEG Workspace is open on the same machine. No additional API key is needed. The credentials config file (`lseg-data.config.json`) is gitignored; the library reads it automatically from the working directory or `~/.config/lseg/`.

**When to use:** In `src/ingestion/lseg.py`. Call `ld.open_session()` once at pipeline startup; subsequent data calls reuse the session.

**Example:**
```python
# src/ingestion/lseg.py
import lseg.data as ld
import pandas as pd


def open_lseg_session() -> None:
    """
    Open a Desktop Session to LSEG Workspace.
    Requires LSEG Workspace Desktop App to be running on this machine.
    Credentials are read from lseg-data.config.json (gitignored).
    """
    ld.open_session()


def fetch_trbc_company_universe(trbc_codes: list[str]) -> pd.DataFrame:
    """
    Fetch all companies classified under the specified TRBC sector codes.

    TRBC codes for AI (to verify against live data):
      57201010 — Computer Processing Hardware
      57201020 — Electronic Equipment & Parts
      45101010 — Internet Software & Services (includes AI SaaS)

    Returns DataFrame with columns: ric, company_name, trbc_code, trbc_name.
    """
    # ScreeningExpression query to filter by TRBC classification
    screening_expr = " OR ".join(
        [f'TR.TRBCActivityCode="{code}"' for code in trbc_codes]
    )
    df = ld.get_data(
        universe=f"SCREEN({screening_expr})",
        fields=["TR.CommonName", "TR.TRBCActivity", "TR.TRBCActivityCode"],
    )
    return df


def fetch_company_financials(rics: list[str], fields: list[str]) -> pd.DataFrame:
    """
    Fetch annual financial data for a list of company RIC codes.

    fields: e.g. ['TR.Revenue', 'TR.RDExpense', 'TR.GrossMargin']
    Returns long-format DataFrame indexed by RIC and fiscal year.
    """
    return ld.get_data(universe=rics, fields=fields)


def close_lseg_session() -> None:
    ld.close_session()
```

**lseg-data.config.json** (gitignored — do NOT commit):
```json
{
    "sessions": {
        "default": "desktop.workspace"
    },
    "desktop": {
        "workspace": {
            "app-key": ""
        }
    }
}
```
Note: For Desktop Session with LSEG Workspace, the app-key field can be left empty — authentication flows through the open Workspace application. Confirm this against LSEG Developer Portal documentation during implementation.

### Pattern 5: wbgapi Fetch with Deflator Co-fetch

**What:** Always fetch the GDP deflator (`NY.GDP.DEFL.ZS`) in the same call as any nominal indicator. This ensures deflation can be applied immediately without a second API round-trip.

**Example:**
```python
# src/ingestion/world_bank.py
import wbgapi as wb
import pandas as pd


def fetch_world_bank_indicators(
    indicators: list[str],
    economies: list[str],
    date_range: tuple[str, str],
) -> pd.DataFrame:
    """
    Fetch multiple World Bank indicators for specified economies and years.
    Always includes NY.GDP.DEFL.ZS (GDP deflator) for downstream deflation.

    Parameters
    ----------
    indicators : list of World Bank indicator codes (e.g. ["NY.GDP.MKTP.CD"])
    economies : list of ISO3 economy codes or ["all"] for global
    date_range : (start_year, end_year) as strings e.g. ("2010", "2025")

    Returns
    -------
    pd.DataFrame in wide format, rows = (economy, year), cols = indicators
    """
    # Always include deflator — non-negotiable
    DEFLATOR = "NY.GDP.DEFL.ZS"
    all_indicators = list(set(indicators + [DEFLATOR]))

    df = wb.data.DataFrame(
        series=all_indicators,
        economy=economies,
        time=range(int(date_range[0]), int(date_range[1]) + 1),
        labels=False,
    )
    # wb.data.DataFrame returns MultiIndex (economy, series) — pivot to wide
    df = df.reset_index().pivot(index=["economy", "time"], columns="series")
    df.columns = df.columns.droplevel(0)
    df.index.names = ["economy", "year"]
    return df.reset_index()
```

### Pattern 6: pandasdmx OECD Fetch

**What:** pandasdmx wraps the OECD SDMX REST endpoint. OECD queries are slow — always wrap in requests-cache. Key OECD datasets for this phase: `MSTI` (Main Science and Technology Indicators) and `PATS_IPC` (Patents by IPC class, targeting class G06N for AI/computing methods).

**Example:**
```python
# src/ingestion/oecd.py
import pandasdmx as sdmx
import pandas as pd
import requests_cache

# Cache OECD responses for 30 days (OECD data updates annually/quarterly)
requests_cache.install_cache(
    "data/raw/oecd/.cache",
    backend="sqlite",
    expire_after=30 * 24 * 60 * 60,
)


def fetch_oecd_msti(countries: list[str], years: list[str]) -> pd.DataFrame:
    """
    Fetch OECD Main Science and Technology Indicators (MSTI).
    Dataset ID: MSTI
    Key variables: GERD (Gross domestic R&D expenditure), researchers, etc.

    Note: OECD SDMX dimension keys and codes must be verified against
    live OECD SDMX metadata before finalizing — see Open Questions.
    """
    oecd = sdmx.Request("OECD")
    data_msg = oecd.data(
        "MSTI",
        key={"LOCATION": "+".join(countries)},
        params={"startPeriod": years[0], "endPeriod": years[-1]},
    )
    df = sdmx.to_pandas(data_msg.data[0], datetime="TIME_PERIOD")
    return df.reset_index()


def fetch_oecd_ai_patents(countries: list[str], years: list[str]) -> pd.DataFrame:
    """
    Fetch OECD patent filings filtered to IPC class G06N (AI/computing methods).
    Dataset ID: PATS_IPC

    IPC G06N: 'Computing; Calculating or Counting — Computing or calculating by
    methods or systems based on specific computational models'
    This is the standard proxy for AI patent activity in OECD methodology papers.
    """
    oecd = sdmx.Request("OECD")
    data_msg = oecd.data(
        "PATS_IPC",
        key={"IPC": "G06N", "LOCATION": "+".join(countries)},
        params={"startPeriod": years[0], "endPeriod": years[-1]},
    )
    df = sdmx.to_pandas(data_msg.data[0], datetime="TIME_PERIOD")
    return df.reset_index()
```

### Pattern 7: Parquet Write with Metadata

**What:** Every Parquet file written to `data/processed/` includes file-level metadata: source, industry, fetch timestamp, and base year. This makes the provenance of every cache file self-documenting.

**Example:**
```python
# src/processing/normalize.py
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
from datetime import datetime, timezone


def write_processed_parquet(
    df: pd.DataFrame,
    path: str,
    source: str,
    industry: str = "ai",
    base_year: int = 2020,
) -> None:
    """
    Write a processed DataFrame to Parquet with provenance metadata.

    Schema conventions:
    - All monetary columns: {name}_real_{base_year} (float64)
    - All monetary columns (if kept nominal): {name}_nominal_{year} (float64)
    - industry_tag column: string, e.g. "ai"
    - industry_segment column: string, e.g. "ai_hardware"
    - estimated_flag column: bool, True if value was interpolated
    """
    table = pa.Table.from_pandas(df)
    # Attach provenance metadata to the file
    existing_meta = table.schema.metadata or {}
    custom_meta = {
        b"source": source.encode(),
        b"industry": industry.encode(),
        b"base_year": str(base_year).encode(),
        b"fetched_at": datetime.now(tz=timezone.utc).isoformat().encode(),
    }
    table = table.replace_schema_metadata({**existing_meta, **custom_meta})
    pq.write_table(
        table,
        path,
        compression="snappy",
        coerce_timestamps="us",           # microseconds: broad compatibility
        allow_truncated_timestamps=False,
    )
```

### Anti-Patterns to Avoid

- **Fetching GDP without deflator:** Never call `wbgapi` for a nominal series without including `NY.GDP.DEFL.ZS` in the same request. A DataFrame with nominal values but no deflator is actively dangerous — it will silently produce wrong results if deflation is forgotten downstream.
- **Hardcoding TRBC codes in ingestion code:** TRBC codes that define the AI company universe belong in `config/industries/ai.yaml`, not in `src/ingestion/lseg.py`. The ingestion module reads them from config.
- **Skipping schema validation during development:** "I'll add validation later" is how silent data corruption happens. pandera validation runs at every fetch boundary, even in development.
- **Modifying files in `data/raw/`:** Raw is immutable. Any transformation writes to `data/interim/` or `data/processed/`. The pipeline must be fully reproducible from `data/raw/`.
- **Using `pd.DataFrame.interpolate()` without flagging:** Missing values filled by interpolation must set `estimated_flag = True` in the same row. Unflagged interpolation creates invisible data.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| World Bank data fetching | Custom requests + JSON parsing | wbgapi 1.0.14 | Handles pagination, multi-economy queries, DataFrame conversion; World Bank's own recommended client |
| OECD SDMX parsing | Custom XML/JSON SDMX parser | pandasdmx 1.10.0 | SDMX is a complex standard; pandasdmx implements SDMX 2.1 and handles dimension codes, codelists, and rate limiting |
| DataFrame schema validation | Custom `assert df.dtypes...` checks | pandera 0.30.0 | Built-in statistical checks (ranges, distributions), null handling, declarative schemas, SchemaError with helpful messages |
| Parquet read/write | CSV or pickle | pyarrow + pandas to_parquet/read_parquet | Columnar compression (snappy), type-safe, schema preservation, 10-100x smaller than CSV for repeated reads |
| API response caching | Manual file-based cache | requests-cache 1.3.1 | Drop-in replacement for requests.Session; SQLite backend; configurable TTL; handles cache invalidation |
| Inflation adjustment math | Ad-hoc deflation formulas | Dedicated `deflate.py` module (custom, 30 lines) | The math is simple; the complexity is the unit-tracking convention and test coverage — hand-roll this module but test it rigorously |

**Key insight:** The ingestion layer is essentially plumbing. Use the official Python clients for World Bank and OECD — they exist precisely to abstract the API-specific complexity. The custom code in this phase is the business logic: deflation, column naming, industry tagging, interpolation flagging, and the config-driven routing.

---

## Common Pitfalls

### Pitfall 1: Starting Data Collection Before Locking the Market Boundary

**What goes wrong:** Fetching data before `config/industries/ai.yaml` is complete means collecting indicators that may not map to the locked segments. Re-discovering the boundary mid-pipeline requires auditing every fetched series for scope compliance.

**Why it happens:** The YAML config feels like "config to write later." It is actually the specification document that constrains everything.

**How to avoid:** Wave 0 of this phase must create `config/industries/ai.yaml` with all 4 segments, proxy indicators, geographic scope, and date range before any ingestion module is written.

**Warning signs:** An ingestion module is written before `ai.yaml` is committed.

### Pitfall 2: Nominal/Real Conflation (Pitfall 6 from project PITFALLS.md)

**What goes wrong:** Nominal columns flow into the processed layer without deflation. Column names don't distinguish real from nominal.

**Why it happens:** wbgapi returns current-year USD by default. Without explicit deflation, all values are nominal.

**How to avoid:** Column naming convention is enforced in `normalize.py`. A pandera check on the processed schema asserts that no column named `_nominal_` exists in the processed layer.

**Warning signs:** Column names like `gdp` or `revenue` without year/nominal/real qualifier in `data/processed/`.

### Pitfall 3: Specific OECD Indicator Codes Needing Live Validation

**What goes wrong:** OECD SDMX dimension codes and dataset IDs documented in research may not match the live OECD endpoint exactly. Dataset IDs like `MSTI` and `PATS_IPC` are the correct OECD names but must be verified against the live SDMX metadata catalog.

**Why it happens:** OECD occasionally reorganizes datasets and changes dimension key names. The SDMX catalog is the authoritative source.

**How to avoid:** In the first task of the ingestion wave, query `oecd.dataflow()` to list available datasets and `oecd.datastructure('MSTI')` to list available dimension codes before writing the fetch queries.

**Warning signs:** A pandasdmx query raises `HTTPError 404` or `KeyError` on dimension names.

### Pitfall 4: LSEG TRBC Code Verification

**What goes wrong:** TRBC sector codes for AI companies are not standardized — LSEG revises the taxonomy. Using wrong codes produces an empty or incomplete company universe.

**Why it happens:** TRBC is a proprietary classification; public documentation is sparse.

**How to avoid:** In the LSEG ingestion task, run a discovery query (`ld.get_data(universe='SCREEN(...)', fields=['TR.TRBCActivity', 'TR.TRBCActivityCode'])`) to inspect what codes actually exist in the live database before relying on any hardcoded list.

**Warning signs:** Company universe fetch returns fewer than 50 companies for global AI sector.

### Pitfall 5: API Schema Changes Silently Corrupting Data (Pitfall 8 from PITFALLS.md)

**What goes wrong:** World Bank or OECD changes a field name, unit, or value range. The pipeline continues without errors but produces wrong values.

**How to avoid:** pandera schemas with value range checks run after every fetch. Raw responses are cached with a fetch timestamp. Any failed validation surfaces as an exception, not silent data.

---

## Code Examples

Verified patterns from official sources:

### wbgapi: Fetch Multiple Indicators as DataFrame

```python
# Source: wbgapi PyPI docs (v1.0.14, 2026-02-27)
import wbgapi as wb

df = wb.data.DataFrame(
    series=["NY.GDP.MKTP.CD", "NY.GDP.DEFL.ZS", "GB.XPD.RSDV.GD.ZS"],
    economy=["USA", "CHN", "GBR", "DEU", "FRA", "JPN"],  # extend to full regional list
    time=range(2010, 2026),
    labels=False,
)
# Returns: MultiIndex DataFrame with (economy, series) on rows, years on columns
```

### pandera: Class-Based Schema with Range Checks

```python
# Source: pandera docs (v0.30.0, 2026-03-16)
import pandera.pandas as pa
from pandera.pandas import DataFrameModel, Field


class WorldBankProcessedSchema(DataFrameModel):
    """Schema for World Bank indicators in processed layer (post-deflation)."""
    economy: str = Field(nullable=False)
    year: int = Field(ge=2010, le=2030)
    gdp_real_2020: float = Field(ge=0, nullable=True)
    rd_pct_gdp: float = Field(ge=0, le=20, nullable=True)
    estimated_flag: bool = Field(nullable=False)
    industry_tag: str = Field(isin=["ai"], nullable=False)

    class Config:
        coerce = True
        strict = False  # allow extra columns
```

### pyarrow: Write Parquet with Snappy Compression

```python
# Source: Apache Arrow Python docs (pyarrow 23.0.1)
import pyarrow.parquet as pq
import pyarrow as pa

table = pa.Table.from_pandas(df, preserve_index=False)
pq.write_table(
    table,
    "data/processed/world_bank_ai.parquet",
    compression="snappy",
    coerce_timestamps="us",
)

# Read back
df_back = pq.read_table("data/processed/world_bank_ai.parquet").to_pandas()
```

### requests-cache: SQLite Backend with TTL

```python
# Source: requests-cache docs (v1.3.1, 2026-03-04)
import requests_cache

session = requests_cache.CachedSession(
    cache_name="data/raw/.http_cache",
    backend="sqlite",
    expire_after=30 * 24 * 3600,   # 30 days — World Bank/OECD update quarterly
)
```

### lseg-data: Desktop Session Open/Close

```python
# Source: LSEG Developer Portal Quick Start (lseg-data 2.1.1)
import lseg.data as ld

# Open — requires LSEG Workspace Desktop App running on same machine
ld.open_session()

# Fetch company data
df = ld.get_data(
    universe=["NVDA.O", "MSFT.O"],
    fields=["TR.Revenue", "TR.RDExpense", "TR.TRBCActivityCode"],
)

ld.close_session()
```

---

## Key World Bank Indicator Codes

Verified against World Bank data catalog. All confirmed available as of 2026-03-17.

| Code | Name | Unit | Use in Pipeline |
|------|------|------|-----------------|
| NY.GDP.MKTP.CD | GDP (current US$) | current USD | Macro denominator; deflate to real |
| NY.GDP.DEFL.ZS | GDP deflator (base varies by country) | index | **Deflation instrument — fetch always** |
| NY.GDP.MKTP.KD.ZG | GDP growth (annual %) | % | Context indicator |
| GB.XPD.RSDV.GD.ZS | R&D expenditure (% of GDP) | % of GDP | AI proxy — R&D intensity |
| SP.POP.SCIE.RD.P6 | Researchers in R&D (per million people) | per million | AI proxy — R&D human capital |
| TX.VAL.TECH.CD | High-technology exports (current US$) | current USD | AI proxy — tech intensity |
| IP.PAT.RESD | Patent applications, residents | count | AI proxy — innovation rate |
| BX.GSR.CCIS.CD | ICT service exports (BoP, current US$) | current USD | AI proxy — ICT sector size |

**Note on deflator:** `NY.GDP.DEFL.ZS` uses 2015=100 as base in the World Bank API. The pipeline converts to 2020 base internally by re-basing to the 2020 observation.

---

## Key OECD Datasets

| Dataset ID | Name | Relevance |
|------------|------|-----------|
| MSTI | Main Science and Technology Indicators | GERD (R&D expenditure by sector), researcher counts |
| PATS_IPC | Patents by IPC Class | AI patent filings — filter to IPC class G06N |
| ANBERD | Analytical Business Enterprise R&D | R&D by industry including ICT sector |

**Caveat (LOW confidence):** OECD SDMX dataset IDs must be validated against live `sdmx.Request('OECD').dataflow()` before use. OECD occasionally reorganizes data structure IDs.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| wbdata / pandas-datareader for World Bank | wbgapi 1.0.14 | 2020–2022 | wbdata unmaintained; wbgapi is World Bank's own client with better DataFrame support |
| pandas-datareader for OECD | pandasdmx 1.10.0 | 2023 | OECD changed API; pandas-datareader OECD reader broken since 2023 |
| Refinitiv Eikon Python API | lseg-data 2.1.1 (LSEG Data Library) | 2022–2023 | Refinitiv rebranded to LSEG; old `eikon` package still works but lseg-data is the current official client |
| pandas < 3.0 | pandas 3.0.x with Copy-on-Write | Jan 2026 | CoW is now default — must write CoW-safe code from day one |
| pyarrow 14.x | pyarrow 23.0.1 | Continuous | Major version bumps; always pin in uv.lock |

**Deprecated/outdated:**
- `fbprophet`: Renamed to `prophet` at v1.0; PyPI package abandoned — do not use
- `eikon` Python package: Still functional but superseded by `lseg-data`; prefer `lseg-data` for new code
- `pandas-datareader` OECD reader: Broken since OECD API change in 2023

---

## Open Questions

1. **Specific OECD SDMX dimension codes for MSTI and PATS_IPC**
   - What we know: Dataset IDs (`MSTI`, `PATS_IPC`) are correct OECD names; OECD SDMX is supported by pandasdmx
   - What's unclear: Exact dimension key names (e.g., `LOCATION` vs `COU`) and valid values for the live endpoint; these changed in OECD's 2023 API migration
   - Recommendation: First task of the OECD ingestion wave must query `oecd.datastructure('MSTI')` to inspect available dimensions before writing the fetch query

2. **LSEG TRBC codes for AI company universe**
   - What we know: TRBC is the methodological anchor; LSEG uses it for sector classification; `lseg-data` supports screening by TRBC code
   - What's unclear: The exact TRBC codes that map to the 4 AI segments; LSEG revises the taxonomy
   - Recommendation: First LSEG task runs a discovery query (`TR.TRBCActivity`, `TR.TRBCActivityCode`) on a sample of known AI companies (NVDA, MSFT, GOOGL) to verify their codes, then uses those to build the screening expression

3. **lseg-data.config.json format for Desktop Session**
   - What we know: Desktop Session requires LSEG Workspace open; `ld.open_session()` handles authentication; app-key field appears optional
   - What's unclear: Whether the config file must be explicitly created or if lseg-data auto-detects Workspace
   - Recommendation: Consult LSEG Developer Portal Quick Start on first setup; the JSON config template is in the official examples repository

4. **World Bank deflator base year (2015 vs 2020)**
   - What we know: `NY.GDP.DEFL.ZS` uses 2015=100 as its base in the World Bank API
   - What's unclear: Whether the pipeline should re-base to 2020 internally or accept 2015 as the deflation anchor
   - Recommendation: Re-base to 2020 internally — divide all deflator values by the 2020 observation to get a 2020=100 index; this matches the locked project convention and is a 2-line operation

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | None — Wave 0 creates `pytest.ini` or `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | config/industries/ai.yaml is parseable and contains all 4 segments, geographic scope, and date range | unit | `pytest tests/test_config.py::test_ai_config_schema -x` | Wave 0 |
| DATA-02 | Each processed row has non-null industry_tag and industry_segment columns | unit | `pytest tests/test_processing.py::test_industry_tagging -x` | Wave 0 |
| DATA-03 | wbgapi fetch returns expected columns including deflator; pandera validation passes | unit (mocked) | `pytest tests/test_ingestion.py::test_world_bank_fetch -x` | Wave 0 |
| DATA-04 | pandasdmx OECD fetch returns MSTI data; pandera validation passes | unit (mocked) | `pytest tests/test_ingestion.py::test_oecd_fetch -x` | Wave 0 |
| DATA-05 | lseg-data fetch returns company DataFrame with TRBC columns | integration (requires Workspace) | `pytest tests/test_ingestion.py::test_lseg_fetch -x -m integration` | Wave 0 |
| DATA-06 | All monetary columns in processed layer have `_real_2020` suffix; no `_nominal_` columns present | unit | `pytest tests/test_deflate.py::test_no_nominal_in_processed -x` | Wave 0 |
| DATA-06 | Deflation arithmetic is correct: 2020 value == nominal 2020 value | unit | `pytest tests/test_deflate.py::test_deflation_base_year_identity -x` | Wave 0 |
| DATA-06 | Interpolated values have estimated_flag=True | unit | `pytest tests/test_interpolate.py::test_estimated_flag_set -x` | Wave 0 |
| DATA-08 | METHODOLOGY.md exists and contains required sections | unit | `pytest tests/test_docs.py::test_methodology_md_exists -x` | Wave 0 |
| ARCH-01 | Pipeline ingests data for a second dummy industry from a second YAML file without code changes | integration | `pytest tests/test_pipeline.py::test_second_industry_yaml -x` | Wave 0 |

**Note on DATA-05:** LSEG tests that hit the live API require LSEG Workspace running. Mark these with `@pytest.mark.integration` and exclude from the standard quick-run suite (`-m "not integration"`).

### Sampling Rate

- **Per task commit:** `pytest tests/ -x -q -m "not integration"`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite (including integration tests with Workspace open) green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_config.py` — covers DATA-01: YAML schema validation
- [ ] `tests/test_ingestion.py` — covers DATA-03, DATA-04, DATA-05 (mocked + integration)
- [ ] `tests/test_deflate.py` — covers DATA-06 deflation arithmetic
- [ ] `tests/test_interpolate.py` — covers DATA-06 estimated_flag
- [ ] `tests/test_processing.py` — covers DATA-02 industry tagging
- [ ] `tests/test_docs.py` — covers DATA-08 METHODOLOGY.md presence
- [ ] `tests/test_pipeline.py` — covers ARCH-01 second-industry YAML test
- [ ] `tests/fixtures/` — sample raw API responses for offline/mocked tests
- [ ] `pytest.ini` or `pyproject.toml [tool.pytest.ini_options]` — configure test markers (integration)
- [ ] Framework install: `uv add --dev pytest` (already in stack; ensure it is in pyproject.toml dev deps)

---

## Sources

### Primary (HIGH confidence)
- wbgapi PyPI v1.0.14 (released 2026-02-27) — version confirmed via PyPI
- pandera PyPI v0.30.0 (released 2026-03-16) — version confirmed via PyPI; API patterns from official docs
- pyarrow PyPI v23.0.1 (released 2026-02-16) — version confirmed via PyPI; Parquet patterns from Apache Arrow docs
- requests-cache PyPI v1.3.1 (released 2026-03-04) — version confirmed via PyPI
- lseg-data PyPI v2.1.1 (released 2025-04-04) — version confirmed via PyPI; Desktop Session auth from LSEG Developer Portal Quick Start
- World Bank indicator codes — confirmed via data.worldbank.org/indicator
- `.planning/research/STACK.md` — pre-researched stack (pandas 3.0, pandasdmx, uv, pyarrow) HIGH confidence
- `.planning/research/ARCHITECTURE.md` — FTI pattern, Cookiecutter DS structure, industry YAML approach HIGH confidence
- `.planning/research/PITFALLS.md` — deflation, schema validation, market boundary pitfalls HIGH confidence

### Secondary (MEDIUM confidence)
- pandasdmx PyPI v1.10.0 — version confirmed; OECD support confirmed via official docs; specific dimension codes NOT verified (see Open Questions)
- pandasdmx readthedocs v1.0 — OECD listed as supported provider; walkthrough examples use ECB, not OECD
- LSEG Developer Portal Quick Start — Desktop Session authentication flow confirmed; config file format partially confirmed (app-key optional for Desktop)
- Apache Arrow Python Parquet docs — write_table patterns confirmed

### Tertiary (LOW confidence)
- OECD dataset IDs (MSTI, PATS_IPC, ANBERD) — known from prior OECD SDMX research; not verified against live SDMX metadata catalog in this session; must be validated during implementation
- TRBC sector codes for AI companies — illustrative codes only; must be verified against live LSEG data

---

## Metadata

**Confidence breakdown:**
- Standard stack (versions): HIGH — all key package versions verified via PyPI as of 2026-03-17
- Architecture patterns: HIGH — drawn from pre-researched ARCHITECTURE.md plus confirmed library patterns
- World Bank indicator codes: HIGH — confirmed via World Bank data catalog
- OECD dataset IDs: MEDIUM — correct names from OECD documentation; dimension codes need live verification
- LSEG auth flow: MEDIUM — Desktop Session mechanism confirmed; config file format partially confirmed
- Pitfalls: HIGH — drawn from pre-researched PITFALLS.md, all critical items verified across multiple sources

**Research date:** 2026-03-17
**Valid until:** 2026-06-17 (90 days — stack is relatively stable; OECD dataset IDs and LSEG TRBC codes require live validation regardless of research date)
