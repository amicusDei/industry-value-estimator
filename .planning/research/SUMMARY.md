# Project Research Summary

**Project:** AI Industry Economic Valuation and Forecasting System — v1.1 Model Rework
**Domain:** Hybrid statistical + ML economic valuation and forecasting (Python)
**Researched:** 2026-03-23
**Confidence:** HIGH

## Executive Summary

This project is a ground-up rework of an existing AI industry valuation model (v1.0) that produced unrealistic flat forecasts because it relied on a PCA composite of proxy indicators (R&D spend, patent filings) rather than real AI market data. v1.1 replaces the PCA composite + value chain multiplier with an anchor-calibrated model that uses published analyst estimates (IDC, Gartner, Goldman Sachs) and bottom-up company revenue attribution as the Y variable, retaining macroeconomic indicators as explanatory X variables. The existing 4-layer pipeline infrastructure (ingestion → processing → modeling → dashboard) is preserved; new components are inserted at defined seam points. The stack is Python 3.12 + pandas 3.0 + statsmodels/Prophet/LightGBM ensemble, with Dash 4.0 for the dashboard and edgartools + yfinance for real market data ingestion. All package versions are current-stable as of March 2026 and have verified pandas 3.0 compatibility.

The central technical challenge is not the modeling itself — the existing ensemble architecture is sound — but the data assembly work that must precede any model retraining. A defensible historical ground truth series for AI market size does not exist in one place; it must be assembled from published analyst reports, company 10-K filings via EDGAR, and analyst consensus estimates, with explicit market boundary definition and value chain layer taxonomy to prevent double-counting. This data assembly is the critical path for v1.1. Only after a clean actuals dataset exists can backtesting produce meaningful MAPE/R² metrics to replace the placeholder diagnostics in the existing dashboard.

The top risks are methodological rather than technical: anchor estimate shopping (choosing the source that fits the model output rather than the definitionally consistent one), AI revenue double-counting across value chain layers (Nvidia GPU revenue → Azure AI Services → OpenAI workloads → Copilot subscriptions all trace to the same underlying economic activity), and presenting single-point private company valuations (range: 3.6x–225x EV/Revenue) without uncertainty ranges. All three are avoidable with upfront design discipline — locking the market boundary in config before data collection, assigning value chain layer taxonomy before attribution, and storing all attribution percentages as parameterized ranges with source and vintage date. The Basic dashboard tier carries its own risk: stripping methodology context from headline numbers to achieve clean presentation produces misleading outputs; every headline number must carry a scope label, vintage date, and uncertainty range.

---

## Key Findings

### Recommended Stack

The v1.0 stack is largely correct and requires extension, not replacement. Python 3.12 + pandas 3.0 with Copy-on-Write is the foundation; statsmodels 0.14.6 is mandatory for econometric credibility (the pandas 3.0 compatibility fix is in 0.14.6 specifically — do not use an older version). LightGBM 4.6 + scikit-learn 1.8 pipelines handle the ML layer; Prophet 1.1 handles irregular AI market time series. Dash 4.0 + Plotly 6.6 handle the dashboard — both are now Narwhals-based and pandas 3.0 compatible.

New for v1.1: edgartools 5.25.1 is the primary source for SEC EDGAR XBRL company revenue ingestion (zero cost, auto rate-limits, returns DataFrames directly, active weekly releases). yfinance 1.2.0 provides market cap and analyst estimates as a cross-check source. skforecast 0.21.0 wraps the existing LightGBM for walk-forward backtesting without model restructuring. numpy-financial 1.0.0 handles DCF arithmetic. rapidfuzz aligns company names across sources. pydantic 2.x validates model inputs at ingestion boundaries. uv manages all dependencies with lockfile reproducibility.

