from __future__ import annotations

"""Tests for openrouter provider model filtering."""

from backend.config import get_settings


def test_openrouter_models_are_only_free_gpt_oss() -> None:
    settings = get_settings()
    ai_config = settings.app_config().get("ai_intake", {})
    openrouter_models = ai_config.get("openrouter_models", [])
    model_ids = [m["id"] for m in openrouter_models]
    assert "openai/gpt-oss-120b" in model_ids
    assert "openai/gpt-oss-20b" in model_ids
    assert "openrouter/anthropic/claude-3.5-sonnet" not in model_ids
    assert "openrouter/openai/gpt-4o" not in model_ids
