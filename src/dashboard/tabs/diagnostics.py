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


def build_diagnostics_layout(segment: str, usd_col: str, mode: str = "normal") -> html.Div:
    """
    Build the Diagnostics tab layout.

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
    expert = mode == "expert"
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

    def _fmt(val, metric_key: str = "") -> str:
        if isinstance(val, float):
            return f"{val:.4f}"
        # "N/A" means not computable from residuals-only parquet
        if val == "N/A" and metric_key in ("mape", "r2"):
            return "Needs actuals"
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
            raw_val = diag.get(metric_key, "N/A")
            fmt_val = _fmt(raw_val, metric_key)
            cell_style = {
                **_TABLE_CELL_STYLE,
                **({"color": "#999", "fontStyle": "italic"} if fmt_val == "Needs actuals" else {}),
            }
            cells.append(html.Td(fmt_val, style=cell_style))
        metric_rows.append(html.Tr(cells))

    scorecard_table = html.Table(
        [html.Thead(html.Tr(header_cells)), html.Tbody(metric_rows)],
        style={"width": "100%", "borderCollapse": "collapse"},
    )

    # Build RMSE highlight cards (one per displayed segment)
    rmse_highlight_cards = []
    for seg in display_segments:
        diag = DIAGNOSTICS.get(seg, {})
        rmse_val = diag.get("rmse", None)
        seg_label = SEGMENT_DISPLAY.get(seg, seg)
        rmse_highlight_cards.append(
            html.Div([
                html.Div(seg_label, style={
                    "fontSize": "12px", "color": "#666", "marginBottom": "4px",
                    "fontWeight": 500,
                }),
                html.Div(
                    f"RMSE: {rmse_val:.4f}" if isinstance(rmse_val, float) else "RMSE: —",
                    style={
                        "fontSize": "18px", "fontWeight": 700,
                        "color": COLOR_DEEP_BLUE,
                    },
                ),
            ], style={
                "backgroundColor": "rgba(30,90,200,0.05)",
                "border": f"1px solid {COLOR_DEEP_BLUE}",
                "borderRadius": "6px",
                "padding": "12px 16px",
                "flex": "1",
                "minWidth": "160px",
            })
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
            "RMSE is the primary metric computed from the residuals parquet \u2014 it measures average forecast "
            "error magnitude in index units. MAPE and R\u00b2 require the actual observed values alongside "
            "predictions: these will be available once the full pipeline runs with real source data. "
            "All RMSE values are from out-of-sample expanding-window CV folds, not in-sample fit.",
            style={"fontSize": "13px", "color": "#666", "marginBottom": "14px"},
        ),
        # RMSE highlight row
        html.Div(rmse_highlight_cards, style={
            "display": "flex", "gap": "12px", "flexWrap": "wrap",
            "marginBottom": "16px",
        }),
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

    sections = [methodology_card, metric_glossary_card, scorecard_card, backtest_card]

    if expert:
        expert_card = html.Div([
            html.H3(
                "Expert View \u2014 CV Design, Formulas & Assumptions",
                style={"fontSize": "16px", "fontWeight": 600, "color": "#7C4DFF", "marginBottom": "12px", "marginTop": "0"},
            ),
            html.H4("Cross-Validation Design", style={"fontSize": "14px", "fontWeight": 600, "marginBottom": "6px"}),
            html.Ul([
                html.Li("Strategy: sklearn TimeSeriesSplit expanding-window (chronological order preserved)", style={"fontSize": "13px"}),
                html.Li("n_splits = 3 folds. Training windows: ~9 obs \u2192 ~11 obs \u2192 ~13 obs. Test: 1 year per fold.", style={"fontSize": "13px"}),
                html.Li("No leakage: StandardScaler for PCA composites is fit on training fold only (train_end_idx parameter).", style={"fontSize": "13px"}),
                html.Li("Prophet CV: manual TimeSeriesSplit refits (not Prophet's built-in cross_validation \u2014 incompatible with 15-year annual panels).", style={"fontSize": "13px"}),
            ], style={"paddingLeft": "20px", "marginBottom": "12px"}),
            html.H4("Metric Formulas", style={"fontSize": "14px", "fontWeight": 600, "marginBottom": "6px"}),
            html.Div([
                html.Code(
                    "RMSE = \u221a(mean((y_actual - y_predicted)\u00b2))  [computed from residuals_statistical.parquet]",
                    style={"display": "block", "fontFamily": "monospace", "fontSize": "12px",
                           "backgroundColor": "#F4F6FA", "padding": "6px 10px", "borderRadius": "4px", "marginBottom": "4px"},
                ),
                html.Code(
                    "MAPE = mean(|y_actual - y_predicted| / |y_actual|) \u00d7 100  [requires actual values \u2014 not in residuals parquet]",
                    style={"display": "block", "fontFamily": "monospace", "fontSize": "12px",
                           "backgroundColor": "#F4F6FA", "padding": "6px 10px", "borderRadius": "4px", "marginBottom": "4px"},
                ),
                html.Code(
                    "R\u00b2 = 1 - SS_res/SS_tot  where SS_res=\u03a3(y-\u0177)\u00b2, SS_tot=\u03a3(y-\u0233)\u00b2  [requires actual values \u2014 not in residuals parquet]",
                    style={"display": "block", "fontFamily": "monospace", "fontSize": "12px",
                           "backgroundColor": "#F4F6FA", "padding": "6px 10px", "borderRadius": "4px", "marginBottom": "8px"},
                ),
            ]),
            html.P([
                html.Strong("Why MAPE/R\u00b2 show 'Needs actuals': "),
                "The residuals_statistical.parquet file stores the residual column only (y_actual - y_predicted). "
                "Computing MAPE and R\u00b2 requires both y_actual and y_predicted independently. "
                "These become available when the full pipeline runs on real source data and logs the CV fold predictions.",
            ], style={"fontSize": "13px", "color": "#444", "lineHeight": "1.6", "marginBottom": "8px"}),
            html.P([
                html.Strong("Model selection rule: "),
                "Winner per segment = model with lower CV MAPE (ARIMA vs. Prophet). "
                "R\u00b2 and in-sample AIC are reported for completeness but NOT used for selection. "
                "See docs/ASSUMPTIONS.md \u00a7 Metric Interpretation and \u00a7 Model Selection is Per-Segment.",
            ], style={"fontSize": "13px", "color": "#444", "lineHeight": "1.6", "marginBottom": "0"}),
        ], style={
            "backgroundColor": "#FAF8FF",
            "border": "1px solid #C5B0FF",
            "borderLeft": "4px solid #7C4DFF",
            "borderRadius": "8px",
            "padding": "18px 20px",
            "marginTop": "24px",
        })
        sections.append(expert_card)

    return html.Div(sections, style={"paddingTop": "8px"})
