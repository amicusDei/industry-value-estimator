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

### Open Issues

1. **ai_software 2024 scope-mixing:** +111% YoY spike from Precedence Research ($209B broad scope) vs CB Insights ($70B narrow). Documented in ASSUMPTIONS.md.

2. **Ensemble backtesting limited:** Only ai_hardware has EDGAR hard actuals. Other segments use soft actuals (circular). Transparently shown on /diagnostics.

3. **CAGR at floors:** All 4 segments are calibration-floor-constrained (model alone underperforms consensus). Documented trade-off.

4. **Interpolation dominance:** 75-85% of quarterly data is interpolated. 6-8 real points per 36 total per segment.

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

### Gate 3: Modell-Qualität (Zielwerte nach Quarterly-Umbau)
```
Segment            MAPE Target    CI80 Coverage Target    CI95 Coverage Target
ai_hardware        < 25%          > 65%                   > 85%
ai_infrastructure  < 25%          > 65%                   > 85%
ai_software        < 30%          > 60%                   > 80%
ai_adoption        < 30%          > 60%                   > 80%
```

### Gate 4: CAGR-Plausibilität
```
Alle Segment-CAGRs 2025-2030 müssen innerhalb [Floor, Floor × 2.5] liegen.
Floors: hardware 15%, infrastructure 25%, software 20%, adoption 15%.
```

### Gate 5: Doku-Konsistenz
```
Kein Verweis auf PCA-Composite, value_chain_multiplier, oder run_statistical_pipeline in aktiver Doku.
ASSUMPTIONS.md, ARCHITECTURE.md, METHODOLOGY.md, README.md alle auf v1.1 konsolidiert.
```

## Arbeitsregeln für Claude Code

1. **Lies REFACTORING_PROMPT.md vor jeder Session** — enthält den vollständigen Arbeitsplan mit 4 Arbeitspaketen.

2. **Ein AP-Schritt pro Session.** Nicht mehrere APs in einer Session mischen. Lieber einen Schritt sauber als drei halb.

3. **Verifikation VOR Commit.** Jede Änderung wird ERST verifiziert (Tests, Pipeline-Run, Daten-Inspektion), DANN committed. Kein "fix later".

4. **Daten-Inspektion ist Pflicht.** Nach jeder Pipeline-Änderung: Parquet laden, Shape prüfen, Ranges prüfen, Stichproben ansehen. Nicht blind auf "PASSED" vertrauen.

5. **Kein Silent Failure.** Bare `except Exception: pass` ist verboten. Jeder Exception-Handler muss mindestens `logging.warning()` haben.

6. **Dokumentation ist Teil der Aufgabe.** Jede Code-Änderung die Verhalten ändert muss in ASSUMPTIONS.md oder ARCHITECTURE.md reflektiert werden. Doku-Drift war der Hauptgrund für die aktuelle Schwammigkeit.

7. **Contract Tests als Abnahme.** Bevor ein AP als "done" markiert wird, müssen die relevanten Quality-Gates bestehen. Wenn ein Gate failt, ist das AP nicht done — egal was der Code tut.

## Vollständiger Arbeitsplan

Siehe `REFACTORING_PROMPT.md` für die detaillierten Arbeitspakete:
- **AP1:** v1.0 Cleanup, Doku-Konsolidierung, Bug-Fixes
- **AP2:** Earnings-basierte AI-Revenue-Attribution (Hybrid Regex + LLM)
- **AP3:** Bloomberg-Style Frontend (Next.js + FastAPI + TradingView Charts)
- **AP4:** Modellqualität auf institutionelles Niveau (Quarterly-Daten, CI-Fix, Private Integration, Backtesting)

Ausführungsreihenfolge: AP1 → AP4.1+4.2 → AP2 → AP4.3-4.5 → AP3 → AP4.6
