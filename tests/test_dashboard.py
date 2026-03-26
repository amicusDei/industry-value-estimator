"""Dashboard unit tests covering PRES-01, PRES-02, PRES-03, DATA-07."""
import pytest
from pathlib import Path


def test_fan_chart_traces():
    """PRES-01: Fan chart has CI bands + historical + forecast dashed line."""
    from src.dashboard.app import FORECASTS_DF
    from src.dashboard.charts.fan_chart import make_fan_chart

    fig = make_fan_chart(FORECASTS_DF, segment="ai_software", usd_col="point_estimate_real_2020")
    trace_names = [t.name for t in fig.data]

    # Must have CI bands + historical + forecast
    assert "95% CI" in trace_names, f"Missing 95% CI trace. Found: {trace_names}"
    assert "80% CI" in trace_names, f"Missing 80% CI trace. Found: {trace_names}"
    assert "Historical" in trace_names, f"Missing Historical trace. Found: {trace_names}"
    assert "Forecast" in trace_names, f"Missing Forecast trace. Found: {trace_names}"

    # Forecast line must be dashed
    forecast_trace = [t for t in fig.data if t.name == "Forecast"][0]
    assert forecast_trace.line.dash == "dash", f"Forecast line should be dashed, got: {forecast_trace.line.dash}"


def test_fan_chart_vline():
    """PRES-01: Fan chart has vertical dashed line at forecast boundary."""
    from src.dashboard.app import FORECASTS_DF
    from src.dashboard.charts.fan_chart import make_fan_chart

    fig = make_fan_chart(FORECASTS_DF, segment="ai_software", usd_col="point_estimate_real_2020")

    # add_vline creates shapes on the figure layout
    shapes = fig.layout.shapes
    assert len(shapes) >= 1, "No shapes found — expected at least one vline"
    # At least one shape should be a vertical line (type='line', x0==x1)
    vlines = [s for s in shapes if s.type == "line" and s.x0 == s.x1]
    assert len(vlines) >= 1, f"No vertical lines found in shapes: {shapes}"


def test_fan_chart_usd_toggle():
    """PRES-01: USD toggle switches column used for point line."""
    from src.dashboard.app import FORECASTS_DF
    from src.dashboard.charts.fan_chart import make_fan_chart

    fig_real = make_fan_chart(FORECASTS_DF, segment="ai_software", usd_col="point_estimate_real_2020")
    fig_nom = make_fan_chart(FORECASTS_DF, segment="ai_software", usd_col="point_estimate_nominal")

    # Historical traces should have different y values for real vs nominal
    hist_real = [t for t in fig_real.data if t.name == "Historical"][0]
    hist_nom = [t for t in fig_nom.data if t.name == "Historical"][0]
    assert list(hist_real.y) != list(hist_nom.y), "Real and nominal should produce different y values"


def test_backtest_chart_traces():
    """PRES-03: Backtest chart renders residual data."""
    from src.dashboard.app import RESIDUALS_DF
    from src.dashboard.charts.backtest import make_backtest_chart

    fig = make_backtest_chart(RESIDUALS_DF, segment="ai_software")
    assert len(fig.data) >= 1, "Backtest chart must have at least one trace"
    # First trace should have y data
    assert fig.data[0].y is not None and len(fig.data[0].y) > 0, "Backtest trace must have y data"


def test_diagnostics_scorecard():
    """PRES-03: Diagnostics dict has all 4 segments with backtesting metrics (DASH-04)."""
    from src.dashboard.app import DIAGNOSTICS

    expected_segments = {"ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"}
    assert set(DIAGNOSTICS.keys()) == expected_segments, f"Expected {expected_segments}, got {set(DIAGNOSTICS.keys())}"

    for seg, metrics in DIAGNOSTICS.items():
        # New DIAGNOSTICS schema: mape, r2, mape_label, has_hard_actuals (from backtesting_results.parquet)
        assert "mape_label" in metrics, f"Segment {seg} missing 'mape_label'"
        assert "has_hard_actuals" in metrics, f"Segment {seg} missing 'has_hard_actuals'"
        assert isinstance(metrics["has_hard_actuals"], bool), (
            f"Segment {seg} has_hard_actuals should be bool, got {type(metrics['has_hard_actuals'])}"
        )
        # mape and r2 may be None for segments without hard actuals
        if metrics["has_hard_actuals"]:
            assert isinstance(metrics["mape"], float), (
                f"Segment {seg} MAPE should be float, got {type(metrics['mape'])}"
            )


def test_shap_image_exists():
    """PRES-02: SHAP summary PNG exists for embedding in Drivers tab."""
    shap_path = Path("models/ai_industry/shap_summary.png")
    assert shap_path.exists(), f"SHAP PNG not found at {shap_path}"
    assert shap_path.stat().st_size > 0, "SHAP PNG is empty"


