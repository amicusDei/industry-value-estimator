"""Tests for industry configuration loading and validation (DATA-01, DATA-02, ARCH-01)."""
import yaml
import pytest
from pathlib import Path

from config.settings import (
    load_industry_config,
    list_available_industries,
    get_all_economy_codes,
    BASE_YEAR,
    INDUSTRIES_DIR,
)


class TestAIConfigSchema:
    """Validate config/industries/ai.yaml structure and content."""

    @pytest.fixture
    def ai_config(self):
        return load_industry_config("ai")

    def test_ai_config_loads(self, ai_config):
        """ai.yaml is parseable YAML."""
        assert isinstance(ai_config, dict)
        assert ai_config["industry"] == "ai"

    def test_ai_config_has_four_segments(self, ai_config):
        """DATA-01: 4 locked segments exist."""
        segments = ai_config["segments"]
        assert len(segments) == 4
        segment_ids = {s["id"] for s in segments}
        assert segment_ids == {"ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"}

    def test_ai_config_has_five_regions(self, ai_config):
        """Geographic scope: global + US + Europe + China + RoW."""
        regions = ai_config["regions"]
        assert len(regions) == 5
        region_ids = {r["id"] for r in regions}
        assert region_ids == {"global", "us", "europe", "china", "row"}

    def test_ai_config_date_range(self, ai_config):
        """Historical period: 2010-present."""
        dr = ai_config["date_range"]
        assert dr["start"] == "2010"
        assert int(dr["end"]) >= 2025

    def test_ai_config_base_year_matches_global(self, ai_config):
        """Deflation base year in YAML matches global BASE_YEAR constant."""
        assert ai_config["base_year"] == BASE_YEAR

    def test_ai_config_has_proxy_indicators(self, ai_config):
        """Proxy indicators for AI activity are defined."""
        proxies = ai_config["proxies"]
        assert len(proxies) >= 4
        proxy_ids = {p["id"] for p in proxies}
        assert "ai_patent_filings" in proxy_ids
        assert "public_co_ai_revenue" in proxy_ids

    def test_ai_config_world_bank_includes_deflator(self, ai_config):
        """World Bank indicators include the GDP deflator (non-negotiable)."""
        wb_codes = [ind["code"] for ind in ai_config["world_bank"]["indicators"]]
        assert "NY.GDP.DEFL.ZS" in wb_codes

    def test_ai_config_world_bank_indicator_count(self, ai_config):
        """At least 6 World Bank indicators configured."""
        assert len(ai_config["world_bank"]["indicators"]) >= 6

    def test_ai_config_oecd_datasets(self, ai_config):
        """OECD datasets include MSTI and PATS_IPC."""
        oecd_ids = {d["id"] for d in ai_config["oecd"]["datasets"]}
        assert "MSTI" in oecd_ids
        assert "PATS_IPC" in oecd_ids

    def test_ai_config_lseg_trbc_codes(self, ai_config):
        """LSEG TRBC codes are defined for AI company universe."""
        trbc = ai_config["lseg"]["trbc_codes"]
        assert len(trbc) >= 3
        codes = {t["code"] for t in trbc}
        assert "57201010" in codes  # Computer Processing Hardware

    def test_ai_config_source_attribution(self, ai_config):
        """Source attribution metadata exists for DATA-07 downstream."""
        attr = ai_config["source_attribution"]
        assert "world_bank" in attr
        assert "oecd" in attr
        assert "lseg" in attr

    def test_ai_config_segments_have_overlap_notes(self, ai_config):
        """Each segment documents its overlap (locked: allow overlap, document range)."""
        for seg in ai_config["segments"]:
            assert "overlap_note" in seg, f"Segment {seg['id']} missing overlap_note"


class TestConfigLoader:
    """Test config loading infrastructure (ARCH-01)."""

    def test_list_available_industries(self):
        """At least 'ai' industry is available."""
        industries = list_available_industries()
        assert "ai" in industries

    def test_load_nonexistent_industry_raises(self):
        """Loading a missing industry raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_industry_config("nonexistent_industry_xyz")

    def test_get_all_economy_codes(self):
        """Economy codes are extracted and deduplicated."""
        config = load_industry_config("ai")
        codes = get_all_economy_codes(config)
        assert "USA" in codes
        assert "CHN" in codes
        assert "GBR" in codes
        # Should be sorted and deduplicated
        assert codes == sorted(set(codes))


class TestMarketBoundary:
    """DATA-08: Market boundary definition locked in ai.yaml."""

    @pytest.fixture
    def ai_config(self):
        return load_industry_config("ai")

    def test_market_boundary_exists(self, ai_config):
        """market_boundary section exists in ai.yaml."""
        assert "market_boundary" in ai_config

    def test_definition_locked_date(self, ai_config):
        """definition_locked is a non-empty date string."""
        mb = ai_config["market_boundary"]
        assert "definition_locked" in mb
        assert len(str(mb["definition_locked"])) >= 10  # YYYY-MM-DD minimum

    def test_scope_statement_nonempty(self, ai_config):
        """scope_statement is a substantial string (not placeholder)."""
        mb = ai_config["market_boundary"]
        assert len(mb["scope_statement"]) > 100

    def test_overlap_zones_documented(self, ai_config):
        """At least 2 overlap zones are documented."""
        mb = ai_config["market_boundary"]
        assert len(mb["overlap_zones"]) >= 2

    def test_adjusted_total_method_documented(self, ai_config):
        """adjusted_total_method explains how overlaps are handled."""
        mb = ai_config["market_boundary"]
        assert "adjusted_total_method" in mb
        assert len(mb["adjusted_total_method"]) > 50


class TestScopeMapping:
    """DATA-08: Scope mapping table maps analyst firms to our segments."""

    @pytest.fixture
    def ai_config(self):
        return load_industry_config("ai")

    def test_scope_mapping_table_exists(self, ai_config):
        """scope_mapping_table section exists."""
        assert "scope_mapping_table" in ai_config

    def test_minimum_firms(self, ai_config):
        """At least 6 analyst firms are mapped."""
        smt = ai_config["scope_mapping_table"]
        assert len(smt) >= 6

    def test_required_firms_present(self, ai_config):
        """IDC, Gartner, and Grand View are all mapped."""
        firms = {e["firm"] for e in ai_config["scope_mapping_table"]}
        for required in ["IDC", "Gartner", "Grand View Research"]:
            assert required in firms, f"Missing required firm: {required}"

    def test_each_firm_has_coefficient(self, ai_config):
        """Every firm has scope_coefficient and scope_coefficient_range."""
        for entry in ai_config["scope_mapping_table"]:
            assert "scope_coefficient" in entry, f"{entry['firm']} missing scope_coefficient"
            assert "scope_coefficient_range" in entry, f"{entry['firm']} missing range"
            low, high = entry["scope_coefficient_range"]
            assert low <= entry["scope_coefficient"] <= high

    def test_each_firm_has_scope_docs(self, ai_config):
        """Every firm has includes and excludes documentation."""
        for entry in ai_config["scope_mapping_table"]:
            assert "includes" in entry, f"{entry['firm']} missing includes"
            assert "excludes" in entry, f"{entry['firm']} missing excludes"

    def test_edgar_companies_coverage(self, ai_config):
        """edgar_companies covers all 4 value chain layers with 13+ companies."""
        ec = ai_config["edgar_companies"]
        assert len(ec) >= 13
        layers = {c["value_chain_layer"] for c in ec}
        assert layers == {"ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"}
