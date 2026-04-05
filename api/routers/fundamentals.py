"""
api/routers/fundamentals.py
=================================
FastAPI endpoints for fundamentals-based event study (Dynamic Mismatch paper).

Provides endpoints to:
1. Pull quarterly fundamentals from yfinance
2. Run the full fundamentals study (Stage 1 DiD + Stage 2 mispricing)
3. Retrieve latest study results
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
import pandas as pd
import json
import logging
from pathlib import Path
from datetime import datetime

from src.ingestion.fundamentals import fetch_quarterly_fundamentals, save_fundamentals
from src.empirics.fundamentals_study import run_full_fundamentals_study

logger = logging.getLogger(__name__)
router = APIRouter(tags=["fundamentals"])

DATA_DIR = Path("data/raw/fundamentals")
RESULTS_DIR = Path("data/empirics")
CREDIT_DIR = Path("data/raw/credit")


def _load_latest_parquet(directory: Path, pattern: str):
    """Load the most recently saved parquet matching pattern."""
    files = sorted(directory.glob(pattern))
    if not files:
        return None
    return pd.read_parquet(files[-1])


# ── ENDPOINTS ────────────────────────────────────────────────────────────────

@router.post("/fundamentals/pull")
async def trigger_fundamentals_pull(
    background_tasks: BackgroundTasks,
    start_date: str = Query(default="2019-01-01"),
):
    """
    Triggers a yfinance pull of quarterly fundamentals in the background.
    Saves results to data/raw/fundamentals/fundamentals_YYYYMMDD.parquet.
    """
    def pull_task():
        try:
            logger.info(f"Starting fundamentals pull from {start_date}...")
            df = fetch_quarterly_fundamentals(start=start_date)
            if not df.empty:
                path = save_fundamentals(df)
                logger.info(f"Fundamentals saved to {path}")
            else:
                logger.warning("Fundamentals pull returned empty DataFrame.")
        except Exception as e:
            logger.error(f"Fundamentals pull failed: {e}")

    background_tasks.add_task(pull_task)
    return {
        "status": "pull_started",
        "message": f"Pulling quarterly fundamentals from yfinance (start={start_date}) in background.",
        "output_dir": str(DATA_DIR),
    }


@router.post("/fundamentals/study")
async def run_fundamentals_study_endpoint(
    event_window_quarters: int = Query(
        default=8,
        description="Number of quarters after each transition to include in Post window",
    ),
    save_results: bool = Query(default=True),
):
    """
    Runs the full fundamentals study on the latest pulled data.

    Stage 1: DiD regression on fundamental metrics (gross margin, operating margin, etc.)
    Stage 2: Mispricing test using equity prices (if available)

    Returns complete results dict.
    """
    # Load latest fundamentals
    fund_df = _load_latest_parquet(DATA_DIR, "fundamentals_*.parquet")
    if fund_df is None:
        raise HTTPException(
            status_code=404,
            detail="No fundamentals data found. Run POST /fundamentals/pull first.",
        )

    # Try to load equity prices for Stage 2
    equity_df = None
    eq_path = CREDIT_DIR / "equity_prices.parquet"
    if eq_path.exists():
        try:
            equity_df = pd.read_parquet(eq_path)
        except Exception as e:
            logger.warning(f"Could not load equity prices: {e}")

    output_path = None
    if save_results:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(
            RESULTS_DIR / f"fundamentals_study_{datetime.today().strftime('%Y%m%d')}.json"
        )

    try:
        results = run_full_fundamentals_study(
            fundamentals_df=fund_df,
            equity_prices_df=equity_df,
            event_window_quarters=event_window_quarters,
            output_path=output_path,
        )
    except Exception as e:
        logger.error(f"Fundamentals study failed: {e}")
        raise HTTPException(status_code=500, detail=f"Fundamentals study failed: {str(e)}")

    return {
        "status": "success",
        "event_window_quarters": event_window_quarters,
        "results": results,
        "saved_to": output_path,
    }


@router.get("/fundamentals/study/latest")
async def get_latest_fundamentals_study():
    """Returns the most recently run fundamentals study results."""
    files = sorted(RESULTS_DIR.glob("fundamentals_study_*.json"))
    if not files:
        raise HTTPException(
            status_code=404,
            detail="No fundamentals study results found. Run POST /fundamentals/study first.",
        )
    with open(files[-1]) as f:
        results = json.load(f)
    return {
        "file": str(files[-1]),
        "results": results,
    }
