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
    ATTRIBUTION_STYLE,
)


def build_overview_layout(segment: str, usd_col: str) -> html.Div:
    """
    Build the Overview tab layout.

    Parameters
    ----------
    segment : str
        Segment ID or "all" to aggregate all segments.
    usd_col : str
        Column name for point line. Either "point_estimate_real_2020" or
        "point_estimate_nominal".

    Returns
    -------
    html.Div
        Dash component tree for the Overview tab.
    """
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

    headline = html.Div([
        html.P(
            headline_text,
            style={
                "fontSize": "36px",
                "fontWeight": 600,
                "color": COLOR_DEEP_BLUE,
                "marginBottom": "4px",
            },
        ),
        html.P(
            "2030 composite forecast index \u00b7 80% and 95% confidence intervals shown",
            style={"fontSize": "12px", "color": "#888", "marginTop": "0"},
        ),
    ], style={"marginBottom": "24px"})

    # --- Fan chart ---
    fan_fig = make_fan_chart(FORECASTS_DF, segment, usd_col)
    fan_section = html.Div([
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
    ], style={"marginBottom": "32px"})

    # --- Segment breakdown bar chart ---
    bar_fig = _build_segment_bar(segment, usd_col)
    bar_section = html.Div([
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
    ])

    return html.Div([headline, fan_section, bar_section])


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
            title="2030 Forecast Index by Segment",
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(title="Segment", gridcolor="#E8EBF0"),
            yaxis=dict(title="Forecast Index", gridcolor="#E8EBF0"),
            margin=dict(l=60, r=40, t=60, b=80),
        )
    else:
        # Time-series bar for the selected segment
        seg_df = (
            FORECASTS_DF[FORECASTS_DF["segment"] == segment]
            .sort_values("year")
            .reset_index(drop=True)
        )
        fig = go.Figure(
            go.Bar(
                x=seg_df["year"],
                y=seg_df[usd_col],
                marker_color=COLOR_DEEP_BLUE,
                hovertemplate="<b>%{x}</b><br>Index: %{y:.2f}<extra></extra>",
            )
        )
        display_name = SEGMENT_DISPLAY.get(segment, segment)
        fig.update_layout(
            title=f"{display_name} — Forecast Index Over Time",
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(title="Year", gridcolor="#E8EBF0"),
            yaxis=dict(title="Forecast Index", gridcolor="#E8EBF0"),
            margin=dict(l=60, r=40, t=60, b=40),
        )

    return fig
