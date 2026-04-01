# AI Industry Value Estimator — Claude Code Context

## Was dieses Projekt ist

Ein datengetriebenes AI-Industry-Valuation-System das ökonometrische Methoden mit Machine Learning kombiniert. Es produziert Marktgrößenschätzungen und Wachstumsprognosen pro AI-Segment (Hardware, Infrastructure, Software, Adoption), verankert an Analyst-Consensus-Daten. Ziel: eine professionelle, Bloomberg-artige Research-Plattform die vor einem institutionellen Publikum (JP Morgan, EZB, Goldman Sachs) bestehen kann.

## Architektur (v1.1 — einzige aktive Pipeline)

```
EDGAR 10-K/10-Q ──┐
LSEG Workspace ────┼──► Ingestion ──► Processing ──► Market Anchors ──► ARIMA/Prophet ──► LightGBM Ensemble ──► Forecasts
World Bank API ────┤                  (Deflation)    (Scope-Norm.)       (per Segment)     (Residual-Korrektur)    (USD Billions)
OECD SDMX API ─────┘                  (Validation)   (Interpolation)     (Temporal CV)     (Quantile CIs)
                                                                                                │
                                                                                    FastAPI ◄───┘──► Next.js Frontend
                                                                                    (JSON API)       (Bloomberg-Style)
```

**Kanonischer Pipeline-Pfad:** `run_ensemble_pipeline.py` (run_statistical_pipeline.py wurde in v1.1 Cleanup entfernt)

## Kritische Dateien

| Datei | Rolle |
|---|---|
| `config/industries/ai.yaml` | Single Source of Truth: Segmente, TRBC-Codes, EDGAR-Companies, Attribution-Ratios, Calibration |
| `scripts/run_ensemble_pipeline.py` | Haupt-Pipeline: ARIMA + Prophet + LightGBM → forecasts_ensemble.parquet |
| `src/ingestion/market_anchors.py` | Analyst-Registry → Scope-Normalisierung → Market-Anchor-Compilation |
| `src/models/ensemble.py` | Inverse-RMSE-Weighted Additive Blend |
| `src/inference/forecast.py` | Forecast-Assembly, CAGR-Verifikation, Deflation |
| `data/processed/forecasts_ensemble.parquet` | Haupt-Output: Point Estimates + CIs in USD Billions (2020 real) |
| `data/processed/market_anchors_ai.parquet` | Ground Truth: Analyst-basierte Marktgrößen pro Segment/Jahr |

## Bekannte Probleme (Stand 2026-03-30, nach Deep Technical Audit)

### [RESOLVED] — Fixed in v1.1 Cleanup + Quality Audit

1. ~~**Backtesting MAPE 37-275%**~~ → [RESOLVED] Prophet LOO MAPE now 22.2%, CI80 coverage 90%, CI95 100%. Fixed via quarterly data (36 pts/seg) + bootstrap CIs.

2. ~~**Nur 6-8 jährliche Datenpunkte**~~ → [RESOLVED] Quarterly expansion: 36 data points per segment (9 years × 4 quarters).

3. ~~**CAGRs unter Consensus-Floors**~~ → [RESOLVED] Adaptive CAGR calibration ensures blended CAGR always meets floor. CI bands scale proportionally.

4. ~~**Revenue-Attribution nur 2024**~~ → [RESOLVED] Earnings-based attribution (regex + LLM validation) for 15 companies. Private market integration ($9B ARR) added.

5. ~~**Private Companies nicht integriert**~~ → [RESOLVED] private_contribution_usd column in forecasts. 18 companies, confidence-weighted ARR.

6. ~~**v1.0/v1.1 Misch-Code**~~ → [RESOLVED] run_statistical_pipeline.py deleted, all PCA references removed, docs consolidated to v1.1.

### [RESOLVED] — Fixed in v1.2 Data Quality + Scope Normalization

7. ~~**ai_software 2024 scope-mixing**~~ → [RESOLVED] Per-entry `segment_scope_coefficient` (0.40) applied to Precedence Research entries. Their $209B broad-scope figure (includes infrastructure software) now normalizes to $83.6B, consistent with CB Insights ($70B) and IDC ($64.5B). YoY spike eliminated: 2023→2024 now +16.6% instead of +111%.

8. ~~**Ensemble backtesting circular**~~ → [RESOLVED] Soft actuals (MAPE=0.0, actual==predicted) completely removed. Replaced with true LOO cross-validation: for each non-interpolated Q4 anchor, refit Prophet on data excluding that year, forecast it, compare. No MAPE=0.0 rows remain. Contract test enforces this.

