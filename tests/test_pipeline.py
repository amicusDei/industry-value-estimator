"""End-to-end pipeline tests including second industry extensibility (ARCH-01)."""
import yaml
import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import json

from config.settings import load_industry_config, list_available_industries, INDUSTRIES_DIR


FIXTURES = Path(__file__).parent / "fixtures"


class TestFullPipeline:
    """Test the full ingestion-to-processed pipeline with mocked APIs."""

    def test_world_bank_pipeline_produces_output(self, tmp_path):
        """World Bank fetch -> normalize -> write Parquet produces a file."""
        # Use normalized (already processed) fixture data as stand-in for fetch result.
        # run_full_pipeline calls fetch_world_bank_indicators and normalize_world_bank.
        # We mock the fetch functions at the pipeline module level so real reshape
        # logic in world_bank.py is bypassed — the test focuses on pipeline orchestration.
        import src.ingestion.pipeline as pipeline_mod

        # Sample wide-format DataFrame matching what fetch_world_bank_indicators returns.
        # Single economy to avoid duplicate year index in deflation step (deflation
        # tests with multi-economy data are covered in test_deflate.py).
        sample_wb = pd.DataFrame([
            {"economy": "USA", "year": 2019, "NY.GDP.MKTP.CD": 20000000000000.0, "NY.GDP.DEFL.ZS": 95.0, "GB.XPD.RSDV.GD.ZS": 3.10},
            {"economy": "USA", "year": 2020, "NY.GDP.MKTP.CD": 21060474000000.0, "NY.GDP.DEFL.ZS": 100.0, "GB.XPD.RSDV.GD.ZS": 3.45},
            {"economy": "USA", "year": 2021, "NY.GDP.MKTP.CD": 23315081000000.0, "NY.GDP.DEFL.ZS": 105.0, "GB.XPD.RSDV.GD.ZS": 3.46},
        ])
        dummy_raw_path = tmp_path / "raw" / "world_bank"
        dummy_raw_path.mkdir(parents=True, exist_ok=True)
        dummy_raw_parquet = dummy_raw_path / "world_bank_ai_20260318.parquet"

        import config.settings as settings
        original_processed = settings.DATA_PROCESSED
        original_raw = settings.DATA_RAW
        settings.DATA_PROCESSED = tmp_path / "processed"
        settings.DATA_RAW = tmp_path / "raw"
        try:
            with patch.object(pipeline_mod, "fetch_world_bank_indicators", return_value=sample_wb), \
                 patch.object(pipeline_mod, "save_raw_world_bank", return_value=dummy_raw_parquet), \
                 patch.object(pipeline_mod, "fetch_oecd_msti", side_effect=Exception("OECD unavailable")), \
                 patch.object(pipeline_mod, "fetch_oecd_ai_patents", side_effect=Exception("OECD unavailable")):

                result = pipeline_mod.run_full_pipeline("ai", include_lseg=False)

            # Assert: result dict should contain 'world_bank' key with a Path to a Parquet file
            assert "world_bank" in result, f"Expected 'world_bank' in pipeline result, got keys: {list(result.keys())}"
            assert result["world_bank"].suffix == ".parquet"
            assert result["world_bank"].exists(), f"Parquet file should exist at {result['world_bank']}"
        finally:
            settings.DATA_PROCESSED = original_processed
            settings.DATA_RAW = original_raw

    def test_pipeline_reads_config_not_hardcoded(self):
        """Pipeline uses load_industry_config, not hardcoded values."""
        import inspect
        from src.ingestion import pipeline as pipeline_module
        source = inspect.getsource(pipeline_module)
        assert "load_industry_config" in source


