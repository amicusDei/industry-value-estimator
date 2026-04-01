# ⚠️ DEPRECATED — Aktive v3-Prompts sind in CLAUDE.md konsolidiert. Diese Datei enthält nur noch historische v2-Prompts als Referenz.

# Prompt Templates für Claude Code

## Template A: Daten/Pipeline-Änderung

```
## KONTEXT
- Projekt: AI Industry Value Estimator
- Lies CLAUDE.md für Architektur-Überblick
- Betroffene Dateien: [DATEI_1], [DATEI_2]
- Aktueller Zustand: [WAS IST DER IST-ZUSTAND?]

## AUFGABE
1. [Schritt 1: konkret was zu ändern ist]
2. [Schritt 2: ...]
3. [Schritt 3: ...]

## CONSTRAINTS
- Ändere NUR die oben genannten Dateien
- Keine neuen Dependencies hinzufügen
- Bestehende Tests dürfen nicht brechen
- Wenn du unsicher bist, FRAGE statt zu raten

## VERIFIKATION
Führe nach ALLEN Änderungen diesen Code aus und zeige das VOLLSTÄNDIGE Ergebnis:

python3 -c "
import pandas as pd
# [KONKRETER VERIFIKATIONSCODE]
# Muss mindestens 3 VERIFY:-Zeilen ausgeben
print('VERIFY: [Metrik] = [Wert] (expect [Erwartung])')
"

python3 -m pytest tests/[RELEVANTER_TEST].py -q --tb=short

Wenn IRGENDEINE Verifikation fehlschlägt, STOPPE und erkläre warum.
```

## Template B: Frontend-Änderung

```
## KONTEXT
- Projekt: AI Industry Value Estimator, Frontend in frontend/
- Stack: Next.js 15 + React 19 + TypeScript + TailwindCSS
- API läuft auf localhost:8000 (FastAPI)
- Betroffene Dateien: [DATEI_1], [DATEI_2]

## AUFGABE
1. [Schritt 1]
2. [Schritt 2]

## CONSTRAINTS
- Bloomberg-Style: dunkler Hintergrund, orange Akzente, mono-Font für Zahlen
- Keine neue NPM-Packages ohne explizite Begründung
- Mobile-responsive (min-width: 375px)
- Alle Zahlen als $XXB oder $X.XT formatieren

## VERIFIKATION
1. cd frontend && npm run build  (muss ohne Error durchlaufen)
2. Zeige den relevanten API-Call und die Response-Struktur
3. Beschreibe was der User auf der Seite sieht (Text-Mockup)

Wenn der Build fehlschlägt, STOPPE und fixe den Error bevor du weitermachst.
```

## Template C: Bug Fix

```
## KONTEXT
- Projekt: AI Industry Value Estimator
- Bug: [BESCHREIBUNG DES BUGS]
- Reproduktion: [WIE MAN DEN BUG SIEHT]
- Betroffene Datei: [DATEI]

## AUFGABE
1. Finde die Root Cause (zeige mir die relevante Code-Stelle VOR der Änderung)
2. Implementiere den Fix
3. Schreibe einen Test der den Bug abfängt (regression test)

## CONSTRAINTS
- Ändere nur die betroffene Datei + den neuen Test
- Der Fix darf keine anderen Tests brechen

## VERIFIKATION
1. Zeige den Bug VORHER (reproduziere ihn)
2. Zeige den Fix
3. Zeige dass der Bug NACHHER nicht mehr auftritt
4. python3 -m pytest tests/ -q --tb=short -k "not dashboard and not shap"
```

## Template D: Neue Feature-Seite (Frontend)

