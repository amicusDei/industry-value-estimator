"""
Processing package — data transformation pipeline from raw ingested data to validated Parquet.

Modules:
    deflate: CPI deflation of nominal USD series to constant base-year USD (2020=100)
    interpolate: Missing value interpolation with estimated_flag transparency
    tag: Industry and segment tagging from config YAML (no hardcoded codes)
    normalize: Full normalization orchestrator (deflate → interpolate → tag → validate)
    validate: Pandera DataFrame schemas for raw and processed layer validation
    features: Feature engineering — PCA composite index, stationarity tests

Design notes:
    Every nominal monetary column is deflated before reaching data/processed/ (enforced by
    validate.check_no_nominal_columns). This is non-negotiable for analytical integrity.
    All interpolated values are flagged with estimated_flag=True for downstream transparency.
"""
