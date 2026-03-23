# Pitfalls Research

**Domain:** AI Industry Economic Valuation — Model Rework (Proxy-to-Real-Data Transition)
**Researched:** 2026-03-23
**Confidence:** HIGH (critical pitfalls verified across multiple sources; v1.1-specific pitfalls from domain research + v1.0 carryover from prior research)

---

## Context: What Changed From v1.0

v1.0 used a PCA composite → value chain multiplier approach and produced flat/unrealistic forecasts.
v1.1 replaces this with real market data anchoring (company filings, published estimates, DCF/multiples for private companies) while preserving the existing data pipeline infrastructure. The pitfalls below are organized by what is *new* in v1.1 and what carries over from v1.0 with updated severity.

---

## Critical Pitfalls (v1.1 New)

### Pitfall 1: Anchor Estimate Shopping — Choosing the Number That Fits

**What goes wrong:**
When switching to real-data anchoring, the builder surveys analyst reports (IDC, Gartner, McKinsey, Grand View Research, Statista) and subconsciously chooses whichever published estimate makes the model's output look plausible. The 2025 AI market estimates range from ~$254 billion (narrow software definition) to $1.5–1.76 trillion (Gartner's broad spending definition including all AI-adjacent infrastructure). That is a 7x spread. Picking the anchor that fits the model is confirmation bias, not methodology. The result looks valid in the demo and falls apart under any methodological scrutiny.

**Why it happens:**
The builder needs *some* anchor to calibrate the model against real market size. Multiple credible sources exist. The temptation is to choose the one that validates the existing output rather than choosing based on definitional consistency with the project's own market boundary.

**How to avoid:**
Choose the anchor source *before* looking at what the model outputs. The anchor choice must follow from the market boundary definition (locked in config), not from model output convenience. Document the anchor in `ASSUMPTIONS.md` with: (a) which report was chosen, (b) what definition it uses, (c) why that definition matches the project's scope, (d) what the model output would be under the next-closest alternative anchor. If the two anchors produce estimates that differ by more than 30%, the market boundary definition needs to be made more precise first.

**Warning signs:**
- The anchor source is chosen after the model produces its first output
- The methodology paper does not explain why a specific report was chosen over alternatives
- Gartner's trillion-dollar figure and IDC's hundred-billion figure appear in the same pipeline without harmonization
- The model's output changes significantly depending on which of two "valid" anchors is used

**Phase to address:**
Phase 1 — Real Data Anchoring Design. Anchor selection is a design decision, not a calibration step.

---

### Pitfall 2: Broken Pipeline Algebra After Model Rework

**What goes wrong:**
The existing pipeline infrastructure is preserved (the requirement says so), but the model logic is replaced. The connective tissue — how the model output flows into dashboard KPIs, how the value chain multiplier was wired, how SHAP values are computed — was designed for PCA composite scores, not real dollar estimates. After the rework, the pipeline appears to run without errors, but the dashboard displays numbers that have been passed through a stale transformation stage designed for the old model. A value that was once a normalized PCA index (bounded roughly 0–1) is now a raw revenue figure (in billions) flowing through the same arithmetic as before. The output is numerically wrong but the code throws no exceptions.

**Why it happens:**
Refactoring "preserves the pipeline" often means the new model output is dropped into the old pipeline at the same connection point. Any intermediate transformation that assumed the old output's scale or interpretation silently corrupts the downstream result. This is a classic interface contract violation: the caller (dashboard/reporting) assumed a different type/unit than the callee (new model) now produces.

**How to avoid:**
Before writing any new model code, audit every downstream consumer of the existing model output: what does it expect (unit, scale, range)? Create an explicit interface contract: `model_output: float (USD billions, 2020 real)`. When the new model is plugged in, write an integration test that asserts the new output matches the interface contract. Remove or replace every transformation stage that assumed the old PCA index scale. Do not add a conversion factor to "bridge" old and new — replace the stage.

**Warning signs:**
- Dashboard numbers look reasonable but don't match independently computed estimates
- The `value_chain_multiplier` module is still in the codebase after the rework and has not been explicitly retired or replaced
- SHAP values sum to a number that doesn't correspond to a dollar figure or percentage
- The pipeline runs green in CI but the integration test for `model_output` units was never written