```
## KONTEXT
- Projekt: AI Industry Value Estimator
- API-Endpunkt: GET /api/v1/[ENDPOINT]
- Zielseite: frontend/src/app/[ROUTE]/page.tsx

## AUFGABE
1. Prüfe den API-Endpunkt: curl http://localhost:8000/api/v1/[ENDPOINT] | python3 -m json.tool
2. Erstelle die Page-Component mit TypeScript-Interfaces für die API-Response
3. Baue die UI (Bloomberg-Style, Charts wo sinnvoll)
4. Verlinke die Seite in der Navigation

## CONSTRAINTS
- Bloomberg-Style: bg-slate-900, text-slate-100, orange-500 Akzente
- Charts: lightweight-charts (TradingView) oder recharts
- Tabellen: mono-Font, right-aligned Zahlen, $-Formatierung
- Loading States und Error Handling sind Pflicht

## VERIFIKATION
1. curl-Response des API-Endpunkts zeigen
2. cd frontend && npm run build (muss durchlaufen)
3. Beschreibe die fertige Seite (was sieht der User)
```

---

## Fertige Prompts für v2 Research-Intelligence Features

Die folgenden Prompts sind copy-paste-ready für Claude Code. Reihenfolge: v2-AP1 + v2-AP2 parallel → v2-AP3 + v2-AP4 parallel → v2-AP5 → v2-AP6.

### v2-AP1: Analyst Dispersion Index (keine Abhängigkeiten)

```
## KONTEXT
- Projekt: AI Industry Value Estimator
- Lies CLAUDE.md für Architektur-Überblick
- Betroffene Dateien: src/ingestion/market_anchors.py, tests/test_market_anchors.py
- Aktueller Zustand: market_anchors_ai.parquet enthält Median-basierte Konsensus-Werte pro Segment/Jahr. Die zugrundeliegenden Einzelschätzungen (aus ai_analyst_registry.yaml) werden aggregiert und dann verworfen. Dispersion-Informationen gehen verloren.

## AUFGABE
1. In market_anchors.py eine neue Funktion `compute_analyst_dispersion(raw_df) -> pd.DataFrame` erstellen die VOR der Median-Aggregation die Einzelschätzungen pro Segment/Jahr analysiert: IQR (Q3-Q1), Standardabweichung, Min, Max, n_sources berechnen.
2. Output als data/processed/analyst_dispersion.parquet speichern mit Spalten: segment, year, iqr_usd_billions, std_usd_billions, min_usd_billions, max_usd_billions, n_sources, dispersion_ratio (IQR/Median).
3. In compile_market_anchors() den Aufruf vor der Aggregation einfügen.
4. Test schreiben: test_analyst_dispersion() prüft Shape, keine NaN wo n_sources >= 3, IQR >= 0.

## CONSTRAINTS
- Ändere NUR die oben genannten Dateien
- Nutze nur pandas/numpy (keine neuen Dependencies)
- Dispersion wird auf scope_normalized_usd_billions berechnet, NICHT auf as_published
- Wenn du unsicher bist, FRAGE statt zu raten

## VERIFIKATION
Führe nach ALLEN Änderungen diesen Code aus und zeige das VOLLSTÄNDIGE Ergebnis:

python3 -c "
import pandas as pd
disp = pd.read_parquet('data/processed/analyst_dispersion.parquet')
print(f'VERIFY: Shape = {disp.shape} (expect ~36 rows = 4 seg × 9 yr)')
print(f'VERIFY: Segments = {sorted(disp.segment.unique())} (expect 4)')
print(f'VERIFY: NaN in IQR where n>=3 = {disp[disp.n_sources>=3].iqr_usd_billions.isna().sum()} (expect 0)')
print(f'VERIFY: Negative IQR = {(disp.iqr_usd_billions < 0).sum()} (expect 0)')
for seg in sorted(disp.segment.unique()):
    s = disp[disp.segment==seg]
    print(f'{seg}: avg n_sources={s.n_sources.mean():.1f}, avg IQR={s.iqr_usd_billions.mean():.1f}B, avg dispersion_ratio={s.dispersion_ratio.mean():.2f}')
"

python3 -m pytest tests/test_market_anchors.py -q --tb=short

Wenn IRGENDEINE Verifikation fehlschlägt, STOPPE und erkläre warum.
```

