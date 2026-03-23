"""
Overview tab layout builder.

Normal mode: dollar headlines, USD fan chart, per-segment USD breakdown, growth rates,
and clean narrative a non-technical reader can follow.

Expert mode: adds raw composite index values, value chain multiplier derivation,
ensemble parameters, CV metrics, and ASSUMPTIONS.md references.
"""
from __future__ import annotations

import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import dcc, html

from src.dashboard.app import (
    FORECASTS_DF,
    SEGMENTS,
    SEGMENT_DISPLAY,
    VALUE_CHAIN_MULTIPLIERS,
    VALUE_CHAIN_DERIVATION,
    SOURCE_ATTRIBUTION,
)

_ATTRIBUTION_TEXT = "Sources: " + ", ".join(SOURCE_ATTRIBUTION.values())
from src.dashboard.charts.fan_chart import make_fan_chart
from src.dashboard.charts.styles import (
    COLOR_DEEP_BLUE,
    COLOR_BG_SECONDARY,
    ATTRIBUTION_STYLE,
)

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


def _fmt_usd(usd_billions: float) -> str:
    """Format a USD billions value as a human-readable string."""
    if usd_billions >= 1000:
        return f"${usd_billions / 1000:.1f}T"
    return f"${usd_billions:.0f}B"


def _compute_cagr(start_val: float, end_val: float, years: int) -> float | None:
    """Compute compound annual growth rate. Returns None if inputs are invalid."""
    if start_val <= 0 or end_val <= 0 or years <= 0:
        return None
    return ((end_val / start_val) ** (1.0 / years) - 1.0) * 100.0