**Phase to address:**
Phase 2 — Ground-Up Model Rework. Interface contract audit must precede any new model code.

---

### Pitfall 3: AI Revenue Attribution Double-Counting for Conglomerates

**What goes wrong:**
Microsoft, Google, Nvidia, and Amazon each receive AI revenue attribution. But these companies transact with each other at scale: Nvidia sells GPUs to Microsoft Azure, Microsoft Azure runs OpenAI workloads, OpenAI buys Microsoft Azure compute. Bloomberg's 2026 circular deal analysis labeled these "AI circular deals" — the same capital flows between the same players and gets counted as AI revenue at each node. If the model attributes AI revenue at both the chip layer (Nvidia GPU sales) and the cloud layer (Azure AI Services revenue) and the application layer (Copilot subscriptions), it is triple-counting the same underlying economic activity. A market size estimate built on top of company-level AI revenue attribution will be meaningfully inflated unless the value chain layer is made explicit.

**Why it happens:**
Revenue attribution is done company by company from public filings. Each filing is internally correct. The analyst aggregating across companies fails to account for the fact that B2B AI transactions appear in both the seller's revenue and the buyer's cost/service revenue. There is no standard accounting treatment that flags "this AI revenue was earned from another AI company."

**How to avoid:**
When aggregating AI revenue across companies, categorize each company by its value chain position: (a) Infrastructure/Chip layer (Nvidia, AMD), (b) Cloud/Platform layer (Microsoft Azure AI, Google Cloud AI, AWS), (c) Application/SaaS layer (Salesforce AI, Adobe Firefly, etc.), (d) End-market layer (companies using AI to sell non-AI products). Choose *one layer* as the primary economic measure, or sum across layers with explicit documentation that this is a gross rather than value-added measure. The methodology paper must state whether the market size estimate is "gross AI economic activity" (sum across layers) or "value-added AI revenue" (one layer only). These are both valid; conflating them is not.

**Warning signs:**
- The company-level AI revenue aggregation produces a total that exceeds published total-market estimates by 2x or more
- Nvidia and Microsoft both appear as "AI revenue" companies without a note about which layer each occupies
- The model treats all company AI revenue figures as additive without a layer decomposition
- No mention of "value chain position" or "gross vs. value-added" in the methodology paper

**Phase to address:**
Phase 3 — AI Revenue Attribution. Layer taxonomy must be designed before data collection starts.

---

### Pitfall 4: Segment Reporting Opacity Creates False Precision in Attribution

**What goes wrong:**
Nvidia reports Data Center revenue (~91% of total revenue in Q4 FY2026) but does not break this into "AI vs. non-AI data center." Microsoft reports "Microsoft Cloud" revenue but the AI portion is embedded across Azure, Office 365, and Copilot without clean separation. Meta reports advertising revenue that is AI-enhanced but not AI-labeled. The temptation is to take a "% of segment" heuristic (e.g., "80% of Nvidia Data Center revenue is AI") and treat it as a data point. This heuristic will vary by analyst and year, producing a false precision: a model that claims to be data-driven but whose core inputs are analyst guesses dressed as data.

**Why it happens:**
Company filings do not map to "AI revenue" as a concept. The analyst needs *some* number, so they apply a reported or estimated percentage. The percentage gets embedded in the pipeline and is never revisited, even as segment definitions change in subsequent filings.

**How to avoid:**
Treat attribution percentages as model parameters with explicit uncertainty ranges, not data points. In the pipeline, store `nvidia_datacenter_ai_pct: {estimate: 0.85, low: 0.70, high: 0.95, source: "Morgan Stanley Q3 2025", vintage: "2025-11"}` rather than a bare float. Propagate this uncertainty into the final market size estimate using Monte Carlo simulation or at minimum sensitivity analysis. The methodology paper must show how the total market size changes as attribution percentages vary across their plausible ranges. If the final estimate changes by more than 20% across the plausible range, the uncertainty is material and must be disclosed as a headline caveat.

