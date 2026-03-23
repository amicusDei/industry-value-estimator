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
    """PRES-03: Diagnostics dict has all 4 segments with RMSE."""
    from src.dashboard.app import DIAGNOSTICS

    expected_segments = {"ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"}
    assert set(DIAGNOSTICS.keys()) == expected_segments, f"Expected {expected_segments}, got {set(DIAGNOSTICS.keys())}"

    for seg, metrics in DIAGNOSTICS.items():
        assert "rmse" in metrics, f"Segment {seg} missing 'rmse'"
        assert isinstance(metrics["rmse"], float), f"Segment {seg} RMSE should be float, got {type(metrics['rmse'])}"
        assert metrics["rmse"] > 0, f"Segment {seg} RMSE should be positive"


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