def test_source_attribution():
    """DATA-07: Source attribution strings loaded from config."""
    from src.dashboard.app import SOURCE_ATTRIBUTION

    for key in ["world_bank", "oecd", "lseg"]:
        assert key in SOURCE_ATTRIBUTION, f"Missing attribution key: {key}"
        assert isinstance(SOURCE_ATTRIBUTION[key], str), f"Attribution for {key} should be string"
        assert len(SOURCE_ATTRIBUTION[key]) > 0, f"Attribution for {key} is empty"


def test_tab_attribution_from_config():
    """DATA-07: Tab files use SOURCE_ATTRIBUTION from config, not hardcoded strings."""
    from src.dashboard.app import SOURCE_ATTRIBUTION
    from src.dashboard.tabs import overview, segments, diagnostics, drivers

    # Build the expected attribution text from config
    expected_prefix = "Sources: " + ", ".join(SOURCE_ATTRIBUTION.values())

    # Verify each tab module exposes the config-driven attribution constant
    for mod_name, mod in [
        ("overview", overview),
        ("segments", segments),
        ("diagnostics", diagnostics),
        ("drivers", drivers),
    ]:
        assert hasattr(mod, "_ATTRIBUTION_TEXT"), (
            f"{mod_name} missing _ATTRIBUTION_TEXT — attribution not config-driven"
        )
        assert mod._ATTRIBUTION_TEXT.startswith(expected_prefix), (
            f"{mod_name}._ATTRIBUTION_TEXT does not start with config-derived prefix.\n"
            f"  Expected prefix: {expected_prefix!r}\n"
            f"  Got: {mod._ATTRIBUTION_TEXT!r}"
        )

    # Verify none of the tab source files contain the old hardcoded string literally
    import inspect
    hardcoded = "World Bank Open Data, OECD.Stat, LSEG Workspace"
    for mod_name, mod in [
        ("overview", overview),
        ("segments", segments),
        ("diagnostics", diagnostics),
        ("drivers", drivers),
    ]:
        source = inspect.getsource(mod)
        # The hardcoded literal must NOT appear anywhere in the module source
        assert hardcoded not in source, (
            f"{mod_name} still contains hardcoded attribution string: {hardcoded!r}"
        )


# ---------------------------------------------------------------------------
# Wave 0: Phase 11 test scaffolds (DASH-01 through DASH-05)
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="Plan 11-01 — basic.py created in that plan")
def test_basic_tab_renders():
    """DASH-01: Basic tab layout renders without error and returns an html.Div."""
    from dash import html
    from src.dashboard.tabs.basic import build_basic_layout

    result = build_basic_layout("all", "point_estimate_nominal", "normal")
    assert result is not None, "build_basic_layout returned None"
    assert isinstance(result, html.Div), (
        f"Expected html.Div, got {type(result)}"
    )


@pytest.mark.skip(reason="Plan 11-01 — basic.py created in that plan")
def test_basic_kpi_cards():
    """DASH-01: Basic tab hero row contains exactly 3 dbc.Card instances."""
    import dash_bootstrap_components as dbc
    from src.dashboard.tabs.basic import build_basic_layout

    layout = build_basic_layout("all", "point_estimate_nominal", "normal")

    # Walk the component tree to collect all dbc.Card instances
    def collect_cards(component, depth=0):
        cards = []
        if isinstance(component, dbc.Card):
            cards.append(component)
        children = getattr(component, "children", None)
        if children is None:
            return cards
        if isinstance(children, list):
            for child in children:
                cards.extend(collect_cards(child, depth + 1))
        elif hasattr(children, "children"):
            cards.extend(collect_cards(children, depth + 1))
        return cards

    # Find first dbc.Row in the layout (KPI row)
    kpi_row = None
    if isinstance(layout.children, list):
        for child in layout.children:
            if isinstance(child, dbc.Row):
                kpi_row = child
                break

    assert kpi_row is not None, "No dbc.Row found in basic layout (expected KPI row)"
    cards = collect_cards(kpi_row)
    assert len(cards) == 3, f"Expected 3 KPI cards in first dbc.Row, found {len(cards)}"


@pytest.mark.skip(reason="Plan 11-01 — basic.py created in that plan")
def test_basic_fan_chart_traces():
    """DASH-01: Basic tab fan chart has required forecast traces."""
    from dash import dcc
    from src.dashboard.tabs.basic import build_basic_layout

    layout = build_basic_layout("all", "point_estimate_nominal", "normal")

    # Walk tree to find dcc.Graph components
    def collect_graphs(component):
        graphs = []
        if isinstance(component, dcc.Graph):
            graphs.append(component)
        children = getattr(component, "children", None)
        if children is None:
            return graphs
        if isinstance(children, list):
            for child in children:
                graphs.extend(collect_graphs(child))
        elif hasattr(children, "children"):
            graphs.extend(collect_graphs(children))
        return graphs

    graphs = collect_graphs(layout)
    assert len(graphs) >= 1, "No dcc.Graph found in basic layout"

    # Find the fan chart (the one with 95% CI trace)
    fan_graph = None
    for g in graphs:
        if g.figure and g.figure.data:
            trace_names = [t.name for t in g.figure.data]
            if "95% CI" in trace_names:
                fan_graph = g
                break

    assert fan_graph is not None, (
        "No fan chart with '95% CI' trace found in basic layout"
    )
    trace_names = [t.name for t in fan_graph.figure.data]
    assert "80% CI" in trace_names, f"Fan chart missing '80% CI' trace. Found: {trace_names}"
    assert "Forecast" in trace_names, f"Fan chart missing 'Forecast' trace. Found: {trace_names}"


