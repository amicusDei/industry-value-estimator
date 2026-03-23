"""
Chart export utilities for PDF report generation.

Converts Plotly figures to base64 PNG data URIs for embedding in HTML templates.
Uses kaleido v1 API (fig.to_image) — NOT fig.write_image() and NOT engine="kaleido".

Functions
---------
fig_to_data_uri : Export a Plotly figure as a base64 PNG data URI.
export_fan_charts : Generate fan chart data URIs for each segment.
export_backtest_charts : Generate backtest chart data URIs for each segment.
export_shap_image : Convert existing SHAP PNG to base64 data URI.
"""
from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def fig_to_data_uri(
    fig: go.Figure,
    width: int = 900,
    height: int = 500,
    scale: int = 2,
) -> str:
    """
    Export a Plotly figure as a base64 PNG data URI string.

    Parameters
    ----------
    fig : go.Figure
        Plotly figure to export.
    width : int
        Image width in pixels (default 900).
    height : int
        Image height in pixels (default 500).
    scale : int
        Resolution multiplier (default 2 for retina quality).

    Returns
    -------
    str
        Data URI string of the form ``data:image/png;base64,{b64_string}``.
    """
    img_bytes: bytes = fig.to_image(format="png", width=width, height=height, scale=scale)
    b64_string = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64_string}"


def export_fan_charts(
    forecasts_df: pd.DataFrame,
    segments: list[str],
    usd_mode: bool = True,
) -> dict[str, str]:
    """
    Generate fan chart data URIs for each segment plus the "all" aggregate.

    Parameters
    ----------
    forecasts_df : pd.DataFrame
        Full forecasts DataFrame (forecasts_ensemble.parquet schema).
        Must include usd_point/usd_ci* columns when usd_mode=True.
    segments : list[str]
        List of segment IDs to generate charts for.
    usd_mode : bool
        If True, plot USD billions (default). If False, plot raw composite index.

    Returns
    -------
    dict[str, str]
        Mapping of segment_id (and "all") to data URI string.
    """
    from src.dashboard.charts.fan_chart import make_fan_chart

    usd_col = "usd_point" if usd_mode else "point_estimate_real_2020"
    uris: dict[str, str] = {}

    for seg in segments:
        fig = make_fan_chart(forecasts_df, segment=seg, usd_col=usd_col, usd_mode=usd_mode)
        uris[seg] = fig_to_data_uri(fig)

    # All-segments aggregate
    fig_all = make_fan_chart(forecasts_df, segment="all", usd_col=usd_col, usd_mode=usd_mode)
    uris["all"] = fig_to_data_uri(fig_all)

    return uris


def export_backtest_charts(
    residuals_df: pd.DataFrame,
    segments: list[str],
) -> dict[str, str]:
    """
    Generate backtest residual chart data URIs for each segment.

    Parameters
    ----------
    residuals_df : pd.DataFrame
        Residuals DataFrame (residuals_statistical.parquet schema).
        Required columns: year, segment, residual.
    segments : list[str]
        List of segment IDs to generate charts for.

    Returns
    -------
    dict[str, str]
        Mapping of segment_id to data URI string.
    """
    from src.dashboard.charts.backtest import make_backtest_chart

    uris: dict[str, str] = {}
    for seg in segments:
        fig = make_backtest_chart(residuals_df, segment=seg)
        uris[seg] = fig_to_data_uri(fig, width=800, height=400)

    return uris


def export_shap_image(shap_path: Path | None = None) -> str:
    """
    Read existing SHAP PNG and convert to base64 data URI.

    Parameters
    ----------
    shap_path : Path, optional
        Path to SHAP PNG file. Defaults to models/ai_industry/shap_summary.png
        relative to project root.

    Returns
    -------
    str
        Data URI string of the form ``data:image/png;base64,{b64_string}``.
        Returns empty string if file does not exist.
    """
    if shap_path is None:
        shap_path = _PROJECT_ROOT / "models" / "ai_industry" / "shap_summary.png"

    shap_path = Path(shap_path)
    if not shap_path.exists():
        return ""

    img_bytes = shap_path.read_bytes()
    b64_string = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64_string}"
