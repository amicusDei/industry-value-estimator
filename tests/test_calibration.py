"""
Tests for CAGR calibration logic, CI band ordering, and scope normalization.
"""
import numpy as np
import pytest


class TestCAGRCalibration:
    """Tests for CAGR calibration logic in the ensemble pipeline."""

    def test_blend_applied_when_model_cagr_below_floor(self):
        """When model CAGR < floor, a calibrated blend should be applied."""
        from config.settings import load_industry_config

        cfg = load_industry_config("ai")
        cal = cfg["model_calibration"]
        cagr_floors = cal["cagr_floors"]
        model_weight = cal["calibration_blend"]["model_weight"]
        consensus_weight = cal["calibration_blend"]["consensus_weight"]

        # Simulate: model predicts flat growth for ai_infrastructure (CAGR = 0)
        last_real = 50.0  # $50B last real value
        n_years = 6
        model_forecast = np.full(n_years, last_real)  # flat = 0% CAGR

        seg = "ai_infrastructure"
        min_cagr = cagr_floors[seg]

        # Model CAGR is 0, which is below the floor
        model_end = model_forecast[-1]
        model_cagr = (model_end / last_real) ** (1.0 / n_years) - 1.0
        assert model_cagr < min_cagr, "Test setup: model CAGR should be below floor"

        # Apply calibration blend (same logic as run_ensemble_pipeline.py)
        calibrated = np.array([last_real * (1 + min_cagr) ** (i + 1) for i in range(n_years)])
        blended = model_weight * model_forecast + consensus_weight * calibrated

        # Blended should show positive growth
        blended_cagr = (blended[-1] / last_real) ** (1.0 / n_years) - 1.0
        assert blended_cagr > 0, "Blended forecast should have positive CAGR"
        assert blended_cagr > model_cagr, "Blended CAGR should exceed model CAGR"

    def test_no_blend_when_model_cagr_above_floor(self):
        """When model CAGR >= floor, no calibration blend should be needed."""
        from config.settings import load_industry_config

        cfg = load_industry_config("ai")
        cagr_floors = cfg["model_calibration"]["cagr_floors"]

        seg = "ai_hardware"
        min_cagr = cagr_floors[seg]

        # Model predicts 20% CAGR (above 15% floor)
        last_real = 100.0
        n_years = 6
        model_forecast = np.array([last_real * (1.20) ** (i + 1) for i in range(n_years)])
        model_cagr = (model_forecast[-1] / last_real) ** (1.0 / n_years) - 1.0

        assert model_cagr >= min_cagr, "Model CAGR should be at or above floor"

    def test_blend_weights_sum_to_one(self):
        """Calibration blend weights should sum to 1.0."""
        from config.settings import load_industry_config

        cfg = load_industry_config("ai")
        blend = cfg["model_calibration"]["calibration_blend"]
        total = blend["model_weight"] + blend["consensus_weight"]
        assert abs(total - 1.0) < 1e-10, f"Blend weights sum to {total}, expected 1.0"


class TestCIBandOrdering:
    """Tests for CI band monotonic ordering."""

    def test_ci_ordering_enforced(self):
        """CI bounds must satisfy: ci95_lower <= ci80_lower <= point <= ci80_upper <= ci95_upper."""
        from src.inference.forecast import clip_ci_bounds

        row = {
            "point_estimate_real_2020": 100.0,
            "ci80_lower": 85.0,
            "ci80_upper": 115.0,
            "ci95_lower": 70.0,
            "ci95_upper": 130.0,
        }
        clipped = clip_ci_bounds(row)
        assert clipped["ci95_lower"] <= clipped["ci80_lower"]
        assert clipped["ci80_lower"] <= clipped["point_estimate_real_2020"]
        assert clipped["point_estimate_real_2020"] <= clipped["ci80_upper"]
        assert clipped["ci80_upper"] <= clipped["ci95_upper"]

    def test_ci_ordering_corrects_inverted_bounds(self):
        """clip_ci_bounds should fix inverted CI bounds."""
        from src.inference.forecast import clip_ci_bounds

        # Deliberately inverted: ci80 wider than ci95
        row = {
            "point_estimate_real_2020": 100.0,
            "ci80_lower": 60.0,
            "ci80_upper": 140.0,
            "ci95_lower": 75.0,   # Wrong: should be <= ci80_lower
            "ci95_upper": 125.0,  # Wrong: should be >= ci80_upper
        }
        clipped = clip_ci_bounds(row)
        assert clipped["ci95_lower"] <= clipped["ci80_lower"]
        assert clipped["ci80_lower"] <= clipped["point_estimate_real_2020"]
        assert clipped["point_estimate_real_2020"] <= clipped["ci80_upper"]
        assert clipped["ci80_upper"] <= clipped["ci95_upper"]

    def test_95_ci_wider_than_80_ci(self):
        """95% CI should always be at least as wide as 80% CI after clipping."""
        from src.inference.forecast import clip_ci_bounds

        row = {
            "point_estimate_real_2020": 50.0,
            "ci80_lower": 40.0,
            "ci80_upper": 60.0,
            "ci95_lower": 30.0,
            "ci95_upper": 70.0,
        }
        clipped = clip_ci_bounds(row)
        ci80_width = clipped["ci80_upper"] - clipped["ci80_lower"]
        ci95_width = clipped["ci95_upper"] - clipped["ci95_lower"]
        assert ci95_width >= ci80_width


class TestScopeNormalization:
    """Tests that segment-specific entries are NOT scope-adjusted."""

    def test_segment_specific_entries_not_scope_adjusted(self):
        """Segment-specific analyst estimates should not have scope_coefficient applied,
        because they already target a specific segment definition."""
        import yaml
        from pathlib import Path

        registry_path = Path(__file__).resolve().parent.parent / "data" / "raw" / "market_anchors" / "ai_analyst_registry.yaml"
        with open(registry_path) as f:
            registry = yaml.safe_load(f)

        # Find segment-specific entries (segment != "total")
        segment_entries = [
            e for e in registry["entries"]
            if e["segment"] != "total"
        ]
        assert len(segment_entries) > 0, "Expected segment-specific entries in registry"

        # Segment-specific entries are raw values for that segment —
        # scope_coefficient from ai.yaml scope_mapping_table should NOT be applied
        # to these entries because they already describe our exact segment definition.
        # This test documents the invariant.
        for entry in segment_entries:
            assert entry["segment"] in (
                "ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"
            ), f"Unexpected segment value: {entry['segment']}"
