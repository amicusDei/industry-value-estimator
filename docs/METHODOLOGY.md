# Market Boundary Definition and Scope Methodology

## Purpose

This document defines what "the AI market" means in this model and explains why that
definition matters. Published AI market size estimates for 2025 range from approximately
$196 billion (Grand View Research — AI software narrow scope) to $1.5 trillion or more
(Gartner — all AI-adjacent infrastructure spending). This is not disagreement about facts;
it is disagreement about what "the AI market" means. A 7x spread between analyst estimates
is not a data quality problem — it is a definitional problem.

The boundary defined here was locked on **2026-03-23**, before any analyst data was
collected or any reconciliation logic was written. This sequencing is deliberate: it
prevents anchor estimate shopping (Pitfall 1 in the research notes), where a model builder
unconsciously chooses a scope definition that produces a "round" or "consensus-looking"
total. The definition stands independent of the estimates it will be compared against.

## Scope Definition

**Locked scope statement (verbatim from config/industries/ai.yaml):**

> AI software platforms, AI infrastructure (cloud compute dedicated to AI workloads,
> AI-specific hardware including GPUs, TPUs, and AI accelerators), and AI services/consulting.
> Excludes: general IT infrastructure not dedicated to AI workloads, AI-enabled consumer
> products where AI is embedded (e.g., smartphone cameras), general enterprise software
> with AI features added post-hoc, and semiconductor foundry revenue not specific to AI chips.

The scope covers four segments modeled separately and reported both independently and as a total:

### What We Include

- **AI Hardware:** GPUs, TPUs, AI accelerators, and AI-specific ASICs (application-specific
  integrated circuits). This segment covers dedicated silicon manufactured for AI training
  and inference workloads — not general-purpose processors that happen to run AI code.
  Primary examples: NVIDIA Data Center GPUs (H100, B100, Blackwell series), AMD Instinct
  series, Google TPUs, custom AI chips at hyperscalers. Intel Gaudi accelerators and
  emerging AI ASIC vendors are included on a partial basis where AI revenue is separately
  disclosed or estimable.

- **AI Infrastructure:** Cloud compute capacity dedicated to AI workloads — hyperscaler
  GPU clusters (Azure AI, AWS AI/ML services, Google Cloud AI), AI-specific data center
  build-out, and networking infrastructure (InfiniBand, optical interconnects) purchased
  specifically for AI training clusters. The defining criterion is workload dedication:
  general-purpose cloud compute that can run AI workloads but is not primarily purchased
  for AI is excluded.

- **AI Software and Platforms:** Foundation model APIs (OpenAI, Anthropic, Cohere, AI21),
  AI SaaS applications built on LLMs, MLOps platforms, enterprise AI tools, and AI-native
  software companies. This segment captures the software layer of the value chain —
  everything from model weights and training pipelines to end-user AI application subscriptions.
  Representative companies: Palantir AIP, C3.ai, Salesforce Einstein/Agentforce, ServiceNow
  Now Assist, Workday AI, UiPath AI.

- **AI Adoption:** Enterprise AI deployment spend, AI consulting and integration services,
  and AI-driven process transformation costs. This segment captures the demand side of the
  value chain — what enterprises spend to deploy, integrate, and operate AI systems across
  their business functions. Includes system integrator fees (Accenture AI, IBM watsonx
  consulting), change management, training, and AI-enabled workflow transformation.

### What We Exclude

- General IT infrastructure not dedicated to AI workloads (commodity cloud compute,
  traditional data centers, general networking)
- Consumer AI products where AI is embedded but not separately priced (smartphone
  cameras, smart speakers, AI-enhanced consumer electronics)
- General enterprise software with AI features added post-hoc (e.g., a CRM that added
  an AI suggestion feature to an existing product)
- Semiconductor foundry revenue not specific to AI chips (TSMC wafer revenue for
  automotive, mobile, or general compute chips)
- AI economic value (productivity gains, GDP uplift from AI adoption) — this model
  measures the AI technology market size, not the economic impact of AI

