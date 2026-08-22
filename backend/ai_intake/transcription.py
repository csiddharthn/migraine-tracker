from __future__ import annotations

"""Purpose: AI transcription service for headache descriptions.

Usage: Transcribes audio/text descriptions using configured AI providers.

Functions available:
- None (service class)

Classes available:
- AITranscriptionError
- GroqTranscriptionService

Call hierarchy:
- transcription.py -> backend.ai_intake.providers
"""

from collections.abc import Callable, Sequence
from typing import Any


from backend.ai_intake.providers import AIProvider
from backend.ai_intake.providers.groq_provider import GroqProvider
from backend.ai_intake.providers.openrouter_provider import OpenRouterProvider


class AITranscriptionError(RuntimeError):
    """A user-safe failure while transcribing a headache description."""


class GroqTranscriptionService:
    def __init__(
        self,
        *,
        provider_name: str | None = None,
        api_key: str,
        models: Sequence[str],
        timeout_seconds: int = 90,
        max_file_size_mb: int = 25,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        if not api_key.strip():
            raise AITranscriptionError("Für die Spracherkennung ist kein Groq-API-Schlüssel konfiguriert.")
        self.models = tuple(dict.fromkeys(model.strip() for model in models if model.strip()))
        if not self.models:
            raise AITranscriptionError("Für die Spracherkennung ist kein Groq-Modell konfiguriert.")
        self.provider_name = provider_name or "groq"
        self.provider: AIProvider = self._build_provider(self.provider_name, api_key, timeout_seconds)
        self.timeout_seconds = timeout_seconds
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.model_used: str | None = None
        self.attempted_models: tuple[str, ...] = ()
        self._api_key = api_key
        self._client_factory = client_factory

    def transcribe(
        self,
        audio: bytes,
        *,
        filename: str = "migraine-description.wav",
        language: str | None = None,
    ) -> str:
        if not audio:
            raise AITranscriptionError("Die Audioaufnahme ist leer.")
        if len(audio) > self.max_file_size_bytes:
            raise AITranscriptionError("Die Audioaufnahme ist größer als das für den kostenlosen Tarif erlaubte Limit.")

        provider = self.provider
        if self._client_factory is not None:
            client = self._client_factory()
            if hasattr(client, "audio"):
                provider = client.audio.transcriptions
            else:
                provider = client
        failures: list[Exception] = []
        attempted: list[str] = []
        for model_name in self.models:
            attempted.append(model_name)
            try:
                arguments: dict[str, Any] = {
                    "file": (filename, audio),
                    "model": model_name,
                    "prompt": (
                        "Kopfschmerz- und Migränetagebuch. Wichtige Begriffe: Kopfschmerzen, Auslöser, "
                        "Übelkeit, Lichtscheu, Lärmscheu, Geruchsempfindlichkeit, Aura, Höhepunkt, "
                        "Eletriptan, Amitriptylin neuraxpharm, Aimovig, Momeallerg Nasenspray."
                    ),
                    "response_format": "json",
                    "temperature": 0.0,
                }
                if language:
                    arguments["language"] = language
                if hasattr(provider, "audio_transcription"):
                    response = provider.audio_transcription(
                        file=(filename, audio),
                        model=model_name,
                        **{k: v for k, v in arguments.items() if k not in ("file", "model")},
                    )
                else:
                    response = provider.create(
                        file=(filename, audio),
                        model=model_name,
                        **{k: v for k, v in arguments.items() if k not in ("file", "model")},
                    )
                transcript = str(response.text).strip()
                if not transcript:
                    raise ValueError("Groq returned an empty transcription.")
                self.model_used = model_name
                self.attempted_models = tuple(attempted)
                return transcript
            except Exception as exc:
                failures.append(exc)

        self.attempted_models = tuple(attempted)
        raise AITranscriptionError(
            "Die Aufnahme konnte mit keinem der konfigurierten Groq-Sprachmodelle transkribiert werden. "
            "Prüfen Sie den API-Schlüssel, die Internetverbindung und die Groq-Nutzungslimits."
        ) from failures[-1]

    def _build_provider(self, provider_name: str, api_key: str, timeout_seconds: int) -> AIProvider:
        if provider_name == "openrouter":
            return OpenRouterProvider(api_key=api_key, timeout_seconds=timeout_seconds)
        return GroqProvider(api_key=api_key, timeout_seconds=timeout_seconds)

    def _client(self) -> AIProvider:
        return self.provider
