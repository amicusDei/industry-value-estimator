"""
Tests for regex-based AI revenue extraction from EDGAR filing text.

Uses known filing snippets from public 10-K disclosures to validate
that extraction patterns produce correct values and confidence levels.
"""

import pytest
import pandas as pd

from src.ingestion.earnings_analysis import (
    extract_ai_revenue_mentions,
    _normalize_value,
    COMPANY_PATTERNS,
    GENERIC_AI_PATTERN,
    fetch_and_extract,
    _empty_result_df,
)


# ---------------------------------------------------------------------------
# Known filing snippets — sourced from public 10-K/10-Q filings
# ---------------------------------------------------------------------------

NVIDIA_10K_SNIPPET = (
    "For fiscal year 2025, our Data Center segment revenue was $115.2 billion, "
    "an increase of 142% from the prior year, driven by demand for our Hopper "
    "architecture GPUs used in AI training and inference workloads."
)

NVIDIA_10K_SNIPPET_MILLIONS = (
    "Data Center revenue for the quarter was $22,604 million, reflecting strong "
    "demand for NVIDIA H100 GPUs across cloud service providers."
)

MICROSOFT_10K_SNIPPET = (
    "Intelligent Cloud revenue was $96.8 billion, an increase of 23%, driven by "
    "Azure and other cloud services revenue growth of 29%. Azure AI services "
    "continued to see significant demand."
)

ALPHABET_10K_SNIPPET = (
    "Google Cloud revenue was $43.1 billion for the year ended December 31, 2024, "
    "compared to $33.1 billion in the prior year, driven by growth in Google Cloud "
    "Platform and Google Workspace."
)

AMAZON_10Q_SNIPPET = (
    "AWS net sales were $26.3 billion for the three months ended September 30, 2024, "
    "compared to $23.1 billion for the three months ended September 30, 2023."
)

META_10K_SNIPPET = (
    "We expect capital expenditures in 2025 to be in the range of $60 billion to "
    "$65 billion, driven by our continued investment in AI infrastructure including "
    "data centers and servers."
)

PALANTIR_10K_SNIPPET = (
    "Revenue from our commercial AIP customers grew 64% year-over-year. "
    "Artificial Intelligence Platform revenue contribution was $1.2 billion "
    "for the full year 2024."
)

AMD_10K_SNIPPET = (
    "Data Center segment revenue was $12.6 billion for the year ended December 2024, "
    "an increase of 94% year-over-year driven by growth in AMD Instinct GPU shipments."
)

GENERIC_AI_SNIPPET = (
    "Our artificial intelligence revenue grew to $3.4 billion in 2024, "
    "representing 18% of total company revenue."
)

NO_MATCH_SNIPPET = (
    "Total revenue for the fiscal year was $45.2 billion. The company reported "
    "strong performance across all operating segments."
)


# ---------------------------------------------------------------------------
# _normalize_value tests
# ---------------------------------------------------------------------------

class TestNormalizeValue:
    def test_billions_word(self):
        assert _normalize_value("47.5", "billion") == 47.5

    def test_billions_abbrev(self):
        assert _normalize_value("47.5", "B") == 47.5

    def test_millions_word(self):
        assert abs(_normalize_value("22604", "million") - 22.604) < 0.001

    def test_millions_abbrev(self):
        assert abs(_normalize_value("500", "M") - 0.5) < 0.001

    def test_commas_in_value(self):
        assert abs(_normalize_value("22,604", "million") - 22.604) < 0.001

    def test_large_billion(self):
        assert _normalize_value("115.2", "billion") == 115.2


# ---------------------------------------------------------------------------
# extract_ai_revenue_mentions tests — company-specific patterns
# ---------------------------------------------------------------------------

class TestNvidiaExtraction:
    def test_data_center_revenue_billions(self):
        """NVIDIA 10-K: Data Center revenue $115.2 billion."""
        results = extract_ai_revenue_mentions(NVIDIA_10K_SNIPPET, "0001045810")
        assert len(results) >= 1
        nvidia_match = results[0]
        assert nvidia_match["pattern_name"] == "nvidia_data_center"
        assert abs(nvidia_match["extracted_value_usd"] - 115.2) < 0.01
        assert nvidia_match["confidence"] == "high"

    def test_data_center_revenue_millions(self):
        """NVIDIA 10-Q: Data Center revenue $22,604 million → 22.604B."""
        results = extract_ai_revenue_mentions(NVIDIA_10K_SNIPPET_MILLIONS, "0001045810")
        assert len(results) >= 1
        assert abs(results[0]["extracted_value_usd"] - 22.604) < 0.01

    def test_snippet_included(self):
        """Extracted result includes context snippet."""
        results = extract_ai_revenue_mentions(NVIDIA_10K_SNIPPET, "0001045810")
        assert len(results) >= 1
        assert "Data Center" in results[0]["raw_snippet"]


class TestMicrosoftExtraction:
    def test_intelligent_cloud_revenue(self):
        """Microsoft 10-K: Intelligent Cloud revenue $96.8 billion."""
        results = extract_ai_revenue_mentions(MICROSOFT_10K_SNIPPET, "0000789019")
        assert len(results) >= 1
        assert abs(results[0]["extracted_value_usd"] - 96.8) < 0.01
        assert results[0]["confidence"] == "medium"