**Core technologies:**
- **Python 3.12 + pandas 3.0 + NumPy 2.x**: Production-stable foundation; CoW-safe from day one
- **statsmodels 0.14.6**: Econometric baseline models (ARIMA, SARIMAX, VAR) — mandatory for portfolio credibility; 0.14.6 specifically required for pandas 3.0 compatibility
- **Prophet 1.1**: Additive decomposition for sparse, fast-growing, structurally-broken AI time series
- **LightGBM 4.6 + scikit-learn 1.8**: Gradient boosting residual correction; sklearn-compatible pipeline API
- **shap 0.46**: Feature interpretability — required for methodology credibility; explains USD forecast variance
- **edgartools 5.25.1**: Primary real market data source via SEC EDGAR XBRL; no API key required
- **yfinance 1.2.0**: Market cap, analyst estimates, and earnings data as calibration cross-check
- **skforecast 0.21.0**: Walk-forward backtesting wrapper for existing LightGBM; no model restructuring needed
- **numpy-financial 1.0.0**: DCF discounting arithmetic (NPV, IRR, terminal value)
- **Dash 4.0 + Plotly 6.6**: Dashboard and interactive charts; Narwhals-based DataFrame bridge
- **WeasyPrint 68 + Jinja2 + Kaleido**: HTML-to-PDF report generation
- **uv 0.5**: Package management with lockfile; 10-100x faster than pip

**Do not add:** spacy/sentence-transformers for earnings call NLP (high engineering cost, marginal gain over XBRL), autodcf/PyValuation (minimal maintenance — use numpy-financial + custom DCF), vectorbt/backtesting.py (trading-event focused, wrong abstraction for market-size validation).

See `.planning/research/STACK.md` for full alternatives analysis and version compatibility matrix.

---

### Expected Features

The v1.0 Dash dashboard (4 tabs: Overview, Segments, Drivers, Diagnostics in Normal/Expert tiers) is already built. v1.1 adds a new data foundation, a reworked model, and one new dashboard tier. Existing dashboard structure is preserved; displayed numbers update automatically once the model produces real USD outputs.

**Must have (table stakes — v1.1 launch):**
- Published analyst estimate corpus (10+ estimates, vintage-tagged) — without this nothing is anchored and the model cannot be credibly validated
- New market size model anchored on real AI revenue (replaces PCA composite)
- AI revenue attribution for 10-15 mixed-tech public companies — segment model depends on this
- Segment breakdown (infrastructure / software / services) summing to total
- Walk-forward backtesting with MAPE and R² against historical actuals — replaces placeholder diagnostics
- Basic dashboard tier (3 hero KPIs + segment chart + growth fan chart) — executive entry point
- Updated Normal/Expert modes to reflect new model outputs
- Analyst consensus panel showing model output vs. published estimate range

**Should have (differentiators — add when P1 work is stable):**
- Private company valuation registry (15-20 companies: OpenAI, Anthropic, Databricks) — comparable multiple methodology, explicit uncertainty
- Revenue multiples reference table (pure-play 33x vs. conglomerate 7x EV/Revenue per PitchBook Q4 2025)
- Data vintage display per segment

**Defer (v2+):**
- Scenario sliders on attribution assumptions (SCEN-01, already flagged in PROJECT.md)
- Expanded private company coverage (50+ companies)
- Sub-sector breakdown (NLP, CV, generative AI) — public data not granular enough at this scope
- Automated earnings call transcript ingestion via LLM — high engineering cost, marginal accuracy gain over XBRL

**Anti-features to avoid:** Single "true" AI market size number without uncertainty (seven analyst firms, 7x spread in estimates — undefined scope is intellectually dishonest), real-time private company valuations (quarterly batch refresh is honest and sufficient), raw LSEG data download via dashboard (licensing violation).

See `.planning/research/FEATURES.md` for full dependency graph and prioritization matrix.

---

### Architecture Approach

The existing 4-layer architecture (data layer → processing layer → modeling layer → dashboard layer) is preserved. v1.1 inserts two new ingestion modules (`market_anchors.py`, extended `lseg.py`) and two new processing modules (`revenue_attribution.py`, `dcf_valuation.py`), creates a new `src/backtesting/` package, and adds a fifth dashboard tab (`basic.py`). The model layer retargets its Y variable from a dimensionless PCA index to USD billions — the highest-impact change, requiring retraining of all three model components (ARIMA, Prophet, LightGBM) but no structural changes to ensemble weighting logic. The value chain multiplier block in `app.py` (current lines 53-109) is deleted entirely; `point_estimate_real_2020` column names are preserved for schema continuity but values change from index units to USD billions. All new data components communicate via Parquet files in the existing cache pattern, maintaining the pipeline's error-isolated step structure.

