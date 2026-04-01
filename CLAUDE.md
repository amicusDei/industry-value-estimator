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

1. **Lies diese Datei (CLAUDE.md) vollständig vor jeder Session** — enthält Vision, Architektur, Arbeitsplan, Qualitäts-Gates und fertige Prompts. Alles in einer Datei, keine externen Leitdateien nötig.

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

**Phase 2 abgeschlossen.** Nächster Schritt: Phase 3 (Frontend Bloomberg-Grade + Portfolio)

### Phase 3 (aktiv): Frontend Bloomberg-Grade + Portfolio-Showcase

Ziel: Projekt von "funktionierendes Tool" zu "vorstellbares Portfolio-Stück" transformieren. Optimiert für den 5-Minuten-Eindruck eines Hiring Managers bei einer Bank.

| AP | Feature | Dateien | Abhängig von | Aufwand |
|---|---|---|---|---|
| **v3-AP1** | README Rewrite + Architecture Diagram | `README.md` | — | 2h |
| **v3-AP2** | Live Deployment (Vercel + Fly.io) | `fly.toml`, `vercel.json` | — | 2h |
| **v3-AP3** | Chart Professionalisierung (CI-Bänder, Tooltips, Legende) | `TimeseriesChart.tsx` | — | 2-3h |
| **v3-AP4** | Diagnostics Page (MAPE-Heatmap, CI Coverage, Regime-Analyse) | `diagnostics/page.tsx`, `api/routers/diagnostics.py` | — | 3h |
| **v3-AP5** | Methodology Paper als PDF (Goldman-Sachs-Research-Note-Stil) | `scripts/generate_methodology_paper.py` | v3-AP3 | 3-4h |
| **v3-AP6** | Screenshots + README Finalisierung | `README.md`, `docs/screenshots/` | v3-AP3, v3-AP4 | 1h |
| **v3-AP7** | Excel/CSV Export + Responsive Cleanup | `ExportButton.tsx`, `api/routers/export.py` | — | 2h |

**Ausführungsreihenfolge:** v3-AP1 + v3-AP3 + v3-AP4 parallel → v3-AP5 + v3-AP7 parallel → v3-AP6 (Screenshots letzter Schritt) → v3-AP2 (Deployment)

Fertige Copy-Paste-Prompts: siehe Section "Phase 3 — Fertige Prompts" weiter unten.

## Prompt-Muster (für neue/eigene Prompts)

Jeder Prompt an Claude Code hat exakt 4 Sections. Keine davon ist optional. Max 3 Dateien pro Prompt. Größen-Regel: Small (1-2 Dateien, 5 min), Medium (2-3 Dateien, 15 min). Kein "Large" — splitten.

```
## KONTEXT
- Projekt: AI Industry Value Estimator
- Lies CLAUDE.md für Architektur-Überblick
- Betroffene Dateien: [max 3]
- Aktueller Zustand: [1-2 Sätze]

## AUFGABE
1. [Konkret, spezifisch, messbar]
2. [...]
(Max 5 Schritte. Mehr = splitten.)

## CONSTRAINTS
- Ändere NUR die oben genannten Dateien
- Wenn du unsicher bist, FRAGE statt zu raten

## VERIFIKATION
python3 -c "
print('VERIFY: [Metrik] = [Wert] (expect [Bereich])')
"
Wenn IRGENDEINE Verifikation fehlschlägt, STOPPE und erkläre warum.
```

## Quick-Verify nach Pipeline-Änderungen

