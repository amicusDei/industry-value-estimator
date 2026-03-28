"""
Parquet data loader with in-memory caching and mtime-based refresh.

Caches DataFrames in memory and reloads only when the underlying file's
modification time changes. This avoids re-reading multi-MB Parquet files
on every API request.
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

_cache: dict[str, tuple[float, pd.DataFrame]] = {}


def _load_cached(filename: str) -> pd.DataFrame:
    """Load a parquet file with mtime-based caching."""
    path = DATA_DIR / filename
    if not path.exists():
        logger.warning("Data file not found: %s", path)
        return pd.DataFrame()

    mtime = path.stat().st_mtime
    if filename in _cache and _cache[filename][0] == mtime:
        return _cache[filename][1]

    df = pd.read_parquet(path)
    _cache[filename] = (mtime, df)
    logger.info("Loaded %s: %d rows", filename, len(df))
    return df


def get_forecasts() -> pd.DataFrame:
    return _load_cached("forecasts_ensemble.parquet")


def get_segments_config() -> list[dict]:
    """Return segment metadata from ai.yaml."""
    import yaml
    config_path = Path(__file__).resolve().parent.parent / "config" / "industries" / "ai.yaml"
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    return cfg.get("segments", [])


def get_companies() -> pd.DataFrame:
    return _load_cached("revenue_attribution_ai.parquet")


def get_backtesting() -> pd.DataFrame:
    return _load_cached("backtesting_results.parquet")


def get_market_anchors() -> pd.DataFrame:
    return _load_cached("market_anchors_ai.parquet")