### v2-AP2: Scenario Engine — Bull/Base/Bear (keine Abhängigkeiten)

```
## KONTEXT
- Projekt: AI Industry Value Estimator
- Lies CLAUDE.md für Architektur-Überblick
- Betroffene Dateien: config/industries/ai.yaml, scripts/run_ensemble_pipeline.py, src/inference/forecast.py
- Aktueller Zustand: Pipeline produziert einen einzigen Forecast-Satz mit fixen CAGR-Floors (hw 15%, infra 25%, sw 20%, adopt 15%). Kein Szenario-Support.

## AUFGABE
1. In ai.yaml einen neuen Block `scenarios` definieren:
   - conservative: CAGR-Floors wie aktuell (1.0×)
   - base: CAGR-Floors × 1.3
   - aggressive: CAGR-Floors × 1.8
2. In run_ensemble_pipeline.py eine Schleife über die drei Szenarien. Für jedes Szenario: CAGR-Floors temporär überschreiben, Pipeline durchlaufen, Ergebnisse mit scenario-Spalte taggen.
3. Alle drei Ergebnisse in forecasts_scenarios.parquet zusammenführen.
4. forecasts_ensemble.parquet weiterhin NUR das base-Szenario enthalten (Backwards-Kompatibilität).

## CONSTRAINTS
- Ändere NUR die oben genannten Dateien
- Die bestehende Pipeline-Logik wird NICHT verändert, nur die Floor-Parameter werden pro Szenario gesetzt
- Laufzeit: Wenn >3min für alle 3 Szenarien, parallelisiere mit concurrent.futures
- Wenn du unsicher bist, FRAGE statt zu raten

## VERIFIKATION
Führe nach ALLEN Änderungen diesen Code aus und zeige das VOLLSTÄNDIGE Ergebnis:

python3 -c "
import pandas as pd
sc = pd.read_parquet('data/processed/forecasts_scenarios.parquet')
print(f'VERIFY: Shape = {sc.shape} (expect 672 = 224 × 3)')
print(f'VERIFY: Scenarios = {sorted(sc.scenario.unique())} (expect [aggressive, base, conservative])')
for scenario in ['conservative', 'base', 'aggressive']:
    s = sc[(sc.scenario==scenario) & (sc.quarter==4)]
    for seg in sorted(s.segment.unique()):
        ss = s[s.segment==seg]
        v26 = ss[ss.year==2026].point_estimate_nominal.iloc[0]
        v30 = ss[ss.year==2030].point_estimate_nominal.iloc[0]
        cagr = (v30/v26)**(1/4) - 1
        print(f'VERIFY: {scenario}/{seg} CAGR={cagr:.1%} 2026={v26:.1f}B→2030={v30:.1f}B')

# Backwards-Compat
ens = pd.read_parquet('data/processed/forecasts_ensemble.parquet')
print(f'VERIFY: forecasts_ensemble.parquet unchanged shape = {ens.shape} (expect 224)')
"

python3 -m pytest tests/test_pipeline_wiring.py tests/test_backtesting.py -q --tb=short

Wenn IRGENDEINE Verifikation fehlschlägt, STOPPE und erkläre warum.
```

### v2-AP3: Dispersion-Visualisierung im Frontend (nach v2-AP1)

