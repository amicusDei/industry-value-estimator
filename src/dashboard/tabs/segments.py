"""
Segments tab layout builder.

Shows a 2x2 grid of per-segment fan charts (or single chart for filtered segment).
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.dashboard.app import FORECASTS_DF, SEGMENTS, SEGMENT_DISPLAY, SOURCE_ATTRIBUTION

_ATTRIBUTION_TEXT = "Sources: " + ", ".join(SOURCE_ATTRIBUTION.values())
from src.dashboard.charts.fan_chart import make_fan_chart
from src.dashboard.charts.styles import COLOR_DEEP_BLUE, ATTRIBUTION_STYLE, vintage_footer

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


def build_segments_layout(segment: str, usd_col: str, mode: str = "normal") -> html.Div:
    """
    Build the Segments tab layout.

    Parameters
    ----------
    segment : str
        Segment ID or "all" to show all four segments in a 2x2 grid.
    usd_col : str
        Column name for point line.
    mode : str
        "normal" for narrative USD view, "expert" for raw index + methodology view.

    Returns
    -------
    html.Div
        Dash component tree for the Segments tab.
    """
    expert = mode == "expert"
    usd_mode = not expert  # Normal: USD chart; Expert: raw index chart

    if usd_mode:
        tab_subtitle = (
            "Each panel shows estimated market size (USD billions) for one of the four AI market segments "
            "from 2010 to 2030. The solid line is the historical baseline; the dashed line is the median "
            "forecast. Blue shading shows 80% (darker) and 95% (lighter) confidence intervals. "
            "Values are calibrated to the ~$200B 2023 industry consensus and expressed in 2020 constant USD."
        )
    else:
        tab_subtitle = (
            "Expert mode: Y-axis shows real 2020 USD market size values. "
            "Segments are modeled independently using the best-fitting model per segment (ARIMA or Prophet)."
        )

    tab_intro = html.Div([
        html.H2(
            "Per-Segment Forecast Fan Charts" if usd_mode else "Per-Segment Raw Index Fan Charts",
            style=_SECTION_HEADING_STYLE,
        ),
        html.P(tab_subtitle, style=_SECTION_SUBTITLE_STYLE),
    ], style={
        "backgroundColor": "#FFFFFF",
        "borderRadius": "8px",
        "padding": "20px 24px 16px",
        "marginBottom": "20px",
        "boxShadow": "0 1px 4px rgba(0,0,0,0.08)",
        "border": "1px solid #E8EBF0",
    })

    # Expert mode: segment model type reference table
    expert_note = None
    if expert:
        expert_note = html.Div([
            html.H4(
                "Expert View \u2014 Per-Segment Modeling Detail",
                style={"fontSize": "14px", "fontWeight": 600, "color": "#7C4DFF", "marginBottom": "8px", "marginTop": "0"},
            ),
            html.Ul([
                html.Li("Each segment uses the model with lower CV MAPE: ARIMA(p,d,q) via auto_arima AICc or Facebook Prophet.", style={"fontSize": "13px"}),
                html.Li("ARIMA order selection: max_p=2, max_q=2, seasonal=False, information_criterion='aicc'.", style={"fontSize": "13px"}),
                html.Li("Prophet: single explicit changepoint at 2022-01-01, changepoint_prior_scale=0.1, no weekly/daily seasonality.", style={"fontSize": "13px"}),
                html.Li("CV folds: expanding-window cross-validation, n_splits=3. Preprocessing fit on training fold only \u2014 no data leakage.", style={"fontSize": "13px"}),
                html.Li("CI bands: 80% and 95% bootstrap intervals derived from model residuals (500 resamples).", style={"fontSize": "13px"}),
                html.Li([
                    "Independence assumption: segments modeled separately, aggregate = sum. ",
                    html.Strong("Cross-segment spillovers are NOT modeled."),
                    " See docs/ASSUMPTIONS.md \u00a7 Per-Segment Independence.",
                ], style={"fontSize": "13px"}),
            ], style={"paddingLeft": "20px", "marginBottom": "0"}),
        ], style={
            "backgroundColor": "#FAF8FF",
            "border": "1px solid #C5B0FF",
            "borderLeft": "4px solid #7C4DFF",
            "borderRadius": "6px",
            "padding": "14px 18px",
            "marginBottom": "20px",
        })

    if segment == "all":
        # 2x2 grid showing all 4 segments
        seg_pairs = [SEGMENTS[i:i + 2] for i in range(0, len(SEGMENTS), 2)]
        rows = []
        for pair in seg_pairs:
            cols = []
            for seg in pair:
                fig = make_fan_chart(FORECASTS_DF, seg, usd_col, usd_mode=usd_mode)
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
                            _ATTRIBUTION_TEXT,
                            style=ATTRIBUTION_STYLE,
                        ),
                    ], style=_CARD_STYLE),
                ], width=6, style={"marginBottom": "20px"})
                cols.append(col)
            rows.append(dbc.Row(cols))
        extra = [expert_note] if expert_note else []
        return html.Div(
            [tab_intro] + extra + rows + [vintage_footer("EDGAR/Analyst Corpus", FORECASTS_DF["data_vintage"].iloc[0])],
            style={"paddingTop": "8px"},
        )
    else:
        # Single segment full-width
        fig = make_fan_chart(FORECASTS_DF, segment, usd_col, usd_mode=usd_mode)
        display_name = SEGMENT_DISPLAY.get(segment, segment)
        description = _SEGMENT_DESCRIPTIONS.get(segment, "")
        extra = [expert_note] if expert_note else []
        return html.Div([
            tab_intro,
        ] + extra + [
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
                    _ATTRIBUTION_TEXT,
                    style=ATTRIBUTION_STYLE,
                ),
            ], style={
                "backgroundColor": "#FFFFFF",
                "borderRadius": "8px",
                "padding": "24px",
                "boxShadow": "0 1px 4px rgba(0,0,0,0.08)",
                "border": "1px solid #E8EBF0",
            }),
            vintage_footer("EDGAR/Analyst Corpus", FORECASTS_DF["data_vintage"].iloc[0]),
        ], style={"paddingTop": "8px"})