**Warning signs:**
- Attribution percentages are stored as bare floats in config without source or vintage
- The methodology paper uses "based on disclosed revenue" for companies that do not disclose AI revenue separately
- The final estimate does not have a sensitivity table showing variation under different attribution assumptions
- Attribution percentages were set at project start and never updated when Q4 2025 or Q1 2026 filings were released

**Phase to address:**
Phase 3 — AI Revenue Attribution. Uncertainty parameterization must be part of the data model design.

---

### Pitfall 5: Private Company Valuation Multiples Are Not Comparable Across Companies or Time

**What goes wrong:**
Private AI company valuations range from 3.6x to 225x revenue (Aventis Advisors, 2025 data). Applying "the AI multiple" to a revenue estimate produces a valuation figure that can be anywhere in a 60x range depending on which comparables were chosen. The model appears to produce a private company market size figure, but that figure is almost entirely determined by which comparables the builder selected — not by any underlying economic reality. Worse, multiples shift rapidly with market sentiment: a 50x multiple applied to 2023 data may be a 15x multiple applied to 2026 data after the valuation reset. A model that bakes in a fixed multiple will drift out of calibration silently.

**Why it happens:**
Private company valuations are opaque by design. There is no public clearing price. Builders use publicly reported funding round valuations (which are not transaction prices) or apply public company multiples with a "private discount." Both approaches have well-documented limitations in academic and practitioner literature, but there is no clean alternative.

**How to avoid:**
(a) Use a range of multiples, not a point estimate, and report the resulting valuation range. (b) Segment private companies by maturity (pre-revenue / early-revenue / growth-stage / pre-IPO) and apply different multiples to each. (c) Source multiples from the most recent available comparable transactions, not from general "AI multiple" reports — funding rounds from 2021-2022 reflect a sentiment regime that no longer exists. (d) Store the multiple as a parameter with vintage date in config, and build a periodic review step into the project maintenance workflow. (e) In the methodology paper, explicitly state that private company valuations are the highest-uncertainty component and report sensitivity to multiple choice.

**Warning signs:**
- A single revenue multiple is applied to all private AI companies regardless of stage
- The multiple was sourced from a 2021 or 2022 report and has not been updated
- The private company contribution to total market size is larger than the public company contribution without an explicit explanation of why
- No sensitivity analysis shows how total market size changes across the plausible multiple range

**Phase to address:**
Phase 4 — Private Company Valuation. Multiple parameterization and vintage dating are required inputs, not optional refinements.

---

### Pitfall 6: Backtesting Against Analyst Consensus Is Not Backtesting

**What goes wrong:**
The "backtesting and validation" requirement is met by comparing model forecasts to published analyst consensus (IDC, Gartner, McKinsey estimates for 2022-2024). This is not backtesting. Analyst consensus is not ground truth — it is another model's output. If the model aligns well with analyst consensus, it means the model agrees with analysts, not that the model is accurate. True backtesting requires comparing forecasts to actual realized outcomes: actual AI company revenues filed in 10-Ks, actual national accounts GDP contributions where available, actual hardware shipment volumes. These "actual" figures are sparse and lagged, which is why the temptation to use analyst consensus is strong, but using it as ground truth is a methodological error.

**Why it happens:**
True ground truth for "AI industry size" as an aggregate concept does not exist cleanly. National accounts data lags by 18-24 months. Company filings are available but require aggregation. The path of least resistance is to use a published market size estimate as if it were measured data.

**How to avoid:**
Distinguish three validation tiers: (a) **Hard validation** — compare model components to directly measurable actuals: Nvidia Data Center revenue from 10-K filings, AWS AI Services revenue from quarterly reports, VC investment totals from PitchBook/Crunchbase. These are real numbers. (b) **Soft validation** — compare total market size to analyst consensus with explicit acknowledgment that both are estimates. (c) **Directional validation** — confirm that the model's growth rate is directionally consistent with observable proxies (patent filings, Google Trends, R&D spend indices). Document which tier each validation belongs to in the methodology paper. Do not present soft or directional validation as if it were hard validation.

**Warning signs:**
- The backtesting section of the paper references IDC or Gartner as "actuals"
- MAPE and R² are computed against analyst estimates rather than filed company revenues
- No filed 10-K or 20-F data appears in the validation dataset
- The validation dataset was assembled by the same process that assembled the training data (selection bias)

