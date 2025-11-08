"""Provider abstractions for LLM-based chunk validation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .structure import extract_structure
from .llm_strategy import ChunkingStrategy, decide_chunking_strategy


class LLMProvider(Protocol):
    """Protocol representing an LLM provider capable of suggesting adjustments."""

    def propose_chunk_operations(
        self,
        markdown_text: str,
        chunks_schema: list[dict[str, Any]],
        *,
        min_tokens: int,
        max_tokens: int,
        language_hint: str = "auto",
    ) -> dict[str, Any] | None:
        ...


@dataclass
class OllamaProvider:
    model: str = "llama3.1:8b"
    base_url: str = "http://localhost:11434"

    def propose_chunk_operations(
        self,
        markdown_text: str,
        chunks_schema: list[dict[str, Any]],
        *,
        min_tokens: int,
        max_tokens: int,
        language_hint: str = "auto",
    ) -> dict[str, Any] | None:
        structure = extract_structure(markdown_text)
        strategy = decide_chunking_strategy(
            markdown_text,
            structure,
            min_tokens,
            max_tokens,
            provider="local",
            model=self.model,
            base_url=self.base_url,
        )
        if not strategy:
            return None
        return _strategy_to_plan(strategy, chunks_schema)


@dataclass
class OpenAIProvider:
    api_key: str | None = None
    model: str = "gpt-4o-mini"

    def propose_chunk_operations(
        self,
        markdown_text: str,
        chunks_schema: list[dict[str, Any]],
        *,
        min_tokens: int,
        max_tokens: int,
        language_hint: str = "auto",
    ) -> dict[str, Any] | None:
        # OpenAI provider is not yet implemented; return None to signal fallback.
        return None


def _strategy_to_plan(
    strategy: ChunkingStrategy, chunks_schema: list[dict[str, Any]]
) -> dict[str, Any]:
    """Convert a ``ChunkingStrategy`` into a plan dictionary."""

    plan: dict[str, Any] = {
        "strategy": strategy.strategy_type,
        "reasoning": strategy.reasoning,
        "operations": [],
    }

    if strategy.strategy_type == "by_level" and strategy.level is not None:
        plan["level"] = strategy.level
    elif strategy.strategy_type == "custom_boundaries" and strategy.boundaries is not None:
        plan["boundaries"] = strategy.boundaries

    return plan


def get_provider(
    provider: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> LLMProvider | None:
    """Factory returning the appropriate provider implementation."""

    provider = (provider or "").lower()
    if provider == "local":
        return OllamaProvider(model=model or "llama3.1:8b", base_url=base_url or "http://localhost:11434")
    if provider == "openai":
        return OpenAIProvider(api_key=api_key, model=model or "gpt-4o-mini")
    return None
