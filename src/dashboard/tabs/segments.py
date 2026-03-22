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
    if segment == "all":
        # 2x2 grid showing all 4 segments
        seg_pairs = [SEGMENTS[i:i + 2] for i in range(0, len(SEGMENTS), 2)]
        rows = []
        for pair in seg_pairs:
            cols = []
            for seg in pair:
                fig = make_fan_chart(FORECASTS_DF, seg, usd_col)
                display_name = SEGMENT_DISPLAY.get(seg, seg)
                col = dbc.Col([
                    html.H5(display_name, style={"fontSize": "16px", "fontWeight": 600, "marginBottom": "4px"}),
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
                ], width=6)
                cols.append(col)
            rows.append(dbc.Row(cols, style={"marginBottom": "24px"}))
        return html.Div(rows)
    else:
        # Single segment full-width
        fig = make_fan_chart(FORECASTS_DF, segment, usd_col)
        display_name = SEGMENT_DISPLAY.get(segment, segment)
        return html.Div([
            html.H5(display_name, style={"fontSize": "16px", "fontWeight": 600, "marginBottom": "4px"}),
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
        ])