**Phase to address:**
Phase 5 — Backtesting and Diagnostics. Ground truth source taxonomy must be written before validation code is written.

---

### Pitfall 7: Diagnostic Metrics That Look Good But Measure Nothing Real

**What goes wrong:**
After the model rework, the diagnostics tab shows MAPE, R², and residual plots that look healthy. But these metrics are computed against the training/in-sample data (because the original v1.0 had no real actuals to measure against — this is called out explicitly in the PROJECT.md). After the rework, if the test set is not carefully constructed from actual filed revenue figures with strict temporal discipline, the same problem persists under a new facade. A MAPE of 8% looks impressive; if it is in-sample MAPE computed against the same data the model was fitted on, it is meaningless.

**Why it happens:**
The dashboard was built to show diagnostics, and the diagnostics infrastructure exists. The temptation is to populate the diagnostics with the numbers the infrastructure can already compute — in-sample fit statistics — rather than rebuilding the evaluation dataset from real actuals, which is harder.

**How to avoid:**
Treat the diagnostics dataset as a first-class artifact. It is not derived from the training data; it is assembled from independently sourced actual figures (company filings, national accounts, verified market data) and stored separately. The diagnostic pipeline computes metrics by comparing model outputs to this independent actuals dataset. If independent actuals are only available for a subset of the model's scope, report diagnostics only for that subset and clearly label the rest as "no validation data available." A narrow honest diagnostic is worth more than a broad misleading one.

**Warning signs:**
- The diagnostics dataset is generated by the same pipeline stage as the training data
- MAPE is reported for years where no filed actual data exists
- The test set dates overlap with the training set
- Removing one data point from the test set changes MAPE by more than 5 percentage points (sample too small to be meaningful)

**Phase to address:**
Phase 5 — Backtesting and Diagnostics. Independent actuals dataset must be assembled before any diagnostic metrics are computed.

---

### Pitfall 8: Basic Dashboard Tier That Misleads by Oversimplifying

**What goes wrong:**
The Basic tier is designed for quick market intelligence — total AI market cap, growth rates, expected value, segment breakdown. The risk is presenting a single "AI Market Cap: $X trillion" headline number without the context required to interpret it: What definition of AI? Which year? Real or nominal? What level of uncertainty? A technically unsophisticated user sees a clean headline number and treats it as authoritative. A technically sophisticated user sees a clean headline number without methodology context and dismisses the tool entirely. Both outcomes are bad.

**Why it happens:**
Dashboard design optimizes for clean presentation. Context is "cluttered." The builder defers methodology footnotes to the Normal/Expert tier and strips them from Basic. The result is a number that looks precise but is misleading without its assumptions.

**How to avoid:**
Every headline number on the Basic tier must carry: (a) a vintage date ("as of Q4 2025 filings"), (b) a one-line scope label ("AI software + hardware + cloud, excluding AI-enabled non-AI products"), (c) a range or confidence indicator that communicates uncertainty without overwhelming. This does not have to be a full CI fan chart — a simple "(range: $X–$Y)" next to the headline figure is sufficient. The range should reflect the sensitivity to anchor choice and attribution assumptions, not just statistical model uncertainty. Test the Basic tier with a user who is not familiar with the project and ask them what they would conclude from the headline number — if their conclusion is wrong, the display needs more context.

**Warning signs:**
- Basic tier shows a single dollar figure with no range or uncertainty indicator
- The scope of the headline number is not visible without clicking through to Normal/Expert tier
- The vintage date of the underlying data is not shown
- A peer reviewer's first question after seeing the Basic tier is "what does this number actually measure?"

**Phase to address:**
Phase 6 — Basic Dashboard Tier. Context requirements must be defined before design begins, not added after.

---

### Pitfall 9: Stale v1.0 PCA Pipeline Code Interfering With v1.1 Model

**What goes wrong:**
The v1.0 PCA composite → value chain multiplier code is "preserved as infrastructure" but the new model is supposed to replace its output. During development, both code paths remain active. The new model runs and produces real-data-anchored estimates; the v1.0 path also runs and produces the old flat forecasts. A subtle wiring error — a mis-patched import, a config flag that wasn't updated — causes the dashboard to display the v1.0 output under the v1.1 label. The developer looks at the dashboard, sees a flat forecast, and concludes the new model isn't working. Hours are spent debugging the new model when the bug is actually a routing error in the pipeline.

