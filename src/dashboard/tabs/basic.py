"""
Basic dashboard tier — single non-scrolling screen.

Implements DASH-01: 3 hero KPI cards (total AI market size, YoY growth, 2030 forecast)
with confidence traffic-light indicators, a segment breakdown bar chart, a growth fan
chart, and an analyst consensus bullet chart. Basic tier always uses nominal USD.

This tab ignores the mode argument — Basic is always Basic (no Normal/Expert distinction).
"""
from __future__ import annotations

import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import dcc, html

from src.dashboard.app import (
    FORECASTS_DF,
    ANCHORS_DF,
    SEGMENTS,
    SEGMENT_DISPLAY,
)
from src.dashboard.charts.fan_chart import make_fan_chart
from src.dashboard.charts.bullet_chart import make_consensus_bullet_chart
from src.dashboard.charts.styles import (
    COLOR_DEEP_BLUE,
    COLOR_CONFIDENCE_GREEN,
    COLOR_CONFIDENCE_AMBER,
    COLOR_CONFIDENCE_RED,
    COLOR_AXES,
    vintage_footer,
)

_ATTRIBUTION_TEXT = "Sources: EDGAR, Analyst Corpus | Basic tier — Nominal USD"

# Current year for KPI display — dynamic from data
_CURRENT_YEAR = int(FORECASTS_DF["year"].max()) if not FORECASTS_DF.empty else 2030
# Use latest non-forecast year as "current" for KPI display
_latest_historical = FORECASTS_DF[FORECASTS_DF.get("is_forecast", pd.Series([True] * len(FORECASTS_DF))) == False] if "is_forecast" in FORECASTS_DF.columns else FORECASTS_DF[FORECASTS_DF["year"] <= 2025]
_CURRENT_YEAR = int(_latest_historical["year"].max()) if not _latest_historical.empty else int(FORECASTS_DF["year"].min())
_PREV_YEAR = _CURRENT_YEAR - 1
_FORECAST_YEAR = 2030


def _confidence_color(ci80_upper: float, ci80_lower: float, point: float) -> str:
    """
    Compute confidence traffic-light color based on CI width ratio.

    Thresholds (per UI-SPEC Color section):
        GREEN  (tight):    ratio < 0.30
        AMBER (moderate):  0.30 <= ratio < 0.60
        RED   (wide):      ratio >= 0.60
    """
    if point <= 0:
        return COLOR_CONFIDENCE_RED
    ratio = (ci80_upper - ci80_lower) / point
    if ratio < 0.30:
        return COLOR_CONFIDENCE_GREEN
    elif ratio < 0.60:
        return COLOR_CONFIDENCE_AMBER
    else:
        return COLOR_CONFIDENCE_RED


def _kpi_card(label: str, value: str, sub: str, confidence_color: str) -> dbc.Card:
    """
    Build a hero KPI card following the UI-SPEC component specification.

    Parameters
    ----------
    label : str
        Short label above the value (12px, color #888).
    value : str
        Formatted metric value (28px, semibold, color #1A1A2E).
    sub : str
        Sub-label below the value for scope/units/context (12px, color #999).
    confidence_color : str
        Hex color for the traffic-light confidence dot (●).
    """
    return dbc.Card(
        dbc.CardBody([
            html.Div(
                label,
                style={
                    "fontSize": "12px",
                    "color": "#888",
                    "marginBottom": "4px",
                    "fontWeight": 400,
                },
            ),
            html.Div([
                html.Span(
                    value,
                    style={
                        "fontSize": "28px",
                        "fontWeight": 600,
                        "color": "#1A1A2E",
                    },
                ),
                html.Span(
                    "\u00a0\u00a0",
                    style={"display": "inline-block", "width": "8px"},
                ),
                html.Span(
                    "\u25cf",
                    style={
                        "color": confidence_color,
                        "fontSize": "12px",
                        "verticalAlign": "middle",
                    },
                    **{"aria-label": f"Confidence: {'high' if confidence_color == COLOR_CONFIDENCE_GREEN else 'moderate' if confidence_color == COLOR_CONFIDENCE_AMBER else 'low'}"},
                ),
            ]),
            html.Div(
                sub,
                style={
                    "fontSize": "12px",
                    "color": "#999",
                    "marginTop": "2px",
                    "fontWeight": 400,
                },
            ),
        ]),
        style={
            "border": f"1px solid {COLOR_AXES}",
            "borderRadius": "8px",
            "boxShadow": "0 1px 4px rgba(0,0,0,0.06)",
        },
    )


