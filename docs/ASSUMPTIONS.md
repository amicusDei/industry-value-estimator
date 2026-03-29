# Modeling Assumptions

*Single source of truth for every assumption in the AI Industry Value Estimator statistical baseline.*
*See [METHODOLOGY.md](METHODOLOGY.md) for data source and processing pipeline documentation.*

---

## Market Anchor Calibration (v1.1)

*Anchors model forecasts to analyst consensus market sizes in USD billions.*

### How v1.1 Works

The v1.1 pipeline does **not** use a PCA composite index or value chain multiplier. Instead, market sizes are estimated directly in USD billions:

1. **Analyst Registry:** Published market size estimates from 8 analyst firms (IDC, Gartner, Grand View Research, Statista, Goldman Sachs, Bloomberg Intelligence, McKinsey, CB Insights) are collected in `data/raw/market_anchors/ai_analyst_registry.yaml`.
2. **Scope Normalization:** Each estimate is multiplied by the firm's `scope_coefficient` from `config/industries/ai.yaml` to normalize to our market boundary definition.
3. **Reconciliation:** Per (estimate_year, segment), the scope-normalized estimates are aggregated: median becomes the point estimate, 25th/75th percentiles become the uncertainty range.
4. **Deflation:** All values are deflated to 2020 constant USD using the World Bank GDP deflator.
5. **Model Input:** The reconciled market anchor series (`data/processed/market_anchors_ai.parquet`) is used directly as the Y-variable for ARIMA/Prophet fitting — no index-to-USD conversion needed.

### Anchor Uncertainty

The analyst consensus range for 2023 global AI market size spans $185–$215B after scope normalization. The median ($200B) is the central estimate. A 10% error propagates linearly to all forecasts. Confidence intervals (80%, 95%) partially absorb this uncertainty, but systematic anchor error shifts the entire forecast range proportionally.

### Configuration

Market anchor parameters are in `config/industries/ai.yaml`:
- `scope_mapping_table`: per-firm scope coefficients and ranges
- `model_calibration`: CAGR floors, calibration blend weights, CI width floors

### Historical Note (v1.0)

The v1.0 pipeline used a PCA composite index of proxy indicators, calibrated to USD via a per-segment multiplier anchored at $200B. This approach was replaced in v1.1 because direct analyst-anchored USD series provide better-grounded forecasts with fewer transformation steps. The v1.0 multiplier logic has been removed from the codebase.

---

## TL;DR \u2014 Practitioner Summary

- **Assumption:** Annual data from 2010 onward is sufficient for trend estimation (~15 observations per segment). **If wrong:** Shorter history means wider confidence intervals and higher overfitting risk; ARIMA parsimony constraints (max_p=2, max_q=2) and AICc correction partially compensate but do not eliminate small-N uncertainty.

- **Assumption:** A structural break occurred around 2022 (GenAI surge) that requires explicit modeling. **If wrong:** Ignoring the 2022 break inflates residuals by mixing pre-GenAI and post-GenAI regimes; forecast accuracy degrades materially, and Phase 3 ML would learn the parametric shift as a spurious pattern.

- **Assumption:** The four AI segments (hardware, infrastructure, software, adoption) can be modeled independently with post-hoc aggregation. **If wrong:** Cross-segment correlations exist (GPU demand drives cloud infrastructure simultaneously); independent modeling underestimates forecast uncertainty and misses spillover-driven accelerations.

- **Assumption (v1.0, replaced in v1.1):** The v1.0 PCA composite index has been replaced by direct analyst-anchored USD market sizes. Proxy indicators now serve as exogenous LightGBM features, not as the primary market size signal.

- **Assumption:** TRBC-classified listed companies are representative of the broader AI market. **If wrong:** Private AI companies (e.g., OpenAI pre-IPO, Anthropic, Mistral) are excluded; the TRBC-based revenue series likely understates true market size, especially post-2022 when private AI fundraising exploded.

- **Assumption:** AICc (not AIC) is the appropriate model selection criterion for ARIMA orders. **If wrong:** Standard AIC systematically over-penalises at N < 30 — selecting higher-order models that overfit; the AICc correction (adding 2k(k+1)/(n-k-1)) prevents this on short annual panels.

