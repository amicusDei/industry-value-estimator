"""
Tests for MODL-03: Private company valuation via comparable multiples.

Test classes:
- TestPrivateValuationRegistry: validates the YAML registry structure and schema compliance
- TestPrivateValuationsModule: validates load_private_registry, apply_comparable_multiples,
  compile_and_write_private_valuations from src.processing.private_valuations
"""
import pandas as pd
import pytest
import yaml
from pathlib import Path

from src.processing.validate import PRIVATE_VALUATION_SCHEMA

REGISTRY_PATH = (
    Path(__file__).parent.parent
    / "data"
    / "raw"
    / "private_companies"
    / "ai_private_registry.yaml"
)

REQUIRED_ENTRY_FIELDS = {
    "company_name",
    "confidence_tier",
    "last_funding_valuation_usd_billions",
    "funding_date",
    "estimated_arr_usd_billions",
    "arr_source",
    "comparable_low_multiple",
    "comparable_mid_multiple",
    "comparable_high_multiple",
    "comparable_peer_group",
    "implied_ev_low",
    "implied_ev_mid",
    "implied_ev_high",
    "segment",
    "vintage_date",
}


class TestPrivateValuationRegistry:
    def test_stub_yaml_loads(self):
        """YAML loads successfully, has 'entries' key, and at least 15 entries."""
        with open(REGISTRY_PATH, "r") as f:
            registry = yaml.safe_load(f)
        assert isinstance(registry, dict), "Registry must be a dict"
        assert "entries" in registry, "Registry must have 'entries' key"
        entries = registry["entries"]
        assert len(entries) >= 15, f"Expected >= 15 entries, got {len(entries)}"
        # All required fields present in every entry
        for entry in entries:
            missing = REQUIRED_ENTRY_FIELDS - set(entry.keys())
            assert not missing, f"Entry '{entry.get('company_name')}' missing fields: {missing}"

    def test_schema_validates_stub(self):
        """Load YAML into DataFrame and validate against PRIVATE_VALUATION_SCHEMA."""
        with open(REGISTRY_PATH, "r") as f:
            registry = yaml.safe_load(f)
        df = pd.DataFrame(registry["entries"])
        # Should not raise SchemaError
        validated = PRIVATE_VALUATION_SCHEMA.validate(df)
        assert len(validated) >= 15

    def test_ev_ordering(self):
        """Assert implied_ev_low <= implied_ev_mid <= implied_ev_high for all entries."""
        with open(REGISTRY_PATH, "r") as f:
            registry = yaml.safe_load(f)
        for entry in registry["entries"]:
            name = entry["company_name"]
            assert entry["implied_ev_low"] <= entry["implied_ev_mid"], (
                f"{name}: implied_ev_low ({entry['implied_ev_low']}) > implied_ev_mid ({entry['implied_ev_mid']})"
            )
            assert entry["implied_ev_mid"] <= entry["implied_ev_high"], (
                f"{name}: implied_ev_mid ({entry['implied_ev_mid']}) > implied_ev_high ({entry['implied_ev_high']})"
            )

    def test_all_confidence_tiers_in_registry(self):
        """Registry must contain entries for HIGH, MEDIUM, and LOW confidence tiers."""
        with open(REGISTRY_PATH, "r") as f:
            registry = yaml.safe_load(f)
        tiers = {entry["confidence_tier"] for entry in registry["entries"]}
        assert "HIGH" in tiers, "Registry must have at least one HIGH confidence entry"
        assert "MEDIUM" in tiers, "Registry must have at least one MEDIUM confidence entry"
        assert "LOW" in tiers, "Registry must have at least one LOW confidence entry"

    def test_no_missing_vintage_dates_in_registry(self):
        """All YAML entries must have a non-empty vintage_date."""
        with open(REGISTRY_PATH, "r") as f:
            registry = yaml.safe_load(f)
        for entry in registry["entries"]:
            name = entry.get("company_name", "unknown")
            assert entry.get("vintage_date"), f"Entry '{name}' has missing vintage_date"

    def test_multiples_reasonable_in_registry(self):
        """All entries must have comparable_mid_multiple in [1.0, 300.0]."""
        with open(REGISTRY_PATH, "r") as f:
            registry = yaml.safe_load(f)
        for entry in registry["entries"]:
            name = entry.get("company_name", "unknown")
            mid = entry.get("comparable_mid_multiple", 0)
            assert 1.0 <= mid <= 300.0, (
                f"Entry '{name}' comparable_mid_multiple={mid} outside [1.0, 300.0]"
            )


class TestApplyComparableMultiples:
    """Tests for the apply_comparable_multiples pure function."""

    def test_returns_tuple_of_three_floats(self):
        """apply_comparable_multiples returns a tuple of 3 floats."""
        from src.processing.private_valuations import apply_comparable_multiples
        result = apply_comparable_multiples(1.0, 10.0, 20.0, 30.0)
        assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
        assert len(result) == 3, f"Expected 3 values, got {len(result)}"
        low, mid, high = result
        assert isinstance(low, float), f"Expected float, got {type(low)}"
        assert isinstance(mid, float), f"Expected float, got {type(mid)}"
        assert isinstance(high, float), f"Expected float, got {type(high)}"

    def test_correct_calculation(self):
        """apply_comparable_multiples returns arr * multiples correctly."""
        from src.processing.private_valuations import apply_comparable_multiples
        low, mid, high = apply_comparable_multiples(2.0, 10.0, 20.0, 30.0)
        assert low == pytest.approx(20.0), f"Expected 20.0, got {low}"
        assert mid == pytest.approx(40.0), f"Expected 40.0, got {mid}"
        assert high == pytest.approx(60.0), f"Expected 60.0, got {high}"

    def test_ordering_preserved(self):
        """apply_comparable_multiples result is ordered low <= mid <= high."""
        from src.processing.private_valuations import apply_comparable_multiples
        low, mid, high = apply_comparable_multiples(3.4, 25.0, 40.0, 60.0)
        assert low <= mid <= high, f"Ordering violated: {low} <= {mid} <= {high}"


