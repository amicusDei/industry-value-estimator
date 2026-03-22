"""
Ingestion package — data source connectors for World Bank, OECD, and LSEG.

Modules:
    world_bank: GDP, R&D, ICT indicators via wbgapi
    oecd: MSTI and AI patents via pandasdmx
    lseg: Company financials via LSEG Workspace Desktop Session
    pipeline: Config-driven orchestrator routing to source connectors

Design notes:
    All connectors return validated pandas DataFrames (pandera schemas).
    Raw data is written to data/raw/ as immutable Parquet with provenance metadata.
    The pipeline is industry-agnostic — governed entirely by config/industries/*.yaml.
"""