- **Assumption:** OLS is the appropriate GDP share regression baseline, upgraded to WLS or GLSAR only when diagnostics require it (Breusch-Pagan p < 0.05 for heteroscedasticity; Ljung-Box p < 0.05 for autocorrelation). **If wrong:** Using OLS with violated assumptions produces inefficient parameter estimates; the diagnostic-driven upgrade chain ensures the estimator matches the error structure.

- **Assumption:** All preprocessing must be fit on training data only inside each CV fold. **If wrong:** Fitting on the full dataset leaks future distributional information into training; reported CV metrics would be optimistically biased and would not generalise to out-of-sample periods.

---

## Data Source Assumptions

### Proxy Validity

Direct measurement of "AI revenue" is not available from any statistical agency. We use six proxy indicators that correlate with AI economic activity:

1. **R&D expenditure in ICT as % of GDP** (`rd_ict_pct_gdp`, OECD ANBERD) — captures R&D input intensity into the technology sector that hosts AI development
2. **AI patent filings** (`ai_patent_filings`, OECD PATS_IPC, IPC class G06N) — innovation output signal directly filtered to machine intelligence patents
3. **VC/PE investment in AI companies** (`vc_ai_investment`, OECD VC_INVEST) — capital allocation signal capturing investor expectations of AI market growth
4. **Public company AI revenue** (`public_co_ai_revenue`, LSEG TRBC codes 57201010, 57201020, 57201030, 45101010) — realized market size for listed AI companies
5. **Researchers per million** (`researchers_per_million`, World Bank SP.POP.SCIE.RD.P6) — human capital input proxy
6. **High-technology exports** (`hightech_exports`, World Bank TX.VAL.TECH.CD) — technology intensity of traded goods

In v1.1, these proxy indicators serve as **exogenous features for LightGBM**, not as PCA input. The primary Y-variable (market size in USD billions) comes from the analyst-anchored market anchors series. The proxy indicators provide additional signal for the ML residual correction layer.

**If this is wrong:** If the proxy indicators do not correlate with AI activity in all segments equally, the LightGBM residual correction may introduce bias. However, unlike the v1.0 PCA approach, the v1.1 pipeline does not depend on these proxies for the primary market size estimate — they only influence the ML correction term.

### TRBC Universe Representativeness

The LSEG TRBC codes used (Computer Processing Hardware 57201010, Electronic Equipment & Parts 57201020, Semiconductors 57201030, Internet Software & Services 45101010) identify listed companies only. This creates two known gaps:

- **Private company exclusion:** Pre-IPO AI companies (e.g., OpenAI, Anthropic, Mistral, xAI) are excluded from the TRBC revenue series. The private AI market has grown faster than the public market post-2022.
- **Survivorship bias:** Companies that were delisted, acquired, or went bankrupt are not in the current TRBC universe. Acquired AI companies (e.g., DeepMind pre-Alphabet, GitHub) contributed revenue that is now attributed to acquirers' broader segments.

**If this is wrong:** Market size is likely understated by 20-40% in 2023-2025 based on public vs. private AI fundraising ratios reported by PitchBook and CB Insights. The understatement is larger in the software/adoption segments (more private activity) and smaller in hardware (dominated by public companies like NVIDIA, AMD).

### Earnings-Based AI Revenue Attribution

Per-company AI revenue attribution uses a three-tier methodology with documented confidence levels:

1. **Earnings regex extraction** (highest priority): Company-specific regex patterns scan EDGAR 10-K/10-Q filing text for AI-related revenue disclosures (e.g., NVIDIA "Data Center segment revenue was $X billion"). Extractions include confidence scores (high/medium/low) based on pattern specificity.

2. **LLM validation** (optional enhancement): When ANTHROPIC_API_KEY is configured, Claude claude-sonnet-4-5 validates regex extractions — confirming whether the figure is genuinely AI-specific, the dollar amount is correctly parsed, and the fiscal period is properly identified. Produces a 0-1 confidence score.

3. **YAML static fallback**: When EDGAR data is unavailable or extraction fails, hand-curated estimates from `data/raw/attribution/ai_attribution_registry.yaml` provide baseline attribution with documented provenance (analyst reports, earnings commentary, analogue ratios).