10. ~~**Negative CI bounds**~~ → [RESOLVED] clip_ci_bounds() now floors at 0.0. CI bands scale proportionally with CAGR calibration. 224-row contract assertion verifies ci95_lower >= 0, ci80_lower <= point <= ci80_upper <= ci95_upper for every row.

11. ~~**Ensemble weights in-sample**~~ → [RESOLVED] stat_rmse now computed via expanding-window CV (train on first N quarters, predict next 4, collect OOS errors). Log shows "(expanding-window CV)" for all segments.

9. ~~**Interpolation dominance**~~ → [PARTIALLY RESOLVED] Total-market estimates (51 entries) now disaggregated into segment-level anchors using time-varying proportions. Data density per segment-year increased from 1-2 to 3-10 contributing sources. Quarterly interpolation remains (Q1-Q3 synthetic), but annual Q4 medians are now derived from multi-source consensus.

### Acknowledged Limitations (Transparent, Not Bugs)

1. **CAGR at calibration floors:** All 4 segments remain floor-constrained (hardware 15%, infrastructure 25%, software 20%, adoption 15%). The statistical model alone consistently underperforms analyst consensus growth rates. This is by design: the floor ensures our projections don't fall below the minimum defensible growth rate supported by 12 analyst firms. In an institutional setting, this is the conservative, defensible choice.

2. **ai_infrastructure MAPE elevated:** Prophet LOO MAPE 59.6% for infrastructure, driven by the rapid structural shift from 21% to 42% market share (cloud/data center boom post-2022). Prophet's linear trend assumption struggles with this regime change. Post-GenAI MAPE (2022+) is 16.5% across all segments, which is the relevant metric for forward-looking credibility.

3. **EDGAR hard actuals limited to ai_hardware:** Only NVIDIA provides direct AI revenue disclosure in 10-K filings. Other segments rely on held-out analyst consensus for LOO validation. This is transparently shown on /diagnostics with actual_type labels.

## Qualitäts-Gates (MÜSSEN bestehen bevor ein Arbeitspaket als "done" gilt)

### Gate 1: Code-Integrität
```bash
uv run python -m pytest tests/ -x -q --tb=short  # Alle Tests müssen grün sein
uv run ruff check src/ scripts/                    # Kein Linting-Fehler
```

### Gate 2: Pipeline-Lauffähigkeit
```bash
uv run python scripts/run_ensemble_pipeline.py     # Muss ohne Error durchlaufen
# Contract Assertions im Script müssen PASSED zeigen
```

### Gate 3: Modell-Qualität (Zielwerte nach v1.2 Scope-Fix + Disaggregation)
```
Segment            Prophet LOO MAPE    CI95 Coverage Target
ai_hardware        < 30%               > 85%
ai_infrastructure  < 65% (regime)      > 85%
ai_software        < 20%               > 85%
ai_adoption        < 30%               > 85%
Post-GenAI (2022+) < 20% overall       > 90%

Current (2026-03-30):
ai_hardware        26.4%               95% ✓
ai_infrastructure  59.6% (regime)      95% ✓
ai_software        13.9% ✓             95% ✓
ai_adoption        22.4% ✓             95% ✓
Post-GenAI         16.5% ✓             95% ✓
```

### Gate 4: CAGR-Plausibilität
```
Alle Segment-CAGRs 2026-2030 müssen innerhalb [Floor, Floor × 2.5] liegen.
Floors: hardware 15%, infrastructure 25%, software 20%, adoption 15%.
```

### Gate 5: Doku-Konsistenz
```
Kein Verweis auf PCA-Composite, value_chain_multiplier, oder run_statistical_pipeline in aktiver Doku.
ASSUMPTIONS.md, ARCHITECTURE.md, METHODOLOGY.md, README.md alle auf v1.1 konsolidiert.
```

### Gate 6: Bubble Index — Datenqualität (YAML-Validierung)

Prüft die Rohdaten in `config/industries/ai.yaml` → `bubble_index` auf Vollständigkeit, Plausibilität und Quellen-Attribution. Jede Verletzung ist ein Hard Fail.

