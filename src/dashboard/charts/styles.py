"""
Dashboard style tokens and typography constants.

Centralizes all visual design decisions for the AI Industry Value Estimator dashboard.
Using module-level constants rather than inline style dicts ensures consistency across
all chart and layout components and makes design changes a single-point update.

Color system:
    Deep blue (#1E5AC8): primary brand color for lines, highlights, and interactive elements
    Coral (#E05A3A): negative values and contrast color in bar charts
    Secondary background (#F4F6FA): tab content area and subtle card backgrounds
    Axes (#E8EBF0): gridlines and table borders

CI band fills use semi-transparent blue to layer 80% and 95% bands visually.
"""
# Color tokens from UI-SPEC
COLOR_DEEP_BLUE = "#1E5AC8"
COLOR_CORAL = "#E05A3A"
COLOR_BG_PRIMARY = "#FFFFFF"
COLOR_BG_SECONDARY = "#F4F6FA"
COLOR_ATTRIBUTION = "#888888"
COLOR_AXES = "#E8EBF0"

# CI band fills
CI95_FILL = "rgba(30, 90, 200, 0.10)"
CI80_FILL = "rgba(30, 90, 200, 0.20)"
FORECAST_BOUNDARY_COLOR = "rgba(120, 120, 120, 0.60)"
CORAL_SERIES = "rgba(224, 90, 58, 0.85)"

# Confidence traffic-light colors (semantic — status/diagnostic use only)
COLOR_CONFIDENCE_GREEN = "#2ECC71"
COLOR_CONFIDENCE_AMBER = "#F39C12"
COLOR_CONFIDENCE_RED = "#E74C3C"


from dash import html  # noqa: E402 — imported here to keep styles.py self-contained


def vintage_footer(data_source: str, vintage: str, model_ver: str = "v1.1") -> html.P:
    """
    Render a subtle vintage/attribution footer paragraph.

    Parameters
    ----------
    data_source : str
        Human-readable source description (e.g. "EDGAR/Analyst Corpus").
    vintage : str
        Vintage date string (e.g. "2024-Q4").
    model_ver : str
        Model version string, defaults to "v1.1".

    Returns
    -------
    html.P
        Dash paragraph component styled as a receding footnote.
    """
    text = f"Data: {data_source} {vintage} | Model: {model_ver} | Last updated: 2026-03-26"
    return html.P(text, style={
        "fontSize": "12px",
        "color": "#AAAAAA",
        "marginTop": "8px",
        "marginBottom": "0",
        "textAlign": "right",
    })

# Typography
FONT_DISPLAY = {"size": 36, "weight": 600}
FONT_HEADING = {"size": 20, "weight": 600}
FONT_BODY = {"size": 16}
FONT_LABEL = {"size": 12}

# Attribution footnote style (reusable dict)
ATTRIBUTION_STYLE = {
    "fontSize": "12px",
    "color": COLOR_ATTRIBUTION,
    "marginTop": "4px",
    "marginBottom": "0",
    "fontStyle": "italic",
}