@pytest.mark.skip(reason="Plan 11-03 — bullet_chart.py and ANCHORS_DF created in that plan")
def test_consensus_panel_segments():
    """DASH-02: Consensus bullet chart renders and has traces."""
    from src.dashboard.app import FORECASTS_DF, ANCHORS_DF, SEGMENT_DISPLAY
    from src.dashboard.charts.bullet_chart import make_consensus_bullet_chart

    fig = make_consensus_bullet_chart(FORECASTS_DF, ANCHORS_DF, 2024, SEGMENT_DISPLAY)
    assert fig is not None, "make_consensus_bullet_chart returned None"
    assert len(fig.data) > 0, "Consensus bullet chart has no traces"


@pytest.mark.skip(reason="Plan 11-03 — bullet_chart.py created in that plan")
def test_consensus_divergence_color():
    """DASH-02: Consensus marker is amber (#F39C12) when model is outside p25-p75."""
    import pandas as pd
    from src.dashboard.charts.bullet_chart import make_consensus_bullet_chart

    # Synthetic data: model value (9999) is far outside consensus range (100-200)
    forecasts_df = pd.DataFrame([
        {"year": 2024, "segment": "ai_hardware", "point_estimate_nominal": 9999.0},
    ])
    anchors_df = pd.DataFrame([
        {
            "estimate_year": 2024,
            "segment": "ai_hardware",
            "estimated_flag": False,
            "p25_usd_billions_nominal": 100.0,
            "p75_usd_billions_nominal": 200.0,
            "median_usd_billions_nominal": 150.0,
        }
    ])
    segment_display = {"ai_hardware": "AI Hardware"}

    fig = make_consensus_bullet_chart(forecasts_df, anchors_df, 2024, segment_display)
    scatter_traces = [t for t in fig.data if t.type == "scatter"]
    assert len(scatter_traces) >= 1, "No scatter trace found in consensus chart"
    marker_color = scatter_traces[0].marker.color
    assert marker_color == "#F39C12", (
        f"Expected amber (#F39C12) for outside-range model, got {marker_color}"
    )


@pytest.mark.skip(reason="Plan 11-03 — revenue multiples added to overview in that plan")
def test_revenue_multiples_in_overview():
    """DASH-03: Revenue multiples table present in Normal mode overview."""
    from src.dashboard.tabs.overview import build_overview_layout
    layout = build_overview_layout("all", "point_estimate_real_2020", "normal")
    # Will verify presence of EV/Revenue table component


@pytest.mark.skip(reason="Plan 11-02 — alias columns removed in that plan")
def test_no_alias_columns():
    """DASH-04: FORECASTS_DF must not contain usd_point alias column after alias removal."""
    from src.dashboard.app import FORECASTS_DF
    assert "usd_point" not in FORECASTS_DF.columns, (
        "Alias column 'usd_point' still present — alias removal not complete"
    )


@pytest.mark.skip(reason="Plan 11-02 — PCA strings removed in that plan")
def test_no_pca_strings():
    """DASH-04: No PCA/composite index strings in Normal mode display."""
    import inspect
    from src.dashboard.tabs.overview import build_overview_layout
    source = inspect.getsource(build_overview_layout)
    assert "PCA" not in source, "PCA string still present in overview layout"


@pytest.mark.skip(reason="Plan 11-04 — diagnostics rewrite in that plan")
def test_diagnostics_real_mape():
    """DASH-04: Diagnostics tab shows real MAPE from backtesting_results."""
    from src.dashboard.tabs.diagnostics import build_diagnostics_layout
    layout = build_diagnostics_layout("all", "point_estimate_real_2020", "normal")
    # Will verify MAPE values from backtesting_results are displayed


@pytest.mark.skip(reason="Plan 11-03 — vintage_footer added to styles.py in that plan")
def test_vintage_footer_present():
    """DASH-05: vintage_footer() returns html.P with expected text content."""
    from dash import html
    from src.dashboard.charts.styles import vintage_footer

    footer = vintage_footer("EDGAR/Analyst Corpus", "2024-Q4")
    assert isinstance(footer, html.P), f"Expected html.P, got {type(footer)}"
    text = footer.children
    assert "Data:" in text, f"Footer missing 'Data:' prefix. Got: {text!r}"
    assert "Model: v1.1" in text, f"Footer missing 'Model: v1.1'. Got: {text!r}"
