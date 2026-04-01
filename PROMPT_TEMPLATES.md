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

---

## Beispiel: Konkreter Prompt für FE-01 (Charts reparieren)

```
## KONTEXT
- Projekt: AI Industry Value Estimator
- Betroffene Dateien: frontend/src/components/charts/TimeseriesChart.tsx
- API: GET /api/v1/forecasts?segment=ai_hardware&valuation=nominal
- Aktueller Zustand: Chart zeigt Linien, aber CI-Bänder sind kaum sichtbar,
  Achsenbeschriftung fehlt, keine Legende, Tooltip zeigt keine Werte

## AUFGABE
1. CI-Bänder als halbtransparente Flächen (AreaSeries) statt dashed Lines
2. Y-Achse: "$0B" bis auto-scaled Maximum, Ticks alle $50B
3. X-Achse: Quarterly labels "Q1'17", "Q2'17" etc.
4. Tooltip: Segment-Name, Datum, Point Estimate, CI80 Range, CI95 Range
5. Legende: "Historical" (grau), "Forecast" (orange), "CI80" (hell-orange), "CI95" (sehr hell-orange)

## CONSTRAINTS
- Nutze lightweight-charts v4 API (bereits installiert)
- Farben: Historical #64748b, Forecast #f97316, CI80 rgba(249,115,22,0.3), CI95 rgba(249,115,22,0.1)
- Keine neuen Dependencies

## VERIFIKATION
1. cd frontend && npm run build
2. curl http://localhost:8000/api/v1/forecasts?segment=ai_hardware&valuation=nominal | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'VERIFY: Rows = {len(data)}')
print(f'VERIFY: First row keys = {list(data[0].keys()) if data else \"EMPTY\"}')
print(f'VERIFY: Has CI columns = {\"ci80_lower_nominal\" in data[0] if data else False}')
"
3. Beschreibe was der User auf /segments/ai_hardware sieht
```