**Why it happens:**
Keeping the old code active "for reference" or "as a fallback" during a model rework is a sensible precaution. But it creates two code paths that can be confused. Without explicit model versioning in the pipeline config, the routing between old and new is ambiguous.

**How to avoid:**
Add a `model_version` flag to the pipeline config (`v1.0_pca` vs. `v1.1_real_data`) and assert at the start of every downstream stage that the expected version is active. The v1.0 code should remain in the codebase but be explicitly gated behind the `v1.0_pca` flag so it can never run in `v1.1_real_data` mode. Write a test that runs the full pipeline end-to-end with `model_version=v1.1_real_data` and asserts that no v1.0 PCA index values appear in the output artifact. Do not delete the v1.0 code until the v1.1 model has passed all backtesting requirements.

**Warning signs:**
- The dashboard shows forecast trajectories that are suspiciously flat (matches the known v1.0 failure mode)
- The `value_chain_multiplier` module is imported anywhere in the v1.1 code path
- There is no config flag distinguishing which model version is active
- CI passes but the integration test for output shape/range was not updated to reflect v1.1 expected values

**Phase to address:**
Phase 2 — Ground-Up Model Rework. Model version gating must be implemented before the new model produces its first output.

---

## Critical Pitfalls (Carried Over From v1.0, Updated Severity)

### Pitfall 10: Data Leakage in Time Series Validation

**What goes wrong:**
The ML models report high in-sample accuracy but perform poorly on true out-of-sample data because future data was seen during training. With the v1.1 rework, the risk increases: the new backtesting dataset will include filed revenue actuals that were published *after* the model training period. If these are not handled with strict temporal discipline, the model inadvertently trains on the future.

**Why it happens:**
Standard scikit-learn idioms (fit on full data, then split) are not valid for time series. Preprocessing transformers fitted on the full dataset leak future scale/distribution information backward.

**How to avoid:**
Use `TimeSeriesSplit` only. Fit all preprocessors (scalers, imputers) exclusively on training data. For Prophet, use `cross_validation()` with explicit `initial`, `period`, `horizon`. In v1.1 specifically: the backtesting actuals dataset must have a strict temporal cutoff that pre-dates the model training cutoff.

**Warning signs:**
- Validation RMSE is much lower than historical data variability implies
- `train_test_split(shuffle=True)` appears anywhere in a time series pipeline
- Filed revenue actuals from 2025-2026 are in the training data despite the model claiming to forecast those years

**Phase to address:**
Phase 2/5 — Model Rework and Backtesting.

---

### Pitfall 11: Undefined or Inconsistent Market Boundary

