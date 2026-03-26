"""
Top-level dashboard layout.

Provides create_layout() which assembles the header bar (with global segment
dropdown and USD toggle), 4-tab navigation, tab content area, and footer.
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.dashboard.app import SEGMENTS, SEGMENT_DISPLAY, FORECASTS_DF
from src.dashboard.charts.styles import (
    COLOR_DEEP_BLUE,
    COLOR_BG_PRIMARY,
    COLOR_BG_SECONDARY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_TERTIARY,
    COLOR_AXES,
)


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
    # Data freshness banner
    _stale_banner = html.Div()  # empty by default
    import os, time
    from config.settings import DATA_PROCESSED
    _forecast_path = DATA_PROCESSED / "forecasts_ensemble.parquet"
    if _forecast_path.exists():
        _age_days = (time.time() - os.path.getmtime(str(_forecast_path))) / 86400
        if _age_days > 30:
            _stale_banner = html.Div(
                f"\u26a0 Data last refreshed {int(_age_days)} days ago \u2014 run pipeline to update",
                style={"backgroundColor": "#FEF3CD", "color": "#856404", "padding": "8px 24px",
                       "fontSize": "13px", "fontWeight": 600, "borderBottom": "1px solid #F39C12"}
            )

    # Data vintage display
    _vintage = FORECASTS_DF["data_vintage"].iloc[0] if "data_vintage" in FORECASTS_DF.columns else "unknown"

    return html.Div([
        _stale_banner,
        # HEADER BAR
        html.Div([
            html.Div([
                html.Span(
                    "AI Industry Value Estimator",
                    style={
                        "fontSize": "20px",
                        "fontWeight": 600,
                        "color": COLOR_TEXT_PRIMARY,
                        "letterSpacing": "-0.3px",
                    },
                ),
                html.Span(
                    "Statistical baseline forecast \u00b7 2010\u20132030",
                    style={
                        "fontSize": "12px",
                        "color": COLOR_TEXT_TERTIARY,
                        "marginLeft": "12px",
                        "fontWeight": 400,
                    },
                ),
                html.Span(
                    f"Data: {_vintage}",
                    style={"fontSize": "12px", "color": COLOR_TEXT_TERTIARY, "marginLeft": "16px"},
                ),
            ], style={"display": "flex", "alignItems": "center"}),
            html.Div([
                # Global segment dropdown — uses dbc.ButtonGroup for full visibility
                html.Label(
                    "Segment:",
                    style={
                        "marginRight": "8px", "fontSize": "13px", "color": COLOR_TEXT_SECONDARY,
                        "fontWeight": 400, "whiteSpace": "nowrap",
                    },
                ),
                html.Div(
                    dcc.Dropdown(
                        id="segment-dropdown",
                        options=[{"label": "All Segments", "value": "all"}] + [
                            {"label": SEGMENT_DISPLAY[s], "value": s} for s in SEGMENTS
                        ],
                        value="all",
                        clearable=False,
                        style={"width": "240px"},
                    ),
                    style={"position": "relative", "zIndex": 2000},
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
                    style={"display": "inline-flex", "alignItems": "center", "fontSize": "13px"},
                    inputStyle={"marginRight": "4px"},
                    labelStyle={"marginRight": "16px"},
                ),
                # Normal / Expert mode toggle
                html.Span(style={"width": "20px", "display": "inline-block"}),
                html.Div([
                    html.Span(
                        "Mode:",
                        style={"marginRight": "8px", "fontSize": "13px", "color": COLOR_TEXT_SECONDARY, "fontWeight": 400},
                    ),
                    dcc.RadioItems(
                        id="mode-toggle",
                        options=[
                            {"label": "Normal", "value": "normal"},
                            {"label": "Expert", "value": "expert"},
                        ],
                        value="normal",
                        inline=True,
                        style={"display": "inline-flex", "alignItems": "center", "fontSize": "13px"},
                        inputStyle={"marginRight": "4px"},
                        labelStyle={"marginRight": "16px"},
                    ),
                ], style={
                    "display": "inline-flex",
                    "alignItems": "center",
                    "padding": "4px 10px",
                    "border": "1px solid #D0D5E0",
                    "borderRadius": "6px",
                    "backgroundColor": "#F8F9FC",
                }),
            ], style={"display": "flex", "alignItems": "center"}),
        ], style={
            "padding": "14px 24px",
            "backgroundColor": COLOR_BG_PRIMARY,
            "borderBottom": f"2px solid {COLOR_AXES}",
            "overflow": "visible",
            "position": "relative",
            "zIndex": 1000,
            # Use flexbox instead of float for reliable cross-browser layout
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "space-between",
        }),

        # TABS
        dcc.Tabs(
            id="main-tabs",
            value="basic",
            children=[
                dcc.Tab(
                    label="Basic",
                    value="basic",
                    style={"padding": "10px 20px", "fontSize": "14px"},
                    selected_style={"padding": "10px 20px", "fontSize": "14px", "fontWeight": 600, "borderTop": f"3px solid {COLOR_DEEP_BLUE}"},
                ),
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
                style={"fontWeight": 600, "color": COLOR_TEXT_SECONDARY},
            ),
            html.Span(
                " \u00b7 Data: World Bank, OECD, LSEG Workspace \u00b7 Forecasts to 2030 with calibrated confidence intervals",
                style={"color": COLOR_TEXT_TERTIARY},
            ),
        ], style={
            "textAlign": "center",
            "fontSize": "12px",
            "padding": "16px 24px",
            "backgroundColor": COLOR_BG_PRIMARY,
            "borderTop": f"1px solid {COLOR_AXES}",
        }),
    ])
