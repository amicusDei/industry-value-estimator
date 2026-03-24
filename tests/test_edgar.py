"""
Tests for SEC EDGAR XBRL ingestion module (src/ingestion/edgar.py).

All tests mock edgartools at the module level to prevent live SEC EDGAR calls.
This ensures tests run offline and without EDGAR_USER_EMAIL being set.

Test classes:
- TestEdgarIdentity: set_edgar_identity does not raise
- TestEdgarCompanyConfig: fetch_all_edgar_companies reads edgar_companies from config
- TestBundledFlag: bundled_flag correctly set for bundled vs direct companies
- TestEdgarSchema: output DataFrame validates against EDGAR_RAW_SCHEMA
- TestCompanyCoverage: all 14 configured companies are covered
- TestXbrlConcepts: priority fallback when first concept returns no data
"""
import pytest
from unittest.mock import patch, MagicMock, call
import pandas as pd

# ------------------------------------------------------------------
# Minimal config fixture matching the edgar_companies structure
# in config/industries/ai.yaml (14 companies).
# ------------------------------------------------------------------

MINIMAL_CONFIG = {
    "edgar_companies": [
        {
            "name": "NVIDIA Corporation",
            "cik": "0001045810",
            "ticker": "NVDA",
            "value_chain_layer": "ai_hardware",
            "ai_disclosure_type": "direct",
            "primary_ai_segment": "Data Center",
        },
        {
            "name": "Microsoft Corporation",
            "cik": "0000789019",
            "ticker": "MSFT",
            "value_chain_layer": "ai_infrastructure",
            "ai_disclosure_type": "bundled",
            "bundled_in": "Intelligent Cloud revenue",
        },
        {
            "name": "Amazon.com Inc.",
            "cik": "0001018724",
            "ticker": "AMZN",
            "value_chain_layer": "ai_infrastructure",
            "ai_disclosure_type": "bundled",
            "bundled_in": "AWS revenue",
        },
        {
            "name": "Alphabet Inc.",
            "cik": "0001652044",
            "ticker": "GOOGL",
            "value_chain_layer": "ai_infrastructure",
            "ai_disclosure_type": "bundled",
            "bundled_in": "Google Cloud revenue",
        },
        {
            "name": "Meta Platforms Inc.",
            "cik": "0001326801",
            "ticker": "META",
            "value_chain_layer": "ai_adoption",
            "ai_disclosure_type": "bundled",
            "bundled_in": "Ad revenue",
        },
        {
            "name": "International Business Machines Corp.",
            "cik": "0000051143",
            "ticker": "IBM",
            "value_chain_layer": "ai_adoption",
            "ai_disclosure_type": "bundled",
            "bundled_in": "Software and Consulting",
        },
        {
            "name": "Accenture PLC",
            "cik": "0001281761",
            "ticker": "ACN",
            "value_chain_layer": "ai_adoption",
            "ai_disclosure_type": "partial",
            "form_types": ["20-F"],
        },
        {
            "name": "Advanced Micro Devices Inc.",
            "cik": "0000002488",
            "ticker": "AMD",
            "value_chain_layer": "ai_hardware",
            "ai_disclosure_type": "partial",
        },
        {
            "name": "Taiwan Semiconductor Manufacturing Company",
            "cik": "0001046179",
            "ticker": "TSM",
            "value_chain_layer": "ai_hardware",
            "ai_disclosure_type": "partial",
            "form_types": ["20-F"],
        },
        {
            "name": "Intel Corporation",
            "cik": "0000050863",
            "ticker": "INTC",
            "value_chain_layer": "ai_hardware",
            "ai_disclosure_type": "partial",
        },
        {
            "name": "Oracle Corporation",
            "cik": "0001341439",
            "ticker": "ORCL",
            "value_chain_layer": "ai_infrastructure",
            "ai_disclosure_type": "partial",
        },
        {
            "name": "Salesforce Inc.",
            "cik": "0001108524",
            "ticker": "CRM",
            "value_chain_layer": "ai_software",
            "ai_disclosure_type": "partial",
        },
        {
            "name": "ServiceNow Inc.",
            "cik": "0001373715",
            "ticker": "NOW",
            "value_chain_layer": "ai_software",
            "ai_disclosure_type": "partial",
        },
        {
            "name": "Palantir Technologies Inc.",
            "cik": "0001321655",
            "ticker": "PLTR",
            "value_chain_layer": "ai_software",
            "ai_disclosure_type": "direct",
        },
    ]
}

ALL_CONFIGURED_CIKS = {c["cik"] for c in MINIMAL_CONFIG["edgar_companies"]}