```
## KONTEXT
- Projekt: AI Industry Value Estimator, Frontend in frontend/
- Stack: Next.js 15 + React 19 + TypeScript + TailwindCSS
- API läuft auf localhost:8000 (FastAPI)
- Betroffene Dateien: frontend/src/components/charts/DispersionChart.tsx (NEU), frontend/src/app/segments/[segment]/page.tsx, api/routers/forecasts.py
- Abhängig von: analyst_dispersion.parquet (v2-AP1 muss abgeschlossen sein)
- Aktueller Zustand: Segment-Detailseiten zeigen Forecast-Charts. Keine Analyst-Dispersion sichtbar.

## AUFGABE
1. Neuen API-Endpoint: GET /api/v1/dispersion?segment=ai_hardware → liefert JSON-Array mit {year, iqr, std, min, max, median, n_sources, dispersion_ratio} pro Jahr.
2. In api/routers/forecasts.py: Endpoint implementieren, der analyst_dispersion.parquet + market_anchors_ai.parquet (für Median) joined und als JSON serviert.
3. Neue React-Komponente DispersionChart.tsx: Area-Chart (recharts) mit Median-Linie, IQR als halbtransparente Fläche, Min/Max als gestrichelte Grenzen. X-Achse: Jahre, Y-Achse: $B.
4. DispersionChart in die Segment-Detailseite integrieren, unterhalb des Forecast-Charts.

## CONSTRAINTS
- Bloomberg-Style: bg-slate-900, text-slate-100, orange-500 Akzente
- Nutze recharts (bereits installiert), NICHT lightweight-charts für diesen Chart-Typ
- Zahlen als $XXB formatieren
- Loading States und Error Handling sind Pflicht
- Wenn n_sources < 3 für ein Jahr: graue Fläche + "Insufficient data" Label

## VERIFIKATION
1. curl http://localhost:8000/api/v1/dispersion?segment=ai_hardware | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'VERIFY: Rows = {len(data)} (expect ~9 = years 2017-2025)')
print(f'VERIFY: Keys = {list(data[0].keys())}')
print(f'VERIFY: Has IQR = {\"iqr\" in data[0]}')
for d in data:
    print(f'  {d[\"year\"]}: median={d[\"median\"]:.1f}B, IQR={d[\"iqr\"]:.1f}B, n={d[\"n_sources\"]}')
"
2. cd frontend && npm run build  (muss ohne Error durchlaufen)
3. Beschreibe was der User auf /segments/ai_hardware sieht (Text-Mockup)

Wenn IRGENDEINE Verifikation fehlschlägt, STOPPE und erkläre warum.
```

### v2-AP4: Scenario-Switcher im Frontend (nach v2-AP2)

```
## KONTEXT
- Projekt: AI Industry Value Estimator, Frontend in frontend/
- Stack: Next.js 15 + React 19 + TypeScript + TailwindCSS
- API läuft auf localhost:8000 (FastAPI)
- Betroffene Dateien: frontend/src/components/ScenarioSelector.tsx (NEU), frontend/src/app/segments/[segment]/page.tsx, api/routers/forecasts.py
- Abhängig von: forecasts_scenarios.parquet (v2-AP2 muss abgeschlossen sein)
- Aktueller Zustand: Forecast-Seiten zeigen nur einen einzigen Forecast-Satz (base). Kein Szenario-Support.

## AUFGABE
1. API-Endpoint erweitern: GET /api/v1/forecasts?segment=ai_hardware&scenario=all → liefert alle drei Szenarien als JSON mit scenario-Feld.
2. Neue React-Komponente ScenarioSelector.tsx: Drei Toggle-Buttons (Conservative / Base / Aggressive) mit Bloomberg-Style Pill-Design. Active State: orange-500, Inactive: slate-700.
3. Auf der Segment-Detailseite: Beim Page-Load ALLE drei Szenarien fetchen (ein API-Call mit scenario=all). State-Management mit useState: aktives Szenario bestimmt welche Daten der Forecast-Chart + Tabelle zeigen.
4. Key-Metriken (CAGR, 2030 Estimate) unterhalb des Selectors aktualisieren sich reaktiv beim Switch.

## CONSTRAINTS
- Bloomberg-Style: bg-slate-900, text-slate-100, orange-500 Akzente
- KEIN Re-Fetch beim Szenario-Wechsel — alle Daten clientseitig vorgeladen
- Keine neuen NPM-Packages
- Default-Selection: "Base" (aktives Szenario beim Page-Load)
- Transition: Zahlen-Wechsel ohne Flackern (kein Loading-State beim Switch)

## VERIFIKATION
1. curl "http://localhost:8000/api/v1/forecasts?segment=ai_hardware&scenario=all" | python3 -c "
import json, sys
data = json.load(sys.stdin)
scenarios = set(d['scenario'] for d in data)
print(f'VERIFY: Scenarios = {sorted(scenarios)} (expect [aggressive, base, conservative])')
print(f'VERIFY: Total rows = {len(data)} (expect ~168 = 56 per scenario × 3)')
for sc in ['conservative', 'base', 'aggressive']:
    sc_data = [d for d in data if d['scenario']==sc and d.get('quarter')==4 and d.get('year')==2030]
    if sc_data:
        print(f'VERIFY: {sc} 2030 Q4 = {sc_data[0][\"point_estimate_nominal\"]:.1f}B')
"
2. cd frontend && npm run build  (muss ohne Error durchlaufen)
3. Beschreibe die User-Interaktion: Was passiert wenn man auf "Aggressive" klickt? Welche Zahlen ändern sich?

Wenn IRGENDEINE Verifikation fehlschlägt, STOPPE und erkläre warum.
```

