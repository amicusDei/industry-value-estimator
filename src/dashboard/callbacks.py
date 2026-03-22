"""
Dash callback wiring for the AI Industry Value Estimator dashboard.

Registers a single callback that renders the appropriate tab content
based on the active tab and global control values.
"""
from __future__ import annotations

from dash import Input, Output, callback

from src.dashboard.tabs.overview import build_overview_layout
from src.dashboard.tabs.segments import build_segments_layout
from src.dashboard.tabs.drivers import build_drivers_layout
from src.dashboard.tabs.diagnostics import build_diagnostics_layout


@callback(
    Output("tab-content", "children"),
    Input("main-tabs", "value"),
    Input("segment-dropdown", "value"),
    Input("usd-toggle", "value"),
    Input("mode-toggle", "value"),
)
def render_tab(active_tab: str, segment: str, usd_col: str, mode: str):
    """
    Render the content area for the currently active tab.

    Parameters
    ----------
    active_tab : str
        Currently selected tab value ("overview", "segments", "drivers", "diagnostics").
    segment : str
        Global segment filter value ("all" or segment ID).
    usd_col : str
        USD column toggle value ("point_estimate_real_2020" or "point_estimate_nominal").
    mode : str
        Display mode ("normal" for narrative view, "expert" for technical detail view).

    Returns
    -------
    dash component
        Layout component tree for the selected tab.
    """
    mode = mode or "normal"
    if active_tab == "overview":
        return build_overview_layout(segment, usd_col, mode)
    elif active_tab == "segments":
        return build_segments_layout(segment, usd_col, mode)
    elif active_tab == "drivers":
        return build_drivers_layout(segment, usd_col, mode)
    elif active_tab == "diagnostics":
        return build_diagnostics_layout(segment, usd_col, mode)
    return build_overview_layout(segment, usd_col, mode)