```python
python3 -c "
import pandas as pd
df = pd.read_parquet('data/processed/forecasts_ensemble.parquet')
print(f'VERIFY: Shape = {df.shape} (expect 224 rows)')
print(f'VERIFY: NaN in point_estimate = {df.point_estimate_nominal.isna().sum()} (expect 0)')
print(f'VERIFY: CI ordering violations = {len(df[df.ci95_lower_nominal > df.point_estimate_nominal])} (expect 0)')
sw24 = df[(df.segment=='ai_software') & (df.year==2024) & (df.quarter==4)]
print(f'VERIFY: ai_software 2024 Q4 = {sw24.point_estimate_nominal.iloc[0]:.1f}B (expect 60-85B)')
for seg in sorted(df.segment.unique()):
    s = df[(df.segment==seg) & (df.quarter==4)]
    v26 = s[s.year==2026].point_estimate_nominal.iloc[0]
    v30 = s[s.year==2030].point_estimate_nominal.iloc[0]
    cagr = (v30/v26)**(1/4) - 1
    print(f'VERIFY: {seg} CAGR 2026-2030 = {cagr:.1%}')
"
```

---

## Phase 3 — Fertige Prompts (Copy-Paste für Claude Code)

Reihenfolge: v3-AP1 + v3-AP3 + v3-AP4 parallel → v3-AP5 + v3-AP7 parallel → v3-AP6 → v3-AP2.

### v3-AP1: README Rewrite + Architecture Diagram

```
## KONTEXT
- Projekt: AI Industry Value Estimator
- Lies CLAUDE.md für Architektur-Überblick
- Betroffene Dateien: README.md
- Aktueller Zustand: README ist veraltet. Referenziert run_dashboard.py (gelöscht), run_reports.py, "$200B 2023 consensus baseline" (nicht mehr korrekt). Keine Screenshots, kein Architecture-Diagram, keine Erwähnung von Dispersion Index, Scenario Engine, Insight Narratives, Bottom-Up Validation.

## AUFGABE
1. README komplett neu schreiben. Struktur:
   - **Header:** Projekt-Name + 1-Satz-Pitch ("Institutional-grade AI market sizing platform combining econometric models with analyst consensus data")
   - **Badge-Leiste:** Python 3.13, Next.js 15, FastAPI, License MIT (oder was aktuell gilt)
   - **Screenshot-Platzhalter:** `![Dashboard](docs/screenshots/dashboard.png)` — 3 Platzhalter (Dashboard, Segment Detail, Diagnostics)
   - **Key Features:** 5-6 Punkte (Ensemble Forecasting, Analyst Dispersion, Scenario Engine, Bottom-Up Validation, Automated Insights, Bloomberg-Style UI) — jeweils 1 Satz
   - **Architecture:** Mermaid-Diagram inline (Ingestion → Processing → Models → API → Frontend)
   - **Quick Start:** Docker Compose (3 Befehle), alternativ manual setup
   - **Data Sources:** Tabelle mit 4-5 Quellen (EDGAR, LSEG, World Bank, OECD, 12 Analyst Firms)
   - **Model Performance:** Tabelle mit MAPE/CI Coverage pro Segment (aus CLAUDE.md Gate 3)
   - **Tech Stack:** Tabelle oder Liste
   - **License + Disclaimer**
2. Maximal 150 Zeilen. Kein Absatz länger als 3 Sätze.
3. Alle Referenzen auf run_dashboard.py, run_reports.py, run_statistical_pipeline.py entfernen.

## CONSTRAINTS
- Ändere NUR README.md
- Englisch (Portfolio-Publikum ist international)
- Keine Emojis im Text (professionell)
- Mermaid-Diagram muss auf GitHub renderbar sein
- Screenshot-Platzhalter als relative Pfade (docs/screenshots/)

## VERIFIKATION
1. Zeige die vollständige README.md
2. Zähle die Zeilen: wc -l README.md (expect <= 150)
3. Prüfe auf veraltete Referenzen: grep -i "run_dashboard\|run_reports\|run_statistical\|200B\|PCA" README.md (expect 0 matches)
4. Prüfe Mermaid-Syntax: der Mermaid-Block muss mit ```mermaid beginnen und enden

