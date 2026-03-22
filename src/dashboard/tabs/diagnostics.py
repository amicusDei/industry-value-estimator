"""
Diagnostics tab layout builder.

Shows model diagnostics scorecard table and backtest residuals chart,
with methodology explanations for each metric.
"""
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.dashboard.app import DIAGNOSTICS, RESIDUALS_DF, SEGMENTS, SEGMENT_DISPLAY
from src.dashboard.charts.backtest import make_backtest_chart
from src.dashboard.charts.styles import COLOR_DEEP_BLUE, ATTRIBUTION_STYLE

_CARD_STYLE = {
    "backgroundColor": "#FFFFFF",
    "borderRadius": "8px",
    "padding": "24px",
    "marginBottom": "24px",
    "boxShadow": "0 1px 4px rgba(0,0,0,0.08)",
    "border": "1px solid #E8EBF0",
}

_SECTION_HEADING_STYLE = {
    "fontSize": "20px",
    "fontWeight": 600,
    "color": "#1A1A2E",
    "marginBottom": "4px",
    "marginTop": "0",
}

_SECTION_SUBTITLE_STYLE = {
    "fontSize": "14px",
    "color": "#666",
    "marginBottom": "16px",
    "marginTop": "0",
    "lineHeight": "1.5",
}

_TABLE_CELL_STYLE = {
    "padding": "10px 12px",
    "border": "1px solid #E8EBF0",
    "textAlign": "left",
    "fontSize": "14px",
}

_TABLE_HEADER_STYLE = {
    "padding": "10px 12px",
    "border": "1px solid #E8EBF0",
    "backgroundColor": "#F4F6FA",
    "fontWeight": 600,
    "textAlign": "left",
    "fontSize": "14px",
}

_TABLE_LABEL_STYLE = {
    **_TABLE_CELL_STYLE,
    "fontWeight": 600,
    "backgroundColor": "#FAFBFD",
    "width": "160px",
}

_METRIC_CARD_STYLE = {
    "backgroundColor": "#FAFBFD",
    "borderRadius": "6px",
    "padding": "16px",
    "marginBottom": "12px",
    "border": "1px solid #E8EBF0",
}

# Metric label -> (display name, what it measures, how calculated, what is good)
_METRIC_INFO = {
    "rmse": {
        "label": "RMSE",
        "full_name": "Root Mean Square Error",
        "what": (
            "RMSE measures the average magnitude of forecast errors in the same units as the index. "
            "A value of 0.50 means the model\u2019s predictions were off by 0.50 index points on average "
            "(accounting for direction, with larger errors weighted more heavily via squaring)."
        ),
        "how": (
            "Calculated as the square root of the average squared difference between actual and predicted "
            "values across all out-of-sample CV folds: \u221a(mean((y_actual \u2212 y_predicted)\u00b2)). "
            "Squaring the errors penalises large deviations more than small ones, making RMSE sensitive "
            "to outlier forecasts."
        ),
        "good": "Lower is better. Comparable within a segment across models; not directly comparable across segments of different scale.",
    },
    "mape": {
        "label": "MAPE",
        "full_name": "Mean Absolute Percentage Error",
        "what": (
            "MAPE expresses the average forecast error as a percentage of the actual value, making it "
            "scale-independent. A MAPE of 8.3% means the model\u2019s predictions were off by about 8.3% "
            "of the true value on average across the CV test folds."
        ),
        "how": (
            "Calculated as the mean of |y_actual \u2212 y_predicted| / |y_actual| across all out-of-sample "
            "observations, multiplied by 100 to express as a percentage. MAPE is the primary model "
            "selection criterion in this project \u2014 the model with the lower CV MAPE wins per segment."
        ),
        "good": "Lower is better. Values under 10% are considered good for annual macroeconomic forecasting. Scale-independent, so values are comparable across all four segments.",
    },
    "r2": {
        "label": "R\u00b2",
        "full_name": "Coefficient of Determination",
        "what": (
            "R\u00b2 measures what fraction of the variance in the actual values is explained by the model\u2019s "
            "predictions. An R\u00b2 of 0.92 means the model explains 92% of the variance. R\u00b2 near 1.0 "
            "looks impressive but is inflated by trend in time series \u2014 even a na\u00efve random walk "
            "achieves R\u00b2 > 0.9 on a growing series."
        ),
        "how": (
            "Calculated as 1 \u2212 SS_res/SS_tot, where SS_res is the sum of squared residuals and "
            "SS_tot is the total sum of squares around the mean. Reported here for completeness but "
            "NOT used for model selection \u2014 use MAPE and RMSE instead, as they are honest "
            "out-of-sample metrics less susceptible to trend inflation."
        ),
        "good": "Higher is better on its face, but treat with skepticism for trend time series. RMSE and MAPE are more informative for this use case.",
    },
}