**Major components:**
1. `src/ingestion/market_anchors.py` (NEW) — loads published analyst estimates and private company valuations from YAML config to Parquet; no API calls
2. `src/processing/revenue_attribution.py` (NEW) — isolates AI revenue share from conglomerate financials using explicit disclosures and analogue ratios; every output includes `attribution_method`, `ratio_source`, `uncertainty_low/high`
3. `src/processing/dcf_valuation.py` (NEW) — DCF + AI revenue multiple valuation for private companies; stores `valuation_method`, `data_freshness_date`, `uncertainty_band_pct` per company
4. `src/backtesting/` (NEW package: holdout.py, walk_forward.py, benchmark_compare.py) — walk-forward validation against known anchor estimates; writes `backtesting_results.parquet` consumed by diagnostics tab
5. `src/dashboard/tabs/basic.py` (NEW) — Basic tier: 3 KPI cards + segment bar chart + growth fan chart; reads from existing `FORECASTS_DF`; every headline number carries scope label, vintage date, and uncertainty range
6. Existing models (ARIMA, Prophet, LightGBM, ensemble) — retrained on USD values; no structural changes to pipeline API
7. `config/industries/ai.yaml` — extended with `market_anchors`, `revenue_attribution`, and `private_company_valuations` sections; all attribution parameters stored with source and vintage date

**Key data contract change:** `point_estimate_real_2020` column in `forecasts_ensemble.parquet` changes from dimensionless PCA index units to USD billions. Column name preserved for schema continuity; the multiplier application block in `app.py` is deleted, not bridged.

**Build order (22 explicit steps):** Phase A (config + new ingestion + processing modules + pipeline wiring) → Phase B (model retraining + backtesting) → Phase C (dashboard updates + Basic tier). Cannot start Phase B until Phase A has produced `market_anchors_ai.parquet` via a full pipeline run.

See `.planning/research/ARCHITECTURE.md` for the full component diagram, project structure, and anti-patterns.

---

### Critical Pitfalls

Nine new v1.1 pitfalls identified plus three carried over from v1.0. Top five by severity:

1. **Anchor estimate shopping** — The 2025 AI market estimate range is $254B (narrow software) to $1.76T (Gartner broad). Lock the market boundary definition in config *before* looking at model output, then choose the definitionally consistent anchor. Document in `ASSUMPTIONS.md` with the alternative anchor comparison. This is a design decision, not a calibration step.

2. **AI revenue double-counting across value chain layers** — Nvidia GPU revenue, Azure AI Services revenue, and Copilot subscriptions all trace to the same economic activity (confirmed by Bloomberg 2026 circular deal analysis). Assign every company a value chain layer (chip / cloud / application / end-market) before data collection. Choose one layer as the primary measure or document explicitly that the total is gross, not value-added.

3. **Broken pipeline algebra after model rework** — New model outputs USD billions where old model output dimensionless index scores. The stale value chain multiplier path silently corrupts outputs if not fully deleted. Write an interface contract test asserting output units before writing any new model code. Gate v1.0 PCA code behind a `model_version` config flag.

4. **Backtesting against analyst consensus is not backtesting** — Comparing forecasts to IDC/Gartner estimates validates model agreement with analysts, not accuracy. Use filed 10-K company revenues as hard validation actuals; label consensus comparisons explicitly as "soft validation." Three-tier taxonomy: hard (filed actuals) / soft (consensus) / directional (proxy indices).

5. **False precision in attribution percentages and private company multiples** — Attribution ratios for non-disclosing companies and private company revenue multiples (range: 3.6x–225x) are model parameters with uncertainty, not data points. Store every attribution percentage with source, vintage date, and low/high range. Store every revenue multiple with vintage date. Show sensitivity tables in the methodology paper.

See `.planning/research/PITFALLS.md` for full prevention strategies, warning signs, and recovery costs for all 12 pitfalls.

---

## Implications for Roadmap

The build order is strictly data-before-model-before-dashboard. The ground truth corpus is the long pole — without it, neither meaningful backtesting nor credible dashboard numbers are possible. Architecture research provides a 22-step dependency-aware build sequence that maps directly to phases.

### Phase 1: Data Architecture and Ground Truth Assembly

**Rationale:** Everything in v1.1 depends on a defensible historical AI market size series and a locked market boundary definition. This is research and data curation work, not engineering. It must happen before any model code is written or anchor estimate shopping (Pitfall 1) is almost certain to occur. The FEATURES.md dependency tree states explicitly: "Ground truth corpus is the critical path."

