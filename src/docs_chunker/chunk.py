import re
from dataclasses import dataclass


@dataclass
class Chunk:
    id: int
    title: str
    level: int
    content: str


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
PARAGRAPH_BREAK_RE = re.compile(r"\n\s*\n")


def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Estimate token count for text using tiktoken if available, otherwise use heuristic.

    Args:
        text: Text to estimate tokens for
        model: Model name for tiktoken encoding (default: "gpt-4")

    Returns:
        Estimated token count (always at least 1)
    """
    try:
        import tiktoken

        enc = tiktoken.encoding_for_model(model)
        return max(1, len(enc.encode(text)))
    except ImportError:
        # Fallback heuristic: ~1 token per 4 chars (safe lower-bound)
        # Ensures Hebrew/RTL text remains counted by length
        return max(1, len(text) // 4)
    except Exception:
        # If tiktoken fails for any reason (e.g., unknown model), fall back
        return max(1, len(text) // 4)


def _find_headings(lines: list[str]) -> list[tuple[int, int, str]]:
    heads: list[tuple[int, int, str]] = []
    for idx, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            heads.append((idx, level, title))
    return heads


def _extract_title_from_content(content: str, fallback: str = "") -> str:
    """Extract title from content's first heading or use fallback."""
    lines = content.splitlines()
    for line in lines[:5]:  # Check first few lines
        m = HEADING_RE.match(line)
        if m:
            return m.group(2).strip()
    # Fallback: use first non-empty line if it's short
    for line in lines[:10]:
        stripped = line.strip()
        if stripped and len(stripped) < 100 and not stripped.startswith("#"):
            return stripped[:80]
    return fallback or "Untitled"