def build_overview_layout(segment: str, usd_col: str, mode: str = "normal") -> html.Div:
    """
    Build the Overview tab layout.

    Parameters
    ----------
    segment : str
        Segment ID or "all" to aggregate all segments.
    usd_col : str
        Column name for point line. Either "point_estimate_real_2020" or
        "point_estimate_nominal".
    mode : str
        "normal" for narrative dollar-headline view, "expert" for technical detail view.

    Returns
    -------
    html.Div
        Dash component tree for the Overview tab.
    """
    expert = mode == "expert"

    # ---------------------------------------------------------------------------
    # Compute USD values for headline stats
    # ---------------------------------------------------------------------------
    df_2024 = FORECASTS_DF[FORECASTS_DF["year"] == 2024]
    df_2030 = FORECASTS_DF[FORECASTS_DF["year"] == 2030]

    if segment == "all":
        usd_2024 = float(df_2024["usd_point"].sum())
        usd_2030 = float(df_2030["usd_point"].sum())
        usd_ci80_lo = float(df_2030["usd_ci80_lower"].sum())
        usd_ci80_hi = float(df_2030["usd_ci80_upper"].sum())
        usd_ci95_lo = float(df_2030["usd_ci95_lower"].sum())
        usd_ci95_hi = float(df_2030["usd_ci95_upper"].sum())
        # Raw index for expert mode
        idx_2023_anchor = float(FORECASTS_DF[FORECASTS_DF["year"] == 2023]["point_estimate_real_2020"].sum())
        idx_2030 = float(df_2030["point_estimate_real_2020"].sum())
    else:
        _get_val = lambda df, col: float(df[df["segment"] == segment][col].iloc[0]) if len(df[df["segment"] == segment]) > 0 else 0.0
        usd_2024 = _get_val(df_2024, "usd_point")
        usd_2030 = _get_val(df_2030, "usd_point")
        usd_ci80_lo = _get_val(df_2030, "usd_ci80_lower")
        usd_ci80_hi = _get_val(df_2030, "usd_ci80_upper")
        usd_ci95_lo = _get_val(df_2030, "usd_ci95_lower")
        usd_ci95_hi = _get_val(df_2030, "usd_ci95_upper")
        idx_2023_anchor = float(
            FORECASTS_DF[(FORECASTS_DF["year"] == 2023) & (FORECASTS_DF["segment"] == segment)]["point_estimate_real_2020"].iloc[0]
            if len(FORECASTS_DF[(FORECASTS_DF["year"] == 2023) & (FORECASTS_DF["segment"] == segment)]) > 0
            else 0.0
        )
        idx_2030 = _get_val(df_2030, "point_estimate_real_2020")

    cagr = _compute_cagr(usd_2024, usd_2030, 6)
    segment_label = "All Segments Combined" if segment == "all" else SEGMENT_DISPLAY.get(segment, segment)

    # ---------------------------------------------------------------------------
    # Normal mode: dollar headline card
    # ---------------------------------------------------------------------------
    headline_main = f"AI Industry: {_fmt_usd(usd_2030)} by 2030"
    headline_ci = f"80% CI: {_fmt_usd(usd_ci80_lo)} \u2013 {_fmt_usd(usd_ci80_hi)}"
    cagr_text = f"{cagr:.1f}% CAGR (2024\u20132030)" if cagr is not None else "Growth rate N/A"

    headline_children = [
        html.P(
            headline_main,
            style={
                "fontSize": "36px",
                "fontWeight": 600,
                "color": COLOR_DEEP_BLUE,
                "marginBottom": "4px",
                "marginTop": "0",
            },
        ),
        html.Div([
            html.Span(
                headline_ci,
                style={"fontSize": "16px", "color": "#555", "marginRight": "20px"},
            ),
            html.Span(
                cagr_text,
                style={"fontSize": "16px", "color": "#555"},
            ),
        ], style={"marginBottom": "8px"}),
        html.P(
            f"2030 market size estimate \u00b7 {segment_label} \u00b7 95% CI: {_fmt_usd(usd_ci95_lo)} \u2013 {_fmt_usd(usd_ci95_hi)} \u00b7 2020 constant USD",
            style={"fontSize": "12px", "color": "#888", "marginTop": "0", "marginBottom": "4px"},
        ),
        html.P(
            "Calibrated against industry consensus: ~$200B global AI market in 2023 "
            "(McKinsey Global Institute, Statista, Grand View Research). "
            "Forecasts use an ensemble of ARIMA and Prophet statistical models. "
            "Wide confidence intervals reflect genuine uncertainty in long-horizon forecasting.",
            style={"fontSize": "13px", "color": "#666", "marginTop": "4px", "marginBottom": "0", "lineHeight": "1.5"},
        ),
    ]

    # Expert mode adds raw index value and multiplier reference to the headline card
    if expert:
        mult = VALUE_CHAIN_MULTIPLIERS.get(segment, sum(VALUE_CHAIN_MULTIPLIERS.values())) if segment != "all" else None
        deriv = VALUE_CHAIN_DERIVATION.get(segment) if segment != "all" else None
        expert_headline_note = html.Div([
            html.Hr(style={"margin": "12px 0", "borderColor": "#EDE9FF"}),
            html.P([
                html.Strong("Expert: "),
                f"Raw composite index at 2030 = {idx_2030:.4f} \u00b7 ",
                f"Anchor year 2023 index = {idx_2023_anchor:.4f}",
            ], style={"fontSize": "13px", "color": "#7C4DFF", "marginBottom": "4px"}),
        ], style={})
        headline_children.append(expert_headline_note)

    headline = html.Div(
        headline_children,
        style={
            **_CARD_STYLE,
            "borderLeft": f"4px solid {COLOR_DEEP_BLUE}",
        },
    )

    # ---------------------------------------------------------------------------
    # Fan chart — normal: USD mode; expert: shows both via tab or side-by-side note
    # ---------------------------------------------------------------------------
    # In normal mode, show USD chart. In expert mode, show raw index chart (expert
    # users understand the index; USD chart is shown in normal mode).
    fan_fig = make_fan_chart(FORECASTS_DF, segment, usd_col, usd_mode=not expert)

    if expert:
        fan_desc = (
            "Expert mode: Y-axis shows the raw composite index (PCA first principal component "
            "of six proxy indicators). Negative values are valid PCA scores \u2014 they indicate "
            "below-baseline activity for that segment/year. The index is centered at 0 by construction. "
            "Switch to Normal mode to see USD estimates."
        )
        fan_title = "Forecast Fan Chart \u2014 Raw Composite Index"
    else:
        fan_desc = (
            "This chart traces estimated AI industry market size from 2010 through the historical record, "
            "then projects it forward to 2030. The solid line shows the historical baseline; the dashed "
            "line shows the median point forecast. The shaded blue regions show where the true value is "
            "expected to fall: the darker inner band covers 80% of likely outcomes, the outer band covers "
            "95%. Wider bands in later years reflect compounding uncertainty over a longer horizon."
        )
        fan_title = "Market Size Forecast (USD Billions)"

    fan_section = html.Div([
        html.H2(fan_title, style=_SECTION_HEADING_STYLE),
        html.P(fan_desc, style=_SECTION_SUBTITLE_STYLE),
        dcc.Loading(
            type="circle",
            color=COLOR_DEEP_BLUE,
            children=dcc.Graph(
                figure=fan_fig,
                id="overview-fan-chart",
                config={"displayModeBar": True},
            ),
        ),
        html.P(
            _ATTRIBUTION_TEXT,
            style=ATTRIBUTION_STYLE,
        ),
    ], style=_CARD_STYLE)

    # ---------------------------------------------------------------------------
    # Segment breakdown bar chart
    # ---------------------------------------------------------------------------
    bar_fig = _build_segment_bar(segment, usd_col, usd_mode=not expert)

    if segment == "all":
        bar_heading = "Segment Breakdown \u2014 2030 Forecast" if not expert else "Segment Breakdown \u2014 2030 Raw Index"
        bar_subtitle = (
            "How the 2030 aggregate forecast is distributed across the four AI market segments: "
            "hardware (chips and semiconductors enabling AI compute), infrastructure (cloud platforms "
            "and data centers), software (AI applications and platforms), and adoption (enterprise "
            "and consumer deployment)."
            if not expert else
            "Raw composite index values at 2030 per segment (before USD conversion). "
            "These are PCA scores \u2014 negative values are valid and indicate below-baseline activity."
        )
    else:
        display_name = SEGMENT_DISPLAY.get(segment, segment)
        bar_heading = (
            f"{display_name} \u2014 Annual Market Size (USD Billions)" if not expert
            else f"{display_name} \u2014 Annual Raw Index"
        )
        bar_subtitle = (
            f"Year-by-year market size estimate for the {display_name} segment from 2010 to 2030, "
            "in USD billions (2020 constant)."
            if not expert else
            f"Year-by-year raw composite index for the {display_name} segment. "
            "PCA scores centered at 0 \u2014 negative values indicate below-baseline activity."
        )

    bar_section = html.Div([
        html.H2(bar_heading, style=_SECTION_HEADING_STYLE),
        html.P(bar_subtitle, style=_SECTION_SUBTITLE_STYLE),
        dcc.Loading(
            type="circle",
            color=COLOR_DEEP_BLUE,
            children=dcc.Graph(
                figure=bar_fig,
                id="overview-bar-chart",
                config={"displayModeBar": True},
            ),
        ),
        html.P(
            _ATTRIBUTION_TEXT,
            style=ATTRIBUTION_STYLE,
        ),
    ], style=_CARD_STYLE)

    # ---------------------------------------------------------------------------
    # Normal mode: narrative insight card
    # ---------------------------------------------------------------------------
    if not expert:
        insight_card = _build_normal_insights_card(segment, usd_2024, usd_2030, cagr, usd_ci80_lo, usd_ci80_hi)
    else:
        insight_card = None

    # ---------------------------------------------------------------------------
    # Expert mode: raw index + multiplier derivation panel
    # ---------------------------------------------------------------------------
    if expert:
        expert_card = _build_expert_methodology_card(segment)
    else:
        expert_card = None

    sections = [headline, fan_section]
    if expert_card:
        sections.append(expert_card)
    if insight_card:
        sections.append(insight_card)
    sections.append(bar_section)
    return html.Div(sections, style={"paddingTop": "8px"})


