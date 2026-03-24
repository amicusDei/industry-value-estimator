"""
Test scaffold for MODL-02: AI revenue attribution for mixed-tech public companies.

Wave 0 scaffold: stub YAML loads and schema validation tests are live.
Plan 10-02 implementation tests are now fully active.

Test classes:
- TestAttributionRegistry: validates the stub YAML registry structure and schema compliance
- TestCompileAttribution: validates compile_and_write_attribution() output
- TestPurePlayMethod: validates pure-play companies use direct_disclosure
- TestAllCompaniesHaveBounds: validates uncertainty bounds for all companies
"""
import pandas as pd
import pytest
import yaml
from pathlib import Path

from src.processing.validate import ATTRIBUTION_SCHEMA

REGISTRY_PATH = (
    Path(__file__).parent.parent
    / "data"
    / "raw"
    / "attribution"
    / "ai_attribution_registry.yaml"
)

REQUIRED_ENTRY_FIELDS = {
    "company_name",
    "cik",
    "value_chain_layer",
    "ai_revenue_usd_billions",
    "attribution_method",
    "ratio_source",
    "vintage_date",
    "uncertainty_low",
    "uncertainty_high",
    "segment",
    "year",
    "estimated_flag",
}

# Pure-play CIKs that should have direct_disclosure
PURE_PLAY_CIKS = {"0001045810", "0001321655", "0001577552"}  # NVIDIA, Palantir, C3.ai


class TestAttributionRegistry:
    def test_stub_yaml_loads(self):
        """YAML loads successfully, has 'entries' key, and at least 3 entries."""
        with open(REGISTRY_PATH, "r") as f:
            registry = yaml.safe_load(f)
        assert isinstance(registry, dict), "Registry must be a dict"
        assert "entries" in registry, "Registry must have 'entries' key"
        entries = registry["entries"]
        assert len(entries) >= 3, f"Expected >= 3 entries, got {len(entries)}"
        # All required fields present in every entry
        for entry in entries:
            missing = REQUIRED_ENTRY_FIELDS - set(entry.keys())
            assert not missing, f"Entry '{entry.get('company_name')}' missing fields: {missing}"

    def test_schema_validates_stub(self):
        """Load stub YAML into DataFrame and validate against ATTRIBUTION_SCHEMA."""
        with open(REGISTRY_PATH, "r") as f:
            registry = yaml.safe_load(f)
        df = pd.DataFrame(registry["entries"])
        # Should not raise SchemaError
        validated = ATTRIBUTION_SCHEMA.validate(df)
        assert len(validated) >= 3

    def test_schema_rejects_missing_vintage(self):
        """ATTRIBUTION_SCHEMA rejects rows with null vintage_date."""
        import pandera.errors
        df = pd.DataFrame(
            {
                "company_name": ["Missing Vintage Co"],
                "cik": ["0001234567"],
                "value_chain_layer": ["chip"],
                "attribution_method": ["direct_disclosure"],
                "ai_revenue_usd_billions": [5.0],
                "uncertainty_low": [4.0],
                "uncertainty_high": [6.0],
                "vintage_date": [None],  # should be rejected
                "ratio_source": ["test source"],
                "segment": ["ai_hardware"],
                "year": [2024],
            }
        )
        with pytest.raises(Exception):  # pandera.errors.SchemaError
            ATTRIBUTION_SCHEMA.validate(df)

    def test_yaml_has_all_edgar_entries(self):
        """YAML registry must have entries for all 15 EDGAR companies in ai.yaml."""
        with open(REGISTRY_PATH, "r") as f:
            registry = yaml.safe_load(f)
        entries = registry["entries"]
        assert len(entries) == 15, f"Expected 15 entries (all EDGAR companies), got {len(entries)}"


