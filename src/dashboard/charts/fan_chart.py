"""
Fan chart builder for AI industry forecast visualization.

Produces a Plotly figure with:
- 95% CI band
- 80% CI band
- Historical solid line
- Forecast dashed line (bridged from last historical point)
- Vertical forecast boundary line
- Shaded forecast region
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .styles import (
    COLOR_DEEP_BLUE,
    COLOR_AXES,
    CI95_FILL,
    CI80_FILL,
    FORECAST_BOUNDARY_COLOR,
)


def make_fan_chart(df: pd.DataFrame, segment: str, usd_col: str) -> go.Figure:
    """
    Build a fan chart figure for a given segment.

    Parameters
    ----------
    df : pd.DataFrame
        Full forecasts DataFrame (forecasts_ensemble.parquet schema).
    segment : str
        Segment ID (e.g. "ai_software") or "all" to aggregate all segments.
    usd_col : str
        Column name for the point line. Either "point_estimate_real_2020" or
        "point_estimate_nominal". CI bands always use real 2020 USD columns.

    Returns
    -------
    go.Figure
        Plotly figure with 4+ traces and forecast boundary annotations.
    """
    # --- Aggregate or filter ---
    if segment == "all":
        agg = (
            df.groupby("year", as_index=False)
            .agg(
                {
                    usd_col: "sum",
                    "point_estimate_real_2020": "sum",
                    "point_estimate_nominal": "sum",
                    "ci80_lower": "sum",
                    "ci80_upper": "sum",
                    "ci95_lower": "sum",
                    "ci95_upper": "sum",
                    "is_forecast": "any",
                }
            )
            .sort_values("year")
            .reset_index(drop=True)
        )
        plot_df = agg
    else:
        plot_df = df[df["segment"] == segment].sort_values("year").reset_index(drop=True)

    # Split into historical and forecast
    hist = plot_df[plot_df["is_forecast"] == False].copy()  # noqa: E712
    fore = plot_df[plot_df["is_forecast"] == True].copy()   # noqa: E712

    # Forecast origin = last historical year
    forecast_origin = int(hist["year"].max()) if len(hist) > 0 else int(plot_df["year"].min())
    max_year = int(plot_df["year"].max())

    fig = go.Figure()

    # --- 95% CI band (toself fill) ---
    if len(fore) > 0:
        x_ci = list(fore["year"]) + list(fore["year"][::-1])
        y_ci95 = list(fore["ci95_upper"]) + list(fore["ci95_lower"][::-1])
        fig.add_trace(
            go.Scatter(
                x=x_ci,
                y=y_ci95,
                fill="toself",
                fillcolor=CI95_FILL,
                line=dict(color="rgba(0,0,0,0)", width=0),
                hoverinfo="skip",
                showlegend=False,
                name="95% CI",
            )
        )

        # --- 80% CI band ---
        y_ci80 = list(fore["ci80_upper"]) + list(fore["ci80_lower"][::-1])
        fig.add_trace(
            go.Scatter(
                x=x_ci,
                y=y_ci80,
                fill="toself",
                fillcolor=CI80_FILL,
                line=dict(color="rgba(0,0,0,0)", width=0),
                hoverinfo="skip",
                showlegend=False,
                name="80% CI",
            )
        )

    # --- Historical line ---
    if len(hist) > 0:
        fig.add_trace(
            go.Scatter(
                x=hist["year"],
                y=hist[usd_col],
                mode="lines",
                line=dict(color=COLOR_DEEP_BLUE, width=2),
                name="Historical",
                hovertemplate="<b>%{x}</b><br>%{y:.2f}<extra></extra>",
            )
        )

    # --- Forecast line (bridged from last historical point) ---
    if len(fore) > 0:
        if len(hist) > 0:
            # Bridge: include last historical point as first forecast point
            bridge_x = [int(hist["year"].iloc[-1])] + list(fore["year"])
            bridge_y = [float(hist[usd_col].iloc[-1])] + list(fore[usd_col])
        else:
            bridge_x = list(fore["year"])
            bridge_y = list(fore[usd_col])

        fig.add_trace(
            go.Scatter(
                x=bridge_x,
                y=bridge_y,
                mode="lines",
                line=dict(color=COLOR_DEEP_BLUE, width=2, dash="dash"),
                name="Forecast",
                hovertemplate="<b>%{x}</b><br>%{y:.2f}<extra></extra>",
            )
        )

    # --- Forecast region background ---
    fig.add_vrect(
        x0=forecast_origin,
        x1=max_year,
        fillcolor="rgba(244,246,250,0.6)",
        layer="below",
        line_width=0,
    )

    # --- Forecast boundary vertical line ---
    fig.add_vline(
        x=forecast_origin,
        line_dash="dash",
        line_color=FORECAST_BOUNDARY_COLOR,
        annotation_text="Forecast Start",
        annotation_position="top right",
        annotation_font_size=10,
    )

    # --- Layout ---
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        xaxis=dict(gridcolor=COLOR_AXES),
        yaxis=dict(gridcolor=COLOR_AXES),
        margin=dict(l=60, r=40, t=60, b=40),
    )

    return fig
