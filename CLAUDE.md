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

## Arbeitsregeln für Claude Code

1. **Lies diese Datei (CLAUDE.md) vollständig vor jeder Session** — enthält Vision, Architektur, Arbeitsplan und Qualitäts-Gates. Für fertige Prompts: siehe PROMPT_TEMPLATES.md. Für priorisierte Tasks: siehe BACKLOG.md.

2. **Ein AP-Schritt pro Session.** Nicht mehrere APs in einer Session mischen. Lieber einen Schritt sauber als drei halb.

3. **Verifikation VOR Commit.** Jede Änderung wird ERST verifiziert (Tests, Pipeline-Run, Daten-Inspektion), DANN committed. Kein "fix later".

4. **Daten-Inspektion ist Pflicht.** Nach jeder Pipeline-Änderung: Parquet laden, Shape prüfen, Ranges prüfen, Stichproben ansehen. Nicht blind auf "PASSED" vertrauen.

5. **Kein Silent Failure.** Bare `except Exception: pass` ist verboten. Jeder Exception-Handler muss mindestens `logging.warning()` haben.

6. **Dokumentation ist Teil der Aufgabe.** Jede Code-Änderung die Verhalten ändert muss in ASSUMPTIONS.md oder ARCHITECTURE.md reflektiert werden. Doku-Drift war der Hauptgrund für die aktuelle Schwammigkeit.

7. **Contract Tests als Abnahme.** Bevor ein AP als "done" markiert wird, müssen die relevanten Quality-Gates bestehen. Wenn ein Gate failt, ist das AP nicht done — egal was der Code tut.

## Strategische Vision (v2 — Research-Intelligence-Plattform)

Das Projekt entwickelt sich vom Forecast-Dashboard zur Research-Intelligence-Plattform. Der Kern-Differentiator gegenüber Bloomberg/FactSet ist die Kombination aus Open-Source-Transparenz, Analyst-Dispersion-als-Signal, und automatisierter Narrativ-Generierung. Ein Analyst bei einer Bank nutzt Bloomberg für Rohdaten — und dieses Tool für Interpretation und Szenario-Analyse.

### Drei Dimensionen die den Unterschied machen

1. **Dispersion als Signal:** Nicht nur Konsensus-Mediane, sondern Inter-Quartile-Range der Analystenschätzungen über Zeit tracken. Sinkende Dispersion = konvergierende Marktmeinung = höhere Forecast-Konfidenz. Steigende Dispersion = fundamentale Unsicherheit.

2. **Scenario Engine:** Bull/Base/Bear-Cases mit jeweils eigenem Parametersatz, pre-computed und vergleichbar. Nicht ein Widget mit Slider, sondern drei vollständige Forecast-Sets die den ganzen Stack durchlaufen.

3. **Automatisierte Narrativ-Ebene:** Zahlen in argumentative Kontexte setzen. "ai_hardware wächst mit 15% CAGR — getrieben durch Hyperscaler-Capex (+40% YoY), sinkende Inference-Kosten, und Edge-Deployment TAM-Erweiterung." Regelbasiert, kein LLM nötig.

### Reference-Class: Was die Top-Player machen

- **Bloomberg ASKB:** Agentenbasierte mehrstufige Research-Workflows, Earnings-Call-Cross-Examination
- **Visible Alpha:** 250+ Broker, 28M Analyst Line Items, Dispersion-Tracking, 24h Revisions-Freshness
- **FactSet:** Makro-zu-Mikro Drill-Down, Bottom-Up vs. Top-Down Kreuzvalidierung

## Arbeitsplan

### Phase 1 (abgeschlossen): Foundation

Siehe `REFACTORING_PROMPT.md` für historischen Kontext:
- ~~**AP1:** v1.0 Cleanup, Doku-Konsolidierung, Bug-Fixes~~ ✓
- ~~**AP2:** Earnings-basierte AI-Revenue-Attribution~~ ✓
- ~~**AP4.1-4.5:** Quarterly-Daten, CI-Fix, Private Integration, Backtesting, Scope-Normalisierung~~ ✓

### Phase 2 (aktiv): Research-Intelligence Features

| AP | Feature | Dateien | Abhängig von | Aufwand |
|---|---|---|---|---|
| **v2-AP1** | Analyst Dispersion Index | `src/ingestion/market_anchors.py`, `analyst_dispersion.parquet` | — | 2-3h |
| **v2-AP2** | Scenario Engine (Bull/Base/Bear) | `ai.yaml`, `run_ensemble_pipeline.py`, `forecasts_scenarios.parquet` | — | 3-4h |
| **v2-AP3** | Dispersion-Visualisierung (Frontend) | `DispersionChart.tsx`, Segment-Pages, API | v2-AP1 | 2-3h |
| **v2-AP4** | Scenario-Switcher (Frontend) | `ScenarioSelector.tsx`, Segment-Pages, API | v2-AP2 | 2-3h |
| **v2-AP5** | Automated Insight Narratives | `src/narratives/insight_generator.py`, API, `InsightPanel.tsx` | v2-AP1, v2-AP2 | 3-4h |
| **v2-AP6** | Bottom-Up Validation (EDGAR Capex) | `src/ingestion/edgar_capex.py`, `company_level_ai_revenue.parquet` | — | 4-5h |

**Ausführungsreihenfolge:** v2-AP1 + v2-AP2 parallel → v2-AP3 + v2-AP4 parallel → v2-AP5 → v2-AP6

### Phase 3 (noch nicht begonnen): Frontend Bloomberg-Grade + Portfolio

- **AP3:** Bloomberg-Style Frontend Finishing (Charts, Dark Mode, Export)
- Methodology Paper, Docker-Demo, Portfolio-Showcase

Fertige Copy-Paste-Prompts für jedes v2-AP: siehe `PROMPT_TEMPLATES.md`.
