"""Utilities for building prompts and parsing strategies from LLMs."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal, Optional

from .chunk import estimate_tokens
from .structure import DocumentStructure, get_heading_hierarchy, get_section_preview


@dataclass
class ChunkingStrategy:
    """LLM-determined chunking strategy description."""

    strategy_type: Literal["by_level", "custom_boundaries"]
    level: Optional[int] = None
    boundaries: Optional[list[int]] = None
    reasoning: Optional[str] = None


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

    preview_block = "\n".join(preview_lines) if preview_lines else "(No section previews available)"

    prompt = f"""
You are a document chunking expert optimizing for RAG (Retrieval-Augmented Generation) systems.
Document statistics:
- Total tokens: {structure.total_tokens}
- Total lines: {structure.total_lines}
- Heading levels present: {structure.min_level} to {structure.max_level}

{hierarchy}

Sample Content from Sections:
{preview_block}

RAG Requirements:
- Minimum tokens per chunk: {min_tokens}
- Maximum tokens per chunk: {max_tokens}
- Goal: Optimize for embedding-based semantic retrieval

Task: Analyze this document and decide the optimal chunking strategy.
Considerations:
1. Semantic coherence: keep related content together.
2. Retrieval quality: chunks should be self-contained for embedding search.
3. Token limits: each chunk must be within {min_tokens}-{max_tokens} tokens.
4. Document structure: use natural document boundaries when possible.

For structured documents, choose a heading level (1-6) to chunk by.
For unstructured documents, provide custom line boundaries.

Return JSON format:
{{
  "strategy": "by_level" | "custom_boundaries",
  "level": 2,
  "boundaries": [0, 150, 300],
  "reasoning": "Brief explanation"
}}
""".strip()
    return prompt


def _build_structure_only_prompt(
    structure: DocumentStructure, min_tokens: int, max_tokens: int
) -> str:
    """Prompt focusing solely on structure for large documents."""

    hierarchy = get_heading_hierarchy(structure)
    prompt = f"""
You are a document chunking expert optimizing for RAG (Retrieval-Augmented Generation) systems.
The document is too large to include full content. Use the structure information to decide a chunking strategy.

{hierarchy}

Constraints:
- Minimum tokens per chunk: {min_tokens}
- Maximum tokens per chunk: {max_tokens}
- Goal: Optimize for embedding-based semantic retrieval.

Return JSON format as described previously.
""".strip()
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
    return total_estimate + structure.total_tokens < max_context_tokens


def _call_ollama_strategy(
    prompt: str,
    model: str = "llama3.1:8b",
    base_url: str = "http://localhost:11434",
) -> Optional[str]:
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
    except Exception:
        return None


def _extract_json_from_response(response_text: str) -> Optional[str]:
    if not response_text:
        return None

    code_block = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if code_block:
        return code_block.group(1)

    generic_block = re.search(r"```\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if generic_block:
        return generic_block.group(1)

    start = response_text.find("{")
    end = response_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return response_text[start : end + 1]
    return None


def _parse_strategy_response(response_text: str) -> Optional[ChunkingStrategy]:
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
) -> Optional[ChunkingStrategy]:
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
) -> Optional[ChunkingStrategy]:
    """Determine chunking strategy using the requested provider."""

    if provider != "local":
        # Only Ollama provider is implemented in this module.
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
        prompt = _build_strategy_prompt(structure, markdown_text, min_tokens, max_tokens)
        response = _call_ollama_strategy(prompt, model=model, base_url=base_url)
        if not response:
            return None
        return _parse_strategy_response(response)

    return _decide_strategy_for_large_document(
        structure,
        min_tokens,
        max_tokens,
        model=model,
        base_url=base_url,
    )
