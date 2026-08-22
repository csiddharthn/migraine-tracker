from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any


class AITranscriptionError(RuntimeError):
    """A user-safe failure while transcribing a headache description."""


class GroqTranscriptionService:
    def __init__(
        self,
        *,
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

        client = self._client()
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
                response = client.audio.transcriptions.create(**arguments)
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

    def _client(self) -> Any:
        if self._client_factory is not None:
            return self._client_factory(api_key=self._api_key, timeout=self.timeout_seconds)
        from groq import Groq

        return Groq(api_key=self._api_key, timeout=self.timeout_seconds)
