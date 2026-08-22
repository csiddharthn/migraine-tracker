from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.ai_intake import AITranscriptionError, GroqTranscriptionService


class FakeTranscriptions:
    def __init__(self, results: dict[str, str | Exception]) -> None:
        self.results = results
        self.arguments: list[dict] = []

    def create(self, **kwargs):
        self.arguments.append(kwargs)
        result = self.results[kwargs["model"]]
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(text=result)


class FakeClient:
    def __init__(self, results: dict[str, str | Exception]) -> None:
        self.audio = SimpleNamespace(transcriptions=FakeTranscriptions(results))


def test_transcription_uses_accurate_model_first() -> None:
    client = FakeClient({"whisper-large-v3": "Am Morgen begannen die Kopfschmerzen."})
    service = GroqTranscriptionService(
        api_key="test-key",
        models=["whisper-large-v3", "whisper-large-v3-turbo"],
        client_factory=lambda **_: client,
    )

    transcript = service.transcribe(b"audio", filename="recording.wav", language="de")

    assert transcript == "Am Morgen begannen die Kopfschmerzen."
    assert service.model_used == "whisper-large-v3"
    request = client.audio.transcriptions.arguments[0]
    assert request["file"] == ("recording.wav", b"audio")
    assert request["language"] == "de"
    assert request["temperature"] == 0.0


def test_transcription_falls_back_to_turbo() -> None:
    client = FakeClient(
        {
            "whisper-large-v3": RuntimeError("rate limited"),
            "whisper-large-v3-turbo": "Fallback transcript",
        }
    )
    service = GroqTranscriptionService(
        api_key="test-key",
        models=["whisper-large-v3", "whisper-large-v3-turbo"],
        client_factory=lambda **_: client,
    )

    transcript = service.transcribe(b"audio")

    assert transcript == "Fallback transcript"
    assert service.model_used == "whisper-large-v3-turbo"
    assert service.attempted_models == ("whisper-large-v3", "whisper-large-v3-turbo")


def test_transcription_rejects_empty_or_oversized_audio() -> None:
    service = GroqTranscriptionService(
        api_key="test-key",
        models=["whisper-large-v3"],
        max_file_size_mb=1,
        client_factory=lambda **_: FakeClient({}),
    )

    with pytest.raises(AITranscriptionError):
        service.transcribe(b"")
    with pytest.raises(AITranscriptionError):
        service.transcribe(b"x" * (1024 * 1024 + 1))
