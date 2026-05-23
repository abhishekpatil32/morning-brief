from pathlib import Path

import pytest

from morning_brief.config import load_config


def write_config(path: Path, provider: str, model: str = "test-model") -> None:
    path.write_text(
        f"""
backend: api
provider: {provider}
model: {model}

topic:
  name: "Test Topic"
  description: "Test description"

output:
  num_articles: 3
"""
    )


def test_openai_compatible_provider_loads_with_generic_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config_path = tmp_path / "config.yaml"
    write_config(config_path, "openai-compatible", "gpt-4o-mini")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com/v1")

    cfg = load_config(config_path, require_email=False)

    assert cfg.provider == "openai-compatible"
    assert cfg.model == "gpt-4o-mini"
    assert cfg.env.openai_api_key == "test-key"
    assert cfg.env.openai_base_url == "https://example.com/v1"


def test_openai_compatible_provider_requires_api_key(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    write_config(config_path, "openai-compatible", "gpt-4o-mini")

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        load_config(config_path, require_email=False)


def test_ollama_provider_does_not_require_api_key(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    write_config(config_path, "ollama", "llama3.1:8b")

    cfg = load_config(config_path, require_email=False)

    assert cfg.provider == "ollama"
    assert cfg.model == "llama3.1:8b"
    assert cfg.env.ollama_base_url == "http://localhost:11434"
