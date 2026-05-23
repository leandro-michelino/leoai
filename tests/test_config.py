import os

from leoai.config import get_settings


def test_get_settings_uses_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1-mini")

    settings = get_settings()

    assert settings.api_key == "test-key"
    assert settings.model == "gpt-4.1-mini"


def test_get_settings_raises_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1-mini")

    try:
        get_settings()
        assert False, "Era esperado ValueError"
    except ValueError as exc:
        assert "OPENAI_API_KEY" in str(exc)