### v2-AP5: Automated Insight Narratives (nach v2-AP1 + v2-AP2)

```
## KONTEXT
- Projekt: AI Industry Value Estimator
- Lies CLAUDE.md für Architektur-Überblick
- Betroffene Dateien: src/narratives/insight_generator.py (NEU), tests/test_insights.py (NEU)
- Abhängig von: analyst_dispersion.parquet (v2-AP1) und forecasts_scenarios.parquet (v2-AP2)
- Aktueller Zustand: Keine narrativen Outputs. Nur Zahlen.

## AUFGABE
1. Erstelle src/narratives/__init__.py und src/narratives/insight_generator.py
2. Funktion generate_segment_insights(segment: str) -> list[str] die 3-5 Insight-Strings generiert:
   - CAGR-Insight: "ai_hardware grows at X% CAGR (2026-2030), driven by [driver]"
   - Dispersion-Insight: "Analyst dispersion for ai_software has [decreased/increased] by X% since 2022, indicating [converging/diverging] market views"
   - Scenario-Spread: "In the aggressive scenario, ai_infrastructure reaches $XB by 2030 — Y% above the conservative case"
   - Top-Analyst: "The most bullish source for [segment] is [Name] at $XB — Z% above consensus"
   - Regime-Insight (nur ai_infrastructure): "Post-GenAI growth (since 2022) shows a structural break: MAPE drops from X% to Y%"
3. Template-basiert mit Conditional Logic (min 5 verschiedene Formulierungen pro Template).
4. Tests: Jeder Segment-Aufruf liefert 3-5 Strings, kein String enthält "NaN" oder "None".

## CONSTRAINTS
- Reine Python-Logik, KEIN LLM-Aufruf
- Texte auf Englisch (institutionelles Publikum)
- Zahlen formatiert: $XXB, XX.X%, Ø statt "average"
- Wenn du unsicher bist, FRAGE statt zu raten

## VERIFIKATION
Führe nach ALLEN Änderungen diesen Code aus und zeige das VOLLSTÄNDIGE Ergebnis:

python3 -c "
from src.narratives.insight_generator import generate_segment_insights
for seg in ['ai_hardware', 'ai_infrastructure', 'ai_software', 'ai_adoption']:
    insights = generate_segment_insights(seg)
    print(f'=== {seg} ===')
    print(f'VERIFY: n_insights = {len(insights)} (expect 3-5)')
    for i, ins in enumerate(insights):
        print(f'  [{i}] {ins}')
        assert 'NaN' not in ins, f'NaN found in insight!'
        assert 'None' not in ins, f'None found in insight!'
    print()
"

python3 -m pytest tests/test_insights.py -q --tb=short

Wenn IRGENDEINE Verifikation fehlschlägt, STOPPE und erkläre warum.
```

### v2-AP6a: Bottom-Up Validation — Backend-Erweiterung (keine Abhängigkeiten)

