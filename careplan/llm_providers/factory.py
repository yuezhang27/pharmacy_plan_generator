"""
工厂函数：根据配置返回对应 LLM Service
"""
from typing import Dict, Type

from django.conf import settings

from .base import BaseLLMService
from .openai_service import OpenAIService
from .claude_service import ClaudeService
from .mock_service import MockLLMService

# provider 标识 -> Service 类
_SERVICE_REGISTRY: Dict[str, Type[BaseLLMService]] = {
    "openai": OpenAIService,
    "claude": ClaudeService,
    "mock": MockLLMService,
}


def get_llm_service(provider: str | None = None) -> BaseLLMService:
    """
    根据 provider 返回对应的 LLM Service 实例
    provider: 从参数传入，或从 settings.LLM_PROVIDER 读取，默认 "openai"
    """
    if provider is None:
        provider = getattr(settings, "LLM_PROVIDER", "openai")
    provider = str(provider).lower()

    # Mock 模式优先：USE_MOCK_LLM=1 时强制使用 mock
    if getattr(settings, "USE_MOCK_LLM", True):
        return MockLLMService()

    service_cls = _SERVICE_REGISTRY.get(provider)
    if service_cls is None:
        raise ValueError(f"Unknown LLM provider: {provider}. Known: {list(_SERVICE_REGISTRY.keys())}")
    return service_cls()


def register_llm_service(provider: str, service_cls: Type[BaseLLMService]) -> None:
    """注册新 LLM Service（可选，用于动态扩展）"""
    _SERVICE_REGISTRY[provider.lower()] = service_cls
