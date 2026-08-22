from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from backend.ai_intake.providers import AIProvider


class GroqProvider:
    """Groq provider using the official groq SDK."""

    def __init__(self, api_key: str, timeout_seconds: int = 90) -> None:
        from groq import Groq
        self.client = Groq(api_key=api_key, timeout=timeout_seconds)

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
        return self.client.audio.transcriptions.create(
            file=file,
            model=model,
            **kwargs,
        )
