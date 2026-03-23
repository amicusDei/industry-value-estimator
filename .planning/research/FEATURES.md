# Feature Research

**Domain:** AI Industry Valuation Model Rework + Basic Dashboard Tier (v1.1)
**Researched:** 2026-03-23
**Confidence:** MEDIUM-HIGH

---

## Context: What Is Already Built

v1.0 delivered: data pipeline (World Bank, OECD, LSEG), ARIMA/Prophet + LightGBM ensemble, PCA composite index, quantile regression CIs, 4-tab Dash dashboard (Normal/Expert), SHAP drivers, PDF reports. The core problem is that the PCA composite approach produced flat/unrealistic forecasts because proxy econometric indicators (patent filings, R&D spend) do not measure AI revenue — they correlate with it loosely at best. v1.1 is a ground-up rework of the model to anchor on real AI market data.

This research file covers ONLY the new features needed for v1.1. Existing features are already built and not re-evaluated here.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features any analyst or portfolio reviewer expects from a credible AI valuation tool. Missing these makes the output feel like a student exercise rather than real analysis.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Published analyst estimate anchoring | PitchBook, IDC, Gartner, Goldman Sachs all publish AI market size estimates. A model that ignores these and produces its own number from scratch is immediately suspect. Analysts expect "how does this compare to IDC $X?" | MEDIUM | Collect 6-10 published estimates for the same year (Gartner $1.5T total AI spend, IDC $307B enterprise AI solutions 2025, Grand View Research segment figures). Use these as ground truth anchors, not inputs. The model should explain how it arrives at a number in the same ballpark or justify divergence. HIGH confidence basis: Gartner/IDC official releases. |
| Segment breakdown (infrastructure / software / services) | Market sizing tools (IDC, Grand View, Mordor Intelligence) always segment the market. Analysts expect sub-totals, not just a total figure. The standard analyst segmentation is: hardware/chips, cloud/infrastructure, software/platforms, services/consulting. | MEDIUM | Grand View Research shows services at 36.3% share, software at 34.2% in 2025. Hardware led AI infrastructure at 68% of that sub-market. Build segment model that sums to total — this also makes backtesting tractable because you can validate segments independently. MEDIUM confidence (commercial research sources). |
| Revenue multiples display for comparable companies | PitchBook publishes quarterly AI Public Comp Sheet with EV/Revenue multiples. AI pure-plays traded at 33x EV/TTM Revenue in Q4 2025 vs 7x for conglomerates. Any valuation tool should contextualize its market size estimates against these multiples to pass the "sniff test." | LOW | Display a reference table of current trading multiples for AI pure-plays, semiconductors, conglomerates alongside the market size estimate. Data sourced from public earnings + PitchBook quarterly reports. Adds credibility with zero modeling complexity. HIGH confidence: PitchBook Q4 2025 AI Valuation Guide. |
| Working MAPE / R² diagnostics | Diagnostics tab already exists but shows placeholder metrics because v1.0 had no real actuals to compare against. Any published forecasting tool shows in-sample fit. Backtesting on held-out years (e.g., train pre-2022, evaluate 2022-2024 against published market size data) makes MAPE and R² real and meaningful. | HIGH | Requires assembling a "ground truth" time series of AI market size by year from published sources (IDC, Gartner, Grand View). This is the hardest part — the data doesn't exist in one place. Need to reconcile different methodologies across firms. Once assembled, backtesting is standard time-series cross-validation. MEDIUM confidence: validated approach from ML literature. |
| Realistic forecast trajectory | The v1.0 model produced flat forecasts because proxy indicators don't grow at AI's pace. An AI-specific model should reflect consensus growth rates. Gartner forecasts AI spending at $1.5T in 2025; IDC projects AI infrastructure reaching $758B by 2029. The model's 2025-2030 trajectory must be defensible against these published forecasts. | MEDIUM | "Realistic" here means: growth rate consistent with consensus (roughly 25-40% CAGR for AI overall), not identical to any one source. Document where the model diverges and why. |
| Data vintage and methodology transparency | CB Insights explicitly surfaces "last updated" timestamps on all market estimates. Analysts expect to know when data was last refreshed and which estimation method was applied for each segment. | LOW | Already partially implemented (Parquet cache metadata). Extend to show vintage per data source per segment in the UI. LOW complexity, HIGH credibility payoff. |

---

### Differentiators (Competitive Advantage)

