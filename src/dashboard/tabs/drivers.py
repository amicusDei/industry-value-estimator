"""
Drivers tab layout builder.

Shows SHAP feature attribution PNG image with explanatory text.
"""
from __future__ import annotations

from dash import html

from src.dashboard.charts.styles import ATTRIBUTION_STYLE


def build_drivers_layout(segment: str, usd_col: str) -> html.Div:
    """
    Build the Drivers tab layout.

    Parameters
    ----------
    segment : str
        Segment ID or "all" (not used — SHAP plot is global).
    usd_col : str
        USD column toggle (not used — SHAP plot is static).

    Returns
    -------
    html.Div
        Dash component tree for the Drivers tab.
    """
    return html.Div([
        html.H3(
            "SHAP Driver Attribution",
            style={"fontSize": "20px", "fontWeight": 600},
        ),
        html.P(
            "Feature importance from SHAP analysis \u2014 shows which variables contribute most "
            "to the forecast. R&D spend, patent filings, and VC investment are the primary drivers.",
            style={"color": "#555", "fontSize": "16px"},
        ),
        html.Img(
            src="/assets/shap_summary.png",
            style={"maxWidth": "100%", "height": "auto"},
        ),
        html.P(
            "Sources: World Bank Open Data, OECD.Stat, LSEG Workspace",
            style=ATTRIBUTION_STYLE,
        ),
    ])
