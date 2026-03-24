"""
Test scaffold for MODL-02: AI revenue attribution for mixed-tech public companies.

Wave 0 scaffold: stub YAML loads and schema validation tests are live.
Tests marked @pytest.mark.skip are placeholders for Plan 10-02 implementation.

Test classes:
- TestAttributionRegistry: validates the stub YAML registry structure and schema compliance
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

    @pytest.mark.skip(reason="Plan 10-02 implementation: compile_and_write_attribution()")
    def test_compile_attribution(self):
        """
        Placeholder: compile_attribution() produces revenue_attribution_ai.parquet
        with correct schema and all BUNDLED_SEGMENT_COMPANIES covered.
        """
        pass