```
VOLLSTÄNDIGKEIT:
- Alle 8 Indikatoren müssen für jeden Semi-Annual-Datenpunkt (2020 H1 bis 2026 H1) befüllt sein
- Kein Indikator darf mehr als 1 fehlenden Datenpunkt haben (sonst: Interpolation kennzeichnen)
- Jeder Datenpunkt MUSS ein `source:` Feld haben (z.B. "BIS QR March 2026", "MUFG Dec 2025")
- Datenpunkte ohne Source sind VERBOTEN — lieber `estimated: true` + `source: "Extrapolation from [X]"` als kein Source

PLAUSIBILITÄTSBÄNDER (Hard Bounds — Verletzung = sofortiger Stopp):
  capex_intensity_ratio:       [0.5, 8.0]     # Unter 0.5 wäre keine AI-Industrie, über 8 physisch unmöglich
  market_concentration_pct:    [5.0, 50.0]     # S&P500 Top-5 Anteil — historisch nie unter 5%, über 50% Kartell-Niveau
  dc_build_yoy_growth_pct:     [-20.0, 150.0]  # Negativwachstum möglich (Rezession), über 150% physisch unmöglich
  credit_total_usd_b:          [0.0, 2000.0]   # Obere Schranke: gesamter US IG Bond-Markt
  bis_risk_rating:             [1, 5]          # Definierte Skala
  revenue_and_cost_impact_pct: [0.0, 100.0]    # Prozentangabe
  roi_from_headcount_pct:      [0.0, 100.0]    # Anteil
  margin_erosion_from_ai_infra_pct: [0.0, 100.0] # Anteil — gleicher Feldname wie in YAML/Code
  ai_capex_growth_yoy_pct:     [-50.0, 200.0]  # Extremszenarien
  us_productivity_growth_pct:  [-5.0, 10.0]    # Historisch nie außerhalb dieses Bands
  solow_gap_ratio:             [0.1, 50.0]     # Ratio — 50× wäre absolutes Extrem
  headcount_reduction_pct:     [0.0, 100.0]    # Anteil

TREND-MONOTONIE (Soft Checks — Warning, kein Hard Fail):
- capex_intensity_ratio: Muss 2020→2026 insgesamt steigend sein (erlaubt: max 1 Dip von max -15%)
- credit_total: Muss 2022→2026 strikt steigend sein (BIS: "from near zero to $200B+ in 3 years")
- dc_build_momentum: Muss 2021→2025 insgesamt steigend sein
- Ein Trendbruch ist nicht verboten, aber MUSS kommentiert werden (warum der Bruch?)

DOTCOM-PARALLEL-KONSISTENZ:
- dotcom_parallel Sektion muss exakt 7 Datenpunkte haben (1996-2002)
- Peak-Jahr MUSS 1999 oder 2000 sein (für capex_intensity und concentration)
- Werte müssen mit bekannten Dotcom-Referenzen übereinstimmen:
  - Telecom Bond Issuance 1999-2000: $100-150B Range
  - IT Capex Growth Peak: 20-30% Range
  - S&P Top-5 Concentration Peak: 15-20% Range
```

### Gate 7: Bubble Index — Modellqualität (Score-Validierung)

Prüft die berechneten Scores in `bubble_index.parquet` auf mathematische Korrektheit, interne Konsistenz und Plausibilität gegen Referenzdaten.

