"""Automated insight narratives endpoint."""

from fastapi import APIRouter, Query

from api.schemas import InsightsResponse, InsightItem
from src.narratives.insight_generator import generate_segment_insights

router = APIRouter(prefix="/api/v1", tags=["insights"])


@router.get("/insights", response_model=InsightsResponse)
def insights(
    segment: str = Query(..., description="Segment id, e.g. ai_hardware"),
):
    """Return rule-based narrative insights for a segment."""
    raw = generate_segment_insights(segment)
    items = [InsightItem(type=r["type"], text=r["text"], priority=r["priority"]) for r in raw]
    return InsightsResponse(data=items, count=len(items), segment=segment)