def build_diagnostics_layout(segment: str, usd_col: str) -> html.Div:
    """
    Build the Diagnostics tab layout.

    Parameters
    ----------
    segment : str
        Segment ID or "all" to show diagnostics for all segments.
    usd_col : str
        USD column toggle (not used for diagnostics display).

    Returns
    -------
    html.Div
        Dash component tree for the Diagnostics tab.
    """
    # --- Methodology intro card ---
    methodology_card = html.Div([
        html.H2("Model Diagnostics", style=_SECTION_HEADING_STYLE),
        html.P(
            "These metrics measure how well the models fit out-of-sample data \u2014 not the training data "
            "they were fitted on. All values are computed via expanding-window temporal cross-validation: "
            "the model is trained on years 2010\u20132020 to predict 2021, then 2010\u20132021 to predict "
            "2022, and so on. This mimics real forecasting conditions and prevents the model from "
            "\u2018memorising\u2019 the data it was evaluated on.",
            style=_SECTION_SUBTITLE_STYLE,
        ),
        html.P(
            "Each of the four AI segments has its own model (ARIMA or Prophet \u2014 whichever achieved "
            "lower CV MAPE for that segment). The diagnostics below reflect the winning model per segment.",
            style={"fontSize": "14px", "color": "#666", "lineHeight": "1.5", "marginBottom": "0"},
        ),
    ], style=_CARD_STYLE)

    # --- Metric explanation cards ---
    metric_cards = []
    for metric_key in ["rmse", "mape", "r2"]:
        info = _METRIC_INFO[metric_key]
        metric_cards.append(
            html.Div([
                html.Div([
                    html.Span(info["label"], style={
                        "fontSize": "13px",
                        "fontWeight": 600,
                        "color": COLOR_DEEP_BLUE,
                        "backgroundColor": "rgba(30,90,200,0.08)",
                        "padding": "2px 8px",
                        "borderRadius": "4px",
                        "marginRight": "8px",
                    }),
                    html.Span(info["full_name"], style={
                        "fontSize": "14px",
                        "fontWeight": 600,
                        "color": "#1A1A2E",
                    }),
                ], style={"marginBottom": "8px"}),
                html.P(
                    html.Span([html.Strong("What it measures: "), info["what"]]),
                    style={"fontSize": "13px", "color": "#444", "lineHeight": "1.5", "marginBottom": "4px"},
                ),
                html.P(
                    html.Span([html.Strong("How it\u2019s calculated: "), info["how"]]),
                    style={"fontSize": "13px", "color": "#444", "lineHeight": "1.5", "marginBottom": "4px"},
                ),
                html.P(
                    html.Span([html.Strong("What is good: "), info["good"]]),
                    style={"fontSize": "13px", "color": "#444", "lineHeight": "1.5", "marginBottom": "0"},
                ),
            ], style=_METRIC_CARD_STYLE)
        )

    metric_glossary_card = html.Div([
        html.H3("Metric Glossary", style={
            "fontSize": "16px",
            "fontWeight": 600,
            "color": "#1A1A2E",
            "marginBottom": "12px",
            "marginTop": "0",
        }),
    ] + metric_cards, style=_CARD_STYLE)

    # --- Scorecard table ---
    if segment == "all":
        display_segments = SEGMENTS
    else:
        display_segments = [segment]

    header_cells = [html.Th("Metric", style=_TABLE_HEADER_STYLE)] + [
        html.Th(SEGMENT_DISPLAY.get(s, s), style=_TABLE_HEADER_STYLE)
        for s in display_segments
    ]

    def _fmt(val) -> str:
        if isinstance(val, float):
            return f"{val:.4f}"
        return str(val)

    metric_rows = []
    for metric_key in ["rmse", "mape", "r2"]:
        info = _METRIC_INFO[metric_key]
        cells = [html.Td(
            html.Span([
                html.Strong(info["label"]),
                html.Br(),
                html.Span(info["full_name"], style={"fontSize": "11px", "color": "#888", "fontWeight": 400}),
            ]),
            style=_TABLE_LABEL_STYLE,
        )]
        for seg in display_segments:
            diag = DIAGNOSTICS.get(seg, {})
            cells.append(html.Td(_fmt(diag.get(metric_key, "N/A")), style=_TABLE_CELL_STYLE))
        metric_rows.append(html.Tr(cells))

    scorecard_table = html.Table(
        [html.Thead(html.Tr(header_cells)), html.Tbody(metric_rows)],
        style={"width": "100%", "borderCollapse": "collapse"},
    )

    scorecard_card = html.Div([
        html.H3("Out-of-Sample Fit Scorecard", style={
            "fontSize": "16px",
            "fontWeight": 600,
            "color": "#1A1A2E",
            "marginBottom": "6px",
            "marginTop": "0",
        }),
        html.P(
            "Lower RMSE/MAPE is better. Higher R\u00b2 is better (but treat with caution for trend time series). "
            "All values computed on held-out CV folds \u2014 not in-sample fit.",
            style={"fontSize": "13px", "color": "#666", "marginBottom": "14px"},
        ),
        scorecard_table,
        html.P(
            "Sources: World Bank Open Data, OECD.Stat, LSEG Workspace "
            "\u00b7 Residuals from statistical baseline model",
            style=ATTRIBUTION_STYLE,
        ),
    ], style=_CARD_STYLE)

    # --- Backtest chart ---
    backtest_fig = make_backtest_chart(RESIDUALS_DF, segment)
    backtest_card = html.Div([
        html.H3(
            "Backtesting \u2014 Actual vs. Predicted",
            style={
                "fontSize": "16px",
                "fontWeight": 600,
                "color": "#1A1A2E",
                "marginBottom": "6px",
                "marginTop": "0",
            },
        ),
        html.P(
            "This chart plots the model\u2019s out-of-sample predictions against the actual observed values "
            "for each CV test year. Each point represents one held-out year for one segment. "
            "Points close to the diagonal line (y = x) indicate accurate predictions. Points above the "
            "line mean the model under-predicted; points below mean it over-predicted. "
            "Systematic bias (all points on the same side of the line) would indicate a structural "
            "forecasting error, while random scatter around the line indicates well-calibrated uncertainty.",
            style=_SECTION_SUBTITLE_STYLE,
        ),
        dcc.Loading(
            type="circle",
            color=COLOR_DEEP_BLUE,
            children=dcc.Graph(
                figure=backtest_fig,
                id="diagnostics-backtest-chart",
                config={"displayModeBar": True},
            ),
        ),
        html.P(
            "Sources: World Bank Open Data, OECD.Stat, LSEG Workspace "
            "\u00b7 Backtesting via expanding-window temporal cross-validation",
            style=ATTRIBUTION_STYLE,
        ),
    ], style={**_CARD_STYLE, "marginBottom": "0"})

    return html.Div([
        methodology_card,
        metric_glossary_card,
        scorecard_card,
        backtest_card,
    ], style={"paddingTop": "8px"})
