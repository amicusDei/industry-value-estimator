# Projekt-Backlog — AI Industry Value Estimator

Stand: 2026-04-01

## Strategische Richtung

Von Forecast-Dashboard zu Research-Intelligence-Plattform. Differentiator: Analyst-Dispersion-als-Signal + Scenario Engine + automatisierte Narrativ-Generierung. Vollständige Vision siehe CLAUDE.md → "Strategische Vision (v2)".

## Priorisierung: Impact × Aufwand

### P0 — Jetzt machen: v2 Research-Intelligence Features

Diese APs sind die strategische Priorität. Fertige Prompts in PROMPT_TEMPLATES.md.

#### Backend / Pipeline (parallel ausführbar)
- [ ] **v2-AP1**: Analyst Dispersion Index — IQR, Std, Min/Max pro Segment/Jahr aus vorhandenen Daten berechnen → `analyst_dispersion.parquet` (2-3h, keine Abhängigkeiten)
- [ ] **v2-AP2**: Scenario Engine — Pre-computed Bull/Base/Bear mit unterschiedlichen CAGR-Floors → `forecasts_scenarios.parquet` (3-4h, keine Abhängigkeiten)

#### Frontend (nach Backend-APs)
- [ ] **v2-AP3**: Dispersion-Visualisierung — Fan-Chart/Box-Plot auf Segment-Pages + API-Endpoint (2-3h, nach v2-AP1)
- [ ] **v2-AP4**: Scenario-Switcher — Toggle Conservative/Base/Aggressive, clientseitiges Switching (2-3h, nach v2-AP2)

#### Intelligence Layer (nach Backend-APs)
- [ ] **v2-AP5**: Automated Insight Narratives — Regelbasierte Texte pro Segment: CAGR-Treiber, Dispersion-Trends, Scenario-Spreads, Top-Analyst-Identifikation (3-4h, nach v2-AP1 + v2-AP2)

#### Stretch Goal
- [ ] **v2-AP6**: Bottom-Up Validation — EDGAR Capex-Extraction für Top-5 Companies → Sum-of-Parts vs. Top-Down Kreuzvalidierung (4-5h, parallel möglich)

### P0 — Frontend Bloomberg-Grade (parallel zu v2-APs)

- [ ] **FE-01**: TradingView Charts reparieren/professionalisieren (CI-Bänder, Achsenbeschriftung, Tooltips)
- [ ] **FE-02**: Total Market Chart (Summe aller Segmente mit Overlap-Bereinigung)
- [ ] **FE-04**: Excel/CSV Export aller Forecast-Daten mit Metadaten-Header
- [ ] **FE-05**: Diagnostics-Page fertigstellen (MAPE-Heatmap, CI Coverage, Regime-Analyse)
- [ ] **FE-06**: Responsive Design + Dark Mode (Bloomberg-Look)

Note: FE-03 (Analyst Consensus Visualization) wird durch v2-AP3 (Dispersion-Visualisierung) ersetzt und erweitert.

### P0 — Modell-Credibility

- [ ] **MOD-01**: Mehr Analystendaten beschaffen (Mordor Intelligence, MarketsandMarkets — bereits 12 Firmen, Ziel: 15+)
- [ ] **MOD-02**: Sector-spezifische Features für LightGBM (NVIDIA earnings als Lead-Indikator für ai_hardware)
- [ ] **MOD-03**: Prophet-Hyperparameter-Tuning per Segment (changepoint_prior_scale, seasonality_prior_scale)

### P1 — Nächste Woche (hoher Impact, moderater Aufwand)

#### Institutionelle Dokumentation
- [ ] **DOC-01**: Methodology Paper (2-3 Seiten, LaTeX oder PDF) — Research-Note-Format à la Goldman Sachs
- [ ] **DOC-02**: Data Provenance Dashboard — welche Quelle floss wann mit welchem Gewicht ein

Note: DOC-03 (Sensitivity Analysis) wird durch v2-AP2 (Scenario Engine) + v2-AP4 (Scenario-Switcher) ersetzt.

#### Pipeline-Robustheit
- [ ] **PIPE-01**: CI/CD: GitHub Actions für automatischen Pipeline-Run + Test bei jedem Push
- [ ] **PIPE-02**: Data Freshness Check — Alert wenn Market Anchor-Daten >90 Tage alt
- [ ] **PIPE-03**: Parquet Schema Evolution — pandera-Schema versionieren

### P2 — Mittelfristig (nice-to-have, hoher Aufwand)

- [ ] **EXT-01**: Zweite Industrie (z.B. "Quantum Computing") zum Beweis der Generalisierbarkeit
- [ ] **EXT-02**: Real-time EDGAR Ingestion (automatisch neue 10-K/10-Q parsen) — Vorstufe in v2-AP6
- [ ] **EXT-03**: LLM-basierte Earnings Call Analyse (Keyword-Extraction + Sentiment)
- [ ] **EXT-04**: Monte Carlo Simulation statt Bootstrap für CIs

### P3 — Portfolio-Showcase

- [ ] **SHOW-01**: README mit Screenshots, Architecture-Diagram, Key-Findings
- [ ] **SHOW-02**: Docker Compose für One-Click-Demo (API + Frontend + Pipeline)
- [ ] **SHOW-03**: 2-Minuten Video-Walkthrough (Loom oder ähnlich)
- [ ] **SHOW-04**: LinkedIn Post / Case Study über das Projekt

## Ideation-Inbox

Neue Ideen hier parken, später priorisieren:

- _[Platz für neue Ideen]_

## Erledigte Tasks

- [x] v1.0 Cleanup, Doku-Konsolidierung (AP1)
- [x] Earnings-basierte AI-Revenue-Attribution (AP2)
- [x] ai_software Scope-Mixing fix (segment_scope_coefficient)
- [x] Total-Market Disaggregation (51 entries → 4 segments)
- [x] Circular Backtesting eliminiert (echtes LOO)
- [x] Bootstrap CIs + non-negative enforcement
- [x] Nominal/Real USD Switch (Frontend + API)
- [x] Private Market Integration (18 companies)
