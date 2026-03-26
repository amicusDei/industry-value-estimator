"""
Tabs subpackage — layout builders for each dashboard tab.

Modules:
    overview: Dollar headlines, fan chart, segment breakdown, narrative insights
    segments: 2x2 per-segment fan chart grid (or single segment full-width)
    drivers: SHAP feature attribution plot with methodology explanation
    diagnostics: Model scorecard (RMSE/MAPE/R^2), metric glossary, backtest chart

All tab builders are pure functions: (segment, usd_col, mode) -> html.Div.
Normal mode shows USD estimates with plain-language narrative.
Expert mode shows real USD market size values, model methodology, and ASSUMPTIONS.md refs.
"""
