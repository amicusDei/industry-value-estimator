"""
SEC EDGAR XBRL extraction for AI company segment revenue.

Uses edgartools to fetch 10-K/10-Q filings and extract XBRL revenue concepts.
Phase 8 collects raw filings only — revenue attribution math is deferred to Phase 10.

Companies where AI revenue is bundled into larger segments (e.g., Microsoft Azure,
Amazon AWS) have bundled_flag=True to signal Phase 10 that attribution is required.

SEC requires a User-Agent email header — call set_edgar_identity() before any fetch.

Usage:
    set_edgar_identity(os.environ["EDGAR_USER_EMAIL"])
    config = load_industry_config("ai")
    df = fetch_all_edgar_companies(config)
"""
import logging
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime, timezone
from pathlib import Path
from edgar import Company, set_identity

from config.settings import DATA_RAW, load_industry_config  # noqa: F401

logger = logging.getLogger(__name__)

# Standard XBRL concepts to extract — in priority order (first non-null wins)
XBRL_CONCEPTS = [
    "us-gaap:Revenues",
    "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
    "us-gaap:SegmentReportingInformationRevenue",
    "us-gaap:SalesRevenueNet",
]

# Companies where AI revenue is bundled into a larger segment
# Phase 10 resolution: both Accenture ($3B+ AI consulting, FY2024) and Salesforce
# (Einstein/Agentforce AI revenue, material and growing) are included. Accenture
# stays because its AI consulting revenue is explicitly tracked in management commentary.
# Salesforce added per CONTEXT.md locked decision — AI attribution required.
BUNDLED_SEGMENT_COMPANIES = {
    "0000789019",  # Microsoft
    "0001018724",  # Amazon
    "0001652044",  # Alphabet
    "0001326801",  # Meta
    "0000051143",  # IBM
    "0001281761",  # Accenture
    "0001108524",  # Salesforce (added Phase 10 — Einstein/Agentforce AI attribution required)
}


def set_edgar_identity(email: str) -> None:
    """Set SEC EDGAR user agent identity. Must be called before any fetch."""
    set_identity(email)


def fetch_company_filings(
    cik: str,
    company_name: str,
    form_types: list[str],
    start_year: int,
    end_year: int,
    value_chain_layer: str,
) -> pd.DataFrame:
    """
    Fetch XBRL segment revenue for one company.

    For each filing, queries XBRL_CONCEPTS in priority order — the first concept
    that returns at least one row of data is used (priority fallback pattern).

    Parameters
    ----------
    cik : str
        SEC CIK number, e.g. "0001045810".
    company_name : str
        Display name for the company.
    form_types : list[str]
        Filing form types to fetch, e.g. ["10-K", "10-Q"] or ["20-F"].
    start_year : int
        First fiscal year to include (inclusive).
    end_year : int
        Last fiscal year to include (inclusive).
    value_chain_layer : str
        Value chain layer from ai.yaml (ai_hardware, ai_infrastructure, etc.)

    Returns
    -------
    pd.DataFrame
        Columns: cik, company_name, period_end, form_type, xbrl_concept,
        value_usd, bundled_flag, value_chain_layer
    """
    rows = []
    bundled_flag = cik in BUNDLED_SEGMENT_COMPANIES
    date_filter = f"{start_year}-01-01:{end_year}-12-31"

    company = Company(cik)

    for form_type in form_types:
        try:
            filings = company.get_filings(form=form_type)
            filings = filings.filter(date=date_filter)
            for filing in filings:
                try:
                    xbrl = filing.xbrl()
                    if xbrl is None:
                        logger.debug(
                            "No XBRL for %s %s filing %s",
                            company_name, form_type, filing.period_of_report,
                        )
                        continue

                    # Priority fallback: first concept with data wins.
                    # API: facts.get_facts_by_concept(concept) returns a DataFrame
                    # with columns including numeric_value, period_end, is_dimensioned.
                    # We select non-dimensioned annual (duration) rows for total revenue.
                    for concept in XBRL_CONCEPTS:
                        try:
                            facts_df = xbrl.facts.get_facts_by_concept(concept)
                            if facts_df is not None and len(facts_df) > 0:
                                # Filter to non-dimensioned annual (duration) facts only
                                # to get top-level total revenue, not segment sub-totals
                                if "is_dimensioned" in facts_df.columns:
                                    total_df = facts_df[~facts_df["is_dimensioned"]]
                                else:
                                    total_df = facts_df
                                if "period_type" in total_df.columns:
                                    total_df = total_df[total_df["period_type"] == "duration"]
                                if total_df.empty:
                                    total_df = facts_df  # fallback: use all rows if filter empties

                                for _, fact_row in total_df.iterrows():
                                    # Use numeric_value (float) or fall back to value (string)
                                    raw_value = fact_row.get("numeric_value")
                                    if raw_value is None or (hasattr(raw_value, '__float__') and pd.isna(raw_value)):
                                        raw_str = fact_row.get("value")
                                        try:
                                            raw_value = float(raw_str) if raw_str not in (None, "") else None
                                        except (ValueError, TypeError):
                                            raw_value = None
                                    rows.append({
                                        "cik": cik,
                                        "company_name": company_name,
                                        "period_end": str(fact_row.get("period_end", filing.period_of_report)),
                                        "form_type": form_type,
                                        "xbrl_concept": concept,
                                        "value_usd": float(raw_value) if raw_value is not None else None,
                                        "bundled_flag": bundled_flag,
                                        "value_chain_layer": value_chain_layer,
                                    })
                                break  # first concept with data wins
                        except Exception as concept_err:
                            logger.debug(
                                "Concept %s failed for %s: %s",
                                concept, company_name, concept_err,
                            )
                            continue
                except Exception as filing_err:
                    logger.warning(
                        "Failed to process filing for %s: %s",
                        company_name, filing_err,
                    )
                    continue
        except Exception as form_err:
            logger.warning(
                "Failed to fetch %s filings for %s (CIK %s): %s",
                form_type, company_name, cik, form_err,
            )
            continue

    if not rows:
        logger.info("No XBRL data extracted for %s (CIK %s)", company_name, cik)
        # Return empty DataFrame with correct schema so concatenation works
        return pd.DataFrame(columns=[
            "cik", "company_name", "period_end", "form_type",
            "xbrl_concept", "value_usd", "bundled_flag", "value_chain_layer",
        ])

    return pd.DataFrame(rows)