```
## KONTEXT
- Projekt: AI Industry Value Estimator
- Lies CLAUDE.md für Architektur-Überblick
- Betroffene Dateien: src/ingestion/edgar_capex.py, src/narratives/insight_generator.py, tests/test_bottom_up.py (NEU)
- Aktueller Zustand: edgar_capex.py existiert bereits mit compile_bottom_up_validation(). bottom_up_validation.parquet hat 4 Rows (nur 2024, ein Segment pro Zeile). revenue_attribution_ai.parquet hat 15 Companies mit ai_revenue_usd_billions, segment, year. Die Daten sind da, aber nur für ein Jahr und ohne Narrativ-Integration.

## AUFGABE
1. In edgar_capex.py die Funktion compile_bottom_up_validation() erweitern:
   - Statt nur 2024: alle verfügbaren Jahre aus revenue_attribution_ai.parquet einbeziehen (erwarte 2022-2024)
   - Pro Zeile zusätzlich: top_3_companies (Namen + Beträge der Top-3-Beiträger), coverage_trend (Veränderung der coverage_ratio vs. Vorjahr, NaN für erstes Jahr)
   - Output: bottom_up_validation.parquet mit ~12 Rows (4 Segmente × 3 Jahre)

2. In insight_generator.py eine neue Insight-Funktion _bottom_up_insight(segment) hinzufügen:
   - Lädt bottom_up_validation.parquet
   - Generiert Insight: "ai_hardware top-down estimate of $XB is Y% verifiable through public disclosures (Z companies: [top 3]). Coverage has [improved/declined] from A% to B% since 2022."
   - Wenn coverage_ratio > 0.8: "high confidence — bottom-up validates top-down"
   - Wenn coverage_ratio < 0.5: "significant gap — $XB likely from private companies and long-tail vendors"
   - In generate_segment_insights() als 6. Insight-Typ einbauen

3. Test schreiben: test_bottom_up.py prüft:
   - bottom_up_validation.parquet Shape (expect >= 8 rows, 4 segments × min 2 years)
   - coverage_ratio zwischen 0.0 und 1.5 (>1.0 ist möglich wenn Bottom-Up > Top-Down)
   - Kein NaN in coverage_ratio oder bottom_up_sum
   - Insight-Generator liefert bottom_up Insight für mindestens ai_hardware

## CONSTRAINTS
- Ändere NUR die oben genannten Dateien
- Nutze nur pandas/numpy (keine neuen Dependencies)
- Die bestehende compile_bottom_up_validation() Logik erweitern, nicht ersetzen
- revenue_attribution_ai.parquet ist die Datenquelle — NICHT edgar_ai_raw.parquet (das hat nur Total Company Revenue, nicht AI-spezifisch)
- Wenn du unsicher bist über die attribution-Daten, FRAGE statt zu raten

## VERIFIKATION
Führe nach ALLEN Änderungen diesen Code aus und zeige das VOLLSTÄNDIGE Ergebnis:

python3 -c "
import pandas as pd

# 1. Bottom-Up Validation
buv = pd.read_parquet('data/processed/bottom_up_validation.parquet')
print(f'VERIFY: Shape = {buv.shape} (expect >= 8 rows)')
print(f'VERIFY: Segments = {sorted(buv.segment.unique())} (expect 4)')
print(f'VERIFY: Years = {sorted(buv.year.unique())} (expect 2-3 years)')
print(f'VERIFY: NaN in coverage_ratio = {buv.coverage_ratio.isna().sum()} (expect 0)')
print(f'VERIFY: coverage_ratio range = [{buv.coverage_ratio.min():.2f}, {buv.coverage_ratio.max():.2f}]')
print()
for _, row in buv.sort_values(['segment','year']).iterrows():
    print(f'{row.segment} {row.year}: bottom_up={row.bottom_up_sum:.1f}B, top_down={row.top_down_estimate:.1f}B, coverage={row.coverage_ratio:.1%}, n={row.n_companies}')
print()

# 2. Insight Integration
from src.narratives.insight_generator import generate_segment_insights
hw_insights = generate_segment_insights('ai_hardware')
bu_insights = [i for i in hw_insights if 'verifiable' in i.get('text','').lower() or 'bottom' in i.get('text','').lower() or 'coverage' in i.get('text','').lower()]
print(f'VERIFY: Bottom-up insights for ai_hardware = {len(bu_insights)} (expect >= 1)')
for ins in bu_insights:
    print(f'  → {ins}')
"

python3 -m pytest tests/test_bottom_up.py -q --tb=short

Wenn IRGENDEINE Verifikation fehlschlägt, STOPPE und erkläre warum.
```