Features that separate this tool from both (a) generic open-source forecasting notebooks and (b) opaque commercial reports. These directly address the "valued by thumb" problem stated in PROJECT.md.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| AI revenue attribution for mixed-tech public companies | Microsoft, Alphabet, Amazon, Salesforce, IBM generate substantial AI revenue but do not report it as a separate segment. Analysts use cloud growth as an AI demand proxy (Azure +39% YoY Q4 2025; Google Cloud +48% Q4 2025). A principled attribution model — "X% of Azure revenue is AI-driven" — is more rigorous than just using cloud revenue as a stand-in. | HIGH | Methodology: (1) collect public earnings disclosures for companies with partial AI segment data (Microsoft Copilot revenue, Google AI Overviews ad impact); (2) apply analyst-consensus attribution ratios from sell-side research; (3) cross-check against company "AI contribution" commentary in earnings calls. PitchBook Q4 2025 shows conglomerates trade at 7x vs 33x for pure-plays — the valuation gap itself is evidence of attribution opacity. This is the most analytically interesting feature in v1.1. HIGH confidence: valuation multiple data from PitchBook official reports; attribution methodology from McKinsey/Deloitte AI ROI research. |
| Private company valuation using revenue multiples + proxy data | OpenAI, Anthropic, Databricks are not publicly traded but are major AI market participants. Ignoring them understates the market. Standard approach: apply EV/Revenue multiples from comparable public companies to disclosed or estimated private company ARR. Precedent transactions anchor the range (Anthropic raised at ~36x revenue in 2025). | HIGH | Build a "private company registry" — a small YAML or CSV with company name, estimated ARR, funding round data, implied valuation, data source, and confidence flag. Apply comparable-company multiple ranges (15x-35x for AI pure-plays per Equidam/Aventis Advisors research). Show uncertainty explicitly: "OpenAI implied at $157B using 31x EV/Revenue on estimated $5B ARR." MEDIUM confidence (revenue estimates for private companies are inherently LOW confidence; the methodology is well-established). |
| Analyst consensus layer — "wisdom of crowds" market sizing | CB Insights uses a "wisdom of crowds" Industry Analyst Consensus (IAC) approach — averaging 12,050+ market estimates across analysts to produce a consensus view. Showing both the model's output AND an analyst consensus range (from collected published estimates) makes the tool self-validating: "our model produces $X, analyst consensus center is $Y, divergence is Z%." | MEDIUM | Collect ~10 published estimates per major AI market segment with vintage date and analyst firm. Compute simple mean/median/range. Display alongside model output as a sanity check panel. This is how Bloomberg and FactSet display sell-side consensus vs. actual — familiar framing for any analyst. MEDIUM confidence: methodology documented by CB Insights officially. |
| Backtesting framework with walk-forward validation | Train on pre-2022 data, evaluate on 2022-2024 against published market size actuals. This is standard in financial forecasting (not just AI) — models that cannot beat a naive benchmark are not useful. Walk-forward validation (expanding window retraining) is more rigorous than a single train/test split. | HIGH | Requires: (1) assembling historical published market sizes as "actuals"; (2) implementing walk-forward split logic; (3) computing MAPE, MAE, directional accuracy. MAPE benchmarks: <10% excellent, 10-20% acceptable for market sizing (much harder than product demand forecasting). The existing diagnostics tab is the right home for these results. MEDIUM confidence: forecasting evaluation methodology from PMC/TDS literature. |
| Basic dashboard tier (one-screen market intelligence view) | Executive dashboards work when 3-5 KPIs are shown at large size with trend indicators — no scrolling, no deep navigation required. The Basic tier should answer "what is the AI market worth, how fast is it growing, and what are the top segments?" in a single screen. PitchBook's quarterly AI Comp Sheet is a relevant design reference: headline numbers, a comparison table, and a chart — nothing more. | MEDIUM | Design principle: Z-pattern reading order, 3 hero numbers (total market cap, YoY growth rate, 2030 forecast), 1 segment breakdown bar chart, 1 growth trajectory fan chart. Color: one highlight for "AI-specific" figures vs. grey for context. No SHAP, no diagnostics, no methodology — those live in Normal/Expert. This tier is for the 5-second "is this number credible?" check. HIGH confidence: UXPin/DataCamp dashboard design research + PitchBook UI patterns. |