**Delivers:** Locked `market_boundary` definition in config; `ASSUMPTIONS.md` with anchor selection documented before first model run; `market_anchors_ai.parquet` with 8-10 years of published market size estimates; `ai.yaml` extended with `market_anchors` and `revenue_attribution` config sections; deflation pipeline extended to cover all new data sources; column naming convention (`_real_2020`) enforced for new sources.

**Addresses features:** Published analyst estimate anchoring; data vintage display; analyst consensus panel groundwork

**Avoids pitfalls:** Anchor estimate shopping (Pitfall 1); market boundary inconsistency (Pitfall 11); nominal/real conflation (Pitfall 12)

**Stack:** edgartools 5.25.1, pyarrow, python-dotenv, requests-cache, pydantic 2.x (schema validation)

**Research flag:** NEEDS phase research — assembling a defensible historical actuals series from heterogeneous analyst sources (IDC, Gartner, Goldman, Grand View) requires source-by-source methodology assessment and definitional comparison before selecting anchors. Not a standard engineering problem; closer to economic research.

---

### Phase 2: Ground-Up Model Rework

**Rationale:** Model retraining cannot begin until Phase 1 Parquet files exist. This phase replaces the PCA composite Y variable with real USD anchor values and adds model version gating to prevent v1.0 PCA code from silently running in the v1.1 path. Interface contract audit must precede code changes — the PITFALLS.md is explicit that the broken pipeline algebra pitfall is a "hidden corruption" failure mode where no exceptions are thrown.

**Delivers:** `model_version` config flag gating v1.0/v1.1 paths; ARIMA and Prophet retrained on USD series; LightGBM retrained on USD residuals with updated feature matrix; value chain multiplier path deleted from `inference/forecast.py`; interface contract test asserting output is USD billions; PCA composite demoted to comparison utility in `features.py`; `features.py` macro indicators promoted to X variable matrix.

**Addresses features:** Realistic forecast trajectory; working MAPE/R² diagnostics (model foundation)

**Avoids pitfalls:** Broken pipeline algebra (Pitfall 2); stale v1.0 PCA code interfering (Pitfall 9); data leakage in time series validation (Pitfall 10)

**Stack:** statsmodels 0.14.6, Prophet 1.1, LightGBM 4.6, scikit-learn 1.8 TimeSeriesSplit, skforecast 0.21.0

**Research flag:** Standard patterns — model retraining on a new target variable with interface contract testing is well-documented. skforecast wraps existing LightGBM with no structural changes.

---

### Phase 3: AI Revenue Attribution

**Rationale:** Revenue attribution is the most analytically distinctive feature and the data foundation for the segment model. The value chain layer taxonomy (chip / cloud / application / end-market) is a design artifact that must exist in config before any attribution percentages are populated — retrofitting layer assignments after the fact to fix a double-counting problem is a HIGH recovery cost (per PITFALLS.md recovery table).

**Delivers:** `revenue_attribution.py` with explicit disclosure + analogue ratio paths; value chain layer taxonomy in config; every company assigned a `value_chain_layer` field; all attribution percentages stored with source, vintage date, and low/high range (pydantic-validated); 10-15 mixed-tech public companies attributed (Microsoft, Alphabet, Amazon, Meta, Salesforce, IBM); segment breakdown (infrastructure / software / services) summing to total; `lseg_ai.parquet` extended with `ai_revenue_usd` column; `AIRevenueAttributor` class with methodology documented per company.

**Addresses features:** AI revenue attribution for mixed-tech companies; segment breakdown model; analyst consensus layer (segment level)

**Avoids pitfalls:** AI revenue double-counting (Pitfall 3); segment reporting opacity / false precision (Pitfall 4)

**Stack:** edgartools 5.25.1, yfinance 1.2.0, financetoolkit 2.0.6, rapidfuzz, pydantic 2.x

**Research flag:** NEEDS phase research — value chain layer taxonomy design and per-company attribution source collection requires company-by-company research. Attribution methodology for non-disclosing companies (Meta, IBM, Salesforce) has no standard formula; requires sourcing sell-side analyst decompositions per company.

---

### Phase 4: Private Company Valuation

**Rationale:** Private company valuations are additive to the total market size estimate but do not block the core model or backtesting. Treating them as a separate phase avoids a long-pole dependency on OpenAI/Anthropic revenue estimates (inherently uncertain). Private company multiples require explicit uncertainty parameterization from the start — a single point estimate applied to all companies is never acceptable given the 3.6x–225x range.