### v2-AP6b: Bottom-Up Validation — Frontend (nach v2-AP6a)

```
## KONTEXT
- Projekt: AI Industry Value Estimator, Frontend in frontend/
- Stack: Next.js 15 + React 19 + TypeScript + TailwindCSS
- API läuft auf localhost:8000 (FastAPI)
- Betroffene Dateien: api/routers/forecasts.py, frontend/src/components/charts/BottomUpChart.tsx (NEU), frontend/src/app/segments/[segment]/page.tsx
- Abhängig von: bottom_up_validation.parquet (v2-AP6a muss abgeschlossen sein)
- Aktueller Zustand: Bottom-Up-Daten existieren in Parquet, aber kein API-Endpoint und keine Visualisierung.

## AUFGABE
1. Neuen API-Endpoint: GET /api/v1/bottom-up?segment=ai_hardware → liefert JSON-Array mit {year, bottom_up_sum, top_down_estimate, coverage_ratio, gap_usd_billions, n_companies, top_3_companies} pro Jahr.
2. Neue React-Komponente BottomUpChart.tsx: Gestapeltes Balkendiagramm (recharts BarChart):
   - Pro Jahr ein Bar mit zwei Segmenten: "Verified (Bottom-Up)" in orange-500, "Unverified Gap" in slate-600
   - Gesamthöhe = Top-Down-Estimate, orangener Teil = Bottom-Up-Sum
   - Coverage-Ratio als Prozent-Label über jedem Bar
   - Tooltip mit Company-Breakdown (Top 3 Contributors)
3. BottomUpChart in Segment-Detailseite integrieren, unterhalb der Dispersion-Visualisierung.

## CONSTRAINTS
- Bloomberg-Style: bg-slate-900, text-slate-100, orange-500 / slate-600 für Bars
- Nutze recharts BarChart (bereits installiert)
- Wenn nur 1 Jahr Daten vorhanden: einzelnen Bar anzeigen, kein leeres Chart
- Loading State und "No bottom-up data available" Fallback sind Pflicht

## VERIFIKATION
1. curl http://localhost:8000/api/v1/bottom-up?segment=ai_hardware | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'VERIFY: Rows = {len(data)} (expect 2-3 years)')
print(f'VERIFY: Keys = {list(data[0].keys())}')
for d in data:
    print(f'  {d[\"year\"]}: BU={d[\"bottom_up_sum\"]:.1f}B, TD={d[\"top_down_estimate\"]:.1f}B, coverage={d[\"coverage_ratio\"]:.1%}')
"
2. cd frontend && npm run build  (muss ohne Error durchlaufen)
3. Beschreibe was der User auf /segments/ai_hardware sieht (Text-Mockup des Stacked Bar Charts)

Wenn IRGENDEINE Verifikation fehlschlägt, STOPPE und erkläre warum.
```

---

## Phase 3 Prompts: Frontend Bloomberg-Grade + Portfolio

Reihenfolge: v3-AP1 + v3-AP3 + v3-AP4 parallel → v3-AP5 + v3-AP7 parallel → v3-AP6 → v3-AP2.

### v3-AP1: README Rewrite + Architecture Diagram (keine Abhängigkeiten)

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

### v3-AP3: Chart Professionalisierung (keine Abhängigkeiten)

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

### v3-AP4: Diagnostics Page (keine Abhängigkeiten)

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

### v3-AP7: Excel/CSV Export (keine Abhängigkeiten)

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