```
SCORE-INTEGRITÄT:
- Alle 8 Subscores: Wertebereich [0, 100], keine NaN, keine Inf
- Composite Score: Wertebereich [0, 100], keine NaN
- Composite = gewichtete Summe der 8 Subscores (Toleranz ±0.5 Punkte wegen Rundung)
- Gewichte summieren sich auf 100% (15+10+10+15+10+15+15+10 = 100) ✓

KLASSIFIKATIONS-KONSISTENZ:
- <30 → "Healthy Expansion" (MUSS)
- 30-50 → "Elevated Valuations" (MUSS)
- 50-70 → "Bubble Warning" (MUSS)
- >70 → "Critical Overheating" (MUSS)
- Keine Row darf eine Klassifikation haben die nicht zum Score passt

ZEITREIHEN-PLAUSIBILITÄT:
- 2020 H1 Composite: MUSS < 30 sein (pre-GenAI, kein Bubble-Signal)
- 2022 H2 Composite: MUSS < 45 sein (ChatGPT gerade launched, Investitionswelle beginnt erst)
- 2025 H2 / 2026 H1 Composite: MUSS > 45 sein (Peak der aktuellen Welle)
- Composite darf zwischen aufeinanderfolgenden Halbjahren max ±20 Punkte springen
  (Sprung > 20 = entweder Datenfehler oder Regime-Change der kommentiert werden muss)

CROSS-REFERENZ-VALIDIERUNG (bekannte Fakten):
- capex_intensity 2025: Ratio MUSS > 3.0 sein (MUFG: $443B Capex vs ~$100B Revenue)
- credit_exposure 2025 total: MUSS > $300B sein (BIS: $121B Bonds + $200B Private Credit)
- enterprise_roi_score 2025/2026: MUSS > 50 sein (PwC: 56% CEOs report "nothing")
- productivity_gap_score 2025: MUSS > 40 sein (Capex +36% vs Productivity +2.7% → Ratio ~13×)
- dotcom_parallel_score: MUSS für 2025/2026 > 30 sein (AI hat Dotcom in Capex Intensity übertroffen)
- market_concentration 2025: MUSS > 25% sein (NVIDIA, MSFT, AAPL, GOOG, META ~30% S&P500)

INVERTIERTE-LOGIK-CHECK (Output-Indikatoren):
- enterprise_roi_score MUSS steigen wenn revenue_and_cost_impact_pct sinkt (invertierte Beziehung)
- productivity_gap_score MUSS steigen wenn solow_gap_ratio steigt (direkte Beziehung)
- Wenn headcount_reduction_pct steigt UND roi_from_headcount_pct steigt → enterprise_roi_score MUSS steigen
  (mehr "ROI" aus Personalabbau = höheres Bubble-Signal)

GEWICHTUNGS-SENSITIVITÄT (Robustness Check):
- Berechne Composite mit ±5pp Gewichtsverschiebung (z.B. Input 55%/Output 35%/Parallel 10%)
- Wenn Klassifikation sich ändert → WARNING: "Score is near classification boundary, sensitive to weights"
- Akzeptabel wenn Score ±3 Punkte vom Boundary entfernt ist
```

### Gate 8: API-Contract-Tests (Bubble Index Endpoints)

```
ENDPOINT-VERFÜGBARKEIT:
- GET /api/v1/bubble-index → 200 OK, JSON Array mit >= 12 Rows
- GET /api/v1/bubble-index/dotcom-parallel → 200 OK, JSON mit ai[] und dotcom[] Arrays
- GET /api/v1/bubble-index/dc-risk → 200 OK, JSON mit build_rate[], credit_stack[], refinancing_calendar[], asset_life_mismatch{}

SCHEMA-VALIDIERUNG:
- /bubble-index Response: Jede Row hat year, half, composite_score, classification, plus alle 8 Subscore-Felder
- /dotcom-parallel Response: ai[] und dotcom[] haben jeweils year + composite_score
- /dc-risk Response: credit_stack[].total_usd_b existiert und ist numerisch

KONSISTENZ:
- /bubble-index composite_score == das was in bubble_index.parquet steht (kein Drift zwischen File und API)
- /dotcom-parallel ai[] Werte == /bubble-index composite_score Werte für gleiche Jahre
```

## Arbeitsregeln für Claude Code

1. **Lies diese Datei (CLAUDE.md) vollständig vor jeder Session** — enthält Vision, Architektur, Arbeitsplan, Qualitäts-Gates und fertige Prompts. Alles in einer Datei, keine externen Leitdateien nötig.

2. **Ein AP-Schritt pro Session.** Nicht mehrere APs in einer Session mischen. Lieber einen Schritt sauber als drei halb.

3. **Verifikation VOR Commit.** Jede Änderung wird ERST verifiziert (Tests, Pipeline-Run, Daten-Inspektion), DANN committed. Kein "fix later".

4. **Daten-Inspektion ist Pflicht.** Nach jeder Pipeline-Änderung: Parquet laden, Shape prüfen, Ranges prüfen, Stichproben ansehen. Nicht blind auf "PASSED" vertrauen.

5. **Kein Silent Failure.** Bare `except Exception: pass` ist verboten. Jeder Exception-Handler muss mindestens `logging.warning()` haben.

6. **Dokumentation ist Teil der Aufgabe.** Jede Code-Änderung die Verhalten ändert muss in ASSUMPTIONS.md oder ARCHITECTURE.md reflektiert werden. Doku-Drift war der Hauptgrund für die aktuelle Schwammigkeit.

7. **Contract Tests als Abnahme.** Bevor ein AP als "done" markiert wird, müssen die relevanten Quality-Gates bestehen. Wenn ein Gate failt, ist das AP nicht done — egal was der Code tut.