## Analyst Scope Comparison

The following table documents every analyst firm in the scope mapping table, their
scope alignment to our definition, the coefficient used to normalize their published
figure to our scope, and what their estimate includes or excludes.

| Analyst Firm | Scope Alignment | Scope Coefficient | Coefficient Range | Their Scope | Our Adjustment |
|---|---|---|---|---|---|
| IDC | close | 1.00 | [0.95, 1.05] | Enterprise AI software, infrastructure, services | Minimal — excludes hardware (we add hardware segment) |
| Gartner | broad | 0.18 | [0.15, 0.22] | All AI-adjacent technology spending | Major reduction — includes all IT infrastructure, AI-enabled devices |
| Grand View Research | partial | 1.15 | [1.05, 1.25] | AI software, ML, NLP, CV — software focus | Scale up — their narrow software scope misses hardware + infrastructure |
| Statista | partial | 0.85 | [0.75, 0.95] | Enterprise AI software + services + hardware | Minor reduction — aggregates multiple surveys, some infrastructure double-counting |
| Goldman Sachs | partial | 0.70 | [0.60, 0.80] | Generative AI subset only (GenAI software, GenAI infra, chips) | Scale up then adjust — their GenAI focus excludes traditional ML software |
| Bloomberg Intelligence | partial | 0.90 | [0.80, 1.00] | Enterprise GenAI software/services + hyperscaler CapEx + AI chips | Minor reduction — excludes traditional analytics and non-generative AI tools |
| McKinsey Global Institute | broad | 0.25 | [0.20, 0.30] | GenAI economic VALUE across all sectors (not market size) | Major reduction — their number is economic value potential, not technology market spend |
| CB Insights | close | 0.95 | [0.90, 1.00] | AI software companies + infrastructure + hardware (funding-based) | Minimal — based on company-level revenue/funding data; good segment coverage |

**Why IDC is the closest match:** IDC's Worldwide AI Spending Guide uses a
narrow enterprise definition that maps directly to our ai_infrastructure + ai_software +
ai_adoption segments. The main gap is AI hardware (GPUs, TPUs), which IDC historically
excluded. Our scope_coefficient of 1.0 reflects that IDC's enterprise-only numbers are
approximately comparable to our non-hardware segments combined.

**Why Gartner requires heavy adjustment (0.18x):** Gartner's AI market definition
encompasses all AI-adjacent technology spending — including all cloud infrastructure CapEx
that might run AI workloads, all enterprise software with any AI feature, and all
AI-enabled devices. Their 2025 estimate of approximately $1.5 trillion includes categories
that are many multiples of the direct AI technology market. The 0.18x coefficient reflects
that direct AI technology spending is approximately 18% of Gartner's all-inclusive total.

**Why McKinsey requires the heaviest adjustment (0.25x):** McKinsey Global Institute
publishes economic value potential (productivity gains, GDP impact) — not market size. Their
$4.4 trillion figure is an estimate of economic value that AI could unlock, not what
organizations spend on AI technology. The 0.25x coefficient converts this to a rough market
size equivalent, but the confidence interval is very wide.

## Overlap Handling

The four segments are not mutually exclusive. Three documented overlap zones require
adjustment to produce a defensible total:

**Zone 1: hardware_to_infrastructure (20-30% of ai_infrastructure)**

GPU revenue is counted in the ai_hardware segment (as chip manufacturer revenue) and
again in the ai_infrastructure segment (as cloud provider CapEx for AI clusters). When
AWS buys $10 billion of NVIDIA GPUs, that $10 billion appears in NVIDIA's ai_hardware
revenue AND in the AWS capital expenditure that eventually shows up in ai_infrastructure.
The documented overlap range is 20-30% of ai_infrastructure revenue.

**Zone 2: software_to_adoption (15-25% of ai_adoption)**

