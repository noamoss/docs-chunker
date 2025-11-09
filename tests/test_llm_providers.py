from typing import Any

from docs_chunker.llm_providers import OllamaProvider, OpenAIProvider, get_provider


def test_get_provider_local_returns_ollama():
    provider = get_provider("local", model="model", base_url="http://host")
    assert isinstance(provider, OllamaProvider)
    assert provider.model == "model"
    assert provider.base_url == "http://host"


def test_get_provider_openai_returns_openai():
    provider = get_provider("openai", model="gpt", api_key="key")
    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "gpt"
    assert provider.api_key == "key"


def test_get_provider_unknown_returns_none():
    assert get_provider("unknown") is None


def test_ollama_provider_returns_none_when_strategy_missing(monkeypatch):
    provider = OllamaProvider(model="test", base_url="http://host")

    def fake_decide(*args: Any, **kwargs: Any):
        return None

    monkeypatch.setattr(
        "docs_chunker.llm_providers.decide_chunking_strategy", fake_decide
    )

    result = provider.propose_chunk_operations(
        "# Title",
        [],
        min_tokens=100,
        max_tokens=200,
    )
    assert result is None


def test_openai_provider_not_implemented():
    provider = OpenAIProvider(api_key="key", model="gpt")
    plan = provider.propose_chunk_operations(
        "# Title",
        [],
        min_tokens=100,
        max_tokens=200,
    )
    assert plan is None
