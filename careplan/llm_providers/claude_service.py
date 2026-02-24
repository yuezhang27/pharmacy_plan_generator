"""
Anthropic Claude 实现
"""
import os

from django.conf import settings

from .base import BaseLLMService


class ClaudeService(BaseLLMService):
    """Anthropic Claude API"""

    provider_id = "claude"

    def __init__(self, *, api_key: str | None = None, model: str = "claude-3-5-sonnet-20241022"):
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or getattr(settings, "ANTHROPIC_API_KEY", "")
        self._model = model or getattr(settings, "CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

    def generate(
        self,
        system_message: str,
        user_message: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        if not self._api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment or settings")

        from anthropic import Anthropic

        client = Anthropic(api_key=self._api_key)
        message = client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_message,
            messages=[{"role": "user", "content": user_message}],
            temperature=temperature,
        )
        # Claude 返回 content 为 ContentBlock 列表，取 text 类型拼接
        text_parts = []
        for block in message.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "".join(text_parts) if text_parts else ""