The `estimate_ai_revenue()` function in `revenue_attribution.py` consults `earnings_ai_attribution.parquet` first. If no earnings-based entry exists for a (CIK, year) pair, it falls back to pure-play pass-through (ratio=1.0) or config-driven ratios.

**If this is wrong:** Regex extraction may produce false positives (e.g., matching total segment revenue that includes non-AI items). The LLM validation layer mitigates this. The static YAML fallback carries vintage-date risk: estimates become stale as companies shift AI revenue mix quarter-to-quarter. The uncertainty bounds on each attribution entry quantify this risk.

### Data Quality Notes

**ai_software 2024 growth spike (+111% YoY):** The 2024 ai_software estimate ($117B real 2020 USD) is computed as the median of two firms: CB Insights ($70B, narrow GenAI-native scope) and Precedence Research ($209B, broad "AI software including infrastructure" scope). The 3x spread between these estimates produces a median that appears as a sharp jump from the 2023 value ($56B, single IDC estimate). This is a scope-mixing artifact, not real 111% market growth. The Precedence Research scope is broader than our market boundary definition; a scope coefficient adjustment for segment-level estimates (currently only applied to "total" estimates) would reduce this spike. This is flagged as a known data quality issue for v1.2.

**2022→2023 ai_software decline (-28%):** The 2022 estimate derives from a single interpolated source while 2023 has a direct IDC estimate. The apparent decline reflects source methodology differences, not an actual market contraction.

### Geographic Coverage

The model covers 5 regions comprising 19 economy codes:

- **United States:** USA
- **Europe:** GBR, DEU, FRA, NLD, SWE, IRL, CHE (7 economies)
- **China:** CHN
- **Rest of World:** JPN, KOR, IND, ISR, SGP, CAN, AUS (7 economies)
- **Global:** Aggregate across all regions

Historical estimates suggest this covers approximately 85% of global AI economic activity based on World Bank GDP weights.

**Missing coverage:** Emerging AI ecosystems including UAE, Saudi Arabia (active sovereign AI investments), Vietnam, Brazil, and Indonesia are not covered. These markets are growing faster than the covered economies in 2024–2025.

**If this is wrong:** Global AI market size is understated by approximately 5–15%, growing to 10–20% by 2030 as emerging markets account for a larger share of AI adoption. Forecasts beyond 2027 carry higher geographic uncertainty than near-term estimates.

### Temporal Coverage

- **Historical period:** 2010 to latest available year (configured in `config/industries/ai.yaml` as 2025)
- **Effective training observations per segment:** approximately 12–15 annual data points after accounting for data availability lags across sources
- **Pre-2010 exclusion:** AI as a distinct measurable industry is not separable from general IT before 2010; patent IPC class G06N was sparsely used, TRBC classification did not distinguish AI hardware from general semiconductors

**If this is wrong:** Longer history would improve ARIMA trend estimation precision. However, pre-2010 data would likely be structurally different — AI was a research activity, not a commercial industry — making pre-2010 observations uninformative or misleading for forecasting the commercial phase.

---

## Modeling Assumptions

### Stationarity

Stationarity is assessed using both ADF and KPSS tests in `src/processing/features.py::assess_stationarity()`:

- **ADF null hypothesis:** unit root present (non-stationary)
- **KPSS null hypothesis:** trend-stationary

Interpretation logic:
- ADF rejects (p < 0.05) AND KPSS fails to reject (p > 0.05) → stationary → d=0
- ADF fails to reject OR KPSS rejects → non-stationary → d=1 (first differencing)

The differencing order d is ultimately determined by pmdarima `auto_arima` using AICc as the information criterion — the ADF/KPSS assessment serves as a pre-modeling diagnostic check, not a binding constraint.

**If this is wrong:** Wrong d leads to over-differencing (destroys trend signal) or under-differencing (leaves unit root in residuals). AICc model selection provides a statistical correction, but with N < 20 observations the selection may not be reliable. ADF and KPSS results are logged per segment during model fitting for review.

### ARIMA Order Selection