def fetch_all_edgar_companies(config: dict) -> pd.DataFrame:
    """
    Fetch filings for all companies in config["edgar_companies"].

    Reads edgar_companies list from the industry config (ai.yaml),
    calls fetch_company_filings per company, concatenates results,
    and sets bundled_flag based on BUNDLED_SEGMENT_COMPANIES.

    Parameters
    ----------
    config : dict
        Industry config loaded from YAML via load_industry_config().
        Must have key: edgar_companies (list of company dicts).

    Returns
    -------
    pd.DataFrame
        Concatenated DataFrame with columns: cik, company_name, period_end,
        form_type, xbrl_concept, value_usd, bundled_flag, value_chain_layer.
    """
    companies = config.get("edgar_companies", [])
    if not companies:
        logger.warning("No edgar_companies found in config")
        return pd.DataFrame(columns=[
            "cik", "company_name", "period_end", "form_type",
            "xbrl_concept", "value_usd", "bundled_flag", "value_chain_layer",
        ])

    all_dfs = []
    for company_cfg in companies:
        cik = company_cfg["cik"]
        company_name = company_cfg["name"]
        value_chain_layer = company_cfg.get("value_chain_layer", "")
        # Default form types unless overridden per company (20-F filers like TSMC/Accenture)
        form_types = company_cfg.get("form_types", ["10-K", "10-Q"])

        try:
            df = fetch_company_filings(
                cik=cik,
                company_name=company_name,
                form_types=form_types,
                start_year=2020,
                end_year=2024,
                value_chain_layer=value_chain_layer,
            )
            all_dfs.append(df)
        except Exception as e:
            logger.error(
                "fetch_company_filings failed for %s (CIK %s): %s",
                company_name, cik, e,
            )
            # Append a stub row so this company is represented in output
            all_dfs.append(pd.DataFrame([{
                "cik": cik,
                "company_name": company_name,
                "period_end": "",
                "form_type": form_types[0] if form_types else "10-K",
                "xbrl_concept": "",
                "value_usd": None,
                "bundled_flag": cik in BUNDLED_SEGMENT_COMPANIES,
                "value_chain_layer": value_chain_layer,
            }]))

    if not all_dfs:
        return pd.DataFrame(columns=[
            "cik", "company_name", "period_end", "form_type",
            "xbrl_concept", "value_usd", "bundled_flag", "value_chain_layer",
        ])

    result = pd.concat(all_dfs, ignore_index=True)
    return result


def save_raw_edgar(df: pd.DataFrame, industry_id: str) -> Path:
    """
    Save raw EDGAR DataFrame to data/raw/edgar/ as Parquet with provenance metadata.

    Provenance metadata (source, industry, fetch timestamp) is embedded directly
    in the Parquet file schema metadata using pyarrow — follows the same pattern
    as save_raw_world_bank() in world_bank.py.

    Raw data is NEVER modified after writing. Re-fetches write new timestamped files.

    Parameters
    ----------
    df : pd.DataFrame
        Validated EDGAR DataFrame from fetch_all_edgar_companies().
    industry_id : str
        Industry identifier for filename namespacing (e.g. "ai").

    Returns
    -------
    Path
        Path to the written Parquet file.
    """
    output_dir = DATA_RAW / "edgar"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"edgar_{industry_id}_raw.parquet"

    table = pa.Table.from_pandas(df, preserve_index=False)
    existing_meta = table.schema.metadata or {}
    custom_meta = {
        b"source": b"edgar",
        b"industry": industry_id.encode(),
        b"fetched_at": datetime.now(tz=timezone.utc).isoformat().encode(),
    }
    table = table.replace_schema_metadata({**existing_meta, **custom_meta})
    pq.write_table(table, output_path, compression="snappy")

    return output_path