def _make_mock_filing(concept_value: float = 50_000_000_000.0) -> MagicMock:
    """Create a mock filing with .xbrl() that returns a mock XBRL object."""
    mock_xbrl = MagicMock()

    def _facts_query(concept: str, **kwargs) -> pd.DataFrame:
        # Returns a one-row DataFrame for any concept query
        return pd.DataFrame({
            "period": ["2023-12-31"],
            "value": [concept_value],
        })

    mock_xbrl.facts.query.side_effect = _facts_query
    mock_xbrl.facts.__len__ = lambda self: 1

    mock_filing = MagicMock()
    mock_filing.xbrl.return_value = mock_xbrl
    mock_filing.period_of_report = "2023-12-31"
    mock_filing.form = "10-K"
    return mock_filing


def _make_mock_company(concept_value: float = 50_000_000_000.0) -> MagicMock:
    """Create a mock Company with .get_filings() returning mock filings."""
    mock_filings = MagicMock()
    mock_filings.__iter__ = lambda self: iter([_make_mock_filing(concept_value)])
    mock_filings.__len__ = lambda self: 1
    mock_filings.filter.return_value = mock_filings

    mock_company = MagicMock()
    mock_company.get_filings.return_value = mock_filings
    return mock_company


# ------------------------------------------------------------------
# Test classes
# ------------------------------------------------------------------

class TestEdgarIdentity:
    """set_edgar_identity sets the SEC User-Agent without raising."""

    def test_identity_set(self):
        with patch("src.ingestion.edgar.set_identity") as mock_set_identity:
            from src.ingestion.edgar import set_edgar_identity
            set_edgar_identity("test@example.com")
            mock_set_identity.assert_called_once_with("test@example.com")

    def test_identity_passes_email_through(self):
        with patch("src.ingestion.edgar.set_identity") as mock_set_identity:
            from src.ingestion.edgar import set_edgar_identity
            set_edgar_identity("another@domain.org")
            mock_set_identity.assert_called_once_with("another@domain.org")


class TestEdgarCompanyConfig:
    """fetch_all_edgar_companies reads edgar_companies from config and returns a DataFrame."""

    def test_companies_loaded_from_config(self):
        with patch("src.ingestion.edgar.Company", return_value=_make_mock_company()):
            from src.ingestion.edgar import fetch_all_edgar_companies
            df = fetch_all_edgar_companies(MINIMAL_CONFIG)
            assert isinstance(df, pd.DataFrame)
            assert len(df) > 0

    def test_returns_dataframe_with_required_columns(self):
        with patch("src.ingestion.edgar.Company", return_value=_make_mock_company()):
            from src.ingestion.edgar import fetch_all_edgar_companies
            df = fetch_all_edgar_companies(MINIMAL_CONFIG)
            required = {"cik", "company_name", "period_end", "form_type",
                        "xbrl_concept", "value_usd", "bundled_flag", "value_chain_layer"}
            assert required.issubset(set(df.columns)), (
                f"Missing columns: {required - set(df.columns)}"
            )


class TestBundledFlag:
    """bundled_flag is True for companies in BUNDLED_SEGMENT_COMPANIES, False otherwise."""

    def test_bundled_companies(self):
        from src.ingestion.edgar import BUNDLED_SEGMENT_COMPANIES
        with patch("src.ingestion.edgar.Company", return_value=_make_mock_company()):
            from src.ingestion.edgar import fetch_all_edgar_companies
            df = fetch_all_edgar_companies(MINIMAL_CONFIG)
            for cik in BUNDLED_SEGMENT_COMPANIES:
                rows = df[df["cik"] == cik]
                if len(rows) > 0:
                    assert rows["bundled_flag"].all(), (
                        f"CIK {cik} should have bundled_flag=True"
                    )

    def test_direct_companies(self):
        """NVIDIA (0001045810) is a direct disclosure company — bundled_flag must be False."""
        with patch("src.ingestion.edgar.Company", return_value=_make_mock_company()):
            from src.ingestion.edgar import fetch_all_edgar_companies
            df = fetch_all_edgar_companies(MINIMAL_CONFIG)
            nvidia_rows = df[df["cik"] == "0001045810"]
            assert len(nvidia_rows) > 0, "NVIDIA should have rows in output"
            assert not nvidia_rows["bundled_flag"].any(), (
                "NVIDIA (0001045810) should have bundled_flag=False"
            )

    def test_bundled_set_has_six_ciks(self):
        from src.ingestion.edgar import BUNDLED_SEGMENT_COMPANIES
        assert len(BUNDLED_SEGMENT_COMPANIES) == 6, (
            f"Expected 6 CIKs in BUNDLED_SEGMENT_COMPANIES, got {len(BUNDLED_SEGMENT_COMPANIES)}"
        )


