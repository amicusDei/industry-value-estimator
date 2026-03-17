# AI Industry Valuation Methodology

## Market Boundary

This project estimates the market size and growth trajectory of the global Artificial Intelligence industry. The market boundary defines what economic activities count as "AI" for the purpose of valuation.

### Scope

We adopt a **broad AI value chain** definition — encompassing everything that enables or directly uses AI. This is deliberately inclusive to capture the full economic footprint, mirroring the approach used by major research firms (Gartner, IDC, McKinsey Global Institute).

### Four Segments

The AI industry is modeled as four distinct but overlapping segments:

1. **AI Hardware** — Chips, GPUs, specialized silicon (e.g., NVIDIA, AMD, custom ASICs). Captures the physical compute substrate.
2. **AI Infrastructure** — Cloud compute, data centers, networking for AI workloads. Captures the platform layer.
3. **AI Software & Platforms** — Foundation models, AI SaaS, MLOps platforms. Captures the software layer.
4. **AI Adoption** — Enterprise AI deployment, AI-driven automation, AI-augmented products. Captures the demand side.

### Overlap Treatment

Segments are **not mutually exclusive**. GPU revenue appears in both AI Hardware and AI Infrastructure (when cloud providers buy GPUs). AI SaaS revenue appears in both AI Software and AI Adoption (when enterprises subscribe).

Rather than forcing artificial allocation to eliminate double-counting — which introduces its own measurement error — we **document and quantify the overlap range**. Each segment carries an `overlap_note` in the configuration. The final market size estimate is presented as a range that accounts for this overlap, consistent with how professional research firms handle segment boundaries.

### Geographic Scope

- **Global** aggregate
- **United States** — largest single AI market
- **Europe** — UK, Germany, France, Netherlands, Sweden, Ireland, Switzerland
- **China** — second-largest AI market, distinct regulatory environment
- **Rest of World** — Japan, South Korea, India, Israel, Singapore, Canada, Australia

### Historical Period

2010 to present (~15 years). This captures the pre-deep-learning era (2010-2012), the deep learning breakthrough (2012-2017), the scaling era (2017-2022), and the generative AI surge (2022-present).

### Proxy Indicators

Direct measurement of "AI revenue" is impossible — no statistical agency tracks it as a category. We use proxy indicators that correlate with AI economic activity:

- **AI patent filings** (IPC class G06N) — innovation intensity
- **VC/PE investment in AI** — capital allocation signal
- **Public company revenue** (TRBC-classified AI companies) — realized market size
- **R&D expenditure in ICT** — input intensity
- **High-technology exports** — trade signal
- **ICT service exports** — services market signal

### Monetary Convention

All monetary series are expressed in **2020 constant USD** (deflated using the World Bank GDP deflator, NY.GDP.DEFL.ZS). Column names encode this: `revenue_real_2020` vs `revenue_nominal_2023`. No nominal values appear in the modeling layer.

## Data Sources

| Source | Type | Access | Indicators |
|--------|------|--------|------------|
| World Bank | Macro economic | Public API (wbgapi) | GDP, R&D expenditure, deflator, patents, ICT exports |
| OECD | Technology & innovation | Public API (SDMX via pandasdmx) | MSTI (R&D by sector), PATS_IPC (patents by IPC class), ANBERD |
| LSEG Workspace | Company financial | Desktop API (lseg-data) | Revenue, R&D expense, margins, TRBC classification, M&A deals |

### Why These Sources

- **World Bank**: Most comprehensive free source for cross-country macro data. GDP deflator is essential for inflation adjustment.
- **OECD**: Best source for R&D and patent data disaggregated by technology field. The MSTI dataset is the standard reference for international R&D comparisons.
- **LSEG**: Company-level financial data with the TRBC sector classification — the methodological anchor for identifying which companies are "AI companies."

## Processing Pipeline

1. **Ingest** — Fetch raw data from each source API; validate against pandera schemas; cache as immutable Parquet in `data/raw/`
2. **Deflate** — Convert all nominal monetary series to 2020 constant USD using the GDP deflator
3. **Interpolate** — Fill missing values (linear for dense series, spline for sparse); flag all interpolated values with `estimated_flag=True`
4. **Tag** — Apply `industry_tag` and `industry_segment` columns based on the config YAML
5. **Validate** — Run processed-layer pandera schema; reject any DataFrame with nominal columns remaining
6. **Cache** — Write final processed Parquet with provenance metadata (source, industry, fetch timestamp, base year)

---

*This document serves dual purpose: it drives the pipeline configuration and provides the methodological foundation for the LinkedIn methodology paper (Phase 5).*
