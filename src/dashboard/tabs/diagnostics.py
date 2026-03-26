"""
Diagnostics tab layout builder.

Shows model validation results from leave-one-out cross-validation and
EDGAR hard actuals. LOO results provide non-circular validation for ALL
segments. EDGAR hard actuals provide independent company-level validation.
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.dashboard.app import BACKTESTING_DF, DIAGNOSTICS, SEGMENTS, SEGMENT_DISPLAY, SOURCE_ATTRIBUTION
from src.dashboard.charts.backtest import make_backtest_chart
from src.dashboard.charts.styles import (
    COLOR_DEEP_BLUE,
    COLOR_CONFIDENCE_GREEN,
    COLOR_CONFIDENCE_AMBER,
    COLOR_CONFIDENCE_RED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_TERTIARY,
    COLOR_TEXT_MUTED,
    COLOR_AXES,
    vintage_footer,
)

_CARD_STYLE = {
    "backgroundColor": "#FFFFFF",
    "borderRadius": "8px",
    "padding": "24px",
    "marginBottom": "24px",
    "boxShadow": "0 1px 4px rgba(0,0,0,0.08)",
    "border": f"1px solid {COLOR_AXES}",
}

_PANEL_HEADING_STYLE = {
    "fontSize": "20px",
    "fontWeight": 600,
    "color": COLOR_TEXT_PRIMARY,
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

_SUBLABEL_STYLE = {
    "fontSize": "12px",
    "color": COLOR_TEXT_MUTED,
    "marginBottom": "4px",
    "marginTop": "0",
}

_MAPE_COLOR = {
    "acceptable": COLOR_CONFIDENCE_GREEN,
    "use_with_caution": COLOR_CONFIDENCE_AMBER,
    "directional_only": COLOR_CONFIDENCE_RED,
    "no_data": "#CCCCCC",
}


def build_diagnostics_layout(segment: str, usd_col: str, mode: str = "normal") -> html.Div:
    """Build the Diagnostics tab with LOO cross-validation and EDGAR validation panels."""

    intro_card = html.Div([
        html.H2("Model Diagnostics", style={
            "fontSize": "20px", "fontWeight": 600, "color": COLOR_TEXT_PRIMARY,
            "marginBottom": "4px", "marginTop": "0",
        }),
        html.P(
            "Model validation via Leave-One-Out (LOO) Cross-Validation \u2014 each year excluded from training, then predicted. "
            "For each year, the model is retrained WITHOUT that year\u2019s data, then predicts it. "
            "This gives non-circular Mean Absolute Percentage Error (MAPE) \u2014 lower is better \u2014 for every segment. "
            "EDGAR filings (NVIDIA) provide additional independent validation.",
            style={"fontSize": "14px", "color": COLOR_TEXT_SECONDARY, "marginBottom": "0", "lineHeight": "1.5"},
        ),
    ], style=_CARD_STYLE)

    display_segments = SEGMENTS if segment == "all" else [segment]

    # --- LOO Cross-Validation Panel (main validation) ---
    loo_items = []
    for seg in display_segments:
        seg_label = SEGMENT_DISPLAY.get(seg, seg)
        diag = DIAGNOSTICS.get(seg, {})
        loo_mape = diag.get("loo_mape")
        loo_label = diag.get("loo_label", "no_data")
        loo_folds = diag.get("loo_folds", 0)
        loo_details = diag.get("loo_details", [])

        color = _MAPE_COLOR.get(loo_label, "#CCCCCC")

        seg_items = [
            html.P(seg_label, style={
                "fontSize": "14px", "fontWeight": 600, "color": COLOR_TEXT_PRIMARY,
                "marginBottom": "2px", "marginTop": "12px",
            }),
        ]

        if loo_mape is not None:
            seg_items.append(
                html.P(f"{loo_mape:.1f}% MAPE \u2014 model predictions are typically within {loo_mape:.0f}% of actual values", style={**_METRIC_VALUE_STYLE, "color": color})
            )
            seg_items.append(
                html.P(f"{loo_folds} evaluation folds", style=_SUBLABEL_STYLE)
            )

            # Show per-year breakdown
            if loo_details and mode == "expert":
                for d in loo_details:
                    yr_color = _MAPE_COLOR.get(
                        "acceptable" if d["mape"] < 15 else "use_with_caution" if d["mape"] < 30 else "directional_only",
                        COLOR_TEXT_MUTED
                    )
                    seg_items.append(
                        html.P(
                            f"  {d['year']}: actual=${d['actual']:.1f}B → predicted=${d['predicted']:.1f}B ({d['mape']:.1f}%)",
                            style={"fontSize": "12px", "color": yr_color, "marginBottom": "2px", "marginLeft": "16px"},
                        )
                    )
        else:
            seg_items.append(
                html.P("No LOO data available", style={**_SUBLABEL_STYLE, "color": "#CCCCCC"})
            )

        loo_items.append(html.Div(seg_items))

    loo_panel = html.Div([
        html.H4("Leave-One-Out (LOO) Cross-Validation", style=_PANEL_HEADING_STYLE),
        html.P(
            "Each year excluded from training, model predicts it. Non-circular: "
            "the model never saw the held-out year during fitting.",
            style={"fontSize": "12px", "color": COLOR_TEXT_TERTIARY, "marginBottom": "12px", "fontStyle": "italic"},
        ),
        html.Div(loo_items),
    ], style=_CARD_STYLE)

    # --- EDGAR Hard Actuals Panel ---
    hard_items = []
    for seg in display_segments:
        seg_label = SEGMENT_DISPLAY.get(seg, seg)
        diag = DIAGNOSTICS.get(seg, {})
        hard_details = diag.get("hard_details", [])

        seg_items = [
            html.P(seg_label, style={
                "fontSize": "14px", "fontWeight": 600, "color": COLOR_TEXT_PRIMARY,
                "marginBottom": "2px", "marginTop": "12px",
            }),
        ]

        if hard_details:
            hard_mape = diag.get("hard_mape")
            hard_label = diag.get("hard_label", "no_data")
            color = _MAPE_COLOR.get(hard_label, "#CCCCCC")

            seg_items.append(
                html.P(f"{hard_mape:.1f}% MAPE [EDGAR filing]", style={**_METRIC_VALUE_STYLE, "color": color})
            )
            for d in hard_details:
                yr_color = _MAPE_COLOR.get(
                    "acceptable" if d["mape"] < 15 else "use_with_caution" if d["mape"] < 30 else "directional_only",
                    COLOR_TEXT_MUTED
                )
                seg_items.append(
                    html.P(
                        f"  {d['year']}: NVIDIA=${d['actual']:.1f}B → model=${d['predicted']:.1f}B ({d['mape']:.1f}%)",
                        style={"fontSize": "12px", "color": yr_color, "marginBottom": "2px", "marginLeft": "16px"},
                    )
                )
        else:
            seg_items.append(
                html.P("No EDGAR hard actuals for this segment", style=_SUBLABEL_STYLE)
            )

        hard_items.append(html.Div(seg_items))

    # Scatter chart
    backtest_fig = make_backtest_chart(BACKTESTING_DF, segment if segment != "all" else "all")

    hard_panel = html.Div([
        html.H4("Independent Validation (EDGAR filings)", style=_PANEL_HEADING_STYLE),
        html.P(
            "Company-level revenue from SEC 10-K filings compared to model segment predictions. "
            "Currently NVIDIA only (representative of AI hardware).",
            style={"fontSize": "12px", "color": COLOR_TEXT_TERTIARY, "marginBottom": "12px", "fontStyle": "italic"},
        ),
        html.Div(hard_items),
        html.Hr(style={"borderColor": COLOR_AXES, "marginTop": "16px", "marginBottom": "12px"}),
        dcc.Loading(
            type="circle", color=COLOR_DEEP_BLUE,
            children=dcc.Graph(figure=backtest_fig, id="diagnostics-backtest-chart", config={"displayModeBar": True}),
        ),
    ], style=_CARD_STYLE)

    panels_row = dbc.Row([
        dbc.Col(loo_panel, width=6),
        dbc.Col(hard_panel, width=6),
    ])

    # --- Model Limitations Panel ---
    limitations_card = html.Div([
        html.H4("Model Limitations", style={**_PANEL_HEADING_STYLE, "color": COLOR_CONFIDENCE_RED}),
        html.Ul([
            html.Li(
                "AI Infrastructure (51% MAPE) and AI Software (42% MAPE) forecasts are "
                "directional only -- not suitable for precise valuation.",
                style={"fontSize": "13px", "color": COLOR_TEXT_SECONDARY, "marginBottom": "8px", "lineHeight": "1.5"},
            ),
            html.Li(
                "Model trained on 9 data points per segment (2017-2025), including "
                "interpolated values derived from analyst consensus estimates.",
                style={"fontSize": "13px", "color": COLOR_TEXT_SECONDARY, "marginBottom": "8px", "lineHeight": "1.5"},
            ),
            html.Li(
                "CAGR floors prevent the model from forecasting market contraction -- "
                "structural growth is assumed based on analyst consensus.",
                style={"fontSize": "13px", "color": COLOR_TEXT_SECONDARY, "marginBottom": "8px", "lineHeight": "1.5"},
            ),
            html.Li(
                "No model drift monitoring -- re-validate if market structure changes "
                "(e.g., regulatory shifts, new dominant players, demand shocks).",
                style={"fontSize": "13px", "color": COLOR_TEXT_SECONDARY, "marginBottom": "8px", "lineHeight": "1.5"},
            ),
        ], style={"paddingLeft": "20px", "marginBottom": "0"}),
    ], style=_CARD_STYLE)

    footer = vintage_footer("EDGAR filings 2024 | LOO cross-validation on analyst estimates", "")

    return html.Div([intro_card, panels_row, limitations_card, footer], style={"paddingTop": "8px"})