## Strategische Vision (v3 — Risk-Intelligence + Bubble Analytics)

Das Projekt hat drei Ebenen: (1) Forecast-Engine (Phase 1-2, done), (2) Research-Intelligence mit Dispersion, Scenarios, Narratives, Bottom-Up Validation (Phase 2, done), (3) **Risk-Intelligence mit AI Bubble Index** (Phase 3, done).

Der Kern-Differentiator: Niemand hat einen quantitativen AI Bubble Index der **beide Seiten** misst — die Input-Seite (Investitionsintensität, Credit-Exposure, Leverage) UND die Output-Seite (Produktivitätswachstum, Enterprise-ROI, TFP-Impact). Eine Blase ist die Diskrepanz zwischen Investment und Ertrag. Ohne Produktivitätsmessung ist ein Bubble-Index blind auf einem Auge.

### Sechs Dimensionen die den Unterschied machen

1. **AI Bubble Index (NEU, Centerpiece):** Composite Score 0-100 aus 8 Subindikatoren — 5 Input-Indikatoren (Capex Intensity, Market Concentration, DC Build Momentum, Credit Exposure, Shadow Leverage) + 2 Output-Indikatoren (Enterprise ROI Realization, Productivity Gap / Solow Index) + 1 historischer Vergleich (Dotcom Parallel Score). Die Input/Output-Struktur ist der konzeptionelle Kern: je höher die Inputs und je niedriger die Outputs, desto stärker das Bubble-Signal. Referenz: BIS QR March 2026 (r_qt2603u), BIS Bulletin 120, Goldman Sachs Productivity Study March 2026, PwC Global CEO Survey 2026.

2. **Productivity Gap (Solow Index):** Kernmetrik: AI-Capex-Wachstumsrate vs. Produktivitätswachstumsrate. 2025: Capex +36% YoY, US-Produktivität +2.7% (vs. Dekaden-Durchschnitt 1.4%). Goldman Sachs (März 2026): "no meaningful relationship between productivity and AI adoption at the economy-wide level." PwC CEO Survey: 56% der CEOs sagen sie hätten "nothing" aus AI-Investments bekommen. Die Lücke zwischen Investitionsrate und Produktivitätsrate IS the bubble signal. Kritisch: Was als "AI ROI" gemeldet wird, ist überwiegend Cost-Cutting durch Personalabbau (1.17M Jobs 2025, +54% YoY), nicht echte Produktivitätssteigerung. Nur 17% der Unternehmen berichten AI-getriebene Produktivitätsgewinne als Ursache für Headcount-Reduktion. 84% der Enterprises verlieren Bruttomarge durch AI-Infrastrukturkosten. Der Bubble Index unterscheidet daher: Margin-via-Headcount (Einmaleffekt, nicht nachhaltig) vs. Productivity-per-Worker (nachhaltiger Gain, noch kaum messbar).

3. **Data Centre Risk Layer (NEU):** Build Rate (MW/Jahr), Hyperscaler Bond Issuance ($121B in 2025), Private Credit Exposure ($200B+), Off-Balance-Sheet SPVs, Asset-Life-Mismatch (20-Jahr DC-Annahme vs 18-Monat GPU-Zyklus). Refinanzierungskalender.

4. **Dispersion als Signal:** IQR der Analystenschätzungen über Zeit. Sinkende Dispersion = konvergierende Marktmeinung. Steigende Dispersion = fundamentale Unsicherheit.

5. **Scenario Engine:** Bull/Base/Bear-Cases, pre-computed und vergleichbar.

6. **Automatisierte Narrativ-Ebene:** Zahlen in argumentative Kontexte setzen, regelbasiert.

### Reference-Class

- **BIS Quarterly Review (March 2026):** "Financing the AI infrastructure boom: on- and off-balance sheet borrowing" — Kernquelle für Shadow Leverage und Credit Exposure Methodik
- **Goldman Sachs Productivity Study (March 2026):** "No meaningful relationship between AI and productivity at the economy-wide level" — aber 30% Gain in 2 spezifischen Use Cases. Kernquelle für Enterprise ROI Realization Subindikator.
- **PwC Global CEO Survey 2026:** 4,454 CEOs, 95 Länder — 56% "nothing out of AI investments", nur 12% sowohl Revenue-Growth als auch Cost-Reduction. Quantitative Basis für den Solow-Gap.
- **Robert Solow / Productivity Paradox:** "You can see the computer age everywhere but in the productivity statistics" (1987). Exakt das gleiche Muster bei AI — NBER-Studie (Feb 2026) mit 6,000 CEOs findet kaum Impact.
- **Shiller CAPE / VIX / ICE HY Spread:** Composite-Indikatoren die als Einzel-Initiativen gestartet sind und zu Industrie-Standards wurden — genau das Modell für den AI Bubble Index
- **CNN Fear & Greed Index:** UI-Referenz für Gauge-Visualisierung des Composite Score
- **Bloomberg ASKB / Visible Alpha / FactSet:** Haben die Rohdaten aber nicht die Aggregation