class TestLoadAttributionRegistry:
    def test_load_attribution_registry_returns_dataframe(self):
        """load_attribution_registry() returns a DataFrame with all ATTRIBUTION_SCHEMA columns."""
        from src.processing.revenue_attribution import load_attribution_registry

        df = load_attribution_registry(REGISTRY_PATH)
        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 14

    def test_load_attribution_registry_has_required_columns(self):
        """load_attribution_registry() DataFrame has all ATTRIBUTION_SCHEMA columns."""
        from src.processing.revenue_attribution import load_attribution_registry

        df = load_attribution_registry(REGISTRY_PATH)
        required_cols = {
            "company_name", "cik", "value_chain_layer", "attribution_method",
            "ai_revenue_usd_billions", "uncertainty_low", "uncertainty_high",
            "vintage_date", "ratio_source", "segment", "year",
        }
        missing = required_cols - set(df.columns)
        assert not missing, f"DataFrame missing columns: {missing}"

    def test_load_attribution_registry_missing_file_raises(self):
        """load_attribution_registry() raises FileNotFoundError for missing file."""
        from src.processing.revenue_attribution import load_attribution_registry

        with pytest.raises(FileNotFoundError):
            load_attribution_registry(Path("/nonexistent/path.yaml"))

    def test_load_attribution_registry_missing_entries_key_raises(self):
        """load_attribution_registry() raises KeyError when YAML has no 'entries' key."""
        from src.processing.revenue_attribution import load_attribution_registry
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("notentries:\n  - {}\n")
            tmp_path = f.name

        try:
            with pytest.raises(KeyError):
                load_attribution_registry(Path(tmp_path))
        finally:
            os.unlink(tmp_path)


class TestEstimateAiRevenue:
    def test_estimate_ai_revenue_pure_play_nvidia(self):
        """estimate_ai_revenue for NVIDIA returns ratio=1.0 and direct_disclosure."""
        from src.processing.revenue_attribution import estimate_ai_revenue

        result = estimate_ai_revenue(
            company_revenue=47.5,
            cik="0001045810",
            attribution_config={},
            year=2024,
        )
        assert isinstance(result, dict)
        assert result["attribution_method"] == "direct_disclosure"
        assert result["ratio"] == 1.0
        assert "ai_revenue_usd" in result
        assert "uncertainty_low" in result
        assert "uncertainty_high" in result
        assert "vintage_date" in result
        assert "ratio_source" in result

    def test_estimate_ai_revenue_returns_dict_with_required_keys(self):
        """estimate_ai_revenue returns dict with all required keys."""
        from src.processing.revenue_attribution import estimate_ai_revenue

        result = estimate_ai_revenue(
            company_revenue=100.0,
            cik="0000789019",  # Microsoft
            attribution_config={},
            year=2024,
        )
        required_keys = {
            "ai_revenue_usd", "attribution_method", "ratio",
            "ratio_source", "uncertainty_low", "uncertainty_high", "vintage_date"
        }
        missing = required_keys - set(result.keys())
        assert not missing, f"Result missing keys: {missing}"