Wenn IRGENDEINE Verifikation fehlschlägt, STOPPE und erkläre warum.
```

### v3-AP3: Chart Professionalisierung

```
## KONTEXT
- Projekt: AI Industry Value Estimator, Frontend in frontend/
- Stack: Next.js 15 + React 19 + TypeScript + TailwindCSS
- API läuft auf localhost:8000 (FastAPI)
- Betroffene Dateien: frontend/src/components/charts/TimeseriesChart.tsx
- Chart-Library: lightweight-charts v5.1.0 (bereits installiert)
- Aktueller Zustand: Forecast-Chart zeigt Linien, aber CI-Bänder sind kaum sichtbar oder fehlen, Achsenbeschriftung unvollständig, Tooltip zeigt keine Werte, keine Legende.

## AUFGABE
1. TimeseriesChart.tsx komplett überarbeiten:
   - Historical-Daten (is_forecast=false): durchgehende Linie in slate-500 (#64748b)
   - Forecast-Daten (is_forecast=true): durchgehende Linie in orange-500 (#f97316)
   - CI80: halbtransparente Fläche (AreaSeries) in rgba(249,115,22,0.25)
   - CI95: halbtransparente Fläche in rgba(249,115,22,0.08)
   - Vertikale gestrichelte Linie am Übergang Historical→Forecast (mit Label "Forecast Start")
2. Y-Achse: "$0B" Format, auto-scaled, rechts positioniert (Bloomberg-Konvention)
3. X-Achse: "Q1'17", "Q2'17" Format für Quarterly-Daten
4. Tooltip: Segment-Name, Datum (Q1 2024), Point Estimate ($XX.XB), CI80 Range, CI95 Range
5. Legende oberhalb des Charts: Historical (grau) | Forecast (orange) | CI80 | CI95

## CONSTRAINTS
- Bloomberg-Style: bg-slate-900, border-border, orange Akzente
- Nutze lightweight-charts v5 API (createChart, addLineSeries, addAreaSeries)
- Wenn lightweight-charts AreaSeries nicht unterstützt für CI-Bänder: wechsle zu recharts (bereits in node_modules oder installierbar) — aber nur als Fallback
- Keine neuen npm Dependencies außer recharts falls nötig
- Chart muss responsive sein (resize on container change)

## VERIFIKATION
1. cd frontend && npm run build  (muss ohne Error durchlaufen)
2. Beschreibe visuell was der User auf /segments/ai_hardware sieht:
   - Welche Farben hat die Historical-Linie?
   - Sind CI-Bänder als Flächen sichtbar?
   - Was zeigt der Tooltip beim Hover?
   - Gibt es eine Legende?
3. curl http://localhost:8000/api/v1/forecasts?segment=ai_hardware | python3 -c "
import json, sys
data = json.load(sys.stdin)
forecast = [d for d in data if d.get('is_forecast')]
print(f'VERIFY: Total rows = {len(data)}')
print(f'VERIFY: Forecast rows = {len(forecast)}')
print(f'VERIFY: Has CI80 = {\"ci80_lower_nominal\" in data[0]}')
print(f'VERIFY: Has CI95 = {\"ci95_lower_nominal\" in data[0]}')
"

Wenn der Build fehlschlägt, STOPPE und fixe den Error bevor du weitermachst.
```

### v3-AP4: Diagnostics Page

```
## KONTEXT
- Projekt: AI Industry Value Estimator, Frontend in frontend/
- Stack: Next.js 15 + React 19 + TypeScript + TailwindCSS + recharts
- API: localhost:8000, Endpunkt GET /api/v1/diagnostics existiert bereits
- Betroffene Dateien: frontend/src/app/diagnostics/page.tsx, api/routers/diagnostics.py
- Aktueller Zustand: Diagnostics-Page existiert aber ist unvollständig. API-Endpunkt liefert Basis-Metriken.

## AUFGABE
1. API-Endpunkt /api/v1/diagnostics erweitern um:
   - mape_matrix: Segment × Year MAPE-Werte (aus Backtesting-Ergebnissen)
   - ci_coverage: {segment, ci80_target: 0.80, ci80_actual, ci95_target: 0.95, ci95_actual}
   - regime_comparison: {segment, pre_genai_mape (2017-2021), post_genai_mape (2022+)}
   - data_sources: [{source_name, segments_covered, years_covered, n_entries}]
2. Frontend diagnostics/page.tsx mit Tab-Layout (4 Tabs):
   - Tab 1 "Model Performance": MAPE-Heatmap (recharts oder custom Grid) — Farb-Encoding: grün <15%, gelb 15-30%, orange 30-50%, rot >50%
   - Tab 2 "CI Coverage": Balkendiagramm CI80 Actual vs Target (80%) und CI95 Actual vs Target (95%) pro Segment
   - Tab 3 "Regime Analysis": Grouped Bar Chart Pre-GenAI vs Post-GenAI MAPE pro Segment
   - Tab 4 "Data Sources": Tabelle mit Quellen, Coverage, Eintrags-Anzahl
3. Jeder Tab hat einen erklärenden 1-Satz-Subtitle.

## CONSTRAINTS
- Bloomberg-Style: bg-slate-900, Tabs als Pill-Buttons (wie ScenarioSelector)
- Nutze recharts für alle Charts
- MAPE-Werte aus CLAUDE.md Gate 3 als Referenz
- Loading States pro Tab
- Mobile: Tabs stacken vertikal auf <768px

## VERIFIKATION
1. curl http://localhost:8000/api/v1/diagnostics | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'VERIFY: Keys = {list(data.keys())}')
print(f'VERIFY: Has mape_matrix = {\"mape_matrix\" in data}')
print(f'VERIFY: Has ci_coverage = {\"ci_coverage\" in data}')
print(f'VERIFY: Has regime_comparison = {\"regime_comparison\" in data}')
print(f'VERIFY: Has data_sources = {\"data_sources\" in data}')
if 'ci_coverage' in data:
    for c in data['ci_coverage']:
        print(f'  {c[\"segment\"]}: CI80={c[\"ci80_actual\"]:.0%} (target 80%), CI95={c[\"ci95_actual\"]:.0%} (target 95%)')
"
2. cd frontend && npm run build  (muss ohne Error durchlaufen)
3. Beschreibe die 4 Tabs: was sieht der User jeweils?

Wenn IRGENDEINE Verifikation fehlschlägt, STOPPE und erkläre warum.
```

### v3-AP5: Methodology Paper als PDF (nach v3-AP3)

```
## KONTEXT
- Projekt: AI Industry Value Estimator
- Lies CLAUDE.md für Architektur, Modell-Details, und Quality-Gates
- Lies METHODOLOGY.md und ASSUMPTIONS.md für methodische Details
- Betroffene Dateien: scripts/generate_methodology_paper.py (NEU), docs/methodology_paper.pdf (Output)
- Aktueller Zustand: Methodology ist als Markdown und /methodology-Page dokumentiert. Kein standalone PDF im Research-Note-Format.

## AUFGABE
1. Python-Script scripts/generate_methodology_paper.py erstellen das ein PDF generiert:
   - Nutze fpdf2 (pip install fpdf2 --break-system-packages)
   - Format: A4, 3-4 Seiten
2. PDF-Struktur (Goldman Sachs Research Note Stil):
   - **Seite 1 Header:** "AI Industry Valuation: A Multi-Source Ensemble Approach" | Datum | "Dr. Matthias Wegner"
   - **Key Findings Box** (grauer Kasten): 4 Punkte mit Daten aus Parquet-Files
   - **Methodology (1 Seite):** Data Sources, Ensemble Model, CAGR Calibration, Scope Normalization
   - **Results (1 Seite):** Segment-Forecasts Tabelle (Base/Conservative/Aggressive), MAPE-Tabelle, CI Coverage
   - **Data Sources (0.5 Seite):** Source-Tabelle
   - **Disclaimer Footer**
3. Daten aus Parquet-Files ziehen — keine hardcoded Werte.

## CONSTRAINTS
- Englisch (institutionelles Publikum)
- Professionelles Layout: Schwarz/Grau/Dunkelblau, keine Emojis
- Tabellen mit Gridlines, rechts-ausgerichtete Zahlen
- Output nach docs/methodology_paper.pdf

## VERIFIKATION
1. python3 scripts/generate_methodology_paper.py (muss ohne Error durchlaufen)
2. ls -la docs/methodology_paper.pdf (expect >50KB)
3. python3 -c "
with open('scripts/generate_methodology_paper.py') as f:
    code = f.read()
    assert 'read_parquet' in code, 'ERROR: No parquet reads — values might be hardcoded!'
    print('VERIFY: Script reads from Parquet files')
    import re
    suspicious = re.findall(r'(?:estimate|forecast|mape)\s*=\s*[\d.]+', code, re.I)
    if suspicious:
        print(f'WARNING: Possibly hardcoded values: {suspicious}')
    else:
        print('VERIFY: No suspicious hardcoded values')
"

Wenn IRGENDEINE Verifikation fehlschlägt, STOPPE und erkläre warum.
```

### v3-AP7: Excel/CSV Export

```
## KONTEXT
- Projekt: AI Industry Value Estimator
- API: localhost:8000, Endpunkt GET /api/v1/export existiert bereits (api/routers/export.py)
- Frontend: ExportButton.tsx Komponente existiert bereits
- Betroffene Dateien: api/routers/export.py, frontend/src/components/ExportButton.tsx
- Aktueller Zustand: Export-Infrastruktur existiert aber unklar ob Multi-Sheet und Metadaten-Header funktionieren.

## AUFGABE
1. api/routers/export.py prüfen und erweitern:
   - GET /api/v1/export?segment=ai_hardware&scenario=base&format=xlsx
   - Excel mit 3 Sheets: "Forecasts" (Hauptdaten), "Methodology" (Kurztext + Quellen), "Metadata" (Erstellungsdatum, Segment, Scenario, Datenstand)
   - Forecasts-Sheet: Header-Zeile, dann Year, Quarter, Point Estimate ($B), CI80 Low/High, CI95 Low/High, Historical/Forecast Flag
   - Zahlen mit 1 Dezimalstelle
   - format=csv als Alternative (ohne Multi-Sheet)
2. ExportButton.tsx: Download-Trigger mit Dropdown "Excel (.xlsx)" / "CSV (.csv)"
3. ExportButton in Segment-Detailseite integrieren falls noch nicht verlinkt.

## CONSTRAINTS
- Nutze openpyxl für Excel (bereits in Dependencies)
- Dateiname: "ai_industry_{segment}_{scenario}_{date}.xlsx"
- Keine neuen npm-Packages

## VERIFIKATION
1. curl -o /tmp/test_export.xlsx "http://localhost:8000/api/v1/export?segment=ai_hardware&scenario=base&format=xlsx"
   ls -la /tmp/test_export.xlsx (expect >10KB)
2. python3 -c "
import openpyxl
wb = openpyxl.load_workbook('/tmp/test_export.xlsx')
print(f'VERIFY: Sheets = {wb.sheetnames} (expect [Forecasts, Methodology, Metadata])')
ws = wb['Forecasts']
print(f'VERIFY: Rows = {ws.max_row} (expect >50)')
print(f'VERIFY: Cols = {ws.max_column} (expect >=7)')
"
3. cd frontend && npm run build

Wenn IRGENDEINE Verifikation fehlschlägt, STOPPE und erkläre warum.
```

### v3-AP6: Screenshots + README Finalisierung (nach v3-AP3 + v3-AP4)

Manueller Task: Docker-Container starten, Screenshots machen, in docs/screenshots/ speichern, README.md Platzhalter ersetzen.

### v3-AP2: Live Deployment (nach allen anderen)

Manueller Task: Vercel (Frontend) + Fly.io (API) konfigurieren, klickbaren Link in README einfügen.
