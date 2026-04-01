# ⚠️ DEPRECATED — Roadmap und Task-Status sind in CLAUDE.md konsolidiert. Diese Datei wird nicht mehr gepflegt.

# Projekt-Backlog — AI Industry Value Estimator

Stand: 2026-04-01

## Strategische Richtung

Von Forecast-Dashboard zu Research-Intelligence-Plattform. Differentiator: Analyst-Dispersion-als-Signal + Scenario Engine + automatisierte Narrativ-Generierung. Vollständige Vision siehe CLAUDE.md → "Strategische Vision (v2)".

## Priorisierung: Impact × Aufwand

### P0 — Jetzt machen: v2 Research-Intelligence Features

Diese APs sind die strategische Priorität. Fertige Prompts in PROMPT_TEMPLATES.md.

#### Backend / Pipeline ✓
- [x] **v2-AP1**: Analyst Dispersion Index → `analyst_dispersion.parquet` (45 rows, 4 seg × 9+ yr)
- [x] **v2-AP2**: Scenario Engine → `forecasts_scenarios.parquet` (672 rows, 3 Szenarien)

#### Frontend ✓
- [x] **v2-AP3**: Dispersion-Visualisierung — Fan-Chart auf Segment-Pages
- [x] **v2-AP4**: Scenario-Switcher — Toggle Conservative/Base/Aggressive

#### Intelligence Layer ✓
- [x] **v2-AP5**: Automated Insight Narratives — 5 Insight-Typen pro Segment (314 Zeilen, regelbasiert)

#### ✓ Bottom-Up Validation
- [x] **v2-AP6a**: Bottom-Up Backend-Erweiterung — Multi-Year, Coverage-Trends, Narrativ-Integration
- [x] **v2-AP6b**: Bottom-Up Frontend — Stacked Bar Chart mit Coverage-Ratio, API-Endpoint

### P0 — Phase 3: Frontend Bloomberg-Grade + Portfolio-Showcase

Ziel: 5-Minuten-Eindruck für Hiring Manager. Fertige Prompts in PROMPT_TEMPLATES.md.

#### Parallel startbar (keine Abhängigkeiten)
- [ ] **v3-AP1**: README Rewrite + Architecture Diagram — GitHub-Visitenkarte (2h)
- [ ] **v3-AP3**: Chart Professionalisierung — CI-Bänder, Tooltips, Legende, Forecast-Marker (2-3h)
- [ ] **v3-AP4**: Diagnostics Page — MAPE-Heatmap, CI Coverage, Regime-Analyse, Data Sources (3h)
- [ ] **v3-AP7**: Excel/CSV Export — Multi-Sheet .xlsx mit Metadaten-Header (2h)

#### Sequentiell (nach den parallelen APs)
- [ ] **v3-AP5**: Methodology Paper als PDF — Goldman-Sachs-Research-Note-Stil, 3-4 Seiten (3-4h, nach v3-AP3)
- [ ] **v3-AP6**: Screenshots + README Finalisierung — 3+ Screenshots in README einfügen (1h, nach v3-AP3 + v3-AP4)
- [ ] **v3-AP2**: Live Deployment — Vercel (Frontend) + Fly.io (API), klickbarer Link in README (2h)

Note: FE-01 → v3-AP3, FE-05 → v3-AP4, FE-04 → v3-AP7, DOC-01 → v3-AP5. Dark Mode ist bereits implementiert (CSS vars). FE-02 (Total Market Chart) existiert bereits als TotalChart.tsx.

### P1 — Nach Phase 3

#### Modell-Credibility
- [ ] **MOD-01**: Mehr Analystendaten beschaffen (Mordor Intelligence, MarketsandMarkets — bereits 12 Firmen, Ziel: 15+)
- [ ] **MOD-02**: Sector-spezifische Features für LightGBM (NVIDIA earnings als Lead-Indikator für ai_hardware)
- [ ] **MOD-03**: Prophet-Hyperparameter-Tuning per Segment (changepoint_prior_scale, seasonality_prior_scale)

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
- [x] v2-AP1: Analyst Dispersion Index (45 rows, 4 seg × 9+ yr)
- [x] v2-AP2: Scenario Engine (672 rows, 3 Szenarien)
- [x] v2-AP3: Dispersion-Visualisierung (Frontend)
- [x] v2-AP4: Scenario-Switcher (Frontend)
- [x] v2-AP5: Automated Insight Narratives (5 Insight-Typen, regelbasiert)
- [x] v2-AP6a: Bottom-Up Validation Backend (Multi-Year, Coverage-Trends, Narrativ-Integration)
- [x] v2-AP6b: Bottom-Up Validation Frontend (Stacked Bar Chart, API-Endpoint)