def _build_normal_insights_card(
    segment: str,
    usd_2024: float,
    usd_2030: float,
    cagr: float | None,
    ci80_lo: float,
    ci80_hi: float,
) -> html.Div:
    """Build a plain-language narrative insight card for normal mode."""
    segment_label = "AI Industry" if segment == "all" else SEGMENT_DISPLAY.get(segment, segment)
    cagr_str = f"{cagr:.1f}% per year" if cagr is not None else "unknown growth rate"

    # Compute per-segment 2030 estimates for bullet points when showing all
    bullets = []
    if segment == "all":
        df_2030 = FORECASTS_DF[FORECASTS_DF["year"] == 2030]
        for seg in SEGMENTS:
            seg_rows = df_2030[df_2030["segment"] == seg]
            if len(seg_rows) > 0:
                seg_usd = float(seg_rows["usd_point"].iloc[0])
                bullets.append(
                    html.Li(
                        f"{SEGMENT_DISPLAY.get(seg, seg)}: {_fmt_usd(seg_usd)}",
                        style={"fontSize": "14px", "marginBottom": "4px"},
                    )
                )

    narrative_paragraphs = [
        html.P([
            html.Strong(f"{segment_label} "),
            f"is estimated at {_fmt_usd(usd_2030)} by 2030 under the central forecast, "
            f"growing at approximately {cagr_str} from {_fmt_usd(usd_2024)} in 2024. "
            f"The 80% confidence interval ({_fmt_usd(ci80_lo)} \u2013 {_fmt_usd(ci80_hi)}) "
            "reflects genuine model uncertainty across a 6-year forecast horizon \u2014 "
            "treat the point estimate as the central scenario, not a guaranteed outcome.",
        ], style={"fontSize": "15px", "color": "#333", "lineHeight": "1.6", "marginBottom": "12px"}),
    ]

    if bullets:
        narrative_paragraphs.append(
            html.P(
                "2030 segment breakdown (central estimates):",
                style={"fontSize": "14px", "fontWeight": 600, "color": "#333", "marginBottom": "6px"},
            )
        )
        narrative_paragraphs.append(
            html.Ul(bullets, style={"paddingLeft": "24px", "marginBottom": "12px"})
        )

    narrative_paragraphs.append(
        html.P([
            html.Strong("How to read this: "),
            "Estimates are calibrated to approximately $200B in 2023, the consensus range from "
            "McKinsey Global Institute, Statista, and Grand View Research. The forecast extrapolates "
            "growth trends in R&D spend, patent filings, VC investment, and public-company revenues "
            "using statistical time-series models. Wide confidence intervals are normal for this "
            "forecast horizon \u2014 the honest message is directional, not precise.",
        ], style={"fontSize": "14px", "color": "#555", "lineHeight": "1.6", "marginBottom": "0"}),
    )

    return html.Div([
        html.H2("Key Takeaways", style=_SECTION_HEADING_STYLE),
        html.Div(narrative_paragraphs),
    ], style=_CARD_STYLE)