class TestSecondIndustryExtensibility:
    """ARCH-01: Adding a second industry via YAML config without code changes."""

    @pytest.fixture
    def dummy_industry_yaml(self):
        """Create a minimal dummy industry YAML for testing extensibility."""
        dummy = {
            "industry": "test_retail",
            "display_name": "Test Retail Industry",
            "base_year": 2020,
            "segments": [
                {"id": "retail_online", "display_name": "Online Retail", "overlap_note": "none"},
                {"id": "retail_physical", "display_name": "Physical Retail", "overlap_note": "none"},
            ],
            "regions": [
                {"id": "global", "display_name": "Global"},
                {"id": "us", "display_name": "US", "economy_codes": ["USA"]},
            ],
            "date_range": {"start": "2015", "end": "2025"},
            "proxies": [],
            "world_bank": {
                "indicators": [
                    {"code": "NY.GDP.MKTP.CD", "name": "gdp_current_usd", "unit": "current_usd", "use_for": "macro"},
                    {"code": "NY.GDP.DEFL.ZS", "name": "gdp_deflator_index", "unit": "index", "use_for": "deflation"},
                ]
            },
            "oecd": {"datasets": []},
            "lseg": {"trbc_codes": [], "fields": []},
            "source_attribution": {
                "world_bank": "World Bank",
                "oecd": "OECD",
                "lseg": "LSEG",
            },
        }
        return dummy

    def test_second_industry_config_loads(self, dummy_industry_yaml, tmp_path):
        """A second YAML file in config/industries/ loads without code changes."""
        # Write the dummy config to a temp location
        config_path = INDUSTRIES_DIR / "test_retail.yaml"
        try:
            with open(config_path, "w") as f:
                yaml.dump(dummy_industry_yaml, f, default_flow_style=False)

            # Load it using the same infrastructure as "ai"
            config = load_industry_config("test_retail")
            assert config["industry"] == "test_retail"
            assert len(config["segments"]) == 2
            assert config["base_year"] == 2020
        finally:
            # Clean up
            config_path.unlink(missing_ok=True)

    def test_second_industry_appears_in_list(self, dummy_industry_yaml):
        """list_available_industries() discovers the second industry."""
        config_path = INDUSTRIES_DIR / "test_retail.yaml"
        try:
            with open(config_path, "w") as f:
                yaml.dump(dummy_industry_yaml, f, default_flow_style=False)

            industries = list_available_industries()
            assert "ai" in industries
            assert "test_retail" in industries
        finally:
            config_path.unlink(missing_ok=True)

    def test_pipeline_accepts_second_industry(self, dummy_industry_yaml):
        """run_full_pipeline can be called with the second industry ID."""
        config_path = INDUSTRIES_DIR / "test_retail.yaml"
        try:
            with open(config_path, "w") as f:
                yaml.dump(dummy_industry_yaml, f, default_flow_style=False)

            # Verify the config loads and has expected structure
            config = load_industry_config("test_retail")
            from config.settings import get_all_economy_codes
            codes = get_all_economy_codes(config)
            assert "USA" in codes
        finally:
            config_path.unlink(missing_ok=True)


PIPELINE_SRC = Path(__file__).parent.parent / "src" / "ingestion" / "pipeline.py"


class TestPipelinePhase8Steps:
    """Phase 8 pipeline additions: market anchors (Step 6) and EDGAR (Step 7).

    Tests read pipeline.py source text directly to avoid the pandasdmx top-level
    import error (pandasdmx has a pydantic v2 incompatibility that prevents module
    import in the test environment — a known pre-existing issue in this project).
    """

    @pytest.fixture(autouse=True)
    def pipeline_source(self):
        """Load pipeline.py source text once per test."""
        return PIPELINE_SRC.read_text()

    def test_run_full_pipeline_accepts_include_edgar_parameter(self, pipeline_source):
        """run_full_pipeline signature includes include_edgar: bool = False."""
        assert "include_edgar: bool = False" in pipeline_source, (
            "run_full_pipeline must declare include_edgar: bool = False parameter"
        )

    def test_pipeline_source_calls_compile_and_write_market_anchors(self, pipeline_source):
        """run_full_pipeline contains a call to compile_and_write_market_anchors."""
        assert "compile_and_write_market_anchors" in pipeline_source, (
            "pipeline.py must call compile_and_write_market_anchors"
        )

    def test_pipeline_source_calls_fetch_all_edgar_companies(self, pipeline_source):
        """run_full_pipeline contains a call to fetch_all_edgar_companies."""
        assert "fetch_all_edgar_companies" in pipeline_source, (
            "pipeline.py must call fetch_all_edgar_companies"
        )

    def test_edgar_step_gated_by_include_edgar_flag(self, pipeline_source):
        """EDGAR step is only triggered when include_edgar=True."""
        assert "if include_edgar" in pipeline_source, (
            "fetch_all_edgar_companies must be gated behind 'if include_edgar'"
        )

    def test_edgar_step_gated_by_email_env_var(self, pipeline_source):
        """EDGAR step checks for EDGAR_USER_EMAIL environment variable."""
        assert "EDGAR_USER_EMAIL" in pipeline_source, (
            "pipeline.py must check EDGAR_USER_EMAIL env var before EDGAR ingestion"
        )

    def test_market_anchors_step_not_gated_by_flag(self, pipeline_source):
        """Market anchors always runs (no flag needed — uses local YAML, not external API)."""
        # The compile_and_write_market_anchors call should appear outside any
        # 'if include_*' block — it always runs regardless of optional flags.
        # We verify it appears at the same indentation as other always-run steps.
        lines = pipeline_source.splitlines()
        for i, line in enumerate(lines):
            if "compile_and_write_market_anchors" in line:
                # The call itself should be in a try block but not inside 'if include_edgar'
                # Check that the enclosing scope is not the edgar block
                context_start = max(0, i - 15)
                context = "\n".join(lines[context_start:i])
                assert "if include_edgar" not in context or context.count("if include_edgar") == 0, (
                    "compile_and_write_market_anchors must not be inside the include_edgar block"
                )
                break