**What goes wrong:**
AI market size estimates from major analyst firms for 2025 range from ~$254 billion (narrow software definition) to $1.76 trillion (Gartner's broad definition including all AI-adjacent infrastructure and spending). Mixing sources that use different definitions produces a pipeline that is internally inconsistent. The v1.1 rework anchors on real data — but real data from which definition?

**Why it happens:**
Data collection starts before scope is locked. Each source uses a different definition. The builder collects from all sources and harmonizes later (or never).

**How to avoid:**
The market boundary definition must be locked in config before any v1.1 data collection begins. It must explicitly state which Gartner/IDC/McKinsey definition it most closely matches and why.

**Warning signs:**
- Gartner trillion-dollar figures and IDC hundred-billion figures both appear in the pipeline
- The market definition changes between the ASSUMPTIONS.md and the dashboard label
- Model output changes significantly when switching between two "valid" anchor sources

**Phase to address:**
Phase 1 — Data Architecture. No data collection until boundary is defined.

---

### Pitfall 12: Nominal/Real Conflation Across Time

**What goes wrong:**
v1.0 already specified 2020 constant USD in the pipeline. The v1.1 additions — company filing revenue data, analyst report estimates, DCF valuation figures — will arrive in nominal terms for the year of the filing. If deflation is not applied consistently to all new data sources, the pipeline will silently mix real and nominal values.

**How to avoid:**
All new data entering the v1.1 pipeline must be deflated using the same GDP deflator series (World Bank NY.GDP.DEFL.ZS) used in v1.0. Tag new columns with `_nominal_YYYY` before deflation and `_real_2020` after. Write a test that asserts no `_nominal_` column reaches the model feature matrix.

**Phase to address:**
Phase 1 — Data Pipeline (applies to all new data sources).

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode attribution percentage as a bare float | Fast to implement | Cannot propagate uncertainty; breaks silently when filing data updates | Never — parameterize with source and vintage |
| Validate against analyst consensus instead of actuals | Validation section exists in paper | Methodologically invalid; any quant reviewer will flag it | Only acceptable as a preliminary sanity check labeled "directional only" |
| Keep v1.0 PCA code running alongside v1.1 without version flag | "Safe" fallback | Silent routing errors produce v1.0 output under v1.1 label | Only during initial scaffolding, with explicit gating from day one |
| Apply a single revenue multiple to all private companies | Simple to compute | Multiple range is 3.6x–225x; single point obscures all uncertainty | Never without a range and vintage date |
| Compute MAPE against in-sample data | Diagnostics populate immediately | Metrics are meaningless; readers will not trust the methodology paper | Never — in-sample metrics should be labeled "in-sample" and not featured |
| Strip all context from Basic tier for "clean" presentation | Looks professional | Headline number is misleading without scope/vintage/range | Never — Basic tier must always show scope label and range |

---

## Integration Gotchas

Common mistakes when connecting new v1.1 data sources to the existing pipeline.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| SEC EDGAR (company filings) | Scraping HTML from investor pages (fragile, breaks on redesign) | Use EDGAR's official XBRL API at `data.sec.gov`; pin to specific CIK and form type |
| Company segment reports (Nvidia, Microsoft, Google) | Treating "Data Center" or "Cloud" revenue as equivalent to "AI revenue" | Source the specific "AI revenue" disclosures where they exist (e.g., Microsoft's $13B AI annual run rate disclosure); store as `source=management_commentary` not `source=filing` |
| AI market analyst reports (Gartner, IDC) | Using published figures without documenting which definition was used | Store source, publication date, definition excerpt, and URL alongside every anchor figure in config |
| Private company funding data (Crunchbase, PitchBook) | Treating funding round valuation as enterprise value or revenue multiple | Funding round valuation is a post-money valuation at a specific equity class; it is not comparable to revenue multiples without ARR disclosure |
| Existing v1.0 Parquet cache | Adding new fields to existing Parquet without schema versioning | Use a schema version field in the Parquet metadata; never modify the v1.0 cache in place; write v1.1 data to a new artifact |
| World Bank / OECD (existing) | Reusing v1.0 fetched data without checking if new indicator codes are needed for v1.1 | Audit which v1.0 indicators are still relevant; identify which new indicators v1.1 needs; fetch and cache separately |

---

## Performance Traps

Patterns that work during development but degrade as the real-data pipeline grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Fetching company filing data on every pipeline run | Pipeline takes 10+ minutes; EDGAR rate limits trigger | Cache all filing data with fetch timestamp; only re-fetch if cache is stale (>30 days) | On second run if no caching is implemented |
| Running Monte Carlo simulation for attribution uncertainty in real-time | Dashboard tab takes 30+ seconds to load | Pre-compute Monte Carlo results at pipeline run time; store percentile outputs; dashboard reads stored results | Immediately with 10,000+ simulations |
| Storing all private company valuations in memory during sensitivity analysis | Memory spike; kernel crash in Jupyter notebook | Stream through valuations in batches; only keep aggregates in memory | At ~50K company-year observations |
| No incremental update logic for new quarterly filings | Full pipeline re-run takes hours when only Q4 data changed | Add a `--since` flag to the data fetch stage; only re-process new data and downstream dependents | When quarterly filing updates become routine |

---

## UX Pitfalls

Common user experience mistakes specific to the v1.1 dashboard tiers.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Basic tier shows market cap without scope label | User reports the number as "the AI market" without knowing it excludes AI-enabled non-AI products | Always show a one-line scope label directly below the headline number |
| Attribution uncertainty not shown in Normal tier | User treats the AI revenue attribution figures as measured data | Show a "±" range on all attribution figures; tooltip explains it reflects attribution assumption uncertainty |
| Expert tier diagnostics show only in-sample metrics | Sophisticated users catch this immediately and lose confidence | Label all metrics with [in-sample] or [out-of-sample]; only feature out-of-sample metrics prominently |
| No data vintage shown anywhere | Analyst cannot judge if the data is current enough for their use case | Show a "Data as of: [date]" line for every data source in a sidebar or footer |
| Segment breakdown pie chart without showing uncertainty | Pie chart implies exact precision that doesn't exist in AI segment attribution | Use bar charts with error bars instead of pie charts for segment breakdown |
| "AI Market Cap" label without defining what "cap" means | Ambiguous — could mean market capitalization of AI companies, or total AI market size | Use explicit label: "Total AI Market Size" or "AI Company Market Capitalization" — never conflate the two |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces for v1.1.

- [ ] **Anchor selection:** The anchor estimate source is documented in `ASSUMPTIONS.md` *with* its market definition and why it matches the project scope — verify by reading the ASSUMPTIONS.md entry; it should include the source URL, definition text, and an alternative anchor comparison
- [ ] **Attribution parameterization:** Every AI attribution percentage is stored with source, vintage date, and low/high range — verify by grepping for bare float attribution values in config; none should exist
- [ ] **Value chain layer taxonomy:** Every company in the attribution dataset has an assigned layer (chip/cloud/application/end-market) — verify by checking the company data schema for a `value_chain_layer` field
- [ ] **Pipeline version gating:** The v1.0 PCA code path is gated behind a config flag and cannot run in `v1.1_real_data` mode — verify by setting `model_version=v1.1_real_data` and confirming no PCA composite values appear in the output
- [ ] **Backtesting ground truth:** The validation dataset consists of filed revenue actuals, not analyst consensus — verify by checking the source field on every row of the validation dataset
- [ ] **Diagnostic metrics:** All featured metrics are out-of-sample — verify that the test set dates are strictly later than all training data dates
- [ ] **Basic tier context:** Every headline number has a scope label, vintage date, and range — verify by reviewing the Basic tier with someone unfamiliar with the project
- [ ] **Nominal/real consistency:** All v1.1 data sources have been deflated to 2020 USD before entering the model — verify via column naming convention (`_real_2020`) and the deflation pipeline test
- [ ] **Private company multiple vintage:** Revenue multiples have a date and will trigger a review reminder — verify that the multiple parameter in config has a `vintage_date` field and that there is a comment noting when to update it

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Anchor was chosen to fit model output, not for definitional consistency | HIGH | Stop; lock market boundary in config; reassess which anchor is definitionally consistent; if model output is far off, the model needs recalibration, not anchor adjustment |
| Pipeline algebra broken after rework (stale transforms) | MEDIUM | Audit every downstream consumer of the new model output; add interface contract assertion; fix stale transforms one at a time; do not patch with conversion factors |
| Double-counting across value chain layers discovered in methodology review | HIGH | Rebuild attribution taxonomy from scratch with explicit layer assignment; pick one layer as primary measure; recompute all attribution figures |
| Backtesting was done against analyst consensus, not actuals | MEDIUM | Assemble independent actuals dataset from company filings; re-run validation; update all reported metrics; relabel any consensus-based comparisons as "directional validation" |
| Private company multiples are stale (2021-2022 vintage) | MEDIUM | Source current comparable transaction multiples; re-parameterize; re-run sensitivity analysis; note the change in CHANGELOG |
| v1.0 PCA code produced output under v1.1 label due to routing error | LOW | Add model version flag; trace the routing error; re-run pipeline with correct version; verify output passes interface contract assertion |
| Basic tier misleads users due to missing context | LOW | Add scope label, vintage date, and range to headline number; this is a display change only and does not require model changes |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Anchor estimate shopping | Phase 1: Data Architecture | ASSUMPTIONS.md shows anchor chosen before first model run |
| Broken pipeline algebra after rework | Phase 2: Model Rework | Interface contract test passes; `value_chain_multiplier` not imported in v1.1 path |
| AI revenue double-counting | Phase 3: Revenue Attribution | Value chain layer field exists for every company; gross vs. value-added measure is documented |
| Segment reporting opacity / false precision | Phase 3: Revenue Attribution | Attribution percentages stored with source, vintage, and range; sensitivity table in methodology paper |
| Private company multiple comparability | Phase 4: Private Valuation | Multiple parameters have vintage dates; sensitivity analysis shows market size range |
| Backtesting against consensus, not actuals | Phase 5: Backtesting | Validation dataset source field is all filed actuals; no IDC/Gartner figures labeled as "actuals" |
| Diagnostic metrics measuring nothing real | Phase 5: Backtesting | All featured metrics are labeled and verified as out-of-sample |
| Basic tier context stripped | Phase 6: Basic Dashboard | Basic tier passes user review with scope, vintage, and range visible |
| Stale v1.0 code interfering | Phase 2: Model Rework | Model version flag implemented; CI asserts v1.1 path produces no PCA index values |
| Data leakage in time series | Phase 2/5: Model + Backtesting | All CV splits are temporal; no training data date overlaps validation dates |
| Market boundary inconsistency | Phase 1: Data Architecture | Boundary definition locked in config; all sources checked against it |
| Nominal/real conflation | Phase 1: Data Pipeline | Column naming convention enforced; deflation pipeline test passes for all new sources |

---

## Sources

- [Bloomberg: AI Circular Deals — How Microsoft, OpenAI and Nvidia Keep Paying Each Other](https://www.bloomberg.com/graphics/2026-ai-circular-deals/) — confirms double-counting risk in conglomerate attribution
- [Aventis Advisors: AI Valuation Multiples 2025](https://aventis-advisors.com/ai-valuation-multiples/) — 3.6x–225x revenue multiple range; confirms private company opacity
- [Gartner: Worldwide AI Spending $1.5 Trillion 2025](https://www.gartner.com/en/newsroom/press-releases/2025-09-17-gartner-says-worldwide-ai-spending-will-total-1-point-5-trillion-in-2025) — broad definition anchor
- [Grand View Research: AI Market $390.91B 2025](https://www.grandviewresearch.com/industry-analysis/artificial-intelligence-ai-market) — narrow definition anchor; illustrates 7x spread problem
- [NVIDIA Q4 FY2026 Earnings](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-fourth-quarter-and-fiscal-2025) — Data Center segment ~91% of revenue; confirms segment attribution challenge
- [LuxAlgo: Backtesting Traps — Common Errors to Avoid](https://www.luxalgo.com/blog/backtesting-traps-common-errors-to-avoid/) — look-ahead bias, survivorship bias
- [Portfolio Optimization Book: Seven Sins of Backtesting](https://bookdown.org/palomar/portfoliooptimizationbook/8.2-seven-sins.html) — authoritative backtesting pitfall taxonomy
- [Equidam: AI Startup Valuation Revenue Multiples 2025](https://www.equidam.com/ai-startup-valuation-revenue-multiples-2025-challenges-insights-2/) — DCF limitations for private AI companies
- [OWOX: 2025's Worst Data Visuals](https://www.owox.com/blog/articles/bad-data-visualization-examples) — dashboard misleading visualization patterns
- [University of Utah Visualization Design Lab finding via Julius AI](https://julius.ai/articles/9-principles-of-data-visualization-finance-industry) — 84% misinterpretation rate without contextual information
- [SoftwareSeni: Big Tech AI Revenue Attribution Challenges](https://www.softwareseni.com/comparing-meta-microsoft-amazon-and-google-artificial-intelligence-investment-strategies-and-extracting-lessons-for-technology-companies/) — indirect vs. direct revenue attribution problem
- arXiv:2512.06932 — "Hidden Leaks in Time Series Forecasting: How Data Leakage Affects LSTM Evaluation" (carryover from v1.0 research)
- [KPMG: Data Migration Pitfalls 2025](https://assets.kpmg.com/content/dam/kpmg/ca/pdf/2025/03/ca-white-paper-on-data-migration-en.pdf) — interface contract violations when migrating between model architectures

---

*Pitfalls research for: AI Industry Economic Valuation — v1.1 Model Rework (proxy-to-real-data transition)*
*Researched: 2026-03-23*
