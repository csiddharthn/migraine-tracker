from __future__ import annotations

import pytest
from backend.ai_intake.providers.groq_provider import GroqProvider
from backend.ai_intake.providers.openrouter_provider import OpenRouterProvider


def test_openrouter_provider_init():
    provider = OpenRouterProvider(api_key="fake-key", timeout_seconds=30)
    assert provider.client is not None


def test_groq_provider_init():
    provider = GroqProvider(api_key="fake-key", timeout_seconds=30)
    assert provider.client is not None
