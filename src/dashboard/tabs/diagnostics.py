"""
Diagnostics tab layout builder.

Shows model diagnostics scorecard table and backtest residuals chart.
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.dashboard.app import DIAGNOSTICS, RESIDUALS_DF, SEGMENTS, SEGMENT_DISPLAY
from src.dashboard.charts.backtest import make_backtest_chart
from src.dashboard.charts.styles import COLOR_DEEP_BLUE, ATTRIBUTION_STYLE

_TABLE_CELL_STYLE = {
    "padding": "8px",
    "border": "1px solid #E8EBF0",
    "textAlign": "left",
}

_TABLE_HEADER_STYLE = {
    "padding": "8px",
    "border": "1px solid #E8EBF0",
    "backgroundColor": "#F4F6FA",
    "fontWeight": 600,
    "textAlign": "left",
}


def build_diagnostics_layout(segment: str, usd_col: str) -> html.Div:
    """
    Build the Diagnostics tab layout.

    Parameters
    ----------
    segment : str
        Segment ID or "all" to show diagnostics for all segments.
    usd_col : str
        USD column toggle (not used for diagnostics display).

    Returns
    -------
    html.Div
        Dash component tree for the Diagnostics tab.
    """
    # --- Scorecard table ---
    if segment == "all":
        display_segments = SEGMENTS
    else:
        display_segments = [segment]

    header_cells = [html.Th("Metric", style=_TABLE_HEADER_STYLE)] + [
        html.Th(SEGMENT_DISPLAY.get(s, s), style=_TABLE_HEADER_STYLE)
        for s in display_segments
    ]

    def _fmt(val) -> str:
        if isinstance(val, float):
            return f"{val:.4f}"
        return str(val)

    metric_rows = []
    for metric_key, metric_label in [("rmse", "RMSE"), ("mape", "MAPE"), ("r2", "R\u00b2")]:
        cells = [html.Td(metric_label, style=_TABLE_CELL_STYLE)]
        for seg in display_segments:
            diag = DIAGNOSTICS.get(seg, {})
            cells.append(html.Td(_fmt(diag.get(metric_key, "N/A")), style=_TABLE_CELL_STYLE))
        metric_rows.append(html.Tr(cells))

    scorecard_table = html.Table(
        [html.Thead(html.Tr(header_cells)), html.Tbody(metric_rows)],
        style={"width": "100%", "borderCollapse": "collapse"},
    )

    scorecard_section = html.Div([
        html.H3("Model Diagnostics", style={"fontSize": "20px", "fontWeight": 600}),
        html.P(
            "Out-of-sample fit metrics across all four AI segments. "
            "Lower RMSE/MAPE is better. Higher R\u00b2 is better.",
            style={"color": "#555", "fontSize": "14px"},
        ),
        scorecard_table,
        html.P(
            "Sources: World Bank Open Data, OECD.Stat, LSEG Workspace "
            "\u00b7 Residuals from statistical baseline model",
            style=ATTRIBUTION_STYLE,
        ),
    ], style={"marginBottom": "32px"})

    # --- Backtest chart ---
    backtest_fig = make_backtest_chart(RESIDUALS_DF, segment)
    backtest_section = html.Div([
        html.H3(
            "Backtesting \u2014 Residual Analysis",
            style={"fontSize": "20px", "fontWeight": 600, "marginTop": "24px"},
        ),
        html.P(
            "Expanding-window temporal cross-validation. Each origin shows the model's "
            "out-of-sample prediction at that point in time.",
            style={"color": "#555", "fontSize": "14px"},
        ),
        dcc.Loading(
            type="circle",
            color=COLOR_DEEP_BLUE,
            children=dcc.Graph(
                figure=backtest_fig,
                id="diagnostics-backtest-chart",
                config={"displayModeBar": True},
            ),
        ),
        html.P(
            "Sources: World Bank Open Data, OECD.Stat, LSEG Workspace "
            "\u00b7 Backtesting via expanding-window temporal cross-validation",
            style=ATTRIBUTION_STYLE,
        ),
    ])

    return html.Div([scorecard_section, backtest_section])