**Delivers:** `dcf_valuation.py` with DCF + AI revenue multiple dual-track approach; private company registry (15-20 companies: OpenAI, Anthropic, Databricks, xAI, Mistral, etc.) in `ai.yaml` with valuation method, vintage date, and uncertainty band per company; revenue multiple parameters with vintage dates; sensitivity table showing total market size range across plausible multiple assumptions; `private_valuations_ai.parquet`; `PrivateCompanyValuation` dataclass with methodology fields.

**Addresses features:** Private company valuation registry; total market size completeness

**Avoids pitfalls:** Private company multiple comparability (Pitfall 5)

**Stack:** numpy-financial 1.0.0, pydantic 2.x, yfinance 1.2.0 (public comparable multiples)

**Research flag:** NEEDS phase research — current private company revenue estimates (OpenAI, Anthropic ARR for 2025-2026) and comparable transaction multiples require sourcing from recent (Q1 2026) advisory reports. 2021-2022 vintage multiples are definitively stale per Aventis Advisors and Finro Q1 2026 data.

---

### Phase 5: Backtesting and Diagnostics

**Rationale:** Backtesting requires both the reworked model (Phase 2) and attribution data (Phase 3) to be in place. The diagnostics framework already exists in the dashboard but currently shows placeholder metrics. Ground truth taxonomy (hard / soft / directional validation) must be written as a design document before any validation code is written — otherwise the MAPE values displayed will measure the wrong thing.

**Delivers:** `src/backtesting/` package (holdout.py, walk_forward.py, benchmark_compare.py); `backtesting_results.parquet` with `year`, `segment`, `actual_usd`, `predicted_usd`, `residual_usd`, `model`, `holdout_type` schema; real MAPE and R² computed against filed company revenue actuals (hard validation); analyst consensus comparison labeled explicitly as soft validation; diagnostics tab updated to show real out-of-sample metrics with [in-sample] / [out-of-sample] labels; MAPE benchmark targets documented (under 10% excellent, 10-20% acceptable for market sizing).

**Addresses features:** Walk-forward backtesting with MAPE/R²; working diagnostics tab

**Avoids pitfalls:** Backtesting against consensus, not actuals (Pitfall 6); diagnostic metrics measuring nothing real (Pitfall 7); data leakage in time series (Pitfall 10)

**Stack:** skforecast 0.21.0, scikit-learn TimeSeriesSplit, scipy (supplementary statistical tests)

**Research flag:** Standard patterns — walk-forward backtesting via skforecast is well-documented. The main work is assembling the ground truth dataset (done in Phases 1 and 3), not writing the validation code.

---

### Phase 6: Basic Dashboard Tier and Dashboard Polish

**Rationale:** Basic tier must show real, validated numbers — not placeholders. It is built last in the dashboard sequence after the model is validated and outputs are stable. Dashboard polish (removing multiplier derivation Expert blocks, wiring real segment values, updating Normal/Expert modes) is batched into a single phase to avoid iterating on the same files across multiple phases.

**Delivers:** `src/dashboard/tabs/basic.py` (Z-pattern layout: 3 hero KPIs with scope label, vintage date, and uncertainty range; segment bar chart with error bars replacing pie charts; growth fan chart); Basic tab as 5th tab in `layout.py`; multiplier calibration block deleted from `app.py`; `backtesting_results.parquet` loaded at app startup; Overview and Segments tabs updated to USD-native values; backtest chart rewritten to show actual vs. predicted (not residuals only); analyst consensus panel added to Basic and Normal tiers; revenue multiples reference table; all `"N/A"` diagnostics replaced with real metrics.

**Addresses features:** Basic dashboard tier; updated Normal/Expert modes; revenue multiples reference table; analyst consensus panel; data vintage display

**Avoids pitfalls:** Basic tier context stripped / misleading (Pitfall 8); "AI Market Cap" label ambiguity

**Stack:** Dash 4.0, Plotly 6.6, dash-bootstrap-components (existing)

**Research flag:** Standard patterns — Dash tab routing and KPI card layout are well-documented. No novel integration challenges.

---

### Phase Ordering Rationale

