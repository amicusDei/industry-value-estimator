"""
api/routers/credit_spreads.py
=================================
FastAPI endpoints for the Dynamic Mismatch empirical module.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import pandas as pd
import io
import json
import logging
from pathlib import Path
from datetime import datetime

import lseg.data as rd

from src.ingestion.credit_spreads import (
    run_full_pull,
    ALL_ISSUERS,
    GENERATION_TRANSITIONS,
    GROUP_LABELS,
)
from src.empirics.event_study import run_event_study

logger = logging.getLogger(__name__)
router = APIRouter(tags=["credit-spreads"])

DATA_DIR = Path("data/raw/credit")


# ── HELPERS ───────────────────────────────────────────────────────────────────

def load_latest_parquet(pattern: str) -> Optional[pd.DataFrame]:
    """Load the most recently saved parquet matching pattern."""
    files = sorted(DATA_DIR.glob(pattern))
    if not files:
        return None
    return pd.read_parquet(files[-1])


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@router.get("/credit-spreads/universe")
async def get_universe():
    """Returns the issuer universe with group labels."""
    universe = []
    for name, ric in ALL_ISSUERS.items():
        universe.append({
            "name":  name,
            "ric":   ric,
            "group": GROUP_LABELS.get(name, "unknown"),
        })
    return {"universe": universe, "count": len(universe)}


@router.get("/credit-spreads/transitions")
async def get_transitions():
    """Returns the generational transition dates used as event dates."""
    return {"transitions": GENERATION_TRANSITIONS}


@router.post("/credit-spreads/pull")
async def trigger_data_pull(
    background_tasks: BackgroundTasks,
    start_date: str = Query(default="2020-01-01"),
):
    """
    Triggers a full data pull from LSEG in the background.
    Pulls CDS 5Y spreads, Bond OAS, and market controls.
    """
    def pull_task():
        try:
            rd.open_session()
            logger.info("LSEG session opened for credit spread pull.")
            run_full_pull(
                output_dir=str(DATA_DIR),
                start_date=start_date,
            )
        except Exception as e:
            logger.error(f"Credit spread pull failed: {e}")
        finally:
            try:
                rd.close_session()
                logger.info("LSEG session closed.")
            except Exception:
                pass

    background_tasks.add_task(pull_task)
    return {
        "status": "pull_started",
        "message": f"Pulling CDS/OAS data from {start_date} in background.",
        "output_dir": str(DATA_DIR),
    }


@router.get("/credit-spreads/data")
async def get_spread_data(
    issuer: Optional[str] = Query(default=None, description="Filter by issuer name"),
    group:  Optional[str] = Query(default=None, description="Filter by group: hyperscaler, dc_reit, control"),
    format: str = Query(default="json", description="Response format: json or csv"),
):
    """Returns historical CDS 5Y spread time series."""
    cds_df = load_latest_parquet("cds_spreads_*.parquet")
    if cds_df is None:
        raise HTTPException(
            status_code=404,
            detail="No CDS data found. Run POST /credit-spreads/pull first."
        )

    # Filter columns
    if issuer:
        if issuer not in cds_df.columns:
            raise HTTPException(status_code=404, detail=f"Issuer '{issuer}' not found.")
        cds_df = cds_df[[issuer]]
    elif group:
        cols = [k for k, v in GROUP_LABELS.items() if v == group and k in cds_df.columns]
        if not cols:
            raise HTTPException(status_code=404, detail=f"No data for group '{group}'.")
        cds_df = cds_df[cols]

    if format == "csv":
        stream = io.StringIO()
        cds_df.to_csv(stream)
        stream.seek(0)
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=cds_spreads.csv"}
        )

    # JSON response
    result = cds_df.reset_index()
    result["Date"] = result["Date"].astype(str)
    return {
        "data":    result.to_dict(orient="records"),
        "columns": list(cds_df.columns),
        "n_obs":   len(cds_df),
        "date_range": {
            "start": str(cds_df.index.min()),
            "end":   str(cds_df.index.max()),
        }
    }


@router.post("/credit-spreads/event-study")
async def run_event_study_endpoint(
    event_window_days: int = Query(
        default=90,
        description="Days after each generational transition to include in Post window"
    ),
    save_results: bool = Query(
        default=True,
        description="Save results to data/empirics/"
    ),
):
    """
    Runs the full event study regression on the latest pulled data.

    Tests: do CDS spreads on Hyperscaler/DC-REIT assets widen
    systematically after generational AI transitions, controlling
    for market-wide credit conditions?
    """
    cds_df = load_latest_parquet("cds_spreads_*.parquet")
    if cds_df is None:
        raise HTTPException(
            status_code=404,
            detail="No CDS data found. Run POST /credit-spreads/pull first."
        )

    ctrl_df = load_latest_parquet("market_controls_*.parquet")
    if ctrl_df is None:
        raise HTTPException(
            status_code=404,
            detail="No control data found. Run POST /credit-spreads/pull first."
        )

    output_path = None
    if save_results:
        results_dir = Path("data/empirics")
        results_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(
            results_dir / f"event_study_{datetime.today().strftime('%Y%m%d')}.json"
        )

    try:
        results = run_event_study(
            cds_df=cds_df,
            controls_df=ctrl_df,
            event_window_days=event_window_days,
            output_path=output_path,
        )
    except Exception as e:
        logger.error(f"Event study failed: {e}")
        raise HTTPException(status_code=500, detail=f"Event study failed: {str(e)}")

    return {
        "status":             "success",
        "event_window_days":  event_window_days,
        "results":            results,
        "saved_to":           output_path,
    }


@router.get("/credit-spreads/event-study/latest")
async def get_latest_event_study():
    """Returns the most recently run event study results."""
    results_dir = Path("data/empirics")
    files = sorted(results_dir.glob("event_study_*.json"))
    if not files:
        raise HTTPException(
            status_code=404,
            detail="No event study results found. Run POST /credit-spreads/event-study first."
        )
    with open(files[-1]) as f:
        results = json.load(f)
    return {
        "file":    str(files[-1]),
        "results": results,
    }
