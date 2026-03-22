"""
Backtest residuals chart builder.

Produces a Plotly bar chart of residuals by year for a given segment.
Only the 'residual' column is available in residuals_statistical.parquet —
no actual/predicted values exist, so this is a residual distribution chart.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .styles import COLOR_DEEP_BLUE, COLOR_CORAL, COLOR_AXES

# Map segment IDs to human-readable display names
_SEGMENT_DISPLAY = {
    "ai_hardware": "AI Hardware",
    "ai_infrastructure": "AI Infrastructure",
    "ai_software": "AI Software & Platforms",
    "ai_adoption": "AI Adoption",
}


def make_backtest_chart(residuals_df: pd.DataFrame, segment: str) -> go.Figure:
    """
    Build a residuals-by-year bar chart for a given segment.

    Parameters
    ----------
    residuals_df : pd.DataFrame
        Residuals DataFrame (residuals_statistical.parquet schema).
        Required columns: year, segment, residual.
    segment : str
        Segment ID (e.g. "ai_software") or "all" to aggregate across all segments.

    Returns
    -------
    go.Figure
        Plotly figure with bar trace showing residuals per year.
    """
    if segment == "all":
        plot_df = (
            residuals_df.groupby("year", as_index=False)["residual"]
            .sum()
            .sort_values("year")
            .reset_index(drop=True)
        )
        display_name = "All Segments"
    else:
        plot_df = (
            residuals_df[residuals_df["segment"] == segment]
            .sort_values("year")
            .reset_index(drop=True)
        )
        display_name = _SEGMENT_DISPLAY.get(segment, segment)

    # Color bars: positive = deep blue, negative = coral
    colors = [
        COLOR_DEEP_BLUE if v >= 0 else COLOR_CORAL
        for v in plot_df["residual"]
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=plot_df["year"],
            y=plot_df["residual"],
            marker_color=colors,
            name="Residual",
            hovertemplate="<b>%{x}</b><br>Residual: %{y:.4f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=f"Residuals by Year \u2014 {display_name}",
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(gridcolor=COLOR_AXES, title="Year"),
        yaxis=dict(gridcolor=COLOR_AXES, title="Residual"),
        margin=dict(l=60, r=40, t=60, b=40),
    )

    return fig
