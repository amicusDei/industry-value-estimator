"""
Tests for LLM validation layer (src/ingestion/llm_validator.py).

All tests use mocked Anthropic API responses — no real API calls are made.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.llm_validator import (
    validate_extraction,
    validate_batch,
    _parse_llm_response,
    _UNAVAILABLE_RESULT,
    _VALIDATION_PROMPT_TEMPLATE,
    VALIDATION_MODEL,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_EXTRACTION = {
    "raw_snippet": "Data Center segment revenue was $115.2 billion, an increase of 142%",
    "extracted_value_usd": 115.2,
    "unit": "billion",
    "confidence": "high",
    "pattern_name": "nvidia_data_center",
    "context_window": 200,
}

SAMPLE_CONTEXT = {
    "company_name": "NVIDIA Corporation",
    "filing_type": "10-K",
}

VALID_LLM_RESPONSE = (
    '{"validated": true, "corrected_value_usd": null, '
    '"fiscal_period": "FY2025", "confidence": 0.95, '
    '"reasoning": "Data Center revenue is a direct proxy for AI GPU revenue."}'
)

CORRECTED_LLM_RESPONSE = (
    '{"validated": true, "corrected_value_usd": 110.5, '
    '"fiscal_period": "FY2025", "confidence": 0.80, '
    '"reasoning": "Value is close but appears to be rounded differently."}'
)

REJECTED_LLM_RESPONSE = (
    '{"validated": false, "corrected_value_usd": null, '
    '"fiscal_period": "FY2025", "confidence": 0.90, '
    '"reasoning": "This is total company revenue, not AI-specific."}'
)

FENCED_LLM_RESPONSE = (
    '```json\n'
    '{"validated": true, "corrected_value_usd": null, '
    '"fiscal_period": "FY2025", "confidence": 0.92, '
    '"reasoning": "Correct AI-specific extraction."}\n'
    '```'
)


# ---------------------------------------------------------------------------
# _parse_llm_response tests
# ---------------------------------------------------------------------------

class TestParseLlmResponse:
    def test_valid_json(self):
        result = _parse_llm_response(VALID_LLM_RESPONSE)
        assert result["validated"] is True
        assert result["corrected_value_usd"] is None
        assert result["fiscal_period"] == "FY2025"
        assert result["confidence"] == 0.95
        assert "Data Center" in result["reasoning"]

    def test_corrected_value(self):
        result = _parse_llm_response(CORRECTED_LLM_RESPONSE)
        assert result["validated"] is True
        assert result["corrected_value_usd"] == 110.5

    def test_rejected(self):
        result = _parse_llm_response(REJECTED_LLM_RESPONSE)
        assert result["validated"] is False
        assert result["confidence"] == 0.90

    def test_fenced_json(self):
        """JSON wrapped in ```json ... ``` fences is parsed correctly."""
        result = _parse_llm_response(FENCED_LLM_RESPONSE)
        assert result["validated"] is True
        assert result["confidence"] == 0.92

    def test_malformed_json(self):
        """Non-JSON response returns fallback with reasoning."""
        result = _parse_llm_response("This is not JSON at all.")
        assert result["validated"] is None
        assert result["confidence"] == 0.0
        assert "Failed to parse" in result["reasoning"]

    def test_empty_string(self):
        result = _parse_llm_response("")
        assert result["validated"] is None
        assert result["confidence"] == 0.0


# ---------------------------------------------------------------------------
# validate_extraction tests (mocked API)
# ---------------------------------------------------------------------------

def _make_mock_client(response_text):
    """Create a mock Anthropic client that returns the given text."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = response_text
    mock_response.content = [mock_content]
    mock_client.messages.create.return_value = mock_response
    return mock_client