def _build_expert_methodology_card(segment: str) -> html.Div:
    """Build the expert mode methodology card with raw index values and multiplier derivation."""
    from src.dashboard.app import RESIDUALS_DF
    import numpy as np

    # Per-segment RMSE
    rmse_rows = []
    for seg in SEGMENTS:
        grp = RESIDUALS_DF[RESIDUALS_DF["segment"] == seg]
        if len(grp) > 0:
            rmse_val = float(np.sqrt(np.mean(grp["residual"].to_numpy() ** 2)))
            rmse_rows.append(html.Tr([
                html.Td(SEGMENT_DISPLAY.get(seg, seg), style={"padding": "6px 12px", "fontSize": "13px", "fontWeight": 500}),
                html.Td(f"{rmse_val:.4f}", style={"padding": "6px 12px", "fontSize": "13px", "fontFamily": "monospace"}),
                html.Td(
                    f"{VALUE_CHAIN_MULTIPLIERS.get(seg, 0):.2f} B/unit",
                    style={"padding": "6px 12px", "fontSize": "13px", "fontFamily": "monospace"},
                ),
            ]))

    # Value chain derivation section
    from src.dashboard.app import AI_CONFIG as _AI_CONFIG
    vc = _AI_CONFIG["value_chain"]

    deriv_rows = []
    for seg in SEGMENTS:
        d = VALUE_CHAIN_DERIVATION.get(seg, {})
        deriv_rows.append(html.Tr([
            html.Td(SEGMENT_DISPLAY.get(seg, seg), style={"padding": "5px 10px", "fontSize": "12px"}),
            html.Td(f"{d.get('anchor_usd', 0):.0f}B", style={"padding": "5px 10px", "fontSize": "12px", "fontFamily": "monospace"}),
            html.Td(f"{d.get('index_at_anchor', 0):.4f}", style={"padding": "5px 10px", "fontSize": "12px", "fontFamily": "monospace"}),
            html.Td(f"{d.get('multiplier', 0):.2f}", style={"padding": "5px 10px", "fontSize": "12px", "fontFamily": "monospace"}),
            html.Td(d.get("method", ""), style={"padding": "5px 10px", "fontSize": "11px", "color": "#888"}),
        ]))

    return html.Div([
        html.H2(
            "Expert View \u2014 Raw Index, Multiplier Derivation & Methodology",
            style={**_SECTION_HEADING_STYLE, "color": "#7C4DFF"},
        ),
        html.P(
            "This panel is visible in Expert mode only. It surfaces the raw composite index values, "
            "the value chain multiplier derivation, model parameters, CV metrics, and "
            "docs/ASSUMPTIONS.md references for technical reviewers and reproducibility.",
            style=_SECTION_SUBTITLE_STYLE,
        ),

        # Value chain multiplier derivation
        html.H3(
            "Value Chain Multiplier Derivation",
            style={"fontSize": "16px", "fontWeight": 600, "marginBottom": "8px", "marginTop": "0"},
        ),
        html.P([
            html.Strong("Anchor: "),
            f"Global AI market \u2248 ${vc['anchor_value_usd_billions']}B in {vc['anchor_year']} "
            "(McKinsey Global Institute 2023, Statista 2023, Grand View Research 2024 consensus). ",
            html.Strong("Method: "),
            f"{vc['multiplier_method']} \u2014 each segment gets an anchor USD value proportional to "
            "its consensus market share; multiplier = anchor_usd / index_at_anchor_year.",
        ], style={"fontSize": "13px", "color": "#444", "lineHeight": "1.6", "marginBottom": "10px"}),
        html.Table(
            [
                html.Thead(html.Tr([
                    html.Th("Segment", style={"padding": "6px 10px", "fontSize": "12px", "backgroundColor": "#F4F6FA"}),
                    html.Th("Anchor USD", style={"padding": "6px 10px", "fontSize": "12px", "backgroundColor": "#F4F6FA"}),
                    html.Th("Index at 2023", style={"padding": "6px 10px", "fontSize": "12px", "backgroundColor": "#F4F6FA"}),
                    html.Th("Multiplier (B/unit)", style={"padding": "6px 10px", "fontSize": "12px", "backgroundColor": "#F4F6FA"}),
                    html.Th("Method", style={"padding": "6px 10px", "fontSize": "12px", "backgroundColor": "#F4F6FA"}),
                ])),
                html.Tbody(deriv_rows),
            ],
            style={"borderCollapse": "collapse", "width": "100%", "border": "1px solid #E8EBF0", "marginBottom": "16px"},
        ),
        html.P(
            "Note: Segments with negative index values at the anchor year use a global fallback multiplier "
            "(global_multiplier \u00d7 segment_share). This arises from synthetic/placeholder pipeline data \u2014 "
            "real World Bank/OECD/LSEG data will produce positive index values at the anchor year.",
            style={"fontSize": "12px", "color": "#888", "fontStyle": "italic", "marginBottom": "16px"},
        ),

        html.Hr(style={"margin": "16px 0", "borderColor": "#E8EBF0"}),

        # Ensemble composition + RMSE
        dbc.Row([
            dbc.Col([
                html.H4("Ensemble Composition", style={"fontSize": "14px", "fontWeight": 600, "marginBottom": "8px"}),
                html.Ul([
                    html.Li("Models: ARIMA (pmdarima auto_arima, AICc criterion) + Prophet (Facebook Prophet 1.1)", style={"fontSize": "13px"}),
                    html.Li("Ensemble: equal-weight average of ARIMA and Prophet point estimates", style={"fontSize": "13px"}),
                    html.Li("CI bands: bootstrap-derived from model residuals (500 draws)", style={"fontSize": "13px"}),
                    html.Li("ARIMA: max_p=2, max_q=2, seasonal=False, information_criterion='aicc'", style={"fontSize": "13px"}),
                    html.Li("Prophet: changepoint at 2022-01-01, changepoint_prior_scale=0.1", style={"fontSize": "13px"}),
                ], style={"paddingLeft": "20px", "marginBottom": "0"}),
            ], width=6),
            dbc.Col([
                html.H4("Out-of-Sample RMSE + Multiplier by Segment", style={"fontSize": "14px", "fontWeight": 600, "marginBottom": "8px"}),
                html.Table(
                    [
                        html.Thead(html.Tr([
                            html.Th("Segment", style={"padding": "6px 12px", "fontSize": "13px", "backgroundColor": "#F4F6FA"}),
                            html.Th("RMSE (index)", style={"padding": "6px 12px", "fontSize": "13px", "backgroundColor": "#F4F6FA"}),
                            html.Th("Multiplier", style={"padding": "6px 12px", "fontSize": "13px", "backgroundColor": "#F4F6FA"}),
                        ])),
                        html.Tbody(rmse_rows),
                    ],
                    style={"borderCollapse": "collapse", "width": "100%", "border": "1px solid #E8EBF0"},
                ),
            ], width=6),
        ]),

        html.Hr(style={"margin": "16px 0", "borderColor": "#E8EBF0"}),
        html.P([
            html.Strong("Assumptions reference: "),
            "See ",
            html.Code("docs/ASSUMPTIONS.md", style={"fontSize": "12px"}),
            " for all modeling assumptions, rationale, and what-if analysis. "
            "Key: (1) structural break at 2022 explicitly modeled; "
            "(2) ~15 training obs/segment \u2014 AICc small-sample correction applied; "
            "(3) segments modeled independently with post-hoc aggregation; "
            "(4) PCA first PC of 6 proxy indicators = AI activity index; "
            "(5) value chain multiplier calibrated to $200B 2023 consensus \u2014 "
            "see docs/ASSUMPTIONS.md \u00a7 Value Chain Multiplier Calibration.",
        ], style={"fontSize": "13px", "color": "#444", "lineHeight": "1.6", "marginBottom": "0"}),
    ], style={
        **_CARD_STYLE,
        "border": "1px solid #C5B0FF",
        "borderLeft": "4px solid #7C4DFF",
    })