---

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Single "true" AI market size number without uncertainty | Feels clean and authoritative | Gartner ($1.5T total AI spend), IDC ($307B enterprise AI solutions), and Grand View ($244B AI software) are all "correct" — they measure different things. Presenting one number without scope definition is intellectually dishonest and will be immediately questioned by any analyst. | Present the number with explicit scope definition ("AI software + services, ex-hardware") and show how that scope choice relates to published alternatives. Uncertainty is a feature, not a weakness. |
| Automated ingestion of earnings call transcripts via LLM | Sounds like a sophisticated way to extract AI revenue mentions | Introduces OpenAI/Anthropic API dependency, LLM hallucination risk on financial data, and significant engineering complexity. For a portfolio project, manually curated company revenue attribution is more credible because you can verify each data point. | Hand-curate a focused set of 15-20 key AI companies with clearly documented attribution methodology. Quality over automation. |
| Interactive scenario sliders for revenue attribution assumptions | Flexible and analyst-friendly | Out of scope for v1.1 per PROJECT.md (SCEN-01 deferred to v2). Adds dashboard state management complexity to an already complex rework. | Lock the attribution methodology in v1.1 with documented assumptions. Add sliders in v2 once the base model is validated. |
| Coverage of AI sub-sectors as separate models (NLP, CV, robotics) | More granular = more useful | Granular sub-segment data is not available from public sources at the level needed for individual statistical models. Forces either fabrication or very wide CIs that undermine credibility. | Model at the established analyst segmentation level (infrastructure, software, services) where published data exists. Sub-sector commentary can appear in the report narrative without requiring a separate model. |
| Real-time private company valuation from live funding data | Demonstrates data pipeline sophistication | Private company valuations change discontinuously on funding events, not continuously. A "live" number would require Crunchbase Pro or PitchBook API (paid). And freshness creates a false sense of precision for inherently uncertain estimates. | Quarterly-refreshed private company registry with explicit data vintage. Show confidence intervals on all private company valuations. Batch update is honest and sufficient. |
| Downloading raw underlying data via the dashboard | Transparency and reproducibility | The LSEG data is subscription-only — exposing it for download would violate licensing terms. | Publish the data pipeline code so users can replicate the fetch with their own credentials. For public sources (World Bank, OECD), direct data download links in the UI are fine. |

---

## Feature Dependencies

```
[Published Analyst Estimates (ground truth corpus)]
    └──required by──> [Analyst Consensus Layer]
    └──required by──> [Backtesting Framework]
    └──required by──> [Working MAPE/R² Diagnostics]
    └──required by──> [Realistic Forecast Trajectory]

[Public Company Earnings Data]
    └──required by──> [AI Revenue Attribution (Mixed-Tech Companies)]
    └──required by──> [Revenue Multiples Reference Table]

[AI Revenue Attribution (Mixed-Tech)]
    └──contributes to──> [Segment Breakdown Model]
                             └──required by──> [Basic Dashboard Segment Chart]
                             └──required by──> [Analyst Consensus Layer (segment level)]

[Private Company Revenue Estimates]
    └──required by──> [Private Company Valuation Registry]
                          └──contributes to──> [Total Market Size Estimate]

[Total Market Size Estimate (new model)]
    └──required by──> [Basic Dashboard (hero numbers)]
    └──required by──> [Updated Normal/Expert Views]
    └──required by──> [Backtesting Framework]

[Backtesting Framework]
    └──produces──> [Working MAPE/R² Diagnostics]
                       └──feeds into──> [Diagnostics Tab (existing)]

[Basic Dashboard Tier]
    └──enhances──> [Normal Mode] (Basic is the entry point; Normal adds depth)
    └──no conflict with──> [Expert Mode] (orthogonal tiers)

[Analyst Consensus Layer]
    └──enhances──> [Basic Dashboard (context panel)]
    └──enhances──> [Normal Mode (validation section)]
```

### Dependency Notes

- **Ground truth corpus is the critical path:** Everything in v1.1 depends on assembling a defensible historical time series of AI market sizes from published sources. This is research work, not engineering work, and must happen first.
- **Revenue attribution before segment model:** The total market size is a sum of segments; each segment's estimate is informed by the company-level revenue attribution work. Doing attribution first means the segment model is bottom-up, not top-down.
- **Backtesting requires the new model:** Cannot backtest the v1.0 PCA composite model against AI market actuals — the model types are incompatible. The new anchored model must be built before backtesting is meaningful.
- **Basic dashboard tier requires final model outputs:** The Basic tier should show real numbers, not placeholders. Build it last in the dashboard phase, after the model is stable and validated.
- **Private company valuations are additive but not blocking:** The total market estimate can be produced without private company valuations and then refined when that component is added. Avoids a long-pole dependency.

---

## MVP Definition

This is v1.1 scope, not a greenfield MVP. "Launch" means the milestone is complete and the model is credible.

### Launch With (v1.1)

The minimum that makes the model credible and the Basic tier useful.

