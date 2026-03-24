"""
Ingestion pipeline orchestrator.

Reads the industry config and routes to the appropriate data source connectors.
The pipeline is industry-agnostic: it processes whatever sources are declared
in the industry YAML config file — no hardcoded source list in this module.

Config-driven design (ARCH-01): adding a new data source requires only updating
config/industries/{id}.yaml and adding a connector module. The orchestrator
automatically picks it up via the steps list pattern.

Error isolation: each source step in run_full_pipeline is wrapped in try/except so
a single API failure (e.g., OECD timeout) does not abort the pipeline. Partial
results are returned, allowing downstream processing to proceed with whatever data
was successfully fetched.

Usage:
    results = run_ingestion("ai")
    # results = {"World Bank indicators": Path, "OECD MSTI": Path, "OECD AI Patents": Path}

    processed = run_full_pipeline("ai")
    # processed = {"world_bank": Path, "oecd_msti": Path, "oecd_patents": Path}
"""
from pathlib import Path
from tqdm import tqdm

from config.settings import load_industry_config
from src.ingestion.world_bank import fetch_world_bank_indicators, save_raw_world_bank
from src.ingestion.oecd import fetch_oecd_msti, fetch_oecd_ai_patents, save_raw_oecd
from src.processing.normalize import (
    normalize_world_bank,
    normalize_oecd,
    normalize_lseg,
    write_processed_parquet,
)


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


def run_full_pipeline(
    industry_id: str,
    include_lseg: bool = False,
    include_edgar: bool = False,
) -> dict[str, Path]:
    """
    Run the complete pipeline: ingest raw data, normalize, and write processed Parquet.

    This function is industry-agnostic — it reads whatever config is in
    config/industries/{industry_id}.yaml and processes accordingly.

    Each source step is wrapped in a try/except so a single source failure does
    not abort the entire pipeline. Partial results are returned.

    Parameters
    ----------
    industry_id : str
        Industry identifier matching a YAML in config/industries/
    include_lseg : bool
        Whether to include LSEG data (requires Workspace running)
    include_edgar : bool
        Whether to include EDGAR ingestion (requires EDGAR_USER_EMAIL env var).
        Makes live SEC API calls — set True only when EDGAR data is needed.

    Returns
    -------
    dict mapping output name to processed Parquet path
    """
    config = load_industry_config(industry_id)
    processed_paths = {}

    # Step 1: Ingest World Bank
    try:
        wb_raw = fetch_world_bank_indicators(config)
        save_raw_world_bank(wb_raw, industry_id)
        # Step 2: Normalize World Bank
        wb_processed = normalize_world_bank(wb_raw, config)
        wb_path = write_processed_parquet(
            wb_processed,
            f"world_bank_{industry_id}.parquet",
            source="world_bank",
            industry_id=industry_id,
        )
        processed_paths["world_bank"] = wb_path
    except Exception as e:
        print(f"World Bank ingestion failed: {e}")

    # Step 3: Ingest OECD MSTI
    try:
        msti_raw = fetch_oecd_msti(config)
        save_raw_oecd(msti_raw, "msti", industry_id)
        msti_processed = normalize_oecd(msti_raw, config, "msti")
        msti_path = write_processed_parquet(
            msti_processed,
            f"oecd_msti_{industry_id}.parquet",
            source="oecd",
            industry_id=industry_id,
        )
        processed_paths["oecd_msti"] = msti_path
    except Exception as e:
        print(f"OECD MSTI ingestion failed: {e}")

    # Step 4: Ingest OECD Patents
    try:
        patents_raw = fetch_oecd_ai_patents(config)
        save_raw_oecd(patents_raw, "pats_ipc", industry_id)
        patents_processed = normalize_oecd(patents_raw, config, "pats_ipc")
        patents_path = write_processed_parquet(
            patents_processed,
            f"oecd_pats_{industry_id}.parquet",
            source="oecd",
            industry_id=industry_id,
        )
        processed_paths["oecd_patents"] = patents_path
    except Exception as e:
        print(f"OECD Patents ingestion failed: {e}")

    # Step 5: Ingest LSEG (optional)
    if include_lseg:
        try:
            from src.ingestion.lseg import (
                open_lseg_session,
                close_lseg_session,
                fetch_lseg_companies,
                fetch_company_financials,
                save_raw_lseg,
            )
            # Open Desktop Session before fetching — requires LSEG Workspace running
            open_lseg_session()
            companies = fetch_lseg_companies(config)
            financials = fetch_company_financials(companies, config)
            save_raw_lseg(financials, industry_id)
            lseg_processed = normalize_lseg(financials, config)
            lseg_path = write_processed_parquet(
                lseg_processed,
                f"lseg_{industry_id}.parquet",
                source="lseg",
                industry_id=industry_id,
            )
            processed_paths["lseg"] = lseg_path
            close_lseg_session()
        except Exception as e:
            print(f"LSEG ingestion failed: {e}")
            # Attempt graceful session close even on failure
            try:
                close_lseg_session()
            except Exception:
                pass

    # Step 6: Compile market anchors (YAML registry -> reconciled Parquet)
    try:
        from src.ingestion.market_anchors import compile_and_write_market_anchors
        anchors_path = compile_and_write_market_anchors(industry_id)
        processed_paths["market_anchors"] = anchors_path
    except Exception as e:
        print(f"Market anchors compilation failed: {e}")

    # Step 7: Ingest EDGAR company filings (requires SEC identity)
    if include_edgar:
        try:
            import os
            from src.ingestion.edgar import (
                set_edgar_identity,
                fetch_all_edgar_companies,
                save_raw_edgar,
            )
            from src.processing.validate import EDGAR_RAW_SCHEMA
            edgar_email = os.environ.get("EDGAR_USER_EMAIL")
            if not edgar_email:
                print("EDGAR_USER_EMAIL not set — skipping EDGAR ingestion")
            else:
                set_edgar_identity(edgar_email)
                edgar_df = fetch_all_edgar_companies(config)
                EDGAR_RAW_SCHEMA.validate(edgar_df)
                edgar_path = save_raw_edgar(edgar_df, industry_id)
                processed_paths["edgar"] = edgar_path
        except Exception as e:
            print(f"EDGAR ingestion failed: {e}")

    # Step 8: AI revenue attribution for bundled-segment public companies (Plan 10-02)
    try:
        from src.processing.revenue_attribution import compile_and_write_attribution
        attribution_path = compile_and_write_attribution(industry_id)
        processed_paths["revenue_attribution"] = attribution_path
    except Exception as e:
        print(f"Revenue attribution failed: {e}")

    # Step 9: Private company valuations (compile YAML registry to Parquet)
    try:
        from src.processing.private_valuations import compile_and_write_private_valuations
        private_path = compile_and_write_private_valuations(industry_id)
        processed_paths["private_valuations"] = private_path
    except Exception as e:
        print(f"Private valuations failed: {e}")

    return processed_paths