ARIMA(p, d, q) order is selected using pmdarima `auto_arima` with the following configuration (see `src/models/statistical/arima.py::select_arima_order()`):

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `information_criterion` | `"aicc"` | Small-N correction — required when N < 30 annual observations |
| `max_p` | 2 | Parsimony constraint — prevents AR(3+) overfitting |
| `max_q` | 2 | Parsimony constraint — prevents MA(3+) overfitting |
| `d` | `None` (auto) | ADF-based automatic differencing order detection |
| `seasonal` | `False` | Annual data — no within-year seasonality |
| `stepwise` | `True` | Hyndman-Khandakar stepwise search for efficiency |

The actual ARIMA orders selected per segment depend on the data and are logged during model fitting. Typical expected orders for growing technology time series with ~15 annual observations are ARIMA(1,1,0) or ARIMA(1,1,1).

**If this is wrong:** Higher-order ARIMA (p=3, q=3) may capture additional short-run dynamics but risks overfitting on 15 observations. The max_p=2, max_q=2 constraint trades potential accuracy gains for robustness. The AICc penalty (larger than AIC at small N) provides an additional guard against overfitting.

### Prophet Configuration

Prophet is configured with an explicit changepoint anchoring the 2022 GenAI surge (see `src/models/statistical/prophet_model.py::fit_prophet_segment()`):

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `changepoints` | `["2022-01-01"]` | Explicit GenAI surge anchor — prevents spurious fragmentation from default 25-changepoint prior |
| `changepoint_prior_scale` | `0.1` | 2x the default (0.05) — allows post-break trend flexibility while penalising over-flexibility |
| `yearly_seasonality` | `False` | Annual data — no within-year seasonality to model |
| `weekly_seasonality` | `False` | Annual data |
| `daily_seasonality` | `False` | Annual data |

The `changepoints=["2022-01-01"]` setting overrides Prophet's default behaviour of placing 25 potential changepoints across the training period, which on 15 annual observations would cause severe overfitting to individual year-on-year fluctuations.

**If this is wrong:** Using the default 25-changepoint prior on 15 annual observations would fragment the trend into noise — Prophet would fit local fluctuations rather than the underlying growth trajectory. Conversely, if the true structural break is not at 2022 but at a different year (e.g., 2020 COVID disruption), anchoring at 2022 misattributes trend changes. The CUSUM/Chow test analysis in `src/diagnostics/structural_breaks.py` validates that 2022 is the statistically significant break year.

### Structural Break (2022 GenAI Surge)

Structural break analysis uses a three-step belt-and-suspenders approach (see `src/diagnostics/structural_breaks.py`):

**Step 1 — CUSUM detection:** Constant-only OLS (y = a + ε) residuals are tested via `breaks_cusumolsresid`. Constant-only specification chosen deliberately — linear trend detrending absorbs level shifts and reduces detection power. Significant CUSUM (p < 0.05) signals a break exists.

**Step 2 — Chow confirmation:** Chow F-statistic confirms statistical significance at the endogenously detected break position. The break year is extracted from the Chow result and used in subsequent modeling.

**Step 3 — Regime modeling:** `MarkovRegression(k_regimes=2)` with shared variance (`switching_variance=False`) and shared slope (`switching_exog=False`) but regime-specific intercepts models the transition between pre-GenAI and post-GenAI growth regimes. This captures a gradual regime shift rather than a sharp structural break.

**Fallback:** Markov switching requires a minimum of 20 observations. For segments with fewer observations, or when the EM algorithm fails to converge, the model falls back to a dummy-variable OLS with the break dummy set at the year of the maximum absolute first-difference.

The break year per segment is determined endogenously by CUSUM/Chow and is expected to cluster around 2022–2023 for the GenAI surge.

**If this is wrong:** Ignoring the structural break entirely inflates residuals by ~30–50% (rough estimate based on the magnitude of the GenAI surge in revenue proxies). This would cause Phase 3 ML training to learn the parametric shift as if it were an explanatory pattern — degrading forecast generalization. The Markov switching model is more robust than a sharp dummy because it allows the transition probability to be distributed over multiple periods.

### Per-Segment Independence

Each of the four AI segments (ai_hardware, ai_infrastructure, ai_software, ai_adoption) is modeled independently:

- Separate ARIMA/Prophet models fitted per segment
- No cross-segment regression or correlation structure
- Final aggregate market size = sum of segment forecasts (post-hoc aggregation)
- Segment definitions from `config/industries/ai.yaml` — each has an `overlap_note` documenting known double-counting