- [ ] Published analyst estimate corpus (10+ estimates, documented, vintage-tagged) — without this nothing is anchored
- [ ] New market size model anchored on real AI revenue data — replaces PCA composite
- [ ] AI revenue attribution for 10-15 key mixed-tech public companies — core analytical work
- [ ] Segment breakdown (infrastructure / software / services) summing to total — necessary for credibility and segment-level backtesting
- [ ] Private company valuation registry (15-20 major private AI companies, comparable multiple methodology) — adds significant market coverage
- [ ] Walk-forward backtesting with MAPE and R² against historical actuals — makes diagnostics real
- [ ] Basic dashboard tier (3 hero numbers + segment chart + growth fan chart) — new user-facing tier
- [ ] Updated Normal/Expert modes to reflect new model outputs — existing modes need recalibration
- [ ] Revenue multiples reference table (pure-play vs. semiconductor vs. conglomerate) — context for valuation numbers
- [ ] Analyst consensus panel showing model output vs. published estimate range — self-validating display

### Add After Validation (v1.x)

Add once v1.1 is live and model outputs have been reviewed.

- [ ] Scenario sliders on key attribution assumptions — trigger: SCEN-01, deferred to v2 per PROJECT.md
- [ ] Expanded private company coverage (50+ companies) — trigger: if the 15-20 company registry proves valuable
- [ ] Sub-sector breakdown (NLP, CV, generative AI) — trigger: only if reliable public data sources are found

### Future Consideration (v2+)

- [ ] Scenario analysis with interactive assumptions — SCEN-01 already flagged in PROJECT.md
- [ ] Second industry (e.g., cloud computing) — extensibility already built in config/industries/
- [ ] Automated earnings call ingestion — only if engineering investment is justified by use

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Published analyst estimate corpus | HIGH | MEDIUM (research effort) | P1 |
| New anchored market size model | HIGH | HIGH | P1 |
| AI revenue attribution (public companies) | HIGH | HIGH | P1 |
| Segment breakdown model | HIGH | MEDIUM | P1 |
| Walk-forward backtesting + MAPE/R² | HIGH | MEDIUM | P1 |
| Basic dashboard tier | HIGH | MEDIUM | P1 |
| Updated Normal/Expert modes | HIGH | MEDIUM | P1 |
| Private company valuation registry | MEDIUM | MEDIUM | P1 |
| Analyst consensus panel | HIGH | LOW | P1 |
| Revenue multiples reference table | MEDIUM | LOW | P2 |
| Data vintage display per segment | LOW | LOW | P2 |
| Expanded private company coverage | MEDIUM | MEDIUM | P3 |
| Sub-sector breakdown | MEDIUM | HIGH | P3 |
| Scenario sliders | HIGH | HIGH | P3 (v2) |

**Priority key:**
- P1: Required for v1.1 milestone completion
- P2: Should have; add when P1 work is stable
- P3: Nice to have; defer to v2 or later

---

## Competitor Feature Analysis

These are the tools and reports that do the same thing commercially. Portfolio reviewers will compare implicitly. This is not a competitive product — it is a portfolio project — but the comparison informs what "good" looks like.

| Feature | PitchBook / CB Insights | IDC / Gartner Reports | This Project (v1.1) |
|---------|------------------------|----------------------|---------------------|
| Market size methodology | Proprietary vendor surveys + filings aggregation. CB Insights: 12,050+ market estimates in corpus, "wisdom of crowds" IAC. | Primary vendor surveys (1,000+ vendors), analyst modeling, secondary research cross-check. | Published estimates as anchors + bottom-up segment reconstruction from public filings + comparable multiple valuation for privates. Fully documented. |
| Segment classification | Hardware / infrastructure / software / services / verticals | Similar; varies by report scope definition | Hardware / cloud infrastructure / software / services — standard taxonomy, explicitly scoped |
| Private company coverage | PitchBook: extensive (core product); CB Insights: unicorn tracker, funding data | Limited or excluded from market size | 15-20 key companies, comparable multiple methodology, confidence flags, data vintage |
| Revenue attribution (conglomerates) | PitchBook tracks "AI pure-play" vs "conglomerate" valuations separately; does not attribute within conglomerate | Usually ignored — treats company as pure-play or excludes | Explicit attribution ratios per company, sourced from earnings + analyst commentary, documented uncertainty |
| Backtesting / model validation | Not disclosed / opaque | Not disclosed | Walk-forward validation on historical actuals; MAPE, R², directional accuracy — visible in Diagnostics tab |
| Analyst consensus display | PitchBook shows sell-side consensus EPS / revenue targets | Not shown to end users | Analyst consensus panel in Basic and Normal tiers: "model output vs. published range" |
| Dashboard tiers | One view; no tiering | PDF only; no interactive dashboard | Three tiers: Basic (5-second overview), Normal (analyst depth), Expert (full methodology) |
| Reproducibility | Not reproducible (proprietary data) | Not reproducible | Fully reproducible from public + LSEG data; pipeline code published |

