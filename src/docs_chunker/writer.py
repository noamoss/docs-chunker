import re
from pathlib import Path

import yaml

from .chunk import Chunk, estimate_tokens
from .io import checksum, ensure_dir, output_paths_for, write_text


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\-\s\u0590-\u05FF]", "", text)  # keep Hebrew and word chars
    text = re.sub(r"[\s_]+", "-", text)
    return text[:50] or "chunk"


def _fallback_split_single_chunk(ch: Chunk) -> list[Chunk]:
    lines = ch.content.splitlines(keepends=True)
    # Find first level-2 heading boundary within the content
    first_h2_idx = None
    for idx, line in enumerate(lines):
        m = re.match(r"^(##)\s+", line)
        if m:
            first_h2_idx = idx
            break
    if first_h2_idx is None or first_h2_idx == 0:
        return [ch]

    part1 = "".join(lines[:first_h2_idx])
    part2 = "".join(lines[first_h2_idx:])

    # Titles from headings at the start of each part if present
    def title_level(text: str) -> tuple[str, int]:
        m = re.match(r"^(#{1,6})\s+(.*)$", text.splitlines()[0] if text else "")
        if m:
            return m.group(2).strip(), len(m.group(1))
        return ch.title, ch.level

    t1, l1 = title_level(part1)
    t2, l2 = title_level(part2)

    return [
        Chunk(id=ch.id, title=t1, level=l1, content=part1),
        Chunk(id=ch.id + 1, title=t2, level=l2, content=part2),
    ]


def save_chunks(input_path: Path, chunks: list[Chunk]) -> None:
    base_dir, chunks_dir = output_paths_for(input_path)
    ensure_dir(chunks_dir)

    # Clear old chunks to avoid leftovers from previous runs
    for old_file in chunks_dir.glob("*.md"):
        old_file.unlink()

    # Fallback: ensure at least two chunks when feasible
    if len(chunks) == 1:
        split = _fallback_split_single_chunk(chunks[0])
        if len(split) > 1:
            chunks = split
            for i, c in enumerate(chunks, start=1):
                c.id = i

    for idx, ch in enumerate(chunks, start=1):
        meta = {
            "id": ch.id,
            "title": ch.title,
            "level": ch.level,
            "token_count": estimate_tokens(ch.content),
            "checksum": checksum(ch.content),
        }
        front = (
            "---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=True) + "---\n"
        )
        slug = slugify(ch.title)
        filename = f"{idx:03d}_{slug}.md"
        write_text(chunks_dir / filename, front + ch.content)