- **Phase 1 before everything:** Market boundary definition and anchor selection are design decisions that corrupt everything downstream if deferred. The PITFALLS.md is unambiguous — anchor shopping and boundary inconsistency are the two pitfalls with HIGH recovery cost.
- **Phase 2 before 3/4/5:** Model retraining requires Phase 1 Parquet files. Interface contract and version gating must exist before new data flows in.
- **Phase 3 before 5:** Segment-level backtesting requires segment-level attribution data; MAPE at segment level is only meaningful with real attribution.
- **Phase 4 independent of 5:** Private company valuations are additive; backtesting can proceed (and be meaningful) without them.
- **Phase 6 last:** Dashboard must show stable, validated numbers. Building the Basic tier against placeholder model outputs risks rework when real numbers produce different magnitudes.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Assembling a defensible historical actuals series requires evaluating 8-10 analyst report methodologies for definitional consistency before selecting anchors. This is economic research work, not software engineering.
- **Phase 3:** Value chain layer taxonomy design and per-company analyst source collection. Attribution methodology for non-disclosing companies (Meta, IBM, Salesforce) has no standard formula; requires company-by-company source work.
- **Phase 4:** Private company revenue estimates and Q1 2026 comparable transaction multiples must be freshly sourced; 2021-2022 vintage data is stale.

Phases with standard patterns (skip research-phase):
- **Phase 2:** Model retraining on new target variable + interface contract testing — well-documented via statsmodels, skforecast, and scikit-learn docs.
- **Phase 5:** Walk-forward backtesting via skforecast — standard; the novelty is the ground truth dataset, not the validation code.
- **Phase 6:** Dash tab routing, KPI cards, and chart rewrites — comprehensive official documentation.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All package versions verified via PyPI official sources as of March 2026. Compatibility matrix (pandas 3.0 × statsmodels 0.14.6 × Plotly 6.6 × LightGBM 4.6) explicitly confirmed. edgartools 5.25.1 active with weekly releases. skforecast 0.21.0 released March 13, 2026. |
| Features | HIGH | Table stakes grounded in official analyst reports (Gartner, IDC, PitchBook Q4 2025). Differentiator features grounded in competitor analysis (CB Insights IAC methodology). Feature dependency tree is explicit and verified. Anti-features are well-justified with specific rationale. |
| Architecture | HIGH | Based on direct codebase inspection of the existing 75-file `src/` package (2026-03-23). Component-level modify/preserve/replace table is granular. 22-step dependency-aware build order provided. Integration risks rated with specific notes. |
| Pitfalls | HIGH | 9 new v1.1 pitfalls + 3 carried from v1.0. All critical pitfalls have verifiable warning signs and recovery cost estimates. Double-counting risk confirmed by Bloomberg 2026 circular deal analysis. Multiple range (3.6x–225x) sourced from Aventis Advisors 2025 data. |

**Overall confidence:** HIGH

### Gaps to Address

- **Ground truth actuals series completeness:** The historical AI market size time series will realistically cover only 7-9 years (2016-2024) from heterogeneous sources with different definitions. MAPE over this sample will be noisy and potentially unstable (removing one data point may shift MAPE by 5+ percentage points). The methodology paper must communicate this limitation explicitly alongside every reported metric.
- **Private company revenue estimates:** OpenAI, Anthropic, and xAI revenue estimates for 2025-2026 come from secondary press reporting and investor disclosure. These are inherently low-confidence inputs. The 40% uncertainty band in the architecture config example may understate true uncertainty — validate against multiple independent sources before fixing the config parameters.
- **Market boundary harmonization:** The architecture specifies locking the boundary before data collection but does not prescribe which analyst definition to align to. This decision determines whether the headline number is in the hundreds of billions (IDC scope) or low trillions (Gartner scope) — a material choice with no objectively correct answer. Phase 1 must make this decision explicit and document the rationale.
- **Attribution percentage vintage management:** The pipeline stores attribution percentages with vintage dates, but there is no automated staleness alert. For a quarterly-refreshed portfolio project this is acceptable — but a manual review step must be included in the maintenance workflow.

---

## Sources