class TestValidateExtraction:
    @patch("src.ingestion.llm_validator._get_client")
    def test_valid_extraction(self, mock_get_client):
        mock_get_client.return_value = _make_mock_client(VALID_LLM_RESPONSE)
        result = validate_extraction(SAMPLE_EXTRACTION, SAMPLE_CONTEXT)

        assert result["validated"] is True
        assert result["confidence"] == 0.95
        assert result["fiscal_period"] == "FY2025"

    @patch("src.ingestion.llm_validator._get_client")
    def test_rejected_extraction(self, mock_get_client):
        mock_get_client.return_value = _make_mock_client(REJECTED_LLM_RESPONSE)
        result = validate_extraction(SAMPLE_EXTRACTION, SAMPLE_CONTEXT)

        assert result["validated"] is False
        assert "total company revenue" in result["reasoning"]

    @patch("src.ingestion.llm_validator._get_client")
    def test_corrected_value(self, mock_get_client):
        mock_get_client.return_value = _make_mock_client(CORRECTED_LLM_RESPONSE)
        result = validate_extraction(SAMPLE_EXTRACTION, SAMPLE_CONTEXT)

        assert result["corrected_value_usd"] == 110.5

    @patch("src.ingestion.llm_validator._get_client")
    def test_api_unavailable(self, mock_get_client):
        """When client is None (no API key), returns unavailable fallback."""
        mock_get_client.return_value = None
        result = validate_extraction(SAMPLE_EXTRACTION, SAMPLE_CONTEXT)

        assert result["validated"] is None
        assert result["confidence"] == 0.0
        assert result["reasoning"] == "LLM unavailable"

    @patch("src.ingestion.llm_validator._get_client")
    def test_api_error(self, mock_get_client):
        """When API call raises, returns unavailable fallback."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("API error")
        mock_get_client.return_value = mock_client
        result = validate_extraction(SAMPLE_EXTRACTION, SAMPLE_CONTEXT)

        assert result["validated"] is None
        assert result["confidence"] == 0.0

    @patch("src.ingestion.llm_validator._get_client")
    def test_prompt_contains_company_name(self, mock_get_client):
        """Verify the prompt template includes company name and value."""
        mock_client = _make_mock_client(VALID_LLM_RESPONSE)
        mock_get_client.return_value = mock_client
        validate_extraction(SAMPLE_EXTRACTION, SAMPLE_CONTEXT)

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        prompt_text = messages[0]["content"]
        assert "NVIDIA Corporation" in prompt_text
        assert "115.20" in prompt_text

    @patch("src.ingestion.llm_validator._get_client")
    def test_uses_correct_model(self, mock_get_client):
        mock_client = _make_mock_client(VALID_LLM_RESPONSE)
        mock_get_client.return_value = mock_client
        validate_extraction(SAMPLE_EXTRACTION, SAMPLE_CONTEXT)

        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["model"] == VALIDATION_MODEL


# ---------------------------------------------------------------------------
# validate_batch tests (mocked API)
# ---------------------------------------------------------------------------

class TestValidateBatch:
    @patch("src.ingestion.llm_validator._get_client")
    @patch("src.ingestion.llm_validator.time")
    def test_batch_processes_all(self, mock_time, mock_get_client):
        """Batch processes all extractions and merges results."""
        mock_time.time.return_value = 1000.0  # fixed time to skip rate limit
        mock_time.sleep = MagicMock()
        mock_get_client.return_value = _make_mock_client(VALID_LLM_RESPONSE)

        extractions = [
            {**SAMPLE_EXTRACTION, "cik": "0001045810", "form_type": "10-K"},
            {**SAMPLE_EXTRACTION, "cik": "0001045810", "form_type": "10-K",
             "extracted_value_usd": 22.6},
        ]
        contexts = {
            "0001045810": {"company_name": "NVIDIA", "filing_type": "10-K"},
        }

        results = validate_batch(extractions, contexts)

        assert len(results) == 2
        # Check merged keys exist
        for r in results:
            assert "llm_validated" in r
            assert "llm_confidence" in r
            assert "llm_reasoning" in r
            assert "llm_fiscal_period" in r
            # Original keys preserved
            assert "raw_snippet" in r
            assert "extracted_value_usd" in r

    @patch("src.ingestion.llm_validator._get_client")
    @patch("src.ingestion.llm_validator.time")
    def test_batch_empty_list(self, mock_time, mock_get_client):
        """Empty extraction list returns empty results."""
        mock_time.time.return_value = 1000.0
        results = validate_batch([], {})
        assert results == []

    @patch("src.ingestion.llm_validator._get_client")
    @patch("src.ingestion.llm_validator.time")
    def test_batch_unknown_cik_uses_default_context(self, mock_time, mock_get_client):
        """Unknown CIK falls back to default company context."""
        mock_time.time.return_value = 1000.0
        mock_time.sleep = MagicMock()
        mock_get_client.return_value = _make_mock_client(VALID_LLM_RESPONSE)

        extractions = [{**SAMPLE_EXTRACTION, "cik": "9999999999", "form_type": "10-Q"}]
        results = validate_batch(extractions, {})

        assert len(results) == 1
        assert results[0]["llm_validated"] is True


# ---------------------------------------------------------------------------
# Constants and config tests
# ---------------------------------------------------------------------------

class TestConfig:
    def test_unavailable_result_keys(self):
        """Unavailable result has all required keys."""
        required = {"validated", "corrected_value_usd", "fiscal_period", "confidence", "reasoning"}
        assert set(_UNAVAILABLE_RESULT.keys()) == required

    def test_prompt_template_has_placeholders(self):
        """Prompt template contains all required placeholders."""
        assert "{company_name}" in _VALIDATION_PROMPT_TEMPLATE
        assert "{filing_type}" in _VALIDATION_PROMPT_TEMPLATE
        assert "extracted_value_usd" in _VALIDATION_PROMPT_TEMPLATE
        assert "{raw_snippet}" in _VALIDATION_PROMPT_TEMPLATE
        assert "{pattern_name}" in _VALIDATION_PROMPT_TEMPLATE

    def test_model_is_sonnet(self):
        assert "sonnet" in VALIDATION_MODEL