Enterprise AI SaaS license fees are counted in the ai_software segment (as the software
vendor's revenue) and again in the ai_adoption segment (as the enterprise's AI deployment
spend). When Salesforce sells an Agentforce subscription, that revenue appears in
Salesforce's ai_software revenue AND in the enterprise customer's ai_adoption spend.
The documented overlap range is 15-25% of ai_adoption revenue.

**Zone 3: infrastructure_to_software (10-15% overlap)**

Cloud AI platform revenue (AWS SageMaker, Azure Machine Learning, Google Vertex AI) spans
both the infrastructure layer (compute, storage) and the software layer (managed ML
services, foundation model hosting). The documented overlap range is 10-15% of the
combined infrastructure + software total.

**Adjusted total method:**

Adjusted total = sum(segments) - midpoint(overlap_ranges)

Both the unadjusted sum (showing each segment at full value) and the adjusted total
(accounting for mid-range overlap estimates) are reported in all outputs. This transparency
allows analysts to audit the double-counting assumption and apply their own overlap
adjustments. The overlap ranges are stated as documentation, not as precise estimates —
the midpoint is used for the adjusted figure but the range is reported for sensitivity.

## Reconciliation Approach

After the market boundary definition is locked (this document, this phase), analyst
estimates are collected in `data/raw/market_anchors/ai_analyst_registry.yaml` (Plan 08-02).
The reconciliation algorithm (Plan 08-04) applies a scope-normalized median:

1. For each analyst estimate, retrieve the `scope_coefficient` from the scope_mapping_table
2. Multiply the published estimate by the scope_coefficient to normalize to our scope
3. Per (estimate_year, segment) group, compute the 25th percentile, median, and 75th percentile
   of all normalized estimates
4. The median is the point estimate; the 25th/75th band is the reported uncertainty range
5. Deflate nominal USD values to constant 2020 USD using the GDP deflator from World Bank

Implementation is in `src/ingestion/market_anchors.py`. The Parquet output schema is
defined in `src/processing/validate.py` as `MARKET_ANCHOR_SCHEMA`.

## Scope Coefficient Sensitivity

All partial and broad scope firms have `scope_coefficient_range` values in the
scope_mapping_table (see config/industries/ai.yaml). The reconciliation should be
run at three settings:

- **Low:** Use the lower bound of each firm's scope_coefficient_range
- **Mid:** Use the point estimate scope_coefficient (standard run)
- **High:** Use the upper bound of each firm's scope_coefficient_range

This produces a sensitivity band showing how much the normalized estimate changes
if the scope alignment assumption is tightened or loosened. The band is reported
alongside the central estimate in the final ground truth time series.

## Original v1.0 Methodology Note

This document supersedes the market boundary section of the v1.0 METHODOLOGY.md, which
used a value chain composite index multiplied by an anchor-calibrated coefficient. That
approach is deprecated in Phase 9. The v1.0 value_chain section in ai.yaml is preserved
for continuity but replaced by the analyst-anchored reconciliation approach documented here.

All monetary series continue to be expressed in **2020 constant USD** (deflated using the
World Bank GDP deflator, NY.GDP.DEFL.ZS). Nominal values are stored alongside real values
in all output Parquet files, allowing downstream tools to display whichever is more appropriate.

## Revision Policy

This boundary definition was locked on **2026-03-23**. Any revision requires:

1. Documenting the specific reason for revision with reference to new information
2. Updating `definition_locked` in config/industries/ai.yaml to the revision date
3. Re-running all downstream reconciliation (Plan 08-04 output)
4. Re-running all model calibration that depends on the market anchor series (Phase 9+)
5. Adding a revision history entry to this document

### Revision History

| Date | Author | Change | Reason |
|------|--------|--------|--------|
| 2026-03-23 | Initial | Locked definition (v1.1 milestone) | Phase 8 boundary lock — first commit before any data collection |

---

*This document is the methodological companion to `config/industries/ai.yaml`. The
scope_statement in ai.yaml and the Scope Definition section above are kept in sync.
Any change to ai.yaml's market_boundary section must be reflected here with a revision
history entry.*
