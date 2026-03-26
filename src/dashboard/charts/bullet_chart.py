"""
Analyst consensus bullet chart component.

Renders a horizontal bullet chart where each row is a market segment:
- Grey band shows the analyst p25-p75 consensus range
- Colored diamond marker shows the model point estimate

Marker color:
    Green (#2ECC71) — model estimate is inside the p25-p75 consensus range
    Amber (#F39C12) — model estimate is outside the p25-p75 consensus range

Only segments with real analyst estimates (estimated_flag == False) are rendered.
Segments without real estimates are silently skipped.

Data sources:
    forecasts_ensemble.parquet: point_estimate_nominal for model point
    market_anchors_ai.parquet: p25/p75/median_usd_billions_nominal for consensus range
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .styles import COLOR_CONFIDENCE_GREEN, COLOR_CONFIDENCE_AMBER


def make_consensus_bullet_chart(
    forecasts_df: pd.DataFrame,
    anchors_df: pd.DataFrame,
    year: int,
    segment_display: dict,
) -> go.Figure:
    """
    Build a horizontal bullet chart showing model estimate vs analyst consensus range.

    Parameters
    ----------
    forecasts_df : pd.DataFrame
        Forecast ensemble DataFrame (forecasts_ensemble.parquet schema).
        Must include: year, segment, point_estimate_nominal.
    anchors_df : pd.DataFrame
        Market anchors DataFrame (market_anchors_ai.parquet schema).
        Must include: estimate_year, segment, estimated_flag,
        p25_usd_billions_nominal, p75_usd_billions_nominal, median_usd_billions_nominal.
    year : int
        Reference year to display (e.g. 2024).
    segment_display : dict
        Mapping from segment ID to display name (e.g. {"ai_hardware": "AI Hardware"}).

    Returns
    -------
    go.Figure
        Plotly figure with overlay bar + scatter marker traces per segment.
    """
    fig = go.Figure()
    segments = list(segment_display.keys())

    # Filter to real (non-estimated) anchors only — Pitfall 3 from RESEARCH.md
    real_anchors = anchors_df[anchors_df["estimated_flag"] == False]  # noqa: E712

    legend_added = False

    for seg in segments:
        model_row = forecasts_df[
            (forecasts_df["year"] == year) & (forecasts_df["segment"] == seg)
        ]
        anchor_row = real_anchors[
            (real_anchors["estimate_year"] == year) & (real_anchors["segment"] == seg)
        ]

        # Skip rows with no data or no real consensus data
        if model_row.empty or anchor_row.empty:
            continue

        model_val = float(model_row["point_estimate_nominal"].iloc[0])
        p25 = float(anchor_row["p25_usd_billions_nominal"].iloc[0])
        p75 = float(anchor_row["p75_usd_billions_nominal"].iloc[0])
        median = float(anchor_row["median_usd_billions_nominal"].iloc[0])

        inside = p25 <= model_val <= p75
        marker_color = COLOR_CONFIDENCE_GREEN if inside else COLOR_CONFIDENCE_AMBER

        show_legend = not legend_added

        # Grey consensus band (p25 to p75 range)
        fig.add_trace(go.Bar(
            x=[p75 - p25],
            y=[segment_display[seg]],
            base=[p25],
            orientation="h",
            marker_color="rgba(180,180,180,0.4)",
            showlegend=show_legend,
            name="Analyst range (p25\u2013p75)",
            hovertemplate=f"Consensus: ${p25:.0f}B\u2013${p75:.0f}B<extra>{segment_display[seg]}</extra>",
        ))

        # Model marker (diamond)
        divergence_pct = (model_val - median) / median * 100 if median > 0 else 0
        if inside:
            tooltip = (
                f"Model: ${model_val:.0f}B vs Consensus: ${p25:.0f}B\u2013${p75:.0f}B"
                " \u2014 within range"
            )
        else:
            tooltip = (
                f"Model: ${model_val:.0f}B vs Consensus: ${p25:.0f}B\u2013${p75:.0f}B"
                f" \u2014 divergence: {divergence_pct:+.1f}%"
            )

        fig.add_trace(go.Scatter(
            x=[model_val],
            y=[segment_display[seg]],
            mode="markers",
            marker=dict(color=marker_color, size=14, symbol="diamond"),
            showlegend=show_legend,
            name="Model estimate",
            hovertemplate=tooltip + "<extra></extra>",
        ))

        legend_added = True

    fig.update_layout(
        barmode="overlay",
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            title="USD Billions (Nominal)",
            gridcolor="#E8EBF0",
        ),
        yaxis=dict(title=None),
        margin=dict(l=160, r=40, t=40, b=40),
        height=220,
    )

    return fig