**If this is wrong:** Cross-segment correlations are real and economically meaningful. GPU chip demand (hardware) drives cloud capacity expansion (infrastructure) with a 6–12 month lag. AI software adoption drives hardware demand. Independent modeling misses these spillover effects and underestimates correlated forecast uncertainty — the true uncertainty of the aggregate is higher than the sum of individual segment uncertainties when correlations are positive.

### Top-Down GDP Share Regression

OLS is the baseline estimator for the top-down GDP share model, with diagnostic-driven upgrades (see `src/models/statistical/regression.py::fit_top_down_ols_with_upgrade()`):

| Test | Threshold | Upgrade |
|------|-----------|---------|
| Breusch-Pagan (heteroscedasticity) | p < 0.05 | WLS with weights = 1/(fitted² + 1e-8) |
| Ljung-Box lag-1 (autocorrelation) | p < 0.05 | GLSAR(rho=1) with up to 10 iterations |
| Neither triggered | — | OLS retained |

The OLS diagnostic values (BP statistic, BP p-value, Ljung-Box p-value, R², adjusted R²) are always captured and returned in the diagnostics dict, even when the final model is WLS or GLSAR. This preserves the decision chain for audit purposes.

R&D/GDP, ICT exports, patent applications, researchers per million, and high-tech exports (from World Bank and OECD) are candidate regressors. Variable selection is based on data availability and correlation with the dependent variable.

**If this is wrong:** OLS with heteroscedastic or autocorrelated errors produces inefficient parameter estimates (correct point estimates but inflated standard errors). Confidence intervals on the GDP share regression would be too narrow, giving false precision on market size ranges. The diagnostic-driven upgrade chain ensures the estimator matches the error structure without pre-committing to a specific model form.

---

## Cross-Validation Assumptions

### Temporal CV Design

Temporal cross-validation uses sklearn `TimeSeriesSplit` with an expanding window, implemented in `src/models/statistical/regression.py::temporal_cv_generic()`:

