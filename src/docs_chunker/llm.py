from typing import Any

from .chunk import Chunk, estimate_tokens


def _serialize_chunks(chunks: list[Chunk]) -> list[dict[str, Any]]:
    return [
        {
            "id": c.id,
            "title": c.title,
            "level": c.level,
            "token_count": estimate_tokens(c.content),
        }
        for c in chunks
    ]


def _apply_operations(
    markdown_text: str, chunks: list[Chunk], plan: dict[str, Any]
) -> list[Chunk]:
    ops = plan.get("operations") or []
    result = list(chunks)
    for op in ops:
        if op.get("type") == "merge":
            start, end = op.get("range", [None, None])
            if start is None or end is None:
                continue
            # Treat provided range as 1-based, inclusive; convert to 0-based slice [s:e)
            s = max(1, int(start)) - 1
            e = min(len(result), int(end))
            if s < 0 or e > len(result) or s >= e:
                continue
            merged_content = "".join(ch.content for ch in result[s:e])
            merged = Chunk(
                id=result[s].id,
                title=result[s].title,
                level=result[s].level,
                content=merged_content,
            )
            result = result[:s] + [merged] + result[e:]
        # Future: handle split operation as needed

    # Reassign sequential IDs and return
    for i, ch in enumerate(result, start=1):
        ch.id = i
    # Safety: ensure coverage preserved
    assert "".join(c.content for c in result).strip() == markdown_text.strip()
    return result


def _llm_propose_boundaries(
    markdown_text: str,
    chunks_schema: list[dict[str, Any]],
    *,
    language_hint: str = "auto",
    provider: str = "local",
    max_tokens: int = 1200,
) -> dict[str, Any] | None:
    """
    Placeholder for actual LLM call. Returns None when no external model is available.
    Tests monkeypatch this function to return a plan dict with operations.
    """
    return None


def validate_and_adjust_chunks(
    markdown_text: str,
    chunks: list[Chunk],
    min_tokens: int,
    max_tokens: int,
    *,
    language_hint: str = "auto",
    provider: str = "local",
) -> list[Chunk]:
    """
    Ask an LLM to propose merges/splits, then apply them.
    Guarantees coverage is preserved.
    If LLM is unavailable or returns invalid output, returns the original chunks.
    """
    proposal = _llm_propose_boundaries(
        markdown_text,
        _serialize_chunks(chunks),
        language_hint=language_hint,
        provider=provider,
        max_tokens=max_tokens,
    )
    if not proposal:
        return chunks

    try:
        adjusted = _apply_operations(markdown_text, chunks, proposal)
    except Exception:
        return chunks

    # Optional: enforce min/max softly via further merges (not using LLM)
    result: list[Chunk] = []
    for ch in adjusted:
        if result and estimate_tokens(result[-1].content) < min_tokens:
            prev = result.pop()
            result.append(
                Chunk(
                    id=prev.id,
                    title=prev.title or ch.title,
                    level=min(prev.level, ch.level),
                    content=prev.content + ch.content,
                )
            )
        else:
            result.append(ch)

    for i, ch in enumerate(result, start=1):
        ch.id = i
    assert "".join(c.content for c in result).strip() == markdown_text.strip()
    return result