def _build_segment_bar(segment: str, usd_col: str, usd_mode: bool = True) -> go.Figure:
    """Build a bar chart for segment breakdown or time-series for a single segment."""
    if usd_mode:
        point_col = "usd_point"
        y_title_2030 = "USD Billions (2030 Estimate)"
        y_title_ts = "USD Billions (2020 constant)"
        hover_tpl = "<b>%{x}</b><br>$%{y:.1f}B<extra></extra>"
    else:
        point_col = usd_col
        y_title_2030 = "Composite Index (2030)"
        y_title_ts = "Composite Index (PCA score)"
        hover_tpl = "<b>%{x}</b><br>Index: %{y:.2f}<extra></extra>"

    if segment == "all":
        # Grouped bar: all 4 segments' 2030 forecast values
        df_2030 = FORECASTS_DF[FORECASTS_DF["year"] == 2030]
        labels = [SEGMENT_DISPLAY.get(s, s) for s in SEGMENTS]
        values = [
            float(df_2030.loc[df_2030["segment"] == s, point_col].iloc[0])
            if len(df_2030[df_2030["segment"] == s]) > 0 else 0.0
            for s in SEGMENTS
        ]
        fig = go.Figure(
            go.Bar(
                x=labels,
                y=values,
                marker_color=COLOR_DEEP_BLUE,
                hovertemplate=hover_tpl,
            )
        )
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(
                title=dict(text="AI Market Segment", font=dict(size=12)),
                gridcolor="#E8EBF0",
                tickfont=dict(size=11),
            ),
            yaxis=dict(
                title=dict(text=y_title_2030, font=dict(size=12)),
                gridcolor="#E8EBF0",
                tickfont=dict(size=11),
            ),
            margin=dict(l=70, r=40, t=40, b=80),
        )
    else:
        # Time-series bar for the selected segment
        seg_df = (
            FORECASTS_DF[FORECASTS_DF["segment"] == segment]
            .sort_values("year")
            .reset_index(drop=True)
        )
        # Color bars: historical vs forecast
        colors = [
            COLOR_DEEP_BLUE if not is_fore else "rgba(30,90,200,0.45)"
            for is_fore in seg_df["is_forecast"]
        ]
        fig = go.Figure(
            go.Bar(
                x=seg_df["year"],
                y=seg_df[point_col],
                marker_color=colors,
                hovertemplate=hover_tpl,
            )
        )
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(
                title=dict(text="Year", font=dict(size=12)),
                gridcolor="#E8EBF0",
                tickfont=dict(size=11),
                dtick=1,
            ),
            yaxis=dict(
                title=dict(text=y_title_ts, font=dict(size=12)),
                gridcolor="#E8EBF0",
                tickfont=dict(size=11),
            ),
            margin=dict(l=70, r=40, t=40, b=60),
        )
        # Annotate the forecast boundary
        if len(seg_df[seg_df["is_forecast"] == False]) > 0:
            last_hist_year = int(seg_df[seg_df["is_forecast"] == False]["year"].max())
            fig.add_vline(
                x=last_hist_year + 0.5,
                line_dash="dash",
                line_color="rgba(120,120,120,0.6)",
                annotation_text="Forecast Start",
                annotation_position="top right",
                annotation_font_size=10,
            )

    return fig
