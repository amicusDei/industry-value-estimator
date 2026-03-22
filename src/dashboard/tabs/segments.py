"""
Segments tab layout builder.

Shows a 2x2 grid of per-segment fan charts (or single chart for filtered segment).
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.dashboard.app import FORECASTS_DF, SEGMENTS, SEGMENT_DISPLAY
from src.dashboard.charts.fan_chart import make_fan_chart
from src.dashboard.charts.styles import COLOR_DEEP_BLUE, ATTRIBUTION_STYLE

_CARD_STYLE = {
    "backgroundColor": "#FFFFFF",
    "borderRadius": "8px",
    "padding": "20px",
    "boxShadow": "0 1px 4px rgba(0,0,0,0.08)",
    "border": "1px solid #E8EBF0",
    "height": "100%",
}

_SEGMENT_DESCRIPTIONS = {
    "ai_hardware": (
        "Semiconductors, chips, and specialized AI processors (GPUs, TPUs, NPUs). "
        "This segment captures the physical compute layer that powers AI workloads. "
        "Demand is largely supply-constrained \u2014 NVIDIA, AMD, and TSMC are key players. "
        "The 2022 GenAI surge created a structural demand shock reflected in the trend break."
    ),
    "ai_infrastructure": (
        "Cloud platforms, hyperscale data centers, and AI-as-a-service capacity. "
        "This segment captures the infrastructure layer between chips and applications \u2014 "
        "AWS, Azure, and Google Cloud\u2019s AI-specific build-out. Growth tracks hardware demand "
        "with a 6\u201312 month lag as data center capacity expansion follows chip procurement."
    ),
    "ai_software": (
        "AI applications, foundation model platforms, and developer tooling. "
        "This is the fastest-growing segment, driven by the proliferation of LLM-based products. "
        "Private companies (OpenAI, Anthropic, Mistral) are excluded from the index \u2014 meaning "
        "the true market size is likely understated by 20\u201340% in 2023\u20132025."
    ),
    "ai_adoption": (
        "Enterprise and consumer deployment of AI capabilities across industries. "
        "This segment measures AI as an input to economic activity rather than as a product \u2014 "
        "productivity gains, automation-driven cost savings, and AI-enabled service revenue. "
        "It is the broadest and most uncertain segment due to diffuse measurement across sectors."
    ),
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

_SEGMENT_HEADING_STYLE = {
    "fontSize": "16px",
    "fontWeight": 600,
    "color": "#1A1A2E",
    "marginBottom": "4px",
    "marginTop": "0",
}

_SEGMENT_DESC_STYLE = {
    "fontSize": "13px",
    "color": "#555",
    "marginBottom": "12px",
    "marginTop": "0",
    "lineHeight": "1.5",
}


def build_segments_layout(segment: str, usd_col: str) -> html.Div:
    """
    Build the Segments tab layout.

    Parameters
    ----------
    segment : str
        Segment ID or "all" to show all four segments in a 2x2 grid.
    usd_col : str
        Column name for point line.

    Returns
    -------
    html.Div
        Dash component tree for the Segments tab.
    """
    tab_intro = html.Div([
        html.H2("Per-Segment Forecast Fan Charts", style=_SECTION_HEADING_STYLE),
        html.P(
            "Each panel shows the historical index trajectory and 2030 forecast for one of the four AI "
            "market segments. The solid line is confirmed historical data; the dashed line is the median "
            "forecast. Blue shading shows 80% (darker) and 95% (lighter) confidence intervals \u2014 "
            "wider bands indicate greater uncertainty, which grows with forecast horizon. "
            "Segments are modeled independently using the best-fitting model per segment (ARIMA or Prophet).",
            style=_SECTION_SUBTITLE_STYLE,
        ),
    ], style={
        "backgroundColor": "#FFFFFF",
        "borderRadius": "8px",
        "padding": "20px 24px 16px",
        "marginBottom": "20px",
        "boxShadow": "0 1px 4px rgba(0,0,0,0.08)",
        "border": "1px solid #E8EBF0",
    })

    if segment == "all":
        # 2x2 grid showing all 4 segments
        seg_pairs = [SEGMENTS[i:i + 2] for i in range(0, len(SEGMENTS), 2)]
        rows = []
        for pair in seg_pairs:
            cols = []
            for seg in pair:
                fig = make_fan_chart(FORECASTS_DF, seg, usd_col)
                display_name = SEGMENT_DISPLAY.get(seg, seg)
                description = _SEGMENT_DESCRIPTIONS.get(seg, "")
                col = dbc.Col([
                    html.Div([
                        html.H3(display_name, style=_SEGMENT_HEADING_STYLE),
                        html.P(description, style=_SEGMENT_DESC_STYLE),
                        dcc.Loading(
                            type="circle",
                            color=COLOR_DEEP_BLUE,
                            children=dcc.Graph(
                                figure=fig,
                                id=f"segments-fan-{seg}",
                                config={"displayModeBar": True},
                            ),
                        ),
                        html.P(
                            "Sources: World Bank Open Data, OECD.Stat, LSEG Workspace",
                            style=ATTRIBUTION_STYLE,
                        ),
                    ], style=_CARD_STYLE),
                ], width=6, style={"marginBottom": "20px"})
                cols.append(col)
            rows.append(dbc.Row(cols))
        return html.Div([tab_intro] + rows, style={"paddingTop": "8px"})
    else:
        # Single segment full-width
        fig = make_fan_chart(FORECASTS_DF, segment, usd_col)
        display_name = SEGMENT_DISPLAY.get(segment, segment)
        description = _SEGMENT_DESCRIPTIONS.get(segment, "")
        return html.Div([
            tab_intro,
            html.Div([
                html.H3(display_name, style=_SEGMENT_HEADING_STYLE),
                html.P(description, style=_SEGMENT_DESC_STYLE),
                dcc.Loading(
                    type="circle",
                    color=COLOR_DEEP_BLUE,
                    children=dcc.Graph(
                        figure=fig,
                        id=f"segments-fan-{segment}",
                        config={"displayModeBar": True},
                    ),
                ),
                html.P(
                    "Sources: World Bank Open Data, OECD.Stat, LSEG Workspace",
                    style=ATTRIBUTION_STYLE,
                ),
            ], style={
                "backgroundColor": "#FFFFFF",
                "borderRadius": "8px",
                "padding": "24px",
                "boxShadow": "0 1px 4px rgba(0,0,0,0.08)",
                "border": "1px solid #E8EBF0",
            }),
        ], style={"paddingTop": "8px"})
