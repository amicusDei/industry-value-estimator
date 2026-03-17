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
