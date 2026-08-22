from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.ai_intake import AITranscriptionError, GroqTranscriptionService

TEST_KEY = "test-key"
MODEL_WHISPER = "whisper-large-v3"
MODEL_WHISPER_TURBO = "whisper-large-v3-turbo"
AUDIO_BYTES = b"audio"
FILENAME = "recording.wav"
LANGUAGE = "de"
TRANSCRIPT = "Am Morgen begannen die Kopfschmerzen."
FALLBACK_TRANSCRIPT = "Fallback transcript"
MAX_FILE_SIZE_MB = 1


@pytest.fixture
def audio_sample() -> bytes:
    return AUDIO_BYTES


@pytest.fixture
def audio_filename() -> str:
    return FILENAME


@pytest.fixture
def audio_language() -> str:
    return LANGUAGE


@pytest.fixture
def transcription_factory():
    def make_service(**overrides):
        defaults = {
            "api_key": TEST_KEY,
            "models": [MODEL_WHISPER, MODEL_WHISPER_TURBO],
            "client_factory": lambda **_: FakeClient({MODEL_WHISPER: TRANSCRIPT}),
        }
        defaults.update(overrides)
        return GroqTranscriptionService(**defaults)
    return make_service


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


def test_transcription_uses_accurate_model_first(transcription_factory, audio_sample, audio_filename, audio_language) -> None:
    service = transcription_factory()
    result = service.transcribe(audio_sample, filename=audio_filename, language=audio_language)
    assert result == TRANSCRIPT
    assert service.model_used == MODEL_WHISPER


def test_transcription_falls_back_to_turbo() -> None:
    client = FakeClient({MODEL_WHISPER: RuntimeError("rate limited"), MODEL_WHISPER_TURBO: FALLBACK_TRANSCRIPT})
    service = GroqTranscriptionService(
        api_key=TEST_KEY,
        models=[MODEL_WHISPER, MODEL_WHISPER_TURBO],
        client_factory=lambda **_: client,
    )
    result = service.transcribe(AUDIO_BYTES)
    assert result == FALLBACK_TRANSCRIPT
    assert service.model_used == MODEL_WHISPER_TURBO


def test_transcription_rejects_empty_or_oversized_audio() -> None:
    service = GroqTranscriptionService(
        api_key=TEST_KEY,
        models=[MODEL_WHISPER],
        max_file_size_mb=MAX_FILE_SIZE_MB,
        client_factory=lambda **_: FakeClient({}),
    )

    with pytest.raises(AITranscriptionError):
        service.transcribe(b"")
    with pytest.raises(AITranscriptionError):
        service.transcribe(b"x" * (1024 * 1024 + 1))