---

## Existing Feature Integration Notes

The v1.1 features interact with these already-built components:

- **Data pipeline (Parquet cache):** New model replaces the PCA composite but reuses the same pipeline. LSEG data stays as a driver variable; new anchor data (published estimates, company filings) joins as a separate data layer.
- **ARIMA/Prophet models:** Retained as statistical baselines. New anchored model adds a calibration layer on top, reconciling model output to real-market anchors.
- **LightGBM ensemble:** Reused. The key change is the target variable — instead of a PCA composite index, the target becomes the anchored market size estimate.
- **SHAP drivers:** Already built. Gains credibility when the model is anchored on real data (drivers now explain real revenue variance, not index variance).
- **Diagnostics tab:** Already built. Walk-forward backtesting populates it with real MAPE/R² values.
- **Normal/Expert modes:** Already built. Need recalibration of displayed numbers and narrative text; dashboard structure unchanged.
- **PDF reports:** No changes needed to the PDF generation mechanism; output content updates automatically from model.

---

## Sources

- [PitchBook Q4 2025 AI Public Comp Sheet and Valuation Guide](https://pitchbook.com/news/reports/q4-2025-ai-public-comp-sheet-and-valuation-guide) — HIGH confidence (official PitchBook report)
- [PitchBook Q3 2025 AI Public Comp Sheet](https://pitchbook.com/news/reports/q3-2025-ai-public-comp-sheet-and-valuation-guide) — HIGH confidence
- [Gartner: Worldwide AI Spending to Total $1.5 Trillion in 2025](https://www.gartner.com/en/newsroom/press-releases/2025-09-17-gartner-says-worldwide-ai-spending-will-total-1-point-5-trillion-in-2025) — HIGH confidence (official press release)
- [Gartner: Worldwide GenAI Spending $644B in 2025](https://www.gartner.com/en/newsroom/press-releases/2025-03-31-gartner-forecasts-worldwide-genai-spending-to-reach-644-billion-in-2025) — HIGH confidence
- [IDC: AI Infrastructure Spending to Reach $758Bn by 2029](https://my.idc.com/getdoc.jsp?containerId=prUS53894425) — HIGH confidence (official IDC press release)
- [CB Insights: Industry Analyst Consensus Methodology](https://www.cbinsights.com/research/team-blog/industry-analyst-market-sizings/) — HIGH confidence (official CB Insights methodology post)
- [Grand View Research: AI Market Size 2025 Segment Breakdown](https://www.grandviewresearch.com/industry-analysis/artificial-intelligence-ai-market) — MEDIUM confidence (commercial research firm)
- [AI Startup Valuation Multiples 2025 — Equidam](https://www.equidam.com/ai-startup-valuation-revenue-multiples-2025-challenges-insights-2/) — MEDIUM confidence (boutique advisory, cites deal data)
- [AI Valuation Multiples 2025 — Aventis Advisors](https://aventis-advisors.com/ai-valuation-multiples/) — MEDIUM confidence
- [AI Business Valuation 2026 — FE International](https://www.feinternational.com/blog/ai-business-valuation-model-2026) — MEDIUM confidence
- [Alphabet Q3 2025 Earnings — CNBC](https://www.cnbc.com/2025/10/29/alphabet-google-q3-earnings.html) — HIGH confidence (earnings reporting)
- [Amazon/Microsoft/Alphabet Cloud Q4 2025 — Motley Fool](https://www.fool.com/investing/2026/02/12/amazon-microsoft-and-alphabet-all-reported-robust/) — MEDIUM confidence (secondary reporting on earnings)
- [UXPin Dashboard Design Principles 2025](https://www.uxpin.com/studio/blog/dashboard-design-principles/) — MEDIUM confidence (UX guidance)
- [Forecast Evaluation Best Practices — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9718476/) — HIGH confidence (peer-reviewed)
- [Walk-forward Backtesting Guide — Towards Data Science](https://towardsdatascience.com/putting-your-forecasting-model-to-the-test-a-guide-to-backtesting-24567d377fb5/) — MEDIUM confidence
- [PrivCo: Private Company Valuation Methods](https://www.privco.com/insights/Complete-Guide-to-Private-Company-Valuation-Methods-Formulas-and-Practical-Insights) — MEDIUM confidence

---
*Feature research for: AI Industry Valuation Model Rework + Basic Dashboard Tier (v1.1)*
*Researched: 2026-03-23*
