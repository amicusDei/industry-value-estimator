"""
Drivers tab layout builder.

Shows SHAP feature attribution PNG image with explanatory text.
"""
from __future__ import annotations

from dash import html

from src.dashboard.charts.styles import COLOR_DEEP_BLUE, ATTRIBUTION_STYLE

_CARD_STYLE = {
    "backgroundColor": "#FFFFFF",
    "borderRadius": "8px",
    "padding": "24px",
    "marginBottom": "24px",
    "boxShadow": "0 1px 4px rgba(0,0,0,0.08)",
    "border": "1px solid #E8EBF0",
}

_SECTION_HEADING_STYLE = {
    "fontSize": "20px",
    "fontWeight": 600,
    "color": "#1A1A2E",
    "marginBottom": "4px",
    "marginTop": "0",
}

_SECTION_SUBTITLE_STYLE = {
    "fontSize": "14px",
    "color": "#666",
    "marginBottom": "16px",
    "marginTop": "0",
    "lineHeight": "1.5",
}

_BODY_STYLE = {
    "fontSize": "16px",
    "color": "#333",
    "lineHeight": "1.6",
    "marginBottom": "12px",
    "marginTop": "0",
}


def build_drivers_layout(segment: str, usd_col: str) -> html.Div:
    """
    Build the Drivers tab layout.

    Parameters
    ----------
    segment : str
        Segment ID or "all" (not used \u2014 SHAP plot is global).
    usd_col : str
        USD column toggle (not used \u2014 SHAP plot is static).

    Returns
    -------
    html.Div
        Dash component tree for the Drivers tab.
    """
    intro_card = html.Div([
        html.H2("SHAP Driver Attribution", style=_SECTION_HEADING_STYLE),
        html.P(
            "This chart shows which input variables have the greatest influence on the forecast models, "
            "ranked by their average SHAP (SHapley Additive exPlanations) value across all segments and "
            "time periods. SHAP values decompose each model\u2019s prediction into individual feature "
            "contributions \u2014 a positive SHAP value pushes the forecast higher, a negative value "
            "pushes it lower. The x-axis shows the magnitude of average impact; the color shows "
            "the direction (red = high feature value increases the forecast, blue = high feature "
            "value decreases it).",
            style=_SECTION_SUBTITLE_STYLE,
        ),
        html.P(
            "R\u0026D spend, patent filings, and VC investment are the primary positive drivers. "
            "These three variables collectively explain the majority of the model\u2019s variance, "
            "reflecting that AI market growth is fundamentally driven by innovation investment and "
            "the commercialization of that investment. High-tech exports and researcher density "
            "provide secondary signals, particularly for hardware and infrastructure segments where "
            "traded goods are measurable.",
            style=_BODY_STYLE,
        ),
    ], style=_CARD_STYLE)

    shap_card = html.Div([
        html.H3(
            "Feature Importance \u2014 All Segments",
            style={
                "fontSize": "16px",
                "fontWeight": 600,
                "color": "#1A1A2E",
                "marginBottom": "12px",
                "marginTop": "0",
            },
        ),
        html.Img(
            src="/assets/shap_summary.png",
            style={
                "maxWidth": "100%",
                "height": "auto",
                "display": "block",
                "borderRadius": "4px",
            },
        ),
        html.P(
            "Sources: World Bank Open Data, OECD.Stat, LSEG Workspace",
            style=ATTRIBUTION_STYLE,
        ),
    ], style=_CARD_STYLE)

    methodology_card = html.Div([
        html.H3(
            "How SHAP Attribution Works",
            style={
                "fontSize": "16px",
                "fontWeight": 600,
                "color": "#1A1A2E",
                "marginBottom": "8px",
                "marginTop": "0",
            },
        ),
        html.P(
            "SHAP values are rooted in cooperative game theory (Shapley 1953). For each prediction, "
            "SHAP computes every possible ordering of features and measures each feature\u2019s marginal "
            "contribution when added to a coalition. The average of these marginal contributions across "
            "all orderings is the SHAP value for that feature \u2014 guaranteed to be consistent and "
            "locally accurate (the sum of all SHAP values equals the model output minus the expected output).",
            style={"fontSize": "14px", "color": "#555", "lineHeight": "1.6", "marginBottom": "8px"},
        ),
        html.P(
            "This plot shows beeswarm SHAP values from the Phase 3 ML correction layer, applied on top "
            "of the Phase 2 statistical baseline. Each dot represents one observation (segment-year pair); "
            "the horizontal position shows the SHAP value for that observation; the color shows whether "
            "the raw feature value was high (red) or low (blue) for that observation.",
            style={"fontSize": "14px", "color": "#555", "lineHeight": "1.6", "marginBottom": "0"},
        ),
    ], style={
        **_CARD_STYLE,
        "marginBottom": "0",
        "borderTop": "3px solid #F4F6FA",
    })

    return html.Div([intro_card, shap_card, methodology_card], style={"paddingTop": "8px"})
