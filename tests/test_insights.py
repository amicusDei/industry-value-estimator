"""Tests for the automated insight narrative generator."""

import pytest

from src.narratives.insight_generator import generate_segment_insights

SEGMENTS = ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]


@pytest.mark.parametrize("segment", SEGMENTS)
def test_insight_count(segment: str):
    """Each segment should produce 3-5 insights."""
    insights = generate_segment_insights(segment)
    assert 3 <= len(insights) <= 5, f"{segment}: got {len(insights)} insights"


@pytest.mark.parametrize("segment", SEGMENTS)
def test_insight_keys(segment: str):
    """Every insight must have type, text, and priority keys."""
    insights = generate_segment_insights(segment)
    for i, insight in enumerate(insights):
        assert "type" in insight, f"Insight {i} missing 'type'"
        assert "text" in insight, f"Insight {i} missing 'text'"
        assert "priority" in insight, f"Insight {i} missing 'priority'"


@pytest.mark.parametrize("segment", SEGMENTS)
def test_insight_formatting(segment: str):
    """Insight text should contain $ and % formatting."""
    insights = generate_segment_insights(segment)
    has_dollar = any("$" in ins["text"] for ins in insights)
    has_pct = any("%" in ins["text"] for ins in insights)
    assert has_dollar, f"{segment}: no insight contains '$'"
    assert has_pct, f"{segment}: no insight contains '%'"


@pytest.mark.parametrize("segment", SEGMENTS)
def test_insight_priority_range(segment: str):
    """Priority must be between 1 and 5."""
    insights = generate_segment_insights(segment)
    for ins in insights:
        assert 1 <= ins["priority"] <= 5, (
            f"Priority {ins['priority']} out of range for {ins['type']}"
        )


@pytest.mark.parametrize("segment", SEGMENTS)
def test_insights_sorted_by_priority(segment: str):
    """Insights should be returned sorted by priority ascending."""
    insights = generate_segment_insights(segment)
    priorities = [ins["priority"] for ins in insights]
    assert priorities == sorted(priorities), f"Not sorted: {priorities}"


def test_insight_types_valid():
    """All insight types should be from the known set."""
    valid_types = {
        "cagr_insight",
        "dispersion_insight",
        "scenario_spread",
        "top_growth",
        "yoy_momentum",
    }
    for segment in SEGMENTS:
        insights = generate_segment_insights(segment)
        for ins in insights:
            assert ins["type"] in valid_types, f"Unknown type: {ins['type']}"
