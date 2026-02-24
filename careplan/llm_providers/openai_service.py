"""
OpenAI GPT 实现
"""
import os

from django.conf import settings

from .base import BaseLLMService


class OpenAIService(BaseLLMService):
    """OpenAI API (GPT-4o-mini 等)"""

    provider_id = "openai"

    def __init__(self, *, api_key: str | None = None, model: str = "gpt-4o-mini"):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", "")
        self._model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    def generate(
        self,
        system_message: str,
        user_message: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY not found in environment or settings")

        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
