"""
Ingestion pipeline orchestrator.

Reads the industry config and routes to the appropriate data source connectors.
The pipeline is industry-agnostic: it processes whatever sources are declared
in the industry YAML config file.

Usage:
    results = run_ingestion("ai")
    # results = {"World Bank indicators": Path, "OECD MSTI": Path, "OECD AI Patents": Path}
"""
from pathlib import Path
from tqdm import tqdm

from config.settings import load_industry_config
from src.ingestion.world_bank import fetch_world_bank_indicators, save_raw_world_bank
from src.ingestion.oecd import fetch_oecd_msti, fetch_oecd_ai_patents, save_raw_oecd


def run_ingestion(industry_id: str, include_lseg: bool = False) -> dict[str, Path]:
    """
    Run the full ingestion pipeline for an industry.

    Parameters
    ----------
    industry_id : str
        Industry identifier matching a YAML in config/industries/
    include_lseg : bool
        Whether to include LSEG ingestion (requires Workspace running).
        Default False — LSEG connector is separate and optional.

    Returns
    -------
    dict mapping source name to output Parquet path
    """
    config = load_industry_config(industry_id)
    results = {}

    steps = [
        ("World Bank indicators", _ingest_world_bank),
        ("OECD MSTI", _ingest_oecd_msti),
        ("OECD AI Patents", _ingest_oecd_patents),
    ]

    if include_lseg:
        steps.append(("LSEG company data", _ingest_lseg))

    for step_name, step_fn in tqdm(steps, desc=f"Ingesting {industry_id}"):
        path = step_fn(config, industry_id)
        results[step_name] = path

    return results


def _ingest_world_bank(config: dict, industry_id: str) -> Path:
    df = fetch_world_bank_indicators(config)
    return save_raw_world_bank(df, industry_id)


def _ingest_oecd_msti(config: dict, industry_id: str) -> Path:
    df = fetch_oecd_msti(config)
    return save_raw_oecd(df, "msti", industry_id)


def _ingest_oecd_patents(config: dict, industry_id: str) -> Path:
    df = fetch_oecd_ai_patents(config)
    return save_raw_oecd(df, "pats_ipc", industry_id)


def _ingest_lseg(config: dict, industry_id: str) -> Path:
    from src.ingestion.lseg import fetch_lseg_companies, save_raw_lseg
    df = fetch_lseg_companies(config)
    return save_raw_lseg(df, industry_id)
