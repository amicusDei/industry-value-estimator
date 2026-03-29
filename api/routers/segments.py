"""Segment overview endpoints."""

from fastapi import APIRouter, Query

from api.data_loader import get_segments_config, get_forecasts
from api.schemas import SegmentsResponse, SegmentSummary

router = APIRouter(prefix="/api/v1", tags=["segments"])


@router.get("/segments", response_model=SegmentsResponse)
def list_segments(
    valuation: str = Query("nominal", description="'nominal' or 'real_2020'"),
):
    segments_cfg = get_segments_config()
    df = get_forecasts()
    point_col = "point_estimate_nominal" if valuation == "nominal" else "point_estimate_real_2020"

    summaries = []
    for seg in segments_cfg:
        seg_id = seg["id"]

        market_size = None
        if not df.empty and "quarter" in df.columns:
            q4_2025 = df[(df["segment"] == seg_id) & (df["year"] == 2025) & (df["quarter"] == 4)]
            if not q4_2025.empty:
                market_size = round(float(q4_2025[point_col].iloc[0]), 1)

        cagr = None
        if not df.empty and "quarter" in df.columns:
            q4_2025 = df[(df["segment"] == seg_id) & (df["year"] == 2025) & (df["quarter"] == 4)]
            q4_2030 = df[(df["segment"] == seg_id) & (df["year"] == 2030) & (df["quarter"] == 4)]
            if not q4_2025.empty and not q4_2030.empty:
                v_start = float(q4_2025[point_col].iloc[0])
                v_end = float(q4_2030[point_col].iloc[0])
                if v_start > 0:
                    cagr = round(((v_end / v_start) ** (1 / 5) - 1) * 100, 1)

        summaries.append(SegmentSummary(
            id=seg_id,
            display_name=seg["display_name"],
            market_size_2024_usd_b=market_size,
            cagr_2025_2030_pct=cagr,
            overlap_note=seg.get("overlap_note", ""),
        ))

    return SegmentsResponse(segments=summaries)
