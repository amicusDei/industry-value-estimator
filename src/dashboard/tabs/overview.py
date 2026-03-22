"""
Overview tab layout builder.

Shows headline forecast index stat, aggregate fan chart, and segment breakdown bar chart.
"""
from __future__ import annotations

import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import dcc, html

from src.dashboard.app import FORECASTS_DF, SEGMENTS, SEGMENT_DISPLAY
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
        "normal" for narrative view, "expert" for technical detail view.

    Returns
    -------
    html.Div
        Dash component tree for the Overview tab.
    """
    expert = mode == "expert"
    # --- Headline stat ---
    df_2030 = FORECASTS_DF[FORECASTS_DF["year"] == 2030]
    if segment == "all":
        val_2030 = df_2030[usd_col].sum()
    else:
        seg_row = df_2030[df_2030["segment"] == segment]
        val_2030 = float(seg_row[usd_col].iloc[0]) if len(seg_row) > 0 else 0.0

    if usd_col == "point_estimate_nominal":
        headline_text = f"AI Industry Forecast Index: {val_2030:.2f} by 2030 (nominal)"
    else:
        headline_text = f"AI Industry Forecast Index: {val_2030:.2f} by 2030"

    segment_label = "All Segments Combined" if segment == "all" else SEGMENT_DISPLAY.get(segment, segment)

    headline = html.Div([
        html.P(
            headline_text,
            style={
                "fontSize": "36px",
                "fontWeight": 600,
                "color": COLOR_DEEP_BLUE,
                "marginBottom": "4px",
                "marginTop": "0",
            },
        ),
        html.P(
            f"2030 composite forecast index \u00b7 {segment_label} \u00b7 80% and 95% confidence intervals shown",
            style={"fontSize": "12px", "color": "#888", "marginTop": "0", "marginBottom": "0"},
        ),
    ], style={
        **_CARD_STYLE,
        "borderLeft": f"4px solid {COLOR_DEEP_BLUE}",
    })

    # --- Fan chart section ---
    fan_fig = make_fan_chart(FORECASTS_DF, segment, usd_col)
    fan_section = html.Div([
        html.H2("Forecast Fan Chart", style=_SECTION_HEADING_STYLE),
        html.P(
            "This chart traces the AI industry activity index from 2010 through the historical record, "
            "then projects it forward to 2030 using an ensemble of statistical models (ARIMA and Prophet). "
            "The solid line shows confirmed historical data; the dashed line shows the median point forecast. "
            "The shaded blue regions show where the true value is expected to fall: the darker inner band "
            "covers 80% of likely outcomes, the wider outer band covers 95%. Wider bands in later years "
            "reflect compounding uncertainty over a longer forecast horizon.",
            style=_SECTION_SUBTITLE_STYLE,
        ),
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
            "Sources: World Bank Open Data, OECD.Stat, LSEG Workspace",
            style=ATTRIBUTION_STYLE,
        ),
    ], style=_CARD_STYLE)

    # --- Segment breakdown bar chart ---
    bar_fig = _build_segment_bar(segment, usd_col)

    if segment == "all":
        bar_heading = "Segment Breakdown — 2030 Forecast"
        bar_subtitle = (
            "How the 2030 aggregate forecast is distributed across the four AI market segments: "
            "hardware (chips and semiconductors enabling AI compute), infrastructure (cloud platforms "
            "and data centers), software (AI applications and platforms), and adoption (enterprise "
            "and consumer deployment). Each bar shows the segment\u2019s estimated index value at 2030 "
            "under the point forecast (median of the ensemble)."
        )
    else:
        display_name = SEGMENT_DISPLAY.get(segment, segment)
        bar_heading = f"{display_name} \u2014 Annual Index Over Time"
        bar_subtitle = (
            f"Year-by-year forecast index values for the {display_name} segment from 2010 to 2030. "
            "This view shows the full trajectory \u2014 both the historical record and the projected path \u2014 "
            "in bar form, complementing the fan chart\u2019s uncertainty bands with a clearer reading of "
            "absolute index levels per year."
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
            "Sources: World Bank Open Data, OECD.Stat, LSEG Workspace",
            style=ATTRIBUTION_STYLE,
        ),
    ], style=_CARD_STYLE)

    # --- Expert mode: model parameters panel ---
    sections = [headline, fan_section]

    if expert:
        # Show raw data points, ensemble parameters, forecast origin year
        from src.dashboard.app import RESIDUALS_DF
        import numpy as np

        # Compute per-segment RMSE for the expert panel
        rmse_rows = []
        for seg in SEGMENTS:
            grp = RESIDUALS_DF[RESIDUALS_DF["segment"] == seg]
            if len(grp) > 0:
                rmse_val = float(np.sqrt(np.mean(grp["residual"].to_numpy() ** 2)))
                rmse_rows.append(html.Tr([
                    html.Td(SEGMENT_DISPLAY.get(seg, seg), style={"padding": "6px 12px", "fontSize": "13px", "fontWeight": 500}),
                    html.Td(f"{rmse_val:.4f}", style={"padding": "6px 12px", "fontSize": "13px", "fontFamily": "monospace"}),
                ]))

        expert_card = html.Div([
            html.H2(
                "Expert View \u2014 Model Parameters & Data",
                style={**_SECTION_HEADING_STYLE, "color": "#7C4DFF"},
            ),
            html.P(
                "This panel is visible in Expert mode only. It surfaces the underlying model parameters, "
                "raw numerical outputs, and methodology references for technical reviewers.",
                style=_SECTION_SUBTITLE_STYLE,
            ),
            # Forecast ensemble config
            dbc.Row([
                dbc.Col([
                    html.H4("Ensemble Composition", style={"fontSize": "14px", "fontWeight": 600, "marginBottom": "8px"}),
                    html.Ul([
                        html.Li("Models: ARIMA (pmdarima auto_arima, AICc criterion) + Prophet (Facebook Prophet 1.1)", style={"fontSize": "13px"}),
                        html.Li("Ensemble: equal-weight average of ARIMA and Prophet point estimates", style={"fontSize": "13px"}),
                        html.Li("CI bands: bootstrap-derived from model residuals (500 draws)", style={"fontSize": "13px"}),
                        html.Li("ARIMA order constraints: max_p=2, max_q=2, seasonal=False", style={"fontSize": "13px"}),
                        html.Li("Prophet: changepoint at 2022-01-01, changepoint_prior_scale=0.1", style={"fontSize": "13px"}),
                    ], style={"paddingLeft": "20px", "marginBottom": "0"}),
                ], width=6),
                dbc.Col([
                    html.H4("Out-of-Sample RMSE by Segment", style={"fontSize": "14px", "fontWeight": 600, "marginBottom": "8px"}),
                    html.Table(
                        [
                            html.Thead(html.Tr([
                                html.Th("Segment", style={"padding": "6px 12px", "fontSize": "13px", "backgroundColor": "#F4F6FA"}),
                                html.Th("RMSE (index units)", style={"padding": "6px 12px", "fontSize": "13px", "backgroundColor": "#F4F6FA"}),
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
                " for all modeling assumptions, their rationale, and what-if analysis. "
                "Key assumptions: (1) structural break at 2022 (GenAI surge) explicitly modeled; "
                "(2) ~15 training observations per segment \u2014 AICc small-sample correction applied; "
                "(3) segments modeled independently with post-hoc aggregation; "
                "(4) PCA first PC of 6 proxy indicators = AI market activity index.",
            ], style={"fontSize": "13px", "color": "#444", "lineHeight": "1.6", "marginBottom": "0"}),
        ], style={
            **_CARD_STYLE,
            "border": "1px solid #C5B0FF",
            "borderLeft": "4px solid #7C4DFF",
        })
        sections.append(expert_card)

    sections.append(bar_section)
    return html.Div(sections, style={"paddingTop": "8px"})


def _build_segment_bar(segment: str, usd_col: str) -> go.Figure:
    """Build a bar chart for segment breakdown or time-series for a single segment."""
    if segment == "all":
        # Grouped bar: all 4 segments' 2030 forecast values
        df_2030 = FORECASTS_DF[FORECASTS_DF["year"] == 2030]
        labels = [SEGMENT_DISPLAY.get(s, s) for s in SEGMENTS]
        values = [
            float(df_2030.loc[df_2030["segment"] == s, usd_col].iloc[0])
            if len(df_2030[df_2030["segment"] == s]) > 0 else 0.0
            for s in SEGMENTS
        ]
        fig = go.Figure(
            go.Bar(
                x=labels,
                y=values,
                marker_color=COLOR_DEEP_BLUE,
                hovertemplate="<b>%{x}</b><br>Index: %{y:.2f}<extra></extra>",
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
                title=dict(text="Forecast Index (2030)", font=dict(size=12)),
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
                y=seg_df[usd_col],
                marker_color=colors,
                hovertemplate="<b>%{x}</b><br>Index: %{y:.2f}<extra></extra>",
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
                title=dict(text="Forecast Index", font=dict(size=12)),
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
