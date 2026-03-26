"""
Diagnostics tab layout builder.

Shows split Hard/Soft backtesting panels with real MAPE and R² from
backtesting_results.parquet. Hard panel shows EDGAR actuals with explicit
[out-of-sample] labels. Soft panel shows circular_flag warning and explains
0% MAPE. Includes actual-vs-predicted scatter for hard rows only.
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.dashboard.app import BACKTESTING_DF, DIAGNOSTICS, SEGMENTS, SEGMENT_DISPLAY, SOURCE_ATTRIBUTION

_ATTRIBUTION_TEXT = "Sources: " + ", ".join(SOURCE_ATTRIBUTION.values())
from src.dashboard.charts.backtest import make_backtest_chart
from src.dashboard.charts.styles import (
    COLOR_DEEP_BLUE,
    ATTRIBUTION_STYLE,
    vintage_footer,
)

_CARD_STYLE = {
    "backgroundColor": "#FFFFFF",
    "borderRadius": "8px",
    "padding": "24px",
    "marginBottom": "24px",
    "boxShadow": "0 1px 4px rgba(0,0,0,0.08)",
    "border": "1px solid #E8EBF0",
}

_PANEL_HEADING_STYLE = {
    "fontSize": "20px",
    "fontWeight": 600,
    "color": "#1A1A2E",
    "marginBottom": "12px",
    "marginTop": "0",
}

_METRIC_VALUE_STYLE = {
    "fontSize": "16px",
    "fontWeight": 600,
    "color": COLOR_DEEP_BLUE,
    "marginBottom": "4px",
    "marginTop": "0",
}

_CAVEAT_STYLE = {
    "fontSize": "12px",
    "color": "#999999",
    "marginBottom": "8px",
    "marginTop": "0",
    "fontStyle": "italic",
}

_SUBLABEL_STYLE = {
    "fontSize": "12px",
    "color": "#999999",
    "marginBottom": "4px",
    "marginTop": "0",
}


def build_diagnostics_layout(segment: str, usd_col: str, mode: str = "normal") -> html.Div:
    """
    Build the Diagnostics tab layout with split Hard/Soft backtesting panels.

    Parameters
    ----------
    segment : str
        Segment ID or "all" to show diagnostics for all segments.
    usd_col : str
        USD column toggle (not used for diagnostics display).
    mode : str
        "normal" for narrative view, "expert" for technical detail view with formulas.

    Returns
    -------
    html.Div
        Dash component tree for the Diagnostics tab.
    """
    # --- Intro heading ---
    intro_card = html.Div([
        html.H2("Model Diagnostics", style={
            "fontSize": "20px",
            "fontWeight": 600,
            "color": "#1A1A2E",
            "marginBottom": "4px",
            "marginTop": "0",
        }),
        html.P(
            "Out-of-sample model validation via walk-forward cross-validation. "
            "Hard actuals come from EDGAR filings (NVIDIA, Palantir, C3.ai) — true "
            "out-of-sample data the model never trained on. Soft actuals are analyst "
            "consensus estimates used as pseudo-actuals during training — circular validation.",
            style={
                "fontSize": "14px",
                "color": "#666",
                "marginBottom": "0",
                "marginTop": "0",
                "lineHeight": "1.5",
            },
        ),
    ], style=_CARD_STYLE)

    # --- Determine which segments to display ---
    if segment == "all":
        display_segments = SEGMENTS
    else:
        display_segments = [segment]

    # --- Build Hard Panel (EDGAR actuals) ---
    hard_rows_global = BACKTESTING_DF[BACKTESTING_DF["actual_type"] == "hard"]

    hard_metrics_items = []
    for seg in display_segments:
        seg_hard = hard_rows_global[hard_rows_global["segment"] == seg]
        seg_label = SEGMENT_DISPLAY.get(seg, seg)
        diag = DIAGNOSTICS.get(seg, {})

        if seg_hard.empty or not diag.get("has_hard_actuals", False):
            hard_metrics_items.append(
                html.Div([
                    html.P(f"{seg_label}", style={
                        "fontSize": "14px",
                        "fontWeight": 600,
                        "color": "#1A1A2E",
                        "marginBottom": "2px",
                        "marginTop": "8px",
                    }),
                    html.P("No hard actuals available", style=_SUBLABEL_STYLE),
                ])
            )
        else:
            mape = diag.get("mape")
            r2 = diag.get("r2")

            mape_text = f"{mape:.1f}% MAPE [out-of-sample]" if mape is not None else "MAPE unavailable"
            r2_text = f"R\u00b2 = {r2:.3f} [out-of-sample]" if r2 is not None else None

            seg_items = [
                html.P(f"{seg_label}", style={
                    "fontSize": "14px",
                    "fontWeight": 600,
                    "color": "#1A1A2E",
                    "marginBottom": "2px",
                    "marginTop": "8px",
                }),
                html.P(mape_text, style=_METRIC_VALUE_STYLE),
            ]

            if r2_text:
                seg_items.append(html.P(r2_text, style=_SUBLABEL_STYLE))

            # ai_software caveat: C3.ai revenue only vs full segment
            if seg == "ai_software":
                seg_items.append(
                    html.P(
                        "* C3.ai revenue only vs. full AI software segment — directional signal, not segment MAPE",
                        style=_CAVEAT_STYLE,
                    )
                )

            hard_metrics_items.append(html.Div(seg_items))

    # Actual vs predicted scatter chart (hard rows only)
    # Use first displayed segment or "all"
    chart_segment = segment if segment != "all" else "all"
    backtest_fig = make_backtest_chart(BACKTESTING_DF, chart_segment)

    hard_panel = html.Div([
        html.H4("Validated (EDGAR actuals)", style=_PANEL_HEADING_STYLE),
        html.Div(hard_metrics_items),
        html.Hr(style={"borderColor": "#E8EBF0", "marginTop": "16px", "marginBottom": "12px"}),
        dcc.Loading(
            type="circle",
            color=COLOR_DEEP_BLUE,
            children=dcc.Graph(
                figure=backtest_fig,
                id="diagnostics-backtest-chart",
                config={"displayModeBar": True},
            ),
        ),
    ], style=_CARD_STYLE)

    # --- Build Soft Panel (analyst consensus — circular) ---
    soft_rows_global = BACKTESTING_DF[BACKTESTING_DF["actual_type"] == "soft"]

    soft_metrics_items = []
    for seg in display_segments:
        seg_soft = soft_rows_global[soft_rows_global["segment"] == seg]
        seg_label = SEGMENT_DISPLAY.get(seg, seg)

        if not seg_soft.empty:
            soft_mape = float(seg_soft["mape"].mean()) if seg_soft["mape"].notna().any() else 0.0
            soft_metrics_items.append(
                html.Div([
                    html.P(f"{seg_label}", style={
                        "fontSize": "14px",
                        "fontWeight": 600,
                        "color": "#1A1A2E",
                        "marginBottom": "2px",
                        "marginTop": "8px",
                    }),
                    html.P(
                        f"{soft_mape:.1f}% MAPE [circular_not_validated]",
                        style={**_METRIC_VALUE_STYLE, "color": "#F39C12"},
                    ),
                ])
            )

    soft_panel = html.Div([
        html.H4("Cross-checked (analyst consensus)", style=_PANEL_HEADING_STYLE),
        # Circular flag warning badge
        html.Div([
            html.Span("\u26a0 circular_flag = True", style={
                "fontSize": "13px",
                "fontWeight": 600,
                "color": "#856404",
            }),
        ], style={
            "backgroundColor": "#FEF3CD",
            "border": "1px solid #F39C12",
            "borderRadius": "4px",
            "padding": "8px 16px",
            "marginBottom": "12px",
        }),
        html.P(
            "MAPE = 0% reflects model trained on these estimates — not true out-of-sample validation",
            style=_CAVEAT_STYLE,
        ),
        html.Div(soft_metrics_items),
        html.Hr(style={"borderColor": "#E8EBF0", "marginTop": "16px", "marginBottom": "12px"}),
        html.P(
            "No scatter chart for analyst consensus panel — circular data not meaningful to plot. "
            "The model was trained on these estimates, so apparent fit reflects training, not validation.",
            style={
                "fontSize": "13px",
                "color": "#888888",
                "lineHeight": "1.5",
                "marginBottom": "0",
                "fontStyle": "italic",
            },
        ),
    ], style=_CARD_STYLE)

    # --- Split layout row ---
    panels_row = dbc.Row([
        dbc.Col(hard_panel, width=6),
        dbc.Col(soft_panel, width=6),
    ])

    # --- Vintage footer ---
    footer = vintage_footer(
        "EDGAR filings 2024 | Backtesting via walk-forward CV",
        "",
    )

    sections = [intro_card, panels_row, footer]

    return html.Div(sections, style={"paddingTop": "8px"})
