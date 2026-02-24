"""
Unit tests for LLM service abstraction layer
"""
import pytest
from unittest.mock import patch, MagicMock

from careplan.llm_providers import (
    BaseLLMService,
    OpenAIService,
    ClaudeService,
    MockLLMService,
    get_llm_service,
)
from careplan.llm_providers.mock_service import MOCK_CAREPLAN_TEXT


class TestMockLLMService:
    """Mock service always returns fixed text."""

    def test_generate_returns_mock_text(self):
        service = MockLLMService()
        result = service.generate(
            system_message="You are a pharmacist.",
            user_message="Generate care plan for patient X.",
        )
        assert result == MOCK_CAREPLAN_TEXT
        assert "[Mock]" in result


class TestOpenAIService:
    """OpenAI service (mocked API call)."""

    def test_generate_calls_openai_api(self):
        service = OpenAIService(api_key="test-key")
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated care plan content"

        with patch("careplan.llm_providers.openai_service.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = service.generate(
                system_message="You are a pharmacist.",
                user_message="Generate care plan.",
            )
            assert result == "Generated care plan content"
            mock_client.chat.completions.create.assert_called_once()

    def test_missing_api_key_raises(self):
        service = OpenAIService(api_key="")
        with pytest.raises(ValueError) as exc_info:
            service.generate("sys", "user")
        assert "OPENAI_API_KEY" in str(exc_info.value)


class TestClaudeService:
    """Claude service (mocked API call)."""

    def test_generate_calls_claude_api(self):
        service = ClaudeService(api_key="test-key")
        mock_content = MagicMock()
        mock_content.text = "Claude generated content"
        mock_message = MagicMock()
        mock_message.content = [mock_content]

        with patch("careplan.llm_providers.claude_service.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_message
            mock_anthropic.return_value = mock_client

            result = service.generate(
                system_message="You are a pharmacist.",
                user_message="Generate care plan.",
            )
            assert result == "Claude generated content"
            mock_client.messages.create.assert_called_once()

    def test_missing_api_key_raises(self):
        service = ClaudeService(api_key="")
        with pytest.raises(ValueError) as exc_info:
            service.generate("sys", "user")
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)


class TestGetLLMService:
    """Factory function."""

    def test_mock_mode_returns_mock(self):
        with patch("careplan.llm_providers.factory.settings") as mock_settings:
            mock_settings.USE_MOCK_LLM = True
            mock_settings.LLM_PROVIDER = "openai"
            service = get_llm_service()
            assert isinstance(service, MockLLMService)

    def test_openai_mode_returns_openai(self):
        with patch("careplan.llm_providers.factory.settings") as mock_settings:
            mock_settings.USE_MOCK_LLM = False
            mock_settings.LLM_PROVIDER = "openai"
            service = get_llm_service()
            assert isinstance(service, OpenAIService)

    def test_explicit_provider_overrides_settings(self):
        with patch("careplan.llm_providers.factory.settings") as mock_settings:
            mock_settings.USE_MOCK_LLM = False
            mock_settings.LLM_PROVIDER = "openai"
            service = get_llm_service(provider="claude")
            assert isinstance(service, ClaudeService)

    def test_unknown_provider_raises(self):
        with patch("careplan.llm_providers.factory.settings") as mock_settings:
            mock_settings.USE_MOCK_LLM = False
            with pytest.raises(ValueError) as exc_info:
                get_llm_service(provider="unknown")
            assert "Unknown LLM provider" in str(exc_info.value)


class TestGenerateCareplanIntegration:
    """llm_service.generate_careplan uses get_llm_service."""

    def test_generate_careplan_returns_text(self):
        from careplan.llm_service import generate_careplan
        from types import SimpleNamespace

        patient = SimpleNamespace(first_name="John", last_name="Doe", mrn="123456", dob="1990-01-15")
        provider = SimpleNamespace(name="Dr. Jane", npi="1234567890")

        with patch("careplan.llm_service.get_llm_service") as mock_get:
            mock_service = MockLLMService()
            mock_get.return_value = mock_service

            result = generate_careplan(
                patient=patient,
                provider=provider,
                primary_diagnosis="E11.9",
                additional_diagnosis="",
                medication_name="Metformin",
                medication_history="",
                patient_records="Stable.",
            )
            assert result == MOCK_CAREPLAN_TEXT
            mock_get.assert_called_once_with(provider=None)

    def test_generate_careplan_passes_llm_provider(self):
        from careplan.llm_service import generate_careplan
        from types import SimpleNamespace

        patient = SimpleNamespace(first_name="J", last_name="D", mrn="123456", dob="1990-01-15")
        provider = SimpleNamespace(name="Dr. X", npi="1234567890")

        with patch("careplan.llm_service.get_llm_service") as mock_get:
            mock_service = MockLLMService()
            mock_get.return_value = mock_service

            generate_careplan(
                patient=patient,
                provider=provider,
                primary_diagnosis="E11.9",
                additional_diagnosis="",
                medication_name="M",
                medication_history="",
                patient_records="R",
                llm_provider="claude",
            )
            mock_get.assert_called_once_with(provider="claude")