- **Fold strategy:** Expanding window — each fold adds one year to the training set, preserving chronological order
- **Number of splits:** Default n_splits=3 for ARIMA and Prophet CV. With ~15 annual observations, 3–4 folds yields training windows of approximately 9–12 observations and test windows of 1–2 observations
- **No leakage guarantee:** `fit_fn` receives only the training indices
- **Prophet CV:** Uses manual `TimeSeriesSplit` refits (not Prophet's built-in `cross_validation`). This keeps CV methodology symmetric with ARIMA — Prophet's built-in CV has minimum horizon constraints incompatible with 15-year annual panels

**If this is wrong:** Fitting any preprocessing on the full dataset before splitting would leak future distributional information into the training fold. Reported RMSE and MAPE would be optimistically biased by approximately 10-30% depending on how much the distribution shifts post-2022.

### Metric Interpretation

Primary evaluation metrics:

| Metric | Role | Interpretation |
|--------|------|----------------|
| RMSE | Primary comparison | Scale-dependent; comparable within-segment, not across segments of different sizes |
| MAPE | Primary comparison | Scale-independent; interpretable as % forecast error; guard against division by zero in implementation |
| R² | Reported but not primary | Inflated by trend in time series — R² near 1.0 does not mean accurate forecasting |
| AIC/BIC | Within-model comparison only | Not comparable across model types (ARIMA vs. Prophet) |
| Ljung-Box Q | Residual whiteness validation | Significant result (p < 0.05) indicates unexplained structure remaining in residuals |

The CV-based RMSE and MAPE are the honest out-of-sample metrics. In-sample R² is reported for context but is not used for model selection.

**If this is wrong:** Relying on R² or in-sample AIC to compare ARIMA vs. Prophet would always favour the model with more parameters on the training data. Only CV-based RMSE/MAPE on held-out folds provides a fair comparison. The winner per segment is selected by CV MAPE.

---

## Interpretation Caveats

### Forecast Horizon Uncertainty

Statistical baseline forecasts degrade rapidly beyond 2–3 years with ~15 observations in the training set:

- ARIMA(p,d,q) extrapolates the estimated trend and autocorrelation structure — the uncertainty interval widens as O(steps^{d+0.5}) for differenced series
- Prophet extrapolates the fitted trend and changepoint trajectory — the posterior uncertainty is narrow within the training period but widens steeply beyond the last observation
- Both models have no mechanism to anticipate future structural breaks (e.g., a 2027 AI winter or a 2026 compute cost collapse)

Point forecasts without confidence intervals are not defensible outputs. Phase 3 ML correction is intended to reduce forecast error by learning from structured features, but the fundamental limitation of small-N statistical extrapolation remains.

**If this is wrong:** Users who treat 2028–2030 point forecasts as reliable estimates risk making investment or policy decisions on extrapolations with ±50–100% uncertainty bands. Confidence intervals from Phase 3 are essential for responsible use of these forecasts.

### Model Selection is Per-Segment

The best model (ARIMA or Prophet) is selected independently for each of the four segments based on CV MAPE. This means:

- ai_hardware may win with ARIMA (hardware revenue is smoother, more trend-driven)
- ai_software may win with Prophet (software adoption has more distinct changepoint dynamics)
- No single model describes the entire estimation — "we used ARIMA" is not accurate if Prophet wins for 2 of 4 segments

The winning model per segment is recorded in the residuals Parquet file (`model_type` column) and documented in the Phase 2 execution logs.

**If this is wrong:** Forcing a single model type across all segments sacrifices accuracy for narrative simplicity. The heterogeneous nature of AI segment growth dynamics — hardware supply-constrained, software demand-driven, adoption lagging — makes per-segment model selection methodologically appropriate.

### Proxy Does Not Equal Direct Measurement

In v1.1, the primary market size signal comes from analyst-anchored estimates (direct USD figures), not proxy composites. Proxy indicators (R&D/GDP, ICT exports, patents) serve as exogenous features for the LightGBM residual correction layer, providing supplementary signal rather than the primary measurement.

**If this is wrong:** All estimates carry analyst consensus uncertainty on top of model uncertainty. The total uncertainty band is wider than the model CI alone suggests. Reporting market size as a range (rather than a point estimate) is the only honest presentation.

### Regime Assumptions in Interpretation

The 2022 structural break is modeled as a shift in intercept (level) under the Markov switching specification — not a change in trend slope. This assumes:

- Post-2022 AI growth follows the same structural growth rate as pre-2022, just from a higher base
- The GenAI surge represents a one-time level shift, not an acceleration of the secular trend

**If this is wrong:** If the GenAI surge represents a durable acceleration (higher slope, not just higher intercept), then models calibrated on pre-2022 trend slopes will systematically underestimate 2024–2030 growth. The Prophet changepoint prior scale of 0.1 (2x default) allows some post-break trend flexibility, but may not fully capture a regime with genuinely different slope dynamics.

---

## Mathematical Appendix

### ARIMA(p,d,q) Specification

Let $y_t$ be the observed time series. Define the differencing operator $\nabla^d y_t = (1-L)^d y_t$ where $L$ is the lag operator.

The ARIMA(p,d,q) model is:

$$\phi(L)(1-L)^d y_t = \theta(L)\varepsilon_t, \quad \varepsilon_t \sim \mathcal{N}(0, \sigma^2)$$

where:
- $\phi(L) = 1 - \phi_1 L - \phi_2 L^2 - \ldots - \phi_p L^p$ is the AR polynomial
- $\theta(L) = 1 + \theta_1 L + \theta_2 L^2 + \ldots + \theta_q L^q$ is the MA polynomial
- $d$ is the differencing order (0 or 1 in this project, determined by ADF/AICc)
- $p \leq 2$, $q \leq 2$ (parsimony constraints)

Estimation is via conditional maximum likelihood. The likelihood is:

$$\ell(\phi, \theta, \sigma^2) = -\frac{n}{2}\log(2\pi\sigma^2) - \frac{1}{2\sigma^2}\sum_{t=1}^n \varepsilon_t^2$$

### AICc Small-Sample Correction

Standard AIC: $\text{AIC} = -2\ell + 2k$

AICc corrects for small N:

$$\text{AICc} = \text{AIC} + \frac{2k(k+1)}{n-k-1}$$

where $k$ is the number of estimated parameters (p + q + 1 for intercept + 1 for variance = p+q+2) and $n$ is the number of observations.

The correction term $\frac{2k(k+1)}{n-k-1}$ grows materially when $n < 50$:

| n | k=4 (ARIMA(1,1,1)) | k=6 (ARIMA(2,1,2)) |
|---|--------------------|---------------------|
| 15 | +4.00 | +21.00 |
| 20 | +2.67 | +9.33 |
| 50 | +0.83 | +1.94 |

With n=15 and ARIMA(2,1,2) (k=6), the AICc penalty is 21 points larger than AIC — effectively ruling out higher-order models unless the fit improvement is substantial.

### PCA Composite Construction (Historical — v1.0)

Let $X$ be the $n \times p$ matrix of $p$ standardized proxy indicators over $n$ years.

**Step 1 — Standardization (training data only):**

$$\tilde{X}_{ij} = \frac{X_{ij} - \bar{X}_j^{\text{train}}}{\sigma_j^{\text{train}}}$$

where $\bar{X}_j^{\text{train}}$ and $\sigma_j^{\text{train}}$ are computed on the training fold only.

**Step 2 — PCA via eigendecomposition:**

$$\tilde{X}^T \tilde{X} = V \Lambda V^T$$

where $\Lambda = \text{diag}(\lambda_1, \lambda_2, \ldots, \lambda_p)$ with $\lambda_1 \geq \lambda_2 \geq \ldots$

**Step 3 — First principal component scores (AI activity index):**

$$z_i = \tilde{X}_i \cdot v_1$$

where $v_1$ is the first eigenvector (loadings).

**Explained variance ratio:**

$$\text{EVR}_1 = \frac{\lambda_1}{\sum_{j=1}^p \lambda_j}$$

This was logged per CV fold in v1.0. If EVR₁ < 0.5, the PCA composite was poorly determined and the manual composite sensitivity check became more important. This section is retained as historical reference only.

### Chow Test Statistic

Let the break occur at observation $t^*$ (break index within the series). Define:

- $\text{SSR}_{\text{full}}$ = sum of squared residuals from OLS on full sample
- $\text{SSR}_{\text{pre}}$ = sum of squared residuals from OLS on $t < t^*$
- $\text{SSR}_{\text{post}}$ = sum of squared residuals from OLS on $t \geq t^*$
- $k$ = number of parameters in each sub-period regression (= 2: constant + trend)

The Chow F-statistic:

$$F = \frac{(\text{SSR}_{\text{full}} - \text{SSR}_{\text{pre}} - \text{SSR}_{\text{post}}) / k}{(\text{SSR}_{\text{pre}} + \text{SSR}_{\text{post}}) / (n - 2k)}$$

Under $H_0$ (no structural break), $F \sim F(k, n-2k)$.

Rejection at p < 0.05 confirms a statistically significant break at $t^*$.

### Markov Switching Model

The two-regime Markov switching model (Hamilton 1989) specifies:

$$y_t = \alpha_{S_t} + \beta x_t + \varepsilon_t, \quad \varepsilon_t \sim \mathcal{N}(0, \sigma^2)$$

where $S_t \in \{0, 1\}$ is a latent regime variable, $\alpha_{S_t}$ is the regime-specific intercept, $\beta$ is the shared slope (on a linear trend $x_t = t$), and $\sigma^2$ is the shared variance.

**Transition probabilities:**

$$P(S_t = j | S_{t-1} = i) = p_{ij}, \quad \sum_j p_{ij} = 1$$

Collected in the $2 \times 2$ transition matrix $\mathbf{P}$.

**EM Algorithm (Hamilton filter):** Parameters are estimated by maximizing the log-likelihood via the Expectation-Maximization algorithm. The E-step computes filtered and smoothed regime probabilities using the Hamilton recursion. The M-step updates $\alpha_0, \alpha_1, \beta, \sigma^2, \mathbf{P}$ using weighted OLS.

**Smoothed probabilities:** $P(S_t = j | y_1, \ldots, y_T)$ — the probability of regime $j$ at time $t$ given all observations — are used to characterize the regime transition path.

**Minimum observation requirement:** N ≥ 20 for numerical stability of the EM algorithm on 2-regime models. Implemented in `fit_markov_switching()` with fallback to dummy-variable OLS for shorter series.
