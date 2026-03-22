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
                    style={
                        "fontSize": "20px",
                        "fontWeight": 600,
                        "color": "#1A1A2E",
                        "letterSpacing": "-0.3px",
                    },
                ),
                html.Span(
                    "Statistical baseline forecast \u00b7 2010\u20132030",
                    style={
                        "fontSize": "12px",
                        "color": "#888",
                        "marginLeft": "12px",
                        "fontWeight": 400,
                    },
                ),
            ], style={"display": "inline-block", "verticalAlign": "middle"}),
            html.Div([
                # Global segment dropdown
                html.Label(
                    "Segment:",
                    style={"marginRight": "8px", "fontSize": "13px", "color": "#555", "fontWeight": 400},
                ),
                dcc.Dropdown(
                    id="segment-dropdown",
                    options=[{"label": "All Segments", "value": "all"}] + [
                        {"label": SEGMENT_DISPLAY[s], "value": s} for s in SEGMENTS
                    ],
                    value="all",
                    clearable=False,
                    style={"width": "240px", "display": "inline-block", "verticalAlign": "middle"},
                ),
                # USD toggle
                html.Span(style={"width": "20px", "display": "inline-block"}),
                dcc.RadioItems(
                    id="usd-toggle",
                    options=[
                        {"label": "Real 2020 USD", "value": "point_estimate_real_2020"},
                        {"label": "Nominal USD", "value": "point_estimate_nominal"},
                    ],
                    value="point_estimate_real_2020",
                    inline=True,
                    style={"display": "inline-block", "fontSize": "13px"},
                    inputStyle={"marginRight": "4px"},
                    labelStyle={"marginRight": "16px"},
                ),
            ], style={"display": "inline-block", "float": "right", "verticalAlign": "middle"}),
        ], style={
            "padding": "14px 24px",
            "backgroundColor": "#FFFFFF",
            "borderBottom": "2px solid #E8EBF0",
            "overflow": "hidden",
        }),

        # TABS
        dcc.Tabs(
            id="main-tabs",
            value="overview",
            children=[
                dcc.Tab(
                    label="Overview",
                    value="overview",
                    style={"padding": "10px 20px", "fontSize": "14px"},
                    selected_style={"padding": "10px 20px", "fontSize": "14px", "fontWeight": 600, "borderTop": f"3px solid {COLOR_DEEP_BLUE}"},
                ),
                dcc.Tab(
                    label="Segments",
                    value="segments",
                    style={"padding": "10px 20px", "fontSize": "14px"},
                    selected_style={"padding": "10px 20px", "fontSize": "14px", "fontWeight": 600, "borderTop": f"3px solid {COLOR_DEEP_BLUE}"},
                ),
                dcc.Tab(
                    label="Drivers",
                    value="drivers",
                    style={"padding": "10px 20px", "fontSize": "14px"},
                    selected_style={"padding": "10px 20px", "fontSize": "14px", "fontWeight": 600, "borderTop": f"3px solid {COLOR_DEEP_BLUE}"},
                ),
                dcc.Tab(
                    label="Diagnostics",
                    value="diagnostics",
                    style={"padding": "10px 20px", "fontSize": "14px"},
                    selected_style={"padding": "10px 20px", "fontSize": "14px", "fontWeight": 600, "borderTop": f"3px solid {COLOR_DEEP_BLUE}"},
                ),
            ],
        ),

        # TAB CONTENT
        html.Div(
            id="tab-content",
            style={
                "backgroundColor": COLOR_BG_SECONDARY,
                "padding": "24px 32px",
                "minHeight": "600px",
            },
        ),

        # FOOTER
        html.Div([
            html.Span(
                "AI Industry Value Estimator",
                style={"fontWeight": 600, "color": "#555"},
            ),
            html.Span(
                " \u00b7 Data: World Bank, OECD, LSEG Workspace \u00b7 Forecasts to 2030 with calibrated confidence intervals",
                style={"color": "#888"},
            ),
        ], style={
            "textAlign": "center",
            "fontSize": "12px",
            "padding": "16px 24px",
            "backgroundColor": "#FFFFFF",
            "borderTop": "1px solid #E8EBF0",
        }),
    ])
