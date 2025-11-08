"""Utilities for extracting document structure from Markdown text."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .chunk import HEADING_RE, estimate_tokens


@dataclass
class HeadingInfo:
    """Information about a single heading in the document."""

    level: int
    title: str
    line_idx: int
    token_count: int
    section_start: int
    section_end: int


@dataclass
class DocumentStructure:
    """Complete document structure with heading hierarchy metadata."""

    headings: List[HeadingInfo]
    total_tokens: int
    total_lines: int
    min_level: int
    max_level: int
    has_structure: bool


def extract_structure(markdown_text: str) -> DocumentStructure:
    """Extract heading hierarchy and metadata from Markdown text."""

    lines = markdown_text.splitlines()
    headings_raw: list[tuple[int, int, str]] = []
    for idx, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            headings_raw.append((idx, level, title))

    headings: list[HeadingInfo] = []
    total_lines = len(lines)
    total_tokens = estimate_tokens(markdown_text)

    if not headings_raw:
        return DocumentStructure(
            headings=[],
            total_tokens=total_tokens,
            total_lines=total_lines,
            min_level=0,
            max_level=0,
            has_structure=False,
        )

    for i, (line_idx, level, title) in enumerate(headings_raw):
        next_boundary = total_lines
        for candidate_line, candidate_level, _ in headings_raw[i + 1 :]:
            if candidate_level <= level:
                next_boundary = candidate_line
                break
        section_start = line_idx
        section_end = next_boundary
        section_lines = lines[section_start:section_end]
        section_text = "\n".join(section_lines)
        token_count = estimate_tokens(section_text)
        headings.append(
            HeadingInfo(
                level=level,
                title=title,
                line_idx=line_idx,
                token_count=token_count,
                section_start=section_start,
                section_end=section_end,
            )
        )

    levels = [h.level for h in headings]
    min_level = min(levels)
    max_level = max(levels)

    return DocumentStructure(
        headings=headings,
        total_tokens=total_tokens,
        total_lines=total_lines,
        min_level=min_level,
        max_level=max_level,
        has_structure=True,
    )


def get_heading_hierarchy(structure: DocumentStructure) -> str:
    """Format heading hierarchy as readable text."""

    lines: list[str] = ["Document Structure:"]
    if not structure.headings:
        lines.append("  (No headings found)")
        return "\n".join(lines)

    for heading in structure.headings:
        indent = "  " * max(0, heading.level - 1)
        marker = "#" * heading.level
        lines.append(
            f"{indent}{marker} {heading.title} ({heading.token_count} tokens)"
        )
    return "\n".join(lines)


def get_section_preview(
    markdown_text: str, heading: HeadingInfo, max_chars: int = 300
) -> str:
    """Return preview text for a section bounded by a heading."""

    if max_chars < 0:
        raise ValueError("max_chars must be non-negative")

    lines = markdown_text.splitlines()
    start = max(0, heading.section_start)
    end = heading.section_end if heading.section_end >= 0 else len(lines)
    end = min(len(lines), end)
    section_lines = lines[start:end]
    section_text = "\n".join(section_lines).strip()
    if max_chars == 0:
        return ""
    if len(section_text) <= max_chars:
        return section_text
    return section_text[:max_chars].rstrip() + "…"