class TestAlphabetExtraction:
    def test_google_cloud_revenue(self):
        """Alphabet 10-K: Google Cloud revenue $43.1 billion."""
        results = extract_ai_revenue_mentions(ALPHABET_10K_SNIPPET, "0001652044")
        assert len(results) >= 1
        match = [r for r in results if r["pattern_name"] == "alphabet_google_cloud"]
        assert len(match) >= 1
        assert abs(match[0]["extracted_value_usd"] - 43.1) < 0.01


class TestAmazonExtraction:
    def test_aws_revenue(self):
        """Amazon 10-Q: AWS net sales $26.3 billion."""
        results = extract_ai_revenue_mentions(AMAZON_10Q_SNIPPET, "0001018724")
        assert len(results) >= 1
        match = [r for r in results if r["pattern_name"] == "amazon_aws"]
        assert len(match) >= 1
        assert abs(match[0]["extracted_value_usd"] - 26.3) < 0.01


class TestMetaExtraction:
    def test_ai_investment(self):
        """Meta 10-K: AI infrastructure investment $60 billion."""
        results = extract_ai_revenue_mentions(META_10K_SNIPPET, "0001326801")
        assert len(results) >= 1
        assert results[0]["confidence"] == "low"


class TestAmdExtraction:
    def test_data_center_revenue(self):
        """AMD 10-K: Data Center revenue $12.6 billion."""
        results = extract_ai_revenue_mentions(AMD_10K_SNIPPET, "0000002488")
        assert len(results) >= 1
        assert abs(results[0]["extracted_value_usd"] - 12.6) < 0.01


class TestPalantirExtraction:
    def test_aip_revenue(self):
        """Palantir 10-K: AIP revenue contribution $1.2 billion."""
        results = extract_ai_revenue_mentions(PALANTIR_10K_SNIPPET, "0001321655")
        assert len(results) >= 1
        match = [r for r in results if r["pattern_name"] == "palantir_aip"]
        assert len(match) >= 1
        assert abs(match[0]["extracted_value_usd"] - 1.2) < 0.01
        assert match[0]["confidence"] == "high"


# ---------------------------------------------------------------------------
# Generic pattern tests
# ---------------------------------------------------------------------------

class TestGenericPattern:
    def test_generic_ai_revenue(self):
        """Generic pattern: 'artificial intelligence revenue grew to $3.4 billion'."""
        results = extract_ai_revenue_mentions(GENERIC_AI_SNIPPET, "9999999999")
        assert len(results) >= 1
        assert results[0]["pattern_name"] == "generic_ai_revenue"
        assert abs(results[0]["extracted_value_usd"] - 3.4) < 0.01
        assert results[0]["confidence"] == "low"

    def test_no_match_returns_empty(self):
        """Text without AI revenue mentions returns empty list."""
        results = extract_ai_revenue_mentions(NO_MATCH_SNIPPET, "9999999999")
        assert results == []

    def test_empty_text_returns_empty(self):
        """Empty string returns empty list."""
        assert extract_ai_revenue_mentions("", "0001045810") == []

    def test_none_safe(self):
        """None-like empty text returns empty list."""
        assert extract_ai_revenue_mentions("   ", "0001045810") == []


# ---------------------------------------------------------------------------
# Sanity filter tests
# ---------------------------------------------------------------------------

class TestSanityFilters:
    def test_value_too_large_filtered(self):
        """Values > $500B are filtered as implausible."""
        text = "AI revenue was $600 billion last year."
        results = extract_ai_revenue_mentions(text, "9999999999")
        assert len(results) == 0

    def test_value_too_small_filtered(self):
        """Values < $0.01B ($10M) are filtered."""
        text = "AI revenue contribution was $5 million."
        results = extract_ai_revenue_mentions(text, "9999999999")
        assert len(results) == 0

    def test_deduplication(self):
        """Same value from same pattern is deduplicated."""
        text = (
            "Data Center revenue was $47.5 billion. "
            "As noted, Data Center revenue reached $47.5 billion."
        )
        results = extract_ai_revenue_mentions(text, "0001045810")
        nvidia_matches = [r for r in results if r["pattern_name"] == "nvidia_data_center"]
        assert len(nvidia_matches) == 1


# ---------------------------------------------------------------------------
# DataFrame output tests
# ---------------------------------------------------------------------------

class TestFetchAndExtract:
    def test_empty_result_df_schema(self):
        """_empty_result_df returns correct column schema."""
        df = _empty_result_df()
        expected_cols = {
            "cik", "period_end", "form_type", "pattern_name",
            "extracted_value_usd", "unit", "confidence", "raw_snippet",
        }
        assert set(df.columns) == expected_cols
        assert len(df) == 0

    def test_company_patterns_cover_key_ciks(self):
        """Company-specific patterns exist for at least 5 companies."""
        assert len(COMPANY_PATTERNS) >= 5

    def test_all_patterns_have_required_keys(self):
        """Every pattern config has name, pattern, confidence."""
        for cik, patterns in COMPANY_PATTERNS.items():
            for pat in patterns:
                assert "name" in pat, f"CIK {cik}: missing 'name'"
                assert "pattern" in pat, f"CIK {cik}: missing 'pattern'"
                assert "confidence" in pat, f"CIK {cik}: missing 'confidence'"
                assert pat["confidence"] in ("high", "medium", "low"), (
                    f"CIK {cik}: invalid confidence '{pat['confidence']}'"
                )
