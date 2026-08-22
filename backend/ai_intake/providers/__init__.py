from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


class AIProvider(Protocol):
    """Abstract provider for AI chat/completion and audio transcription."""

    def chat_completion(
        self,
        model: str,
        messages: Sequence[dict[str, Any]],
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        ...

    def audio_transcription(
        self,
        file: tuple[str, bytes],
        model: str,
        **kwargs: Any,
    ) -> Any:
        ...
