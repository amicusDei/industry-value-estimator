"""
Charts subpackage — Plotly figure builders for the dashboard.

Modules:
    fan_chart: Fan chart with historical line, forecast dashed line, 80%/95% CI bands
    backtest: Residuals-by-year bar chart for model diagnostics display
    styles: Color tokens, typography constants, and reusable style dicts

All chart builders return go.Figure objects and are called from tab layout builders.
USD mode vs. raw index mode is controlled by the usd_mode parameter in make_fan_chart.
"""
