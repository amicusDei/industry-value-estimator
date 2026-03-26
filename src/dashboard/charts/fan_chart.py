"""
Fan chart builder for AI industry forecast visualization.

Produces a Plotly figure with:
- 95% CI band
- 80% CI band
- Historical solid line
- Forecast dashed line (bridged from last historical point)
- Vertical forecast boundary line
- Shaded forecast region

In normal mode (usd_mode=True), all axes show USD billions (real 2020).
In expert mode (usd_mode=False), real 2020 USD is shown using the provided usd_col.
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


def _fmt_usd_hover(val: float) -> str:
    """Format a USD billions value for hover labels."""
    if val >= 1000:
        return f"${val / 1000:.2f}T"
    return f"${val:.1f}B"


def make_fan_chart(
    df: pd.DataFrame,
    segment: str,
    usd_col: str,
    usd_mode: bool = False,
) -> go.Figure:
    """
    Build a fan chart figure for a given segment.

    Parameters
    ----------
    df : pd.DataFrame
        Full forecasts DataFrame (forecasts_ensemble.parquet schema),
        must include point_estimate_real_2020/ci80_lower/ci80_upper/ci95_lower/ci95_upper
        columns if usd_mode=True.
    segment : str
        Segment ID (e.g. "ai_software") or "all" to aggregate all segments.
    usd_col : str
        Column name for the point line. Either "point_estimate_real_2020" or
        "point_estimate_nominal". Used for both usd_mode=True and usd_mode=False.
    usd_mode : bool
        If True, plot real 2020 USD columns with USD billion labels.
        If False, plot the provided usd_col with USD billion labels.

    Returns
    -------
    go.Figure
        Plotly figure with 4+ traces and forecast boundary annotations.
    """
    # Select real or nominal columns based on mode
    if usd_col == "point_estimate_nominal" or usd_mode:
        point_col = "point_estimate_nominal"
        ci80_lower_col = "ci80_lower_nominal" if "ci80_lower_nominal" in df.columns else "ci80_lower"
        ci80_upper_col = "ci80_upper_nominal" if "ci80_upper_nominal" in df.columns else "ci80_upper"
        ci95_lower_col = "ci95_lower_nominal" if "ci95_lower_nominal" in df.columns else "ci95_lower"
        ci95_upper_col = "ci95_upper_nominal" if "ci95_upper_nominal" in df.columns else "ci95_upper"
    else:
        point_col = "point_estimate_real_2020"
        ci80_lower_col = "ci80_lower"
        ci80_upper_col = "ci80_upper"
        ci95_lower_col = "ci95_lower"
        ci95_upper_col = "ci95_upper"

    # --- Aggregate or filter ---
    if segment == "all":
        agg_cols = {
            point_col: "sum",
            ci80_lower_col: "sum",
            ci80_upper_col: "sum",
            ci95_lower_col: "sum",
            ci95_upper_col: "sum",
            "is_forecast": "any",
        }
        # Avoid duplicate keys if point_col overlaps with ci cols (shouldn't happen)
        agg = (
            df.groupby("year", as_index=False)
            .agg(agg_cols)
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

    # Build hover template based on mode — always include units
    if usd_mode:
        hover_tpl = "<b>%{x}</b><br>$%{y:.1f}B<extra></extra>"
    else:
        hover_tpl = "<b>%{x}</b><br>%{y:.2f} (Real 2020 USD B)<extra></extra>"

    # --- 95% CI band (toself fill) — zorder=1 keeps fills behind lines ---
    if len(fore) > 0:
        x_ci = list(fore["year"]) + list(fore["year"][::-1])
        y_ci95 = list(fore[ci95_upper_col]) + list(fore[ci95_lower_col][::-1])
        fig.add_trace(
            go.Scatter(
                x=x_ci,
                y=y_ci95,
                fill="toself",
                fillcolor=CI95_FILL,
                line=dict(color="rgba(0,0,0,0)", width=0),
                hoverinfo="skip",
                showlegend=True,
                legendrank=3,
                zorder=1,
                name="95% CI",
            )
        )

        # --- 80% CI band ---
        y_ci80 = list(fore[ci80_upper_col]) + list(fore[ci80_lower_col][::-1])
        fig.add_trace(
            go.Scatter(
                x=x_ci,
                y=y_ci80,
                fill="toself",
                fillcolor=CI80_FILL,
                line=dict(color="rgba(0,0,0,0)", width=0),
                hoverinfo="skip",
                showlegend=True,
                legendrank=2,
                zorder=2,
                name="80% CI",
            )
        )

    # --- Historical line — zorder=4 renders on top of CI fills ---
    if len(hist) > 0:
        fig.add_trace(
            go.Scatter(
                x=hist["year"],
                y=hist[point_col],
                mode="lines",
                line=dict(color=COLOR_DEEP_BLUE, width=2.5),
                name="Historical",
                legendrank=1,
                zorder=4,
                hovertemplate=hover_tpl,
            )
        )

    # --- Forecast line (bridged from last historical point) — zorder=5 on top ---
    if len(fore) > 0:
        if len(hist) > 0:
            # Bridge: include last historical point as first forecast point
            bridge_x = [int(hist["year"].iloc[-1])] + list(fore["year"])
            bridge_y = [float(hist[point_col].iloc[-1])] + list(fore[point_col])
        else:
            bridge_x = list(fore["year"])
            bridge_y = list(fore[point_col])

        fig.add_trace(
            go.Scatter(
                x=bridge_x,
                y=bridge_y,
                mode="lines+markers",
                marker=dict(size=5, color=COLOR_DEEP_BLUE),
                line=dict(color=COLOR_DEEP_BLUE, width=2.5, dash="dash"),
                name="Forecast",
                legendrank=0,
                zorder=5,
                hovertemplate=hover_tpl,
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
    if usd_mode:
        y_label = "USD Billions (2020 constant)"
    elif usd_col == "point_estimate_nominal":
        y_label = "USD Billions (Nominal)"
    else:
        y_label = "USD Billions (Real 2020)"

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
        xaxis=dict(
            title=dict(text="Year", font=dict(size=12)),
            gridcolor=COLOR_AXES,
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            title=dict(text=y_label, font=dict(size=12)),
            gridcolor=COLOR_AXES,
            tickfont=dict(size=11),
        ),
        margin=dict(l=70, r=40, t=60, b=60),
    )

    return fig