## Arbeitsplan

### Phase 1 (abgeschlossen): Foundation

Siehe `REFACTORING_PROMPT.md` für historischen Kontext:
- ~~**AP1:** v1.0 Cleanup, Doku-Konsolidierung, Bug-Fixes~~ ✓
- ~~**AP2:** Earnings-basierte AI-Revenue-Attribution~~ ✓
- ~~**AP4.1-4.5:** Quarterly-Daten, CI-Fix, Private Integration, Backtesting, Scope-Normalisierung~~ ✓

### Phase 2 (abgeschlossen): Research-Intelligence Features

| AP | Feature | Status |
|---|---|---|
| ~~**v2-AP1**~~ | Analyst Dispersion Index → `analyst_dispersion.parquet` (45 rows) | ✓ Done |
| ~~**v2-AP2**~~ | Scenario Engine → `forecasts_scenarios.parquet` (672 rows, 3 Szenarien) | ✓ Done |
| ~~**v2-AP3**~~ | Dispersion-Visualisierung (Frontend) | ✓ Done |
| ~~**v2-AP4**~~ | Scenario-Switcher (Frontend) | ✓ Done |
| ~~**v2-AP5**~~ | Automated Insight Narratives (5 Typen, regelbasiert) | ✓ Done |
| ~~**v2-AP6a**~~ | Bottom-Up Validation Backend — Multi-Year, Coverage-Trends, Narrativ-Integration | ✓ Done |
| ~~**v2-AP6b**~~ | Bottom-Up Validation Frontend — Stacked Bar Chart, API-Endpoint | ✓ Done |

**Phase 2 abgeschlossen.**

### Phase 3 (abgeschlossen): AI Bubble Index + Risk Intelligence + Bloomberg-Grade Frontend

Ziel: Vom Forecast-Tool zur Risk-Intelligence-Plattform. Das Centerpiece ist der AI Bubble Index — ein quantitativer Composite-Indikator der AI-Überhitzung misst und mit dem Dotcom-Zyklus vergleicht.

| AP | Feature | Status |
|---|---|---|
| ~~**v3-AP1**~~ | AI Bubble Index — Backend + Data Pipeline (98 sourced data points, 8 sub-indicators, composite 0-100) | ✓ Done |
| ~~**v3-AP2**~~ | AI Bubble Index — Frontend Dashboard (BubbleGauge, SubindicatorBars, DotcomParallel) | ✓ Done |
| ~~**v3-AP3**~~ | Data Centre Risk Deep-Dive (Build Rate, Credit Stack, Refinancing Wall, Asset-Life Mismatch) | ✓ Done |
| ~~**v3-AP4**~~ | Chart-System Upgrade (CI-Bänder als Flächen, Tooltip, Legende, responsive) | ✓ Done |
| ~~**v3-AP5**~~ | README + Methodology Paper PDF + Screenshots | ✓ Done |
| ~~**v3-AP6**~~ | Live Deployment (Vercel, self-contained Next.js API routes) | ✓ Done |

**Zusätzlich in Phase 3 erledigt:**
- Diagnostics Page (4-Tab: MAPE Heatmap, CI Coverage, Regime Analysis, Data Sources)
- Excel/CSV Export (3-Sheet, Scenario-Support)
- Methodology Paper PDF (5 Seiten, Goldman-Style, datengetrieben aus Parquet)
- EDGAR CapEx Bottom-Up Validation (real XBRL extraction + fallback, 9 Companies × 5 Jahre)

**Live:** https://frontend-blue-chi-18.vercel.app
**Bubble Index:** https://frontend-blue-chi-18.vercel.app/bubble-index
**GitHub:** https://github.com/amicusDei/industry-value-estimator

**Phase 3 abgeschlossen.** Alle Features deployed und live.

Fertige Copy-Paste-Prompts und Quick-Verify-Skripte: siehe **`PROMPTS.md`**.

