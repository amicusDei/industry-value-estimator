"""
Test scaffold for MODL-03: Private company valuation via comparable multiples.

Wave 0 scaffold: stub YAML loads and schema validation tests are live.
Tests marked @pytest.mark.skip are placeholders for Plan 10-03 implementation.

Test classes:
- TestPrivateValuationRegistry: validates the stub YAML registry structure and schema compliance
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
        """Load stub YAML into DataFrame and validate against PRIVATE_VALUATION_SCHEMA."""
        with open(REGISTRY_PATH, "r") as f:
            registry = yaml.safe_load(f)
        df = pd.DataFrame(registry["entries"])
        # Should not raise SchemaError
        validated = PRIVATE_VALUATION_SCHEMA.validate(df)
        assert len(validated) >= 3

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

    @pytest.mark.skip(reason="Plan 10-03 implementation: compile_and_write_private_valuations()")
    def test_compile_private_valuations(self):
        """
        Placeholder: compile_and_write_private_valuations() produces
        private_valuations_ai.parquet with PRIVATE_VALUATION_SCHEMA compliance.
        """
        pass