class TestLoadPrivateRegistry:
    """Tests for load_private_registry function."""

    def test_loads_registry_returns_dataframe(self):
        """load_private_registry returns a pandas DataFrame."""
        from src.processing.private_valuations import load_private_registry
        df = load_private_registry(REGISTRY_PATH)
        assert isinstance(df, pd.DataFrame), f"Expected DataFrame, got {type(df)}"

    def test_loads_at_least_15_companies(self):
        """load_private_registry returns DataFrame with >= 15 rows."""
        from src.processing.private_valuations import load_private_registry
        df = load_private_registry(REGISTRY_PATH)
        assert len(df) >= 15, f"Expected >= 15 rows, got {len(df)}"

    def test_loads_required_columns(self):
        """load_private_registry returns DataFrame with all required fields."""
        from src.processing.private_valuations import load_private_registry
        df = load_private_registry(REGISTRY_PATH)
        for field in REQUIRED_ENTRY_FIELDS:
            assert field in df.columns, f"Expected column '{field}' in DataFrame"

    def test_missing_file_raises_error(self):
        """load_private_registry raises FileNotFoundError for missing file."""
        from src.processing.private_valuations import load_private_registry
        with pytest.raises(FileNotFoundError):
            load_private_registry(Path("/nonexistent/path.yaml"))


class TestCompileAndWritePrivateValuations:
    """Tests for compile_and_write_private_valuations function."""

    def test_compile_private_valuations(self):
        """compile_and_write_private_valuations produces a Parquet file."""
        from src.processing.private_valuations import compile_and_write_private_valuations
        output_path = compile_and_write_private_valuations("ai")
        assert output_path.exists(), f"Expected Parquet at {output_path}, file not found"
        df = pd.read_parquet(output_path)
        assert len(df) >= 15, f"Expected >= 15 rows, got {len(df)}"
        # Verify all PRIVATE_VALUATION_SCHEMA columns present
        schema_cols = [
            "company_name", "confidence_tier", "implied_ev_low", "implied_ev_mid",
            "implied_ev_high", "segment", "vintage_date", "comparable_mid_multiple",
        ]
        for col in schema_cols:
            assert col in df.columns, f"Expected column '{col}' in output Parquet"

    def test_ev_ordering_all_rows(self):
        """All rows in compiled Parquet have implied_ev_low <= implied_ev_mid <= implied_ev_high."""
        from src.processing.private_valuations import compile_and_write_private_valuations
        output_path = compile_and_write_private_valuations("ai")
        df = pd.read_parquet(output_path)
        assert (df["implied_ev_low"] <= df["implied_ev_mid"]).all(), (
            "implied_ev_low > implied_ev_mid for some rows"
        )
        assert (df["implied_ev_mid"] <= df["implied_ev_high"]).all(), (
            "implied_ev_mid > implied_ev_high for some rows"
        )

    def test_confidence_tiers_present(self):
        """All three confidence tiers (HIGH, MEDIUM, LOW) appear in compiled output."""
        from src.processing.private_valuations import compile_and_write_private_valuations
        output_path = compile_and_write_private_valuations("ai")
        df = pd.read_parquet(output_path)
        tiers = set(df["confidence_tier"].unique())
        assert "HIGH" in tiers, f"Expected HIGH tier in output, got: {tiers}"
        assert "MEDIUM" in tiers, f"Expected MEDIUM tier in output, got: {tiers}"
        assert "LOW" in tiers, f"Expected LOW tier in output, got: {tiers}"

    def test_no_missing_vintage_dates(self):
        """vintage_date is not null/empty for any row in compiled output."""
        from src.processing.private_valuations import compile_and_write_private_valuations
        output_path = compile_and_write_private_valuations("ai")
        df = pd.read_parquet(output_path)
        assert df["vintage_date"].notna().all(), "Some rows have null vintage_date"
        assert (df["vintage_date"] != "").all(), "Some rows have empty vintage_date"

    def test_multiples_reasonable(self):
        """comparable_mid_multiple is between 1.0 and 300.0 for all rows."""
        from src.processing.private_valuations import compile_and_write_private_valuations
        output_path = compile_and_write_private_valuations("ai")
        df = pd.read_parquet(output_path)
        assert (df["comparable_mid_multiple"] >= 1.0).all(), (
            "Some rows have comparable_mid_multiple < 1.0"
        )
        assert (df["comparable_mid_multiple"] <= 300.0).all(), (
            "Some rows have comparable_mid_multiple > 300.0"
        )

    def test_returns_path_ending_in_parquet(self):
        """compile_and_write_private_valuations returns a Path ending in .parquet."""
        from src.processing.private_valuations import compile_and_write_private_valuations
        output_path = compile_and_write_private_valuations("ai")
        assert str(output_path).endswith(".parquet"), (
            f"Expected path ending in .parquet, got {output_path}"
        )
        assert "private_valuations_ai" in str(output_path), (
            f"Expected 'private_valuations_ai' in path, got {output_path}"
        )

    def test_schema_validation_passes(self):
        """Compiled Parquet passes PRIVATE_VALUATION_SCHEMA validation."""
        from src.processing.private_valuations import compile_and_write_private_valuations
        output_path = compile_and_write_private_valuations("ai")
        df = pd.read_parquet(output_path)
        # Should not raise SchemaError
        validated = PRIVATE_VALUATION_SCHEMA.validate(df)
        assert len(validated) >= 15