class TestCompileAttribution:
    def test_compile_attribution_creates_parquet(self):
        """compile_and_write_attribution('ai') creates revenue_attribution_ai.parquet."""
        from src.processing.revenue_attribution import compile_and_write_attribution

        output_path = compile_and_write_attribution("ai")
        assert output_path.exists(), f"Parquet file not found at {output_path}"
        assert output_path.name == "revenue_attribution_ai.parquet"

    def test_compile_attribution_has_15_rows(self):
        """Compiled Parquet has 15 company rows (all EDGAR companies in ai.yaml)."""
        from src.processing.revenue_attribution import compile_and_write_attribution

        output_path = compile_and_write_attribution("ai")
        df = pd.read_parquet(output_path)
        assert len(df) == 15, f"Expected 15 rows, got {len(df)}"

    def test_compile_attribution_passes_schema(self):
        """Compiled Parquet DataFrame validates against ATTRIBUTION_SCHEMA."""
        from src.processing.revenue_attribution import compile_and_write_attribution

        output_path = compile_and_write_attribution("ai")
        df = pd.read_parquet(output_path)
        validated = ATTRIBUTION_SCHEMA.validate(df)
        assert len(validated) == 15

    def test_compile_attribution_no_null_uncertainty(self):
        """Compiled Parquet has no null uncertainty_low or uncertainty_high."""
        from src.processing.revenue_attribution import compile_and_write_attribution

        output_path = compile_and_write_attribution("ai")
        df = pd.read_parquet(output_path)
        assert df["uncertainty_low"].notna().all(), "Found null uncertainty_low values"
        assert df["uncertainty_high"].notna().all(), "Found null uncertainty_high values"

    def test_compile_attribution_has_provenance_metadata(self):
        """Compiled Parquet has pyarrow provenance metadata."""
        import pyarrow.parquet as pq
        from src.processing.revenue_attribution import compile_and_write_attribution

        output_path = compile_and_write_attribution("ai")
        table = pq.read_table(output_path)
        meta = table.schema.metadata
        assert meta is not None, "Parquet file has no schema metadata"
        assert b"source" in meta, "Parquet metadata missing 'source' key"
        assert b"compiled_at" in meta, "Parquet metadata missing 'compiled_at' key"

    def test_compile_attribution_returns_path(self):
        """compile_and_write_attribution() returns a Path object."""
        from src.processing.revenue_attribution import compile_and_write_attribution

        result = compile_and_write_attribution("ai")
        assert isinstance(result, Path), f"Expected Path, got {type(result)}"


class TestPurePlayMethod:
    def test_pure_play_companies_use_direct_disclosure(self):
        """NVIDIA, Palantir, and C3.ai all have attribution_method='direct_disclosure'."""
        from src.processing.revenue_attribution import compile_and_write_attribution

        output_path = compile_and_write_attribution("ai")
        df = pd.read_parquet(output_path)

        pure_play_df = df[df["cik"].isin(PURE_PLAY_CIKS)]
        assert len(pure_play_df) == 3, (
            f"Expected 3 pure-play companies, got {len(pure_play_df)}: "
            f"{pure_play_df['company_name'].tolist()}"
        )
        for _, row in pure_play_df.iterrows():
            assert row["attribution_method"] == "direct_disclosure", (
                f"{row['company_name']} expected 'direct_disclosure', "
                f"got '{row['attribution_method']}'"
            )


class TestAllCompaniesHaveBounds:
    def test_all_companies_have_valid_uncertainty_bounds(self):
        """Every company has uncertainty_low <= ai_revenue_usd_billions <= uncertainty_high."""
        from src.processing.revenue_attribution import compile_and_write_attribution

        output_path = compile_and_write_attribution("ai")
        df = pd.read_parquet(output_path)

        for _, row in df.iterrows():
            company = row["company_name"]
            low = row["uncertainty_low"]
            rev = row["ai_revenue_usd_billions"]
            high = row["uncertainty_high"]
            assert low <= rev, (
                f"{company}: uncertainty_low ({low}) > ai_revenue ({rev})"
            )
            assert rev <= high, (
                f"{company}: ai_revenue ({rev}) > uncertainty_high ({high})"
            )

    def test_bundled_companies_have_wider_bounds_than_pure_play(self):
        """Bundled companies have wider relative uncertainty than pure-play companies."""
        from src.processing.revenue_attribution import compile_and_write_attribution

        output_path = compile_and_write_attribution("ai")
        df = pd.read_parquet(output_path)

        pure_play = df[df["cik"].isin(PURE_PLAY_CIKS)]
        bundled = df[~df["cik"].isin(PURE_PLAY_CIKS)]

        # Relative range: (high - low) / revenue
        pure_play_range = (
            (pure_play["uncertainty_high"] - pure_play["uncertainty_low"])
            / pure_play["ai_revenue_usd_billions"]
        ).mean()
        bundled_range = (
            (bundled["uncertainty_high"] - bundled["uncertainty_low"])
            / bundled["ai_revenue_usd_billions"]
        ).mean()

        assert bundled_range > pure_play_range, (
            f"Expected bundled uncertainty range ({bundled_range:.2%}) > "
            f"pure-play range ({pure_play_range:.2%})"
        )
