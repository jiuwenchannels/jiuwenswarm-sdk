"""Tests for openjiuwen.sdk.core.config — ModelConfig and RemoteConfig."""

from __future__ import annotations

import os

import pytest

from openjiuwen.sdk.core.config import ModelConfig, RemoteConfig, _normalise_provider


class TestNormaliseProvider:
    def test_openai_lowercase(self):
        assert _normalise_provider("openai") == "OpenAI"

    def test_anthropic_lowercase(self):
        assert _normalise_provider("anthropic") == "Anthropic"

    def test_siliconflow(self):
        assert _normalise_provider("siliconflow") == "SiliconFlow"

    def test_unknown_passthrough(self):
        assert _normalise_provider("MyCustomProvider") == "MyCustomProvider"

    def test_case_insensitive(self):
        assert _normalise_provider("OPENAI") == "OpenAI"
        assert _normalise_provider("Anthropic") == "Anthropic"


class TestModelConfig:
    def test_defaults(self):
        cfg = ModelConfig()
        assert cfg.provider == "openai"
        assert cfg.model == "gpt-4o"
        assert cfg.api_key is None
        assert cfg.timeout == 60.0

    def test_frozen(self):
        cfg = ModelConfig()
        with pytest.raises((AttributeError, TypeError)):
            cfg.model = "other"  # type: ignore[misc]

    def test_normalised_provider(self):
        cfg = ModelConfig(provider="anthropic")
        assert cfg._normalised_provider == "Anthropic"

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("JIUWENSWARM_PROVIDER", raising=False)
        monkeypatch.delenv("JIUWENSWARM_MODEL", raising=False)
        monkeypatch.delenv("JIUWENSWARM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("JIUWENSWARM_API_BASE", raising=False)
        monkeypatch.delenv("JIUWENSWARM_TEMPERATURE", raising=False)
        monkeypatch.delenv("JIUWENSWARM_MAX_TOKENS", raising=False)
        cfg = ModelConfig.from_env()
        assert cfg.provider == "openai"
        assert cfg.model == "gpt-4o"
        assert cfg.api_key is None

    def test_from_env_reads_vars(self, monkeypatch):
        monkeypatch.setenv("JIUWENSWARM_PROVIDER", "anthropic")
        monkeypatch.setenv("JIUWENSWARM_MODEL", "claude-3-5-sonnet-20241022")
        monkeypatch.setenv("JIUWENSWARM_API_KEY", "sk-test-key")
        monkeypatch.setenv("JIUWENSWARM_TEMPERATURE", "0.7")
        monkeypatch.setenv("JIUWENSWARM_MAX_TOKENS", "2048")
        cfg = ModelConfig.from_env()
        assert cfg.provider == "anthropic"
        assert cfg.model == "claude-3-5-sonnet-20241022"
        assert cfg.api_key == "sk-test-key"
        assert cfg.temperature == 0.7
        assert cfg.max_tokens == 2048

    def test_from_env_openai_key_fallback(self, monkeypatch):
        monkeypatch.delenv("JIUWENSWARM_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
        cfg = ModelConfig.from_env()
        assert cfg.api_key == "sk-openai"

    def test_from_env_anthropic_key_fallback(self, monkeypatch):
        monkeypatch.delenv("JIUWENSWARM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic")
        cfg = ModelConfig.from_env()
        assert cfg.api_key == "sk-anthropic"


class TestRemoteConfig:
    def test_defaults(self):
        cfg = RemoteConfig()
        assert cfg.server_url == "ws://localhost:19000/v1/ws"
        assert cfg.auth_token is None
        assert cfg.timeout == 60.0

    def test_frozen(self):
        cfg = RemoteConfig()
        with pytest.raises((AttributeError, TypeError)):
            cfg.auth_token = "x"  # type: ignore[misc]

    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("JIUWENSWARM_URL", raising=False)
        monkeypatch.delenv("JIUWENSWARM_TOKEN", raising=False)
        cfg = RemoteConfig.from_env()
        assert cfg.server_url == "ws://localhost:19000/v1/ws"
        assert cfg.auth_token is None

    def test_from_env_reads_vars(self, monkeypatch):
        monkeypatch.setenv("JIUWENSWARM_URL", "ws://prod.example.com/v1/ws")
        monkeypatch.setenv("JIUWENSWARM_TOKEN", "tok_abc123")
        cfg = RemoteConfig.from_env()
        assert cfg.server_url == "ws://prod.example.com/v1/ws"
        assert cfg.auth_token == "tok_abc123"