class TestEdgarSchema:
    """Output DataFrame validates against EDGAR_RAW_SCHEMA."""

    def test_schema_validates(self):
        from src.processing.validate import EDGAR_RAW_SCHEMA
        with patch("src.ingestion.edgar.Company", return_value=_make_mock_company()):
            from src.ingestion.edgar import fetch_all_edgar_companies
            df = fetch_all_edgar_companies(MINIMAL_CONFIG)
            validated = EDGAR_RAW_SCHEMA.validate(df)
            assert validated is not None

    def test_required_columns(self):
        with patch("src.ingestion.edgar.Company", return_value=_make_mock_company()):
            from src.ingestion.edgar import fetch_all_edgar_companies
            df = fetch_all_edgar_companies(MINIMAL_CONFIG)
            required = ["cik", "company_name", "period_end", "form_type",
                        "xbrl_concept", "value_usd", "bundled_flag", "value_chain_layer"]
            for col in required:
                assert col in df.columns, f"Column '{col}' missing from output DataFrame"

    def test_form_type_values(self):
        """form_type values must be in the allowed set (10-K, 10-Q, 20-F)."""
        with patch("src.ingestion.edgar.Company", return_value=_make_mock_company()):
            from src.ingestion.edgar import fetch_all_edgar_companies
            df = fetch_all_edgar_companies(MINIMAL_CONFIG)
            allowed = {"10-K", "10-Q", "20-F"}
            assert set(df["form_type"].unique()).issubset(allowed), (
                f"Unexpected form_type values: {set(df['form_type'].unique()) - allowed}"
            )


class TestCompanyCoverage:
    """All 14 configured companies appear in the output."""

    def test_all_configured_companies(self):
        with patch("src.ingestion.edgar.Company", return_value=_make_mock_company()):
            from src.ingestion.edgar import fetch_all_edgar_companies
            df = fetch_all_edgar_companies(MINIMAL_CONFIG)
            output_ciks = set(df["cik"].unique())
            missing = ALL_CONFIGURED_CIKS - output_ciks
            assert not missing, (
                f"Missing CIKs in output: {missing}"
            )

    def test_fourteen_companies_in_config(self):
        """The MINIMAL_CONFIG fixture covers all 14 companies from ai.yaml."""
        assert len(MINIMAL_CONFIG["edgar_companies"]) == 14


class TestXbrlConcepts:
    """XBRL concept priority fallback: first non-null concept wins."""

    def test_priority_fallback(self):
        """When first XBRL concept returns no rows, falls back to second concept."""
        call_count = [0]

        def _facts_query_with_fallback(concept: str, **kwargs) -> pd.DataFrame:
            call_count[0] += 1
            # First concept returns empty — simulate no data for that concept
            if "Revenues" in concept and "Contract" not in concept and call_count[0] <= 2:
                return pd.DataFrame()
            return pd.DataFrame({
                "period": ["2023-12-31"],
                "value": [12_000_000_000.0],
            })

        mock_xbrl = MagicMock()
        mock_xbrl.facts.query.side_effect = _facts_query_with_fallback

        mock_filing = MagicMock()
        mock_filing.xbrl.return_value = mock_xbrl
        mock_filing.period_of_report = "2023-12-31"
        mock_filing.form = "10-K"

        mock_filings = MagicMock()
        mock_filings.__iter__ = lambda self: iter([mock_filing])
        mock_filings.__len__ = lambda self: 1
        mock_filings.filter.return_value = mock_filings

        mock_company = MagicMock()
        mock_company.get_filings.return_value = mock_filings

        with patch("src.ingestion.edgar.Company", return_value=mock_company):
            from src.ingestion.edgar import fetch_company_filings
            df = fetch_company_filings(
                cik="0001045810",
                company_name="NVIDIA Corporation",
                form_types=["10-K"],
                start_year=2023,
                end_year=2023,
                value_chain_layer="ai_hardware",
            )
            # Should have at least one row (fallback concept succeeded)
            assert len(df) > 0, "Expected at least one row from fallback concept"
            # The returned value should be non-null
            assert df["value_usd"].notna().any(), "Expected non-null value_usd from fallback"

    def test_xbrl_concepts_list_has_four_entries(self):
        from src.ingestion.edgar import XBRL_CONCEPTS
        assert len(XBRL_CONCEPTS) == 4, (
            f"Expected 4 XBRL concepts, got {len(XBRL_CONCEPTS)}"
        )