def build_basic_layout(segment: str, usd_col: str, mode: str) -> html.Div:
    """
    Build the Basic dashboard tier layout.

    Always uses nominal USD regardless of the global USD toggle. The mode argument
    is accepted for callback compatibility but is intentionally ignored — Basic is
    always the Basic view.

    Parameters
    ----------
    segment : str
        Global segment filter ("all" or segment ID). Used for the fan chart only.
    usd_col : str
        USD column toggle value (ignored — Basic always uses point_estimate_nominal).
    mode : str
        Display mode ("normal" or "expert") — intentionally ignored.

    Returns
    -------
    html.Div
        Full Basic tab layout: KPI row + vintage footer + chart row + consensus panel.
    """
    # --- Data preparation ---
    df_current = FORECASTS_DF[FORECASTS_DF["year"] == _CURRENT_YEAR]
    df_prev = FORECASTS_DF[FORECASTS_DF["year"] == _PREV_YEAR]
    df_2030 = FORECASTS_DF[FORECASTS_DF["year"] == _FORECAST_YEAR]

    total_current_nom = float(df_current["point_estimate_nominal"].sum())
    total_prev_nom = float(df_prev["point_estimate_nominal"].sum())
    total_2030_nom = float(df_2030["point_estimate_nominal"].sum())

    # YoY growth
    yoy_growth = (total_current_nom / total_prev_nom - 1) * 100 if total_prev_nom > 0 else 0.0

    # Confidence for current year KPIs: use real_2020 CI for width ratio
    ci80_lo_current = float(df_current["ci80_lower"].sum())
    ci80_hi_current = float(df_current["ci80_upper"].sum())
    total_current_real = float(df_current["point_estimate_real_2020"].sum())

    conf_color_total = _confidence_color(ci80_hi_current, ci80_lo_current, total_current_real)

    # YoY growth confidence: treat wider current CI as more uncertain growth
    conf_color_yoy = conf_color_total  # same underlying data uncertainty

    # 2030 forecast confidence
    ci80_lo_2030 = float(df_2030["ci80_lower"].sum())
    ci80_hi_2030 = float(df_2030["ci80_upper"].sum())
    total_2030_real = float(df_2030["point_estimate_real_2020"].sum())
    conf_color_2030 = _confidence_color(ci80_hi_2030, ci80_lo_2030, total_2030_real)

    # Approximate nominal CIs for 2030 by scaling real CIs
    if total_2030_real > 0:
        scale = total_2030_nom / total_2030_real
        ci80_lo_2030_nom = ci80_lo_2030 * scale
        ci80_hi_2030_nom = ci80_hi_2030 * scale
    else:
        ci80_lo_2030_nom = ci80_lo_2030
        ci80_hi_2030_nom = ci80_hi_2030

    # Format KPI values
    def _fmt_usd(val: float) -> str:
        if val >= 1000:
            return f"${val / 1000:.1f}T"
        return f"${val:.0f}B"

    data_vintage = FORECASTS_DF["data_vintage"].iloc[0]

    # --- Hero KPI row ---
    kpi_row = dbc.Row([
        dbc.Col(
            _kpi_card(
                label="Total AI Market Size",
                value=_fmt_usd(total_current_nom),
                sub=f"{_CURRENT_YEAR} \u00b7 Nominal USD \u00b7 Scope: AI software + services + infrastructure",
                confidence_color=conf_color_total,
            ),
            width=4,
        ),
        dbc.Col(
            _kpi_card(
                label="YoY Market Growth",
                value=f"{yoy_growth:.1f}%",
                sub=f"{_PREV_YEAR}\u2192{_CURRENT_YEAR} \u00b7 Nominal USD",
                confidence_color=conf_color_yoy,
            ),
            width=4,
        ),
        dbc.Col(
            _kpi_card(
                label="2030 Forecast",
                value=_fmt_usd(total_2030_nom),
                sub=(
                    f"Nominal USD \u00b7 CI: {_fmt_usd(ci80_lo_2030_nom)}\u2013{_fmt_usd(ci80_hi_2030_nom)} (80%)"
                ),
                confidence_color=conf_color_2030,
            ),
            width=4,
        ),
    ], className="g-3", style={"marginBottom": "0"})

    # Vintage footer below KPIs
    kpi_footer = vintage_footer("EDGAR/Analyst Corpus", data_vintage)

    # --- Segment bar chart (2024 breakdown) ---
    seg_df = df_current.copy()
    seg_labels = [SEGMENT_DISPLAY.get(s, s) for s in seg_df["segment"].tolist()]
    seg_values = seg_df["point_estimate_nominal"].tolist()

    seg_fig = go.Figure(go.Bar(
        x=seg_values,
        y=seg_labels,
        orientation="h",
        marker_color=COLOR_DEEP_BLUE,
        hovertemplate="%{y}: $%{x:.0f}B<extra></extra>",
    ))
    seg_fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            title="USD Billions (Nominal)",
            gridcolor=COLOR_AXES,
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            title=None,
            tickfont=dict(size=11),
        ),
        margin=dict(l=10, r=20, t=30, b=40),
        title=dict(
            text=f"Segment Breakdown {_CURRENT_YEAR}",
            font=dict(size=13),
            x=0.0,
            xanchor="left",
        ),
    )

    # --- Fan chart ---
    fan_fig = make_fan_chart(
        FORECASTS_DF,
        segment=segment,
        usd_col="point_estimate_nominal",
        usd_mode=False,
    )

    # --- Chart row ---
    chart_row = dbc.Row([
        dbc.Col(
            dcc.Graph(
                figure=seg_fig,
                style={"height": "calc(100vh - 320px)", "minHeight": "220px"},
                config={"displayModeBar": False},
            ),
            width=5,
        ),
        dbc.Col(
            dcc.Graph(
                figure=fan_fig,
                style={"height": "calc(100vh - 320px)", "minHeight": "220px"},
                config={"displayModeBar": False},
            ),
            width=7,
        ),
    ], className="g-3", style={"marginTop": "8px"})

    # --- Consensus bullet chart ---
    bullet_fig = make_consensus_bullet_chart(
        FORECASTS_DF,
        ANCHORS_DF,
        _CURRENT_YEAR,
        SEGMENT_DISPLAY,
    )

    consensus_panel = html.Div([
        html.H4(
            "Model vs Analyst Consensus",
            style={
                "fontSize": "20px",
                "fontWeight": 600,
                "color": "#1A1A2E",
                "marginBottom": "4px",
                "marginTop": "8px",
            },
        ),
        dcc.Graph(
            figure=bullet_fig,
            config={"displayModeBar": False},
        ),
        vintage_footer("Analyst corpus (8 firms)", "Latest vintage: 2025"),
    ])

    return html.Div([
        kpi_row,
        kpi_footer,
        chart_row,
        consensus_panel,
    ], style={
        "height": "calc(100vh - 120px)",
        "overflow": "hidden",
    })
