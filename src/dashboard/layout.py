"""
Top-level dashboard layout.

Provides create_layout() which assembles the header bar (with global segment
dropdown and USD toggle), 4-tab navigation, tab content area, and footer.
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.dashboard.app import SEGMENTS, SEGMENT_DISPLAY
from src.dashboard.charts.styles import COLOR_DEEP_BLUE, COLOR_BG_SECONDARY


def create_layout() -> html.Div:
    """
    Build and return the full dashboard layout.

    The global controls (segment-dropdown, usd-toggle) live OUTSIDE tab-content
    so they persist across tab switches and never reset.

    Returns
    -------
    html.Div
        Root Dash component tree for the dashboard.
    """
    return html.Div([
        # HEADER BAR
        html.Div([
            html.Div([
                html.Span(
                    "AI Industry Value Estimator",
                    style={"fontSize": "20px", "fontWeight": 600},
                ),
            ], style={"display": "inline-block"}),
            html.Div([
                # Global segment dropdown
                html.Label("Segment:", style={"marginRight": "8px", "fontSize": "14px"}),
                dcc.Dropdown(
                    id="segment-dropdown",
                    options=[{"label": "All Segments", "value": "all"}] + [
                        {"label": SEGMENT_DISPLAY[s], "value": s} for s in SEGMENTS
                    ],
                    value="all",
                    clearable=False,
                    style={"width": "300px", "display": "inline-block", "verticalAlign": "middle"},
                ),
                # USD toggle
                html.Span(style={"width": "24px", "display": "inline-block"}),
                dcc.RadioItems(
                    id="usd-toggle",
                    options=[
                        {"label": "Real 2020 USD", "value": "point_estimate_real_2020"},
                        {"label": "Nominal USD", "value": "point_estimate_nominal"},
                    ],
                    value="point_estimate_real_2020",
                    inline=True,
                    style={"display": "inline-block", "fontSize": "14px"},
                ),
            ], style={"display": "inline-block", "float": "right"}),
        ], style={
            "padding": "16px",
            "backgroundColor": "#FFFFFF",
            "borderBottom": "1px solid #E8EBF0",
            "overflow": "hidden",
        }),

        # TABS
        dcc.Tabs(
            id="main-tabs",
            value="overview",
            children=[
                dcc.Tab(label="Overview", value="overview"),
                dcc.Tab(label="Segments", value="segments"),
                dcc.Tab(label="Drivers", value="drivers"),
                dcc.Tab(label="Diagnostics", value="diagnostics"),
            ],
        ),

        # TAB CONTENT
        html.Div(
            id="tab-content",
            style={
                "backgroundColor": COLOR_BG_SECONDARY,
                "padding": "24px",
                "minHeight": "600px",
            },
        ),

        # FOOTER
        html.Div(
            "AI Industry Value Estimator \u00b7 Data: World Bank, OECD, LSEG Workspace "
            "\u00b7 Forecasts to 2030 with calibrated confidence intervals",
            style={
                "textAlign": "center",
                "fontSize": "12px",
                "color": "#888888",
                "padding": "16px",
                "backgroundColor": "#FFFFFF",
                "borderTop": "1px solid #E8EBF0",
            },
        ),
    ])