### Primary (HIGH confidence)
- [edgartools PyPI v5.25.1, March 2026](https://pypi.org/project/edgartools/) — EDGAR XBRL ingestion; rate limiting; caching
- [edgartools documentation](https://edgartools.readthedocs.io/) — XBRL concept extraction patterns
- [skforecast PyPI v0.21.0, March 2026](https://pypi.org/project/skforecast/) — walk-forward backtesting API
- [scikit-learn release history v1.8.0](https://scikit-learn.org/stable/whats_new.html) — pipeline and CV splitter API
- [LightGBM PyPI v4.6.0](https://pypi.org/project/lightgbm/) — gradient boosting; pandas 3.0 compatibility
- [statsmodels PyPI v0.14.6](https://pypi.org/project/statsmodels/) — econometric models; pandas 3.0 fix documented
- [Plotly PyPI v6.6.0](https://pypi.org/project/plotly/) — Narwhals DataFrame bridge
- [Dash PyPI v4.0.x](https://pypi.org/project/dash/) — dashboard framework
- [WeasyPrint PyPI v68.1](https://pypi.org/project/weasyprint/) — HTML-to-PDF
- [yfinance PyPI v1.2.0, February 2026](https://pypi.org/project/yfinance/) — market cap and analyst estimates
- [numpy-financial v1.0.0](https://numpy.org/numpy-financial/) — DCF arithmetic
- [Gartner: Worldwide AI Spending $1.5T 2025](https://www.gartner.com/en/newsroom/press-releases/2025-09-17-gartner-says-worldwide-ai-spending-will-total-1-point-5-trillion-in-2025) — broad market anchor
- [IDC: AI Infrastructure $758B by 2029](https://my.idc.com/getdoc.jsp?containerId=prUS53894425) — narrow market anchor
- [PitchBook Q4 2025 AI Valuation Guide](https://pitchbook.com/news/reports/q4-2025-ai-public-comp-sheet-and-valuation-guide) — EV/Revenue multiples; pure-play vs. conglomerate comparison
- [CB Insights: Industry Analyst Consensus Methodology](https://www.cbinsights.com/research/team-blog/industry-analyst-market-sizings/) — wisdom of crowds approach
- [RapidFuzz GitHub](https://github.com/rapidfuzz/RapidFuzz) — fuzzy name matching
- [financetoolkit PyPI v2.0.6](https://pypi.org/project/financetoolkit/) — segment revenue and analyst estimates
- Direct codebase inspection: `src/` package, 75 Python files, 2026-03-23

### Secondary (MEDIUM confidence)
- [Aventis Advisors: AI Valuation Multiples 2025](https://aventis-advisors.com/ai-valuation-multiples/) — 3.6x–225x private company multiple range
- [Equidam: AI Startup Valuation Multiples 2025](https://www.equidam.com/ai-startup-valuation-revenue-multiples-2025-challenges-insights-2/) — DCF limitations for private AI companies
- [AI Valuation Multiples Q1 2026, Finro](https://www.finrofca.com/news/ai-valuation-multiples-q1-2026-update) — current private market multiple dispersion
- [Grand View Research: AI Market 2025 Segments](https://www.grandviewresearch.com/industry-analysis/artificial-intelligence-ai-market) — segment share benchmarks
- [Bloomberg: AI Circular Deals 2026](https://www.bloomberg.com/graphics/2026-ai-circular-deals/) — double-counting risk confirmation
- [Forecast Evaluation Best Practices, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9718476/) — MAPE benchmarks for market sizing
- [Walk-forward Backtesting, Towards Data Science](https://towardsdatascience.com/putting-your-forecasting-model-to-the-test-a-guide-to-backtesting-24567d377fb5/) — walk-forward holdout validation pattern
- [UXPin Dashboard Design Principles 2025](https://www.uxpin.com/studio/blog/dashboard-design-principles/) — Z-pattern layout; KPI hierarchy
- [uv project management guide](https://docs.astral.sh/uv/guides/projects/) — lockfile-based dependency resolution
- [edgartools HTTP client and caching internals, DeepWiki](https://deepwiki.com/dgunning/edgartools/7.3-http-client-and-caching) — rate limiting and cache behavior
- arXiv:2512.06932 — time series data leakage in LSTM evaluation (carryover from v1.0)

### Tertiary (LOW confidence — needs validation)
- Private AI company revenue estimates (OpenAI $5B ARR, Anthropic Series E implied valuation) — sourced from secondary press reporting; treat as calibration inputs only with wide uncertainty bands; validate against multiple sources before fixing config

---
*Research completed: 2026-03-23*
*Ready for roadmap: yes*
