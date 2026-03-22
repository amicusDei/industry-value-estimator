"""
Dashboard package — Dash-based interactive visualization of AI industry forecasts.

Modules:
    app: Dash app instance, data loading at startup, value chain multiplier calibration
    layout: Top-level page layout (header, tabs, footer) via create_layout()
    callbacks: Dash callback wiring for tab content rendering

Subpackages:
    charts: Plotly figure builders (fan chart, backtest residuals, style tokens)
    tabs: Tab content builders (overview, segments, drivers, diagnostics)

Design:
    Data is loaded once at import time in app.py (module-level) and shared via
    module globals (FORECASTS_DF, RESIDUALS_DF). Tab layouts are pure functions
    of (segment, usd_col, mode) — stateless, enabling uniform callback dispatch.
    Global controls (segment-dropdown, mode-toggle) live outside tab-content so
    they persist across tab switches without state reset.
"""
