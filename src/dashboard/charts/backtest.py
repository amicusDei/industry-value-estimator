"""
Backtest actual-vs-predicted scatter chart builder.

Produces a Plotly scatter chart of actual vs predicted USD values for a given segment,
using only hard actuals (actual_type == 'hard') from backtesting_results.parquet.
Soft/circular rows (circular_flag=True) are never plotted.
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


def make_backtest_chart(backtesting_df: pd.DataFrame, segment: str) -> go.Figure:
    """
    Build an actual-vs-predicted scatter chart for hard actuals only.

    Parameters
    ----------
    backtesting_df : pd.DataFrame
        Backtesting results DataFrame (backtesting_results.parquet schema).
        Required columns: year, segment, actual_usd, predicted_usd, actual_type.
        Filters to actual_type == 'hard' only — soft/circular rows are excluded.
    segment : str
        Segment ID (e.g. "ai_software") or "all" to aggregate across all segments.

    Returns
    -------
    go.Figure
        Plotly figure with scatter trace showing actual vs predicted (hard rows only).
        Includes y=x diagonal reference line for visual calibration assessment.
    """
    # Filter to hard actuals only — never plot soft/circular rows
    hard_df = backtesting_df[backtesting_df["actual_type"] == "hard"].copy()

    if segment == "all":
        plot_df = hard_df.sort_values("year").reset_index(drop=True)
        display_name = "All Segments (Hard Actuals)"
    else:
        plot_df = (
            hard_df[hard_df["segment"] == segment]
            .sort_values("year")
            .reset_index(drop=True)
        )
        display_name = _SEGMENT_DISPLAY.get(segment, segment)

    fig = go.Figure()

    if plot_df.empty:
        # No hard actuals for this segment — show empty chart with message
        fig.add_annotation(
            text="No hard actuals available for this segment",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="#999999"),
        )
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=300,
            margin=dict(l=60, r=40, t=40, b=40),
        )
        return fig

    # Assign color by segment — primary gets deep blue, secondary gets coral
    # For multi-segment "all" view, color by segment
    segments_in_plot = plot_df["segment"].unique() if "segment" in plot_df.columns else [segment]
    color_map = {}
    for i, seg in enumerate(sorted(segments_in_plot)):
        color_map[seg] = COLOR_DEEP_BLUE if i == 0 else COLOR_CORAL

    if segment == "all":
        # One trace per segment for legend clarity
        for seg, seg_df in plot_df.groupby("segment"):
            seg_label = _SEGMENT_DISPLAY.get(seg, seg)
            marker_color = color_map.get(seg, COLOR_DEEP_BLUE)
            fig.add_trace(
                go.Scatter(
                    mode="markers",
                    x=seg_df["actual_usd"],
                    y=seg_df["predicted_usd"],
                    name=seg_label,
                    marker=dict(color=marker_color, size=8),
                    hovertemplate=(
                        f"<b>{seg_label}</b><br>"
                        "Year: %{customdata}<br>"
                        "Actual: $%{x:.1f}B<br>"
                        "Predicted: $%{y:.1f}B<extra></extra>"
                    ),
                    customdata=seg_df["year"],
                )
            )
    else:
        fig.add_trace(
            go.Scatter(
                mode="markers",
                x=plot_df["actual_usd"],
                y=plot_df["predicted_usd"],
                name=display_name,
                marker=dict(color=COLOR_DEEP_BLUE, size=8),
                hovertemplate=(
                    "Year: %{customdata}<br>"
                    "Actual: $%{x:.1f}B<br>"
                    "Predicted: $%{y:.1f}B<extra></extra>"
                ),
                customdata=plot_df["year"],
            )
        )

    # Add y=x diagonal reference line for calibration assessment
    all_vals = list(plot_df["actual_usd"]) + list(plot_df["predicted_usd"])
    if all_vals:
        min_val = min(all_vals)
        max_val = max(all_vals)
        # Add a small margin
        margin = (max_val - min_val) * 0.05 if max_val > min_val else 1.0
        fig.add_shape(
            type="line",
            x0=min_val - margin,
            y0=min_val - margin,
            x1=max_val + margin,
            y1=max_val + margin,
            line=dict(color="#AAAAAA", dash="dash", width=1),
        )

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            title="Actual USD (Billions)",
            gridcolor=COLOR_AXES,
        ),
        yaxis=dict(
            title="Predicted USD (Billions)",
            gridcolor=COLOR_AXES,
        ),
        height=300,
        margin=dict(l=60, r=40, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig
