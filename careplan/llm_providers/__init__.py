"""
LLM 服务抽象层：业务代码不依赖具体 LLM 实现
支持 OpenAI、Claude 等，通过配置切换
"""
from .base import BaseLLMService
from .openai_service import OpenAIService
from .claude_service import ClaudeService
from .mock_service import MockLLMService
from .factory import get_llm_service

__all__ = [
    "BaseLLMService",
    "OpenAIService",
    "ClaudeService",
    "MockLLMService",
    "get_llm_service",
]
