"""
Tests for the analyst registry YAML and market_anchors.py ingestion module (DATA-09).

Test classes:
- TestAnalystRegistry: validates the YAML registry structure and content
- TestScopeNormalization: validates scope_normalize() function correctness
- TestMarketAnchorSchema: validates compiled DataFrame schema compliance
- TestSourceCoverage: validates per-year source coverage requirements
- TestCompileMarketAnchors: validates compile_market_anchors() pipeline output
"""
import yaml
import pandas as pd
import pytest
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent.parent / "data" / "raw" / "market_anchors" / "ai_analyst_registry.yaml"

VALID_SEGMENTS = {"total", "ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"}
REQUIRED_ENTRY_FIELDS = {
    "source_firm",
    "publication_year",
    "estimate_year",
    "segment",
    "as_published_usd_billions",
    "scope_includes",
    "scope_excludes",
    "methodology_notes",
    "confidence",
}


@pytest.fixture
def registry() -> dict:
    """Load the YAML registry once and share across tests."""
    with open(REGISTRY_PATH, "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def entries(registry) -> list:
    """Return the list of entries from the registry."""
    return registry["entries"]


class TestAnalystRegistry:
    def test_registry_loads(self, registry):
        """YAML loads successfully and has top-level 'entries' key."""
        assert isinstance(registry, dict)
        assert "entries" in registry

    def test_minimum_entries(self, entries):
        """Registry has at least 40 entries."""
        assert len(entries) >= 40, f"Expected >= 40 entries, got {len(entries)}"

    def test_required_fields(self, entries):
        """Every entry has all required fields with non-null values."""
        for i, entry in enumerate(entries):
            for field in REQUIRED_ENTRY_FIELDS:
                assert field in entry, f"Entry {i} missing field '{field}': {entry.get('source_firm', '?')}"
                assert entry[field] is not None, (
                    f"Entry {i} field '{field}' is None for {entry.get('source_firm', '?')}"
                )

    def test_segment_values(self, entries):
        """Every entry's segment is one of the valid segment values."""
        for i, entry in enumerate(entries):
            assert entry["segment"] in VALID_SEGMENTS, (
                f"Entry {i} has invalid segment '{entry['segment']}' "
                f"(firm={entry.get('source_firm', '?')}, year={entry.get('estimate_year', '?')})"
            )

    def test_vintage_coverage(self, entries):
        """Publication years span at least 2019 to 2025."""
        pub_years = {entry["publication_year"] for entry in entries}
        assert min(pub_years) <= 2019, f"Oldest publication_year is {min(pub_years)}, expected <= 2019"
        assert max(pub_years) >= 2025, f"Newest publication_year is {max(pub_years)}, expected >= 2025"


class TestScopeNormalization:
    def test_normalize_idc(self):
        """IDC estimate with scope_coefficient 1.0 returns unchanged value."""
        from src.ingestion.market_anchors import scope_normalize
        result = scope_normalize(207.0, 1.0)
        assert abs(result - 207.0) < 0.001, f"Expected ~207.0, got {result}"

    def test_normalize_gartner(self):
        """Gartner $1500B with scope_coefficient 0.18 returns ~$270B."""
        from src.ingestion.market_anchors import scope_normalize
        result = scope_normalize(1500.0, 0.18)
        assert abs(result - 270.0) < 0.01, f"Expected ~270.0, got {result}"

    def test_normalize_zero_returns_zero(self):
        """Zero input returns zero regardless of coefficient."""
        from src.ingestion.market_anchors import scope_normalize
        assert scope_normalize(0.0, 0.85) == 0.0

    def test_normalize_proportional(self):
        """Scope normalization is purely multiplicative (proportional)."""
        from src.ingestion.market_anchors import scope_normalize
        assert abs(scope_normalize(100.0, 0.5) - 50.0) < 0.001


class TestMarketAnchorSchema:
    def test_compiled_df_validates(self):
        """Compiled DataFrame passes MARKET_ANCHOR_SCHEMA.validate() without error."""
        from src.ingestion.market_anchors import compile_market_anchors, validate_market_anchors
        df = compile_market_anchors("ai")
        result = validate_market_anchors(df)
        assert result is not None
        assert len(result) > 0

    def test_has_both_nominal_and_real(self):
        """Compiled DataFrame has _nominal columns (real_2020 is Plan 08-04 responsibility)."""
        from src.ingestion.market_anchors import compile_market_anchors
        df = compile_market_anchors("ai")
        # Plan 08-02 outputs nominal only; real_2020 deflation is done in Plan 08-04
        nominal_cols = [c for c in df.columns if "nominal" in c]
        assert len(nominal_cols) >= 1, f"Expected at least one _nominal column, got: {df.columns.tolist()}"


class TestSourceCoverage:
    def test_per_year_source_count(self):
        """For years 2020-2024, the compiled DataFrame has n_sources >= 3."""
        from src.ingestion.market_anchors import compile_market_anchors
        df = compile_market_anchors("ai")
        for year in range(2020, 2025):
            year_rows = df[df["estimate_year"] == year]
            if len(year_rows) == 0:
                pytest.fail(f"No rows for estimate_year={year}")
            max_sources = year_rows["n_sources"].max()
            assert max_sources >= 3, (
                f"Year {year}: max n_sources={max_sources}, expected >= 3. "
                f"Rows: {year_rows[['segment', 'n_sources']].to_dict('records')}"
            )


class TestCompileMarketAnchors:
    def test_compile_returns_dataframe(self):
        """compile_market_anchors('ai') returns a non-empty pd.DataFrame."""
        from src.ingestion.market_anchors import compile_market_anchors
        df = compile_market_anchors("ai")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_percentile_ordering(self):
        """p25 <= median <= p75 for all rows in the compiled DataFrame."""
        from src.ingestion.market_anchors import compile_market_anchors
        df = compile_market_anchors("ai")
        for i, row in df.iterrows():
            assert row["p25_usd_billions_nominal"] <= row["median_usd_billions_nominal"], (
                f"Row {i}: p25 ({row['p25_usd_billions_nominal']}) > median ({row['median_usd_billions_nominal']})"
            )
            assert row["median_usd_billions_nominal"] <= row["p75_usd_billions_nominal"], (
                f"Row {i}: median ({row['median_usd_billions_nominal']}) > p75 ({row['p75_usd_billions_nominal']})"
            )

    def test_expected_columns(self):
        """Compiled DataFrame has all expected columns."""
        from src.ingestion.market_anchors import compile_market_anchors
        df = compile_market_anchors("ai")
        expected_cols = {
            "estimate_year", "segment",
            "p25_usd_billions_nominal", "median_usd_billions_nominal", "p75_usd_billions_nominal",
            "n_sources", "source_list", "estimated_flag",
        }
        missing = expected_cols - set(df.columns)
        assert not missing, f"Missing columns: {missing}"

    def test_segment_values_in_compiled(self):
        """All segments in compiled output are valid segment values."""
        from src.ingestion.market_anchors import compile_market_anchors
        df = compile_market_anchors("ai")
        for seg in df["segment"].unique():
            assert seg in VALID_SEGMENTS, f"Invalid segment in compiled output: {seg}"

    def test_load_analyst_registry_returns_dataframe(self):
        """load_analyst_registry() returns a DataFrame with all YAML entry fields."""
        from src.ingestion.market_anchors import load_analyst_registry
        df = load_analyst_registry(REGISTRY_PATH)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        for field in REQUIRED_ENTRY_FIELDS:
            assert field in df.columns, f"Missing column '{field}' in registry DataFrame"
