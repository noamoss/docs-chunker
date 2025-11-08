import json
import sys
import types

import pytest

from docs_chunker.llm_strategy import (
    ChunkingStrategy,
    _build_strategy_prompt,
    _call_ollama_strategy,
    _can_fit_in_context,
    _parse_strategy_response,
    decide_chunking_strategy,
)
from docs_chunker.structure import DocumentStructure, HeadingInfo


@pytest.fixture
def sample_structure() -> DocumentStructure:
    headings = [
        HeadingInfo(level=1, title="Title", line_idx=0, token_count=10, section_start=0, section_end=3),
        HeadingInfo(level=2, title="Section", line_idx=3, token_count=5, section_start=3, section_end=5),
    ]
    return DocumentStructure(
        headings=headings,
        total_tokens=150,
        total_lines=10,
        min_level=1,
        max_level=2,
        has_structure=True,
    )


def test_build_strategy_prompt_includes_requirements(sample_structure):
    prompt = _build_strategy_prompt(sample_structure, "# Title\n\n## Section\nContent", 200, 1200)
    assert "RAG Requirements" in prompt
    assert "Minimum tokens per chunk: 200" in prompt
    assert "Maximum tokens per chunk: 1200" in prompt


def test_can_fit_in_context_true(sample_structure):
    markdown = "# Title\n\n## Section\nContent"
    assert _can_fit_in_context(sample_structure, markdown, max_context_tokens=10000)


def test_parse_strategy_response_by_level():
    response = json.dumps({"strategy": "by_level", "level": 2, "reasoning": "test"})
    strategy = _parse_strategy_response(response)
    assert isinstance(strategy, ChunkingStrategy)
    assert strategy.strategy_type == "by_level"
    assert strategy.level == 2
    assert strategy.reasoning == "test"


def test_parse_strategy_response_custom_boundaries():
    response = json.dumps(
        {
            "strategy": "custom_boundaries",
            "boundaries": [0, 100, 200],
            "reasoning": "custom",
        }
    )
    strategy = _parse_strategy_response(response)
    assert isinstance(strategy, ChunkingStrategy)
    assert strategy.strategy_type == "custom_boundaries"
    assert strategy.boundaries == [0, 100, 200]


def test_parse_strategy_response_from_code_block():
    response = "```json\n{\"strategy\": \"by_level\", \"level\": 3}\n```"
    strategy = _parse_strategy_response(response)
    assert strategy is not None
    assert strategy.level == 3


def test_parse_strategy_response_invalid_returns_none():
    assert _parse_strategy_response("not json") is None
    assert _parse_strategy_response("{}") is None


def test_call_ollama_strategy_success(monkeypatch):
    class DummyClient:
        def __init__(self, host: str):
            self.host = host

        def generate(self, **kwargs):
            return {"response": "{\"strategy\": \"by_level\", \"level\": 2}"}

    dummy_module = types.SimpleNamespace(Client=DummyClient)
    monkeypatch.setitem(sys.modules, "ollama", dummy_module)

    response = _call_ollama_strategy("prompt", model="test", base_url="http://example")
    assert "\"strategy\"" in response

    monkeypatch.delitem(sys.modules, "ollama")


def test_call_ollama_strategy_missing_module():
    if "ollama" in sys.modules:
        del sys.modules["ollama"]
    assert _call_ollama_strategy("prompt") is None


def test_decide_chunking_strategy_returns_none_when_provider_unknown(sample_structure):
    result = decide_chunking_strategy(
        "# Title",
        sample_structure,
        200,
        1200,
        provider="openai",
    )
    assert result is None
