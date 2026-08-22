from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from backend.ai_intake.providers import AIProvider


class OpenRouterProvider:
    """OpenRouter provider using the openai SDK (OpenRouter is OpenAI-compatible)."""

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1", timeout_seconds: int = 90) -> None:
        import openai
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
        )

    def chat_completion(
        self,
        model: str,
        messages: Sequence[dict[str, Any]],
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            response_format=response_format,
            **kwargs,
        )

    def audio_transcription(
        self,
        file: tuple[str, bytes],
        model: str,
        **kwargs: Any,
    ) -> Any:
        # OpenRouter does not expose a native audio endpoint; delegate to openai-compatible audio endpoint if available.
        return self.client.audio.transcriptions.create(
            file=file,
            model=model,
            **kwargs,
        )
