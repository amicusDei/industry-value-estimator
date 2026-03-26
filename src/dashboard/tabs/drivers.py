"""
Drivers tab layout builder.

Shows SHAP feature attribution PNG image with explanatory text.
"""
from __future__ import annotations

from dash import html

from src.dashboard.app import FORECASTS_DF, SOURCE_ATTRIBUTION
from src.dashboard.charts.styles import (
    COLOR_DEEP_BLUE,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_AXES,
    ATTRIBUTION_STYLE,
    vintage_footer,
)

_ATTRIBUTION_TEXT = "Sources: " + ", ".join(SOURCE_ATTRIBUTION.values())

_CARD_STYLE = {
    "backgroundColor": "#FFFFFF",
    "borderRadius": "8px",
    "padding": "24px",
    "marginBottom": "24px",
    "boxShadow": "0 1px 4px rgba(0,0,0,0.08)",
    "border": f"1px solid {COLOR_AXES}",
}

_SECTION_HEADING_STYLE = {
    "fontSize": "20px",
    "fontWeight": 600,
    "color": COLOR_TEXT_PRIMARY,
    "marginBottom": "4px",
    "marginTop": "0",
}

_SECTION_SUBTITLE_STYLE = {
    "fontSize": "14px",
    "color": COLOR_TEXT_SECONDARY,
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


def build_drivers_layout(segment: str, usd_col: str, mode: str = "normal") -> html.Div:
    """
    Build the Drivers tab layout.

    Parameters
    ----------
    segment : str
        Segment ID or "all" (not used \u2014 SHAP plot is global).
    usd_col : str
        USD column toggle (not used \u2014 SHAP plot is static).
    mode : str
        "normal" for narrative view, "expert" for technical detail view.

    Returns
    -------
    html.Div
        Dash component tree for the Drivers tab.
    """
    expert = mode == "expert"
    intro_card = html.Div([
        html.H2("SHAP (SHapley Additive exPlanations) Driver Attribution", style=_SECTION_HEADING_STYLE),
        html.P(
            "SHAP shows how much each factor contributed to the forecast. "
            "This chart shows which input variables have the greatest influence on the forecast models, "
            "ranked by their average SHAP value across all segments and "
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
                "color": COLOR_TEXT_PRIMARY,
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
            _ATTRIBUTION_TEXT,
            style=ATTRIBUTION_STYLE,
        ),
    ], style=_CARD_STYLE)

    methodology_card = html.Div([
        html.H3(
            "How SHAP Attribution Works",
            style={
                "fontSize": "16px",
                "fontWeight": 600,
                "color": COLOR_TEXT_PRIMARY,
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
            style={"fontSize": "14px", "color": COLOR_TEXT_SECONDARY, "lineHeight": "1.6", "marginBottom": "8px"},
        ),
        html.P(
            "This plot shows beeswarm SHAP values from the Phase 3 ML correction layer, applied on top "
            "of the Phase 2 statistical baseline. Each dot represents one observation (segment-year pair); "
            "the horizontal position shows the SHAP value for that observation; the color shows whether "
            "the raw feature value was high (red) or low (blue) for that observation.",
            style={"fontSize": "14px", "color": COLOR_TEXT_SECONDARY, "lineHeight": "1.6", "marginBottom": "0"},
        ),
    ], style={
        **_CARD_STYLE,
        "marginBottom": "0",
        "borderTop": "3px solid #F4F6FA",
    })

    sections = [intro_card, shap_card]

    if expert:
        # Expert mode: SHAP mathematical detail + feature list
        expert_card = html.Div([
            html.H3(
                "Expert View \u2014 SHAP Mathematical Detail",
                style={"fontSize": "16px", "fontWeight": 600, "color": "#7C4DFF", "marginBottom": "8px", "marginTop": "0"},
            ),
            html.P(
                "SHAP values (Lundberg & Lee 2017) are rooted in Shapley values from cooperative game theory "
                "(Shapley 1953). For a prediction f(x), the SHAP value \u03c6_i for feature i satisfies:",
                style={"fontSize": "13px", "color": COLOR_TEXT_SECONDARY, "lineHeight": "1.6", "marginBottom": "4px"},
            ),
            html.Code(
                "\u03c6_i = \u03a3_{S \u2286 F\u2216{i}} [|S|!(|F|-|S|-1)!/|F|!] \u00d7 [f(S\u222a{i}) - f(S)]",
                style={
                    "display": "block", "fontFamily": "monospace", "fontSize": "13px",
                    "backgroundColor": "#F4F6FA", "padding": "8px 12px",
                    "borderRadius": "4px", "marginBottom": "8px",
                },
            ),
            html.P(
                "where F is the full feature set, S ranges over all subsets of F not containing i, "
                "and f(S) is the model prediction with features in S (others set to their expected values).",
                style={"fontSize": "13px", "color": COLOR_TEXT_SECONDARY, "lineHeight": "1.6", "marginBottom": "8px"},
            ),
            html.P([
                html.Strong("Features in the model: "),
                "R&D spend (rd_ict_pct_gdp), AI patent filings (ai_patent_filings), "
                "VC/PE investment (vc_ai_investment), public company AI revenue (public_co_ai_revenue), "
                "researchers per million (researchers_per_million), high-technology exports (hightech_exports). "
                "Source: OECD ANBERD, OECD PATS_IPC (IPC G06N), OECD VC_INVEST, LSEG TRBC, "
                "World Bank SP.POP.SCIE.RD.P6, World Bank TX.VAL.TECH.CD.",
            ], style={"fontSize": "13px", "color": COLOR_TEXT_SECONDARY, "lineHeight": "1.6", "marginBottom": "8px"}),
            html.P([
                html.Strong("Implementation: "),
                "SHAP TreeExplainer on the Phase 3 XGBoost ML correction layer. Each dot in the beeswarm "
                "plot represents one segment-year observation. The plot is generated by ",
                html.Code("src/models/ml/shap_explain.py", style={"fontSize": "12px"}),
                " and saved to ",
                html.Code("models/ai_industry/shap_summary.png", style={"fontSize": "12px"}),
                ".",
            ], style={"fontSize": "13px", "color": COLOR_TEXT_SECONDARY, "lineHeight": "1.6", "marginBottom": "0"}),
        ], style={
            "backgroundColor": "#FAF8FF",
            "border": "1px solid #C5B0FF",
            "borderLeft": "4px solid #7C4DFF",
            "borderRadius": "8px",
            "padding": "18px 20px",
            "marginBottom": "24px",
        })
        sections.append(expert_card)

    sections.append(methodology_card)
    sections.append(vintage_footer("World Bank, OECD, LSEG", FORECASTS_DF["data_vintage"].iloc[0]))
    return html.Div(sections, style={"paddingTop": "8px"})