def _split_oversized_chunk(
    chunk: Chunk, max_tokens: int, max_depth: int = 10, current_depth: int = 0
) -> list[Chunk]:
    """
    Split a chunk that exceeds max_tokens by paragraphs or subheadings.

    Args:
        chunk: Chunk to split
        max_tokens: Maximum tokens per chunk
        max_depth: Maximum recursion depth to prevent infinite loops (default: 10)
        current_depth: Current recursion depth (default: 0)

    Returns:
        List of Chunk objects

    Raises:
        RuntimeError: If max_depth is exceeded (indicates content that can't be split)
    """
    # Prevent infinite recursion on edge cases
    if current_depth >= max_depth:
        # Fallback: split by character count to ensure progress
        target_size = max_tokens * 4  # chars
        if len(chunk.content) <= target_size:
            return [chunk]
        # Force split by approximate char count
        parts = []
        for i in range(0, len(chunk.content), target_size):
            parts.append(chunk.content[i : i + target_size])
        split_chunks = []
        for idx, part in enumerate(parts):
            title = chunk.title if idx == 0 else f"{chunk.title} (part {idx + 1})"
            split_chunks.append(
                Chunk(id=chunk.id, title=title, level=chunk.level, content=part)
            )
        return split_chunks

    content = chunk.content
    tokens = estimate_tokens(content)
    if tokens <= max_tokens:
        return [chunk]

    lines = content.splitlines(keepends=True)
    # Try splitting by subheadings first (deeper level than current)
    subheadings = []
    for idx, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) > chunk.level:
            subheadings.append((idx, len(m.group(1)), m.group(2).strip()))

    if subheadings:
        # Split by subheadings
        parts: list[tuple[int, int, str]] = []
        for i, (sub_idx, sub_level, sub_title) in enumerate(subheadings):
            start = subheadings[i - 1][0] if i > 0 else 0
            end = sub_idx
            if start < end:
                parts.append(
                    (start, end, subheadings[i - 1][2] if i > 0 else chunk.title)
                )
        # Add last part
        if subheadings:
            last_start = subheadings[-1][0]
            parts.append((last_start, len(lines), subheadings[-1][2]))

        split_chunks: list[Chunk] = []
        for start, end, part_title in parts:
            part_content = "".join(lines[start:end])
            if estimate_tokens(part_content) > max_tokens:
                # Recursively split this part
                temp_chunk = Chunk(
                    id=chunk.id,
                    title=part_title,
                    level=chunk.level + 1,
                    content=part_content,
                )
                split_chunks.extend(
                    _split_oversized_chunk(
                        temp_chunk, max_tokens, max_depth, current_depth + 1
                    )
                )
            else:
                split_chunks.append(
                    Chunk(
                        id=chunk.id,
                        title=part_title,
                        level=chunk.level + 1,
                        content=part_content,
                    )
                )
        return split_chunks

    # No subheadings: try to split by numbered list items or bold headings first
    # Look for numbered list patterns (1., 2., etc.) or bold text (**text**)
    numbered_item_re = re.compile(r"^\s*\d+\.\s+", re.MULTILINE)
    bold_re = re.compile(r"^\s*\*\*[^*]+\*\*", re.MULTILINE)

    # Find potential split points
    split_points: list[int] = [0]
    for match in numbered_item_re.finditer(content):
        if match.start() > 0:
            split_points.append(match.start())
    for match in bold_re.finditer(content):
        if match.start() > 0 and match.start() not in split_points:
            split_points.append(match.start())
    split_points = sorted(set(split_points))
    split_points.append(len(content))

    # If we found split points, use them
    if len(split_points) > 2:
        split_chunks: list[Chunk] = []
        for i in range(len(split_points) - 1):
            start = split_points[i]
            end = split_points[i + 1]
            part_content = content[start:end]
            part_tokens = estimate_tokens(part_content)

            if part_tokens > max_tokens:
                # Recursively split this part
                part_title = _extract_title_from_content(part_content, chunk.title)
                temp_chunk = Chunk(
                    id=chunk.id,
                    title=part_title,
                    level=chunk.level,
                    content=part_content,
                )
                split_chunks.extend(
                    _split_oversized_chunk(
                        temp_chunk, max_tokens, max_depth, current_depth + 1
                    )
                )
            else:
                part_title = _extract_title_from_content(part_content, chunk.title)
                split_chunks.append(
                    Chunk(
                        id=chunk.id,
                        title=part_title,
                        level=chunk.level,
                        content=part_content,
                    )
                )

        return split_chunks if split_chunks else [chunk]

    # Fallback: split by paragraphs, preserving exact whitespace
    # Find all paragraph breaks with their exact positions and content
    para_breaks = list(PARAGRAPH_BREAK_RE.finditer(content))
    if len(para_breaks) == 0:
        # Single paragraph or no clear breaks: split by approximate size
        target_size = max_tokens * 4  # chars
        if len(content) <= target_size:
            return [chunk]
        # Split by approximate char count
        parts = []
        for i in range(0, len(content), target_size):
            parts.append(content[i : i + target_size])
        split_chunks = []
        for idx, part in enumerate(parts):
            title = chunk.title if idx == 0 else f"{chunk.title} (part {idx + 1})"
            split_chunks.append(
                Chunk(id=chunk.id, title=title, level=chunk.level, content=part)
            )
        return split_chunks

    # Extract paragraphs with their original separators preserved
    # Each element is (paragraph_text, separator_after)
    paragraphs_with_seps: list[tuple[str, str]] = []
    last_end = 0

    for match in para_breaks:
        # Extract paragraph text (from last break to current break)
        para_text = content[last_end : match.start()]
        # Extract the exact separator (the matched whitespace/newlines)
        separator = match.group(0)
        paragraphs_with_seps.append((para_text, separator))
        last_end = match.end()

    # Add the last paragraph (after the last break)
    if last_end < len(content):
        paragraphs_with_seps.append((content[last_end:], ""))

    # Split by paragraphs, grouping to stay under max_tokens
    # Preserve original separators when joining
    split_chunks: list[Chunk] = []
    current_group: list[tuple[str, str]] = []  # (text, separator_after)
    current_tokens = 0

    for para_text, separator in paragraphs_with_seps:
        para_tokens = estimate_tokens(para_text)
        # If a single paragraph exceeds max_tokens, split it
        if para_tokens > max_tokens:
            # Finish current group first
            if current_group:
                # Reconstruct with original separators
                group_parts = []
                for p_text, p_sep in current_group:
                    group_parts.append(p_text)
                    if p_sep:
                        group_parts.append(p_sep)
                group_content = "".join(group_parts)
                title = _extract_title_from_content(group_content, chunk.title)
                split_chunks.append(
                    Chunk(
                        id=chunk.id,
                        title=title,
                        level=chunk.level,
                        content=group_content,
                    )
                )
                current_group = []
                current_tokens = 0
            # Split the oversized paragraph
            part_title = _extract_title_from_content(para_text, chunk.title)
            temp_chunk = Chunk(
                id=chunk.id, title=part_title, level=chunk.level, content=para_text
            )
            split_parts = _split_oversized_chunk(
                temp_chunk, max_tokens, max_depth, current_depth + 1
            )
            # Preserve the separator after the oversized paragraph by appending it
            # to the last chunk of the split result
            if split_parts and separator:
                split_parts[-1] = Chunk(
                    id=split_parts[-1].id,
                    title=split_parts[-1].title,
                    level=split_parts[-1].level,
                    content=split_parts[-1].content + separator,
                )
            split_chunks.extend(split_parts)
        elif current_tokens + para_tokens > max_tokens and current_group:
            # Finish current group
            group_parts = []
            for p_text, p_sep in current_group:
                group_parts.append(p_text)
                if p_sep:
                    group_parts.append(p_sep)
            group_content = "".join(group_parts)
            title = _extract_title_from_content(group_content, chunk.title)
            split_chunks.append(
                Chunk(
                    id=chunk.id, title=title, level=chunk.level, content=group_content
                )
            )
            current_group = [(para_text, separator)]
            current_tokens = para_tokens
        else:
            current_group.append((para_text, separator))
            current_tokens += para_tokens

    # Add remaining
    if current_group:
        group_parts = []
        for p_text, p_sep in current_group:
            group_parts.append(p_text)
            if p_sep:
                group_parts.append(p_sep)
        group_content = "".join(group_parts)
        title = _extract_title_from_content(group_content, chunk.title)
        split_chunks.append(
            Chunk(id=chunk.id, title=title, level=chunk.level, content=group_content)
        )

    return split_chunks if split_chunks else [chunk]


