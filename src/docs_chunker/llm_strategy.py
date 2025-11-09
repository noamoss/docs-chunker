"""Utilities for building prompts and parsing strategies from LLMs."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Literal

from .chunk import estimate_tokens
from .structure import DocumentStructure, get_heading_hierarchy, get_section_preview

logger = logging.getLogger(__name__)


@dataclass
class ChunkingStrategy:
    """LLM-determined chunking strategy description."""

    strategy_type: Literal["by_level", "custom_boundaries"]
    level: int | None = None
    boundaries: list[int] | None = None
    reasoning: str | None = None


def _build_strategy_prompt(
    structure: DocumentStructure,
    markdown_text: str,
    min_tokens: int,
    max_tokens: int,
    preview_chars: int = 300,
) -> str:
    """Build a rich prompt including structure and sample content."""

    hierarchy = get_heading_hierarchy(structure)
    preview_lines: list[str] = []
    for heading in structure.headings[:10]:
        preview = get_section_preview(markdown_text, heading, max_chars=preview_chars)
        marker = "#" * heading.level
        preview_lines.append(f"{marker} {heading.title}:\n{preview}\n")

    preview_block = (
        "\n".join(preview_lines) if preview_lines else "(No section previews available)"
    )

    prompt = (
        "You are a document chunking expert optimizing for RAG "
        "(Retrieval-Augmented Generation) systems.\n"
        "Document statistics:\n"
        f"- Total tokens: {structure.total_tokens}\n"
        f"- Total lines: {structure.total_lines}\n"
        f"- Heading levels present: {structure.min_level} to {structure.max_level}\n\n"
        f"{hierarchy}\n\n"
        "Sample Content from Sections:\n"
        f"{preview_block}\n\n"
        "RAG Requirements:\n"
        f"- Minimum tokens per chunk: {min_tokens}\n"
        f"- Maximum tokens per chunk: {max_tokens}\n"
        "- Goal: Optimize for embedding-based semantic retrieval\n\n"
        "Task: Analyze this document and decide the optimal chunking strategy.\n"
        "Considerations:\n"
        "1. Semantic coherence: keep related content together.\n"
        "2. Retrieval quality: chunks should be self-contained for embedding search.\n"
        "3. Token limits: each chunk must be within "
        f"{min_tokens}-{max_tokens} tokens.\n"
        "4. Document structure: use natural document boundaries when possible.\n\n"
        "For structured documents, choose a heading level (1-6) to chunk by.\n"
        "For unstructured documents, provide custom line boundaries.\n\n"
        "Return JSON format:\n"
        "{\n"
        '  "strategy": "by_level" | "custom_boundaries",\n'
        '  "level": 2,\n'
        '  "boundaries": [0, 150, 300],\n'
        '  "reasoning": "Brief explanation"\n'
        "}"
    )
    return prompt


def _build_structure_only_prompt(
    structure: DocumentStructure, min_tokens: int, max_tokens: int
) -> str:
    """Prompt focusing solely on structure for large documents."""

    hierarchy = get_heading_hierarchy(structure)
    prompt = (
        "You are a document chunking expert optimizing for RAG "
        "(Retrieval-Augmented Generation) systems.\n"
        "The document is too large to include full content. Use the structure "
        "information to decide a chunking strategy.\n\n"
        f"{hierarchy}\n\n"
        "Constraints:\n"
        f"- Minimum tokens per chunk: {min_tokens}\n"
        f"- Maximum tokens per chunk: {max_tokens}\n"
        "- Goal: Optimize for embedding-based semantic retrieval.\n\n"
        "Return JSON format as described previously."
    )
    return prompt


def _can_fit_in_context(
    structure: DocumentStructure,
    markdown_text: str,
    max_context_tokens: int = 8000,
    preview_chars: int = 300,
) -> bool:
    """Heuristic check for whether the prompt can include document previews."""

    hierarchy_tokens = estimate_tokens(get_heading_hierarchy(structure))
    preview_tokens = 0
    for heading in structure.headings[:10]:
        preview = get_section_preview(markdown_text, heading, max_chars=preview_chars)
        preview_tokens += estimate_tokens(preview)

    instructions_budget = 600  # rough allowance for instructions in the prompt
    total_estimate = hierarchy_tokens + preview_tokens + instructions_budget
    return total_estimate < max_context_tokens


def _call_ollama_strategy(
    prompt: str,
    model: str = "llama3.1:8b",
    base_url: str = "http://localhost:11434",
) -> str | None:
    """Call the Ollama API and return the raw response text."""

    try:
        import importlib

        ollama = importlib.import_module("ollama")
    except ModuleNotFoundError:
        return None
    except Exception:
        return None

    try:
        client = ollama.Client(host=base_url)
        response = client.generate(
            model=model,
            prompt=prompt,
            options={"temperature": 0.3},
        )
        return str(response.get("response", "")).strip()
    except Exception as e:
        logger.warning(f"Ollama API call failed: {e}", exc_info=True)
        return None


def _extract_json_from_response(response_text: str) -> str | None:
    if not response_text:
        return None

    # Try to find JSON in code blocks with bracket counting for nested structures
    json_block_match = re.search(r"```(?:json)?\s*(\{)", response_text, re.DOTALL)
    if json_block_match:
        start_pos = json_block_match.start(1)
        # Find the matching closing brace by counting brackets
        brace_count = 0
        for i in range(start_pos, len(response_text)):
            if response_text[i] == "{":
                brace_count += 1
            elif response_text[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    # Found matching closing brace
                    json_text = response_text[start_pos : i + 1]
                    # Check if it's followed by closing code block marker
                    remaining = response_text[i + 1 :].strip()
                    if remaining.startswith("```") or not remaining.startswith("`"):
                        return json_text
                    break

    # Fallback: find first { and last } (handles nested JSON correctly)
    start = response_text.find("{")
    end = response_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return response_text[start : end + 1]
    return None


def _parse_strategy_response(response_text: str) -> ChunkingStrategy | None:
    """Parse JSON response into a ``ChunkingStrategy`` instance."""

    json_text = _extract_json_from_response(response_text)
    if not json_text:
        return None

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return None

    strategy_type = data.get("strategy")
    reasoning = data.get("reasoning")

    if strategy_type == "by_level":
        level = data.get("level")
        if isinstance(level, int) and 1 <= level <= 6:
            return ChunkingStrategy(
                strategy_type="by_level", level=level, reasoning=reasoning
            )
        return None

    if strategy_type == "custom_boundaries":
        boundaries = data.get("boundaries")
        if (
            isinstance(boundaries, list)
            and boundaries
            and all(isinstance(b, int) and b >= 0 for b in boundaries)
        ):
            return ChunkingStrategy(
                strategy_type="custom_boundaries",
                boundaries=boundaries,
                reasoning=reasoning,
            )
        return None

    return None


def _decide_strategy_for_large_document(
    structure: DocumentStructure,
    min_tokens: int,
    max_tokens: int,
    *,
    model: str,
    base_url: str,
) -> ChunkingStrategy | None:
    """Fallback path when the document cannot fit entirely into the LLM context."""

    prompt = _build_structure_only_prompt(structure, min_tokens, max_tokens)
    response = _call_ollama_strategy(prompt, model=model, base_url=base_url)
    if not response:
        return None
    return _parse_strategy_response(response)


def decide_chunking_strategy(
    markdown_text: str,
    structure: DocumentStructure,
    min_tokens: int,
    max_tokens: int,
    *,
    provider: str = "local",
    model: str = "llama3.1:8b",
    base_url: str = "http://localhost:11434",
) -> ChunkingStrategy | None:
    """Determine chunking strategy using the requested provider.

    This function uses an LLM to analyze document structure and decide the optimal
    chunking strategy. The LLM considers document hierarchy, section sizes, and
    RAG requirements to determine whether to chunk by heading level or use custom
    boundaries.

    Args:
        markdown_text: Full document text in Markdown format
        structure: DocumentStructure object containing heading hierarchy and metadata
        min_tokens: Minimum tokens per chunk (RAG requirement)
        max_tokens: Maximum tokens per chunk (RAG requirement)
        provider: LLM provider to use ("local" for Ollama, "openai" for OpenAI)
        model: Model identifier for the chosen provider
        base_url: Base URL for Ollama API (only used with "local" provider)

    Returns:
        ChunkingStrategy object if successful, None if LLM unavailable or error occurs.
        None is returned gracefully to allow fallback to heuristic chunking.

    Example:
        >>> structure = extract_structure(markdown_text)
        >>> strategy = decide_chunking_strategy(
        ...     markdown_text,
        ...     structure,
        ...     min_tokens=200,
        ...     max_tokens=1200,
        ...     provider="local",
        ...     model="llama3.1:8b"
        ... )
        >>> if strategy:
        ...     print(f"Strategy: {strategy.strategy_type}, Level: {strategy.level}")
    """
    try:
        if provider != "local":
            # Only Ollama provider is implemented in this module.
            logger.debug(f"Provider '{provider}' not yet implemented, returning None")
            return None

        if not structure.has_structure and not structure.headings:
            structure = DocumentStructure(
                headings=[],
                total_tokens=structure.total_tokens,
                total_lines=structure.total_lines,
                min_level=0,
                max_level=0,
                has_structure=False,
            )

        if _can_fit_in_context(structure, markdown_text):
            prompt = _build_strategy_prompt(
                structure,
                markdown_text,
                min_tokens,
                max_tokens,
            )
            response = _call_ollama_strategy(prompt, model=model, base_url=base_url)
            if not response:
                logger.debug("No response from Ollama API")
                return None
            return _parse_strategy_response(response)

        return _decide_strategy_for_large_document(
            structure,
            min_tokens,
            max_tokens,
            model=model,
            base_url=base_url,
        )
    except Exception as e:
        logger.warning(
            f"LLM strategy decision failed: {e}",
            exc_info=True,
        )
        return None