def chunk_markdown(
    markdown_text: str, min_tokens: int = 200, max_tokens: int = 1200
) -> list[Chunk]:
    """
    Chunk markdown text into smaller pieces based on structure and token limits.

    Args:
        markdown_text: Markdown text to chunk
        min_tokens: Minimum tokens per chunk (must be >= 1)
        max_tokens: Maximum tokens per chunk (must be >= min_tokens)

    Returns:
        List of Chunk objects

    Raises:
        ValueError: If min_tokens < 1 or max_tokens < min_tokens
    """
    if min_tokens < 1:
        raise ValueError(f"min_tokens must be >= 1, got {min_tokens}")
    if max_tokens < min_tokens:
        raise ValueError(
            f"max_tokens ({max_tokens}) must be >= min_tokens ({min_tokens})"
        )
    lines = markdown_text.splitlines(keepends=True)
    headings = _find_headings(lines)

    if not headings:
        # No headings: split by size if needed
        if estimate_tokens(markdown_text) > max_tokens:
            chunks = _split_oversized_chunk(
                Chunk(
                    id=1,
                    title=_extract_title_from_content(markdown_text),
                    level=0,
                    content=markdown_text,
                ),
                max_tokens,
            )
            for i, ch in enumerate(chunks, start=1):
                ch.id = i
            return chunks
        return [
            Chunk(
                id=1,
                title=_extract_title_from_content(markdown_text),
                level=0,
                content=markdown_text,
            )
        ]

    # Choose a base level that partitions the document
    # (one level deeper than the minimum if possible)
    min_level = min(level for _, level, _ in headings)
    has_deeper = any(level > min_level for _, level, _ in headings)
    base_level = min_level + 1 if has_deeper else min_level

    # Boundaries are all headings with level <= base_level, starting from the first line
    boundaries: list[int] = [0]
    titles_levels: list[tuple[str, int]] = []
    for idx, level, title in headings:
        if level <= base_level:
            boundaries.append(idx)
            titles_levels.append((title, level))

    # Ensure unique, sorted boundaries and include document end
    boundaries = sorted(set(boundaries))
    if boundaries[0] != 0:
        boundaries.insert(0, 0)
    if boundaries[-1] != len(lines):
        boundaries.append(len(lines))

    # Build chunks between consecutive boundaries;
    # title/level from the heading at the start boundary if present
    chunks: list[Chunk] = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        # Find heading at start
        m = HEADING_RE.match(lines[start]) if start < len(lines) else None
        if m:
            title = m.group(2).strip()
            level = len(m.group(1))
        else:
            # Use previous heading's title/level if exists;
            # otherwise extract from content
            if chunks:
                title = chunks[-1].title
                level = chunks[-1].level
            else:
                # Extract from first lines of content
                content_preview = "".join(lines[start : min(start + 10, end)])
                title = _extract_title_from_content(content_preview)
                level = 0
        content = "".join(lines[start:end])
        chunks.append(
            Chunk(id=len(chunks) + 1, title=title, level=level, content=content)
        )

    # Merge undersized adjacent chunks
    merged: list[Chunk] = []
    for ch in chunks:
        if merged and estimate_tokens(merged[-1].content) < min_tokens:
            prev = merged.pop()
            combined = Chunk(
                id=prev.id,
                title=prev.title or ch.title,
                level=min(prev.level, ch.level),
                content=prev.content + ch.content,
            )
            merged.append(combined)
        else:
            merged.append(ch)

    # Split oversized chunks
    final: list[Chunk] = []
    for ch in merged:
        if estimate_tokens(ch.content) > max_tokens:
            split = _split_oversized_chunk(ch, max_tokens)
            final.extend(split)
        else:
            # Ensure title is not empty
            if not ch.title:
                ch.title = _extract_title_from_content(ch.content)
            final.append(ch)

    # Reassign IDs
    for i, ch in enumerate(final, start=1):
        ch.id = i

    return final
