"""Comprehensive edge case tests for document chunking.

This test suite covers edge cases in document structure to ensure:
1. No content loss during chunking
2. Token constraints are respected
3. Graceful handling of malformed/invalid inputs
"""

from docs_chunker.chunk import (
    Chunk,
    chunk_by_strategy,
    chunk_markdown,
    estimate_tokens,
    _split_oversized_chunk,
)
from docs_chunker.llm_strategy import ChunkingStrategy
from docs_chunker.structure import extract_structure

import pytest


def verify_content_preservation(original: str, chunks: list[Chunk]) -> None:
    """Helper to verify no content is lost during chunking."""
    reconstructed = "".join(c.content for c in chunks)
    assert reconstructed == original, (
        f"Content mismatch:\n"
        f"Original length: {len(original)}\n"
        f"Reconstructed length: {len(reconstructed)}\n"
        f"Original: {repr(original[:100])}\n"
        f"Reconstructed: {repr(reconstructed[:100])}"
    )


def verify_token_constraints(
    chunks: list[Chunk], min_tokens: int, max_tokens: int
) -> None:
    """Helper to verify token constraints are respected."""
    for chunk in chunks:
        tokens = estimate_tokens(chunk.content)
        # After normalization, chunks should respect max_tokens
        assert tokens <= max_tokens, (
            f"Chunk exceeds max_tokens: {tokens} > {max_tokens}\n"
            f"Content: {chunk.content[:200]}"
        )
        # Note: min_tokens is only enforced after merging, so individual chunks
        # might be below min_tokens if they can't be merged


# ============================================================================
# 1. Empty/Minimal Documents
# ============================================================================


def test_empty_string():
    """Test handling of empty string."""
    chunks = chunk_markdown("", min_tokens=1, max_tokens=100)
    assert len(chunks) == 1
    assert chunks[0].content == ""
    verify_content_preservation("", chunks)


def test_only_whitespace():
    """Test handling of whitespace-only documents."""
    for whitespace in [" ", "\n", "\t", "  \n  \n  "]:
        chunks = chunk_markdown(whitespace, min_tokens=1, max_tokens=100)
        verify_content_preservation(whitespace, chunks)


def test_single_character():
    """Test handling of single character document."""
    chunks = chunk_markdown("a", min_tokens=1, max_tokens=100)
    assert len(chunks) == 1
    verify_content_preservation("a", chunks)


def test_single_word():
    """Test handling of single word document."""
    chunks = chunk_markdown("hello", min_tokens=1, max_tokens=100)
    assert len(chunks) == 1
    verify_content_preservation("hello", chunks)


def test_single_line():
    """Test handling of single line document."""
    content = "This is a single line of text."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)


# ============================================================================
# 2. Heading Structure Edge Cases
# ============================================================================


def test_malformed_headings_too_many_hashes():
    """Test that headings with >6 # are not recognized as headings."""
    # HEADING_RE only matches 1-6 #, so ####### should not match
    content = "####### Too many hashes\nContent here."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    # Should be treated as regular text, not a heading
    structure = extract_structure(content)
    assert len(structure.headings) == 0


def test_malformed_headings_no_space():
    """Test headings without space after #."""
    content = "#no space\nContent here."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    # Should not be recognized as heading
    structure = extract_structure(content)
    assert len(structure.headings) == 0


def test_headings_with_empty_titles():
    """Test headings with empty titles."""
    content = "# \nContent here.\n## \nMore content."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    structure = extract_structure(content)
    # Headings with empty titles should still be recognized
    assert len(structure.headings) == 2
    assert structure.headings[0].title == ""


def test_inconsistent_heading_levels():
    """Test documents with inconsistent heading levels (skipping levels)."""
    content = "# Title\n\n### Subsection (skipping ##)\nContent here."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    structure = extract_structure(content)
    assert len(structure.headings) == 2
    assert structure.headings[0].level == 1
    assert structure.headings[1].level == 3


def test_headings_at_document_start():
    """Test headings at document start with no intro content."""
    content = "# First Heading\nContent here."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    assert len(chunks) >= 1


def test_headings_at_document_end():
    """Test headings at document end with no content after."""
    content = "Content here.\n# Final Heading"
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    structure = extract_structure(content)
    assert len(structure.headings) == 1
    # Last heading should have section_end at document end
    assert structure.headings[0].section_end == len(content.splitlines())


def test_very_deep_nesting():
    """Test documents with maximum nesting depth (6 levels)."""
    content = (
        "# Level 1\n"
        "## Level 2\n"
        "### Level 3\n"
        "#### Level 4\n"
        "##### Level 5\n"
        "###### Level 6\n"
        "Content at deepest level."
    )
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    structure = extract_structure(content)
    assert structure.max_level == 6


def test_headings_with_special_characters():
    """Test headings with special characters."""
    content = "# Heading with émojis 🎉 and spéciál chars\nContent."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    structure = extract_structure(content)
    assert len(structure.headings) == 1
    assert "émojis" in structure.headings[0].title


def test_headings_with_markdown_syntax():
    """Test headings with markdown formatting."""
    content = "## **Bold** Heading with [Link](url)\nContent."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    structure = extract_structure(content)
    assert len(structure.headings) == 1
    # Markdown syntax should be preserved in title
    title = structure.headings[0].title
    assert "**Bold**" in title or "Bold" in title


def test_single_heading():
    """Test document with only one heading."""
    content = "# Only Heading\nSome content here."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    assert len(chunks) >= 1


# ============================================================================
# 3. Content Structure Edge Cases
# ============================================================================


def test_very_large_section():
    """Test section that exceeds max_tokens."""
    large_content = "Word " * 5000  # Very large content
    content = f"# Title\n{large_content}"
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    verify_token_constraints(chunks, 1, 100)
    # Should be split into multiple chunks
    assert len(chunks) > 1


def test_very_small_sections():
    """Test multiple tiny sections below min_tokens."""
    content = "# Section 1\nTiny.\n## Section 2\nAlso tiny.\n## Section 3\nSmall."
    chunks = chunk_markdown(content, min_tokens=50, max_tokens=100)
    verify_content_preservation(content, chunks)
    # Small sections should be merged
    verify_token_constraints(chunks, 50, 100)


def test_single_paragraph_exceeding_max_tokens():
    """Test single paragraph that exceeds max_tokens."""
    long_para = "Word " * 3000
    content = f"# Title\n{long_para}"
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    verify_token_constraints(chunks, 1, 100)


def test_content_before_first_heading():
    """Test content before first heading."""
    content = "Intro text before heading.\n# First Heading\nContent."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    # Intro content should be in first chunk
    assert "Intro text" in chunks[0].content


def test_content_after_last_heading():
    """Test content after last heading."""
    content = "# Heading\nContent.\n\nMore content after."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    # Content after heading should be preserved
    all_content = "".join(c.content for c in chunks)
    assert "More content after" in all_content


def test_mixed_content_types_code_blocks():
    """Test documents with code blocks."""
    content = (
        "# Title\n"
        "```python\n"
        "def hello():\n"
        "    print('world')\n"
        "```\n"
        "More content."
    )
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    all_content = "".join(c.content for c in chunks)
    assert "```python" in all_content


def test_mixed_content_types_tables():
    """Test documents with markdown tables."""
    content = (
        "# Title\n"
        "| Col1 | Col2 |\n"
        "|------|------|\n"
        "| Val1 | Val2 |\n"
        "More content."
    )
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    all_content = "".join(c.content for c in chunks)
    assert "| Col1 | Col2 |" in all_content


def test_mixed_content_types_lists():
    """Test documents with lists."""
    content = (
        "# Title\n"
        "- Item 1\n"
        "- Item 2\n"
        "  1. Nested 1\n"
        "  2. Nested 2\n"
        "More content."
    )
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    all_content = "".join(c.content for c in chunks)
    assert "- Item 1" in all_content


def test_mixed_content_types_blockquotes():
    """Test documents with blockquotes."""
    content = (
        "# Title\n"
        "> This is a quote.\n"
        "> Multiple lines.\n"
        "More content."
    )
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    all_content = "".join(c.content for c in chunks)
    assert "> This is a quote" in all_content


# ============================================================================
# 4. Token Limit Edge Cases
# ============================================================================


def test_document_smaller_than_min_tokens():
    """Test document smaller than min_tokens."""
    content = "Short text."
    chunks = chunk_markdown(content, min_tokens=1000, max_tokens=2000)
    verify_content_preservation(content, chunks)
    # Should still create at least one chunk
    assert len(chunks) >= 1
    # Chunk will be below min_tokens, which is acceptable if it's the entire document
    tokens = estimate_tokens(chunks[0].content)
    assert tokens < 1000


def test_document_exactly_min_tokens():
    """Test document exactly at min_tokens."""
    # Create content that's approximately min_tokens
    content = "Word " * 200  # Approximately 200 tokens
    chunks = chunk_markdown(content, min_tokens=200, max_tokens=400)
    verify_content_preservation(content, chunks)
    assert len(chunks) >= 1


def test_document_exactly_max_tokens():
    """Test document exactly at max_tokens."""
    # Create content that's approximately max_tokens
    content = "Word " * 300  # Approximately 300 tokens
    chunks = chunk_markdown(content, min_tokens=100, max_tokens=300)
    verify_content_preservation(content, chunks)
    verify_token_constraints(chunks, 100, 300)


def test_very_large_max_tokens():
    """Test with very large max_tokens."""
    content = "# Title\n" + "Content. " * 1000
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100000)
    verify_content_preservation(content, chunks)
    # Should create fewer chunks
    assert len(chunks) <= 2


def test_very_small_max_tokens():
    """Test with very small max_tokens."""
    content = "# Title\n" + "Word " * 100
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=10)
    verify_content_preservation(content, chunks)
    verify_token_constraints(chunks, 1, 10)
    # Should create many chunks
    assert len(chunks) > 1


# ============================================================================
# 5. Line/Whitespace Edge Cases
# ============================================================================


def test_different_line_endings_crlf():
    """Test documents with CRLF line endings."""
    content = "# Title\r\nContent line 1\r\nContent line 2\r\n"
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)


def test_different_line_endings_cr():
    """Test documents with CR line endings."""
    content = "# Title\rContent line 1\rContent line 2\r"
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)


def test_no_trailing_newline():
    """Test document without trailing newline."""
    content = "# Title\nContent here"
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)


def test_multiple_trailing_newlines():
    """Test document with multiple trailing newlines."""
    content = "# Title\nContent here\n\n\n"
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)


def test_mixed_line_endings():
    """Test document with mixed line endings."""
    content = "# Title\nContent line 1\r\nContent line 2\nContent line 3\r"
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)


def test_tabs_vs_spaces():
    """Test document with tabs and spaces."""
    content = "# Title\n\tTabbed line\n    Spaced line"
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    all_content = "".join(c.content for c in chunks)
    assert "\tTabbed" in all_content
    assert "    Spaced" in all_content


# ============================================================================
# 6. Special Content Edge Cases
# ============================================================================


def test_code_blocks_with_hash_comments():
    """Test code blocks with # that look like headings.

    Expected: Lines starting with # inside code blocks should NOT be
    recognized as headings. Only the actual heading should be detected.

    See TASK_CODE_BLOCK_HEADING_FILTER.md for implementation details.
    """
    content = (
        "# Title\n"
        "```python\n"
        "# This is a comment, not a heading\n"
        "def func():\n"
        "    # Another comment\n"
        "    pass\n"
        "```\n"
        "More content."
    )
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    structure = extract_structure(content)
    # Should only have one heading (the actual # Title)
    # Lines with # inside code blocks should be ignored
    assert len(structure.headings) == 1
    assert structure.headings[0].title == "Title"


def test_horizontal_rules():
    """Test documents with horizontal rules."""
    content = (
        "# Title\n"
        "Content before.\n"
        "---\n"
        "Content after."
    )
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    all_content = "".join(c.content for c in chunks)
    assert "---" in all_content


def test_html_in_markdown():
    """Test HTML elements in markdown."""
    content = (
        "# Title\n"
        "<div>HTML content</div>\n"
        "<p>Paragraph</p>\n"
        "More markdown."
    )
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    all_content = "".join(c.content for c in chunks)
    assert "<div>HTML content</div>" in all_content


def test_links_and_images():
    """Test links and images in markdown."""
    content = (
        "# Title\n"
        "[Link text](https://example.com)\n"
        "![Image alt](image.png)\n"
        "More content."
    )
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    all_content = "".join(c.content for c in chunks)
    assert "[Link text](https://example.com)" in all_content
    assert "![Image alt](image.png)" in all_content


def test_inline_code_with_backticks():
    """Test inline code with backticks."""
    content = (
        "# Title\n"
        "Use `code()` function.\n"
        "Or `another_function()` here."
    )
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    all_content = "".join(c.content for c in chunks)
    assert "`code()`" in all_content


# ============================================================================
# 7. RTL/LTR Edge Cases
# ============================================================================


def test_pure_rtl():
    """Test pure RTL (Hebrew) document."""
    content = "# כותרת\nפסקה בעברית.\n## סעיף\nעוד תוכן."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    structure = extract_structure(content)
    assert len(structure.headings) == 2


def test_pure_ltr():
    """Test pure LTR (English) document."""
    content = "# Title\nEnglish paragraph.\n## Section\nMore content."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)


def test_mixed_rtl_ltr_same_line():
    """Test mixed RTL/LTR in same line."""
    content = "# Title: כותרת\nMixed: עברית and English."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)


def test_rtl_headings_ltr_content():
    """Test RTL headings with LTR content."""
    content = "# כותרת\nEnglish content here."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)


def test_ltr_headings_rtl_content():
    """Test LTR headings with RTL content."""
    content = "# Title\nפסקה בעברית."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)


# ============================================================================
# 8. LLM Strategy Edge Cases
# ============================================================================


def test_custom_boundaries_out_of_range_negative():
    """Test custom boundaries with negative values."""
    md = "Line 1\nLine 2\nLine 3\n"
    structure = extract_structure(md)
    strategy = ChunkingStrategy(
        strategy_type="custom_boundaries",
        boundaries=[-1, 2, 5]  # -1 should be ignored, 5 is out of range
    )
    chunks = chunk_by_strategy(md, structure, strategy, min_tokens=1, max_tokens=100)
    verify_content_preservation(md, chunks)
    # Boundaries should be validated and clamped


def test_custom_boundaries_out_of_range_too_large():
    """Test custom boundaries exceeding total lines."""
    md = "Line 1\nLine 2\nLine 3\n"
    structure = extract_structure(md)
    strategy = ChunkingStrategy(
        strategy_type="custom_boundaries",
        boundaries=[0, 2, 100]  # 100 is out of range
    )
    chunks = chunk_by_strategy(md, structure, strategy, min_tokens=1, max_tokens=100)
    verify_content_preservation(md, chunks)
    # Should clamp to total_lines


def test_custom_boundaries_duplicates():
    """Test custom boundaries with duplicate values."""
    md = "Line 1\nLine 2\nLine 3\nLine 4\n"
    structure = extract_structure(md)
    strategy = ChunkingStrategy(
        strategy_type="custom_boundaries",
        boundaries=[0, 2, 2, 4]  # Duplicate 2
    )
    chunks = chunk_by_strategy(md, structure, strategy, min_tokens=1, max_tokens=100)
    verify_content_preservation(md, chunks)
    # Duplicates should be handled (set removes them)


def test_custom_boundaries_unsorted():
    """Test custom boundaries that are unsorted."""
    md = "Line 1\nLine 2\nLine 3\nLine 4\n"
    structure = extract_structure(md)
    strategy = ChunkingStrategy(
        strategy_type="custom_boundaries",
        boundaries=[3, 1, 0, 4]  # Unsorted
    )
    chunks = chunk_by_strategy(md, structure, strategy, min_tokens=1, max_tokens=100)
    verify_content_preservation(md, chunks)
    # Should be sorted automatically


def test_custom_boundaries_empty_list():
    """Test custom boundaries with empty list."""
    md = "Line 1\nLine 2\n"
    structure = extract_structure(md)
    strategy = ChunkingStrategy(
        strategy_type="custom_boundaries",
        boundaries=[]  # Empty
    )
    with pytest.raises(ValueError, match="Unsupported or incomplete"):
        chunk_by_strategy(md, structure, strategy, min_tokens=1, max_tokens=100)


def test_custom_boundaries_adjacent():
    """Test adjacent boundaries (no content between)."""
    md = "Line 1\nLine 2\nLine 3\n"
    structure = extract_structure(md)
    strategy = ChunkingStrategy(
        strategy_type="custom_boundaries",
        boundaries=[0, 1, 2, 3]  # Adjacent boundaries
    )
    chunks = chunk_by_strategy(md, structure, strategy, min_tokens=1, max_tokens=100)
    verify_content_preservation(md, chunks)
    # Adjacent boundaries should create empty or minimal chunks that get filtered


def test_strategy_invalid_level_too_low():
    """Test strategy with level < 1."""
    md = "# Title\n## Section\n"
    structure = extract_structure(md)
    strategy = ChunkingStrategy(strategy_type="by_level", level=0)
    with pytest.raises(ValueError, match="Invalid heading level"):
        chunk_by_strategy(md, structure, strategy, min_tokens=1, max_tokens=100)


def test_strategy_invalid_level_too_high():
    """Test strategy with level > 6."""
    md = "# Title\n## Section\n"
    structure = extract_structure(md)
    strategy = ChunkingStrategy(strategy_type="by_level", level=7)
    with pytest.raises(ValueError, match="Invalid heading level"):
        chunk_by_strategy(md, structure, strategy, min_tokens=1, max_tokens=100)


def test_strategy_missing_level():
    """Test by_level strategy without level."""
    md = "# Title\n## Section\n"
    structure = extract_structure(md)
    strategy = ChunkingStrategy(strategy_type="by_level", level=None)
    with pytest.raises(ValueError, match="Unsupported or incomplete"):
        chunk_by_strategy(md, structure, strategy, min_tokens=1, max_tokens=100)


def test_strategy_missing_boundaries():
    """Test custom_boundaries strategy without boundaries."""
    md = "# Title\n## Section\n"
    structure = extract_structure(md)
    strategy = ChunkingStrategy(strategy_type="custom_boundaries", boundaries=None)
    with pytest.raises(ValueError, match="Unsupported or incomplete"):
        chunk_by_strategy(md, structure, strategy, min_tokens=1, max_tokens=100)


# ============================================================================
# 9. Boundary Cases
# ============================================================================


def test_document_exactly_one_line():
    """Test document with exactly one line."""
    content = "Single line of text."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    assert len(chunks) == 1


def test_document_exactly_two_lines():
    """Test document with exactly two lines."""
    content = "Line one.\nLine two."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    assert len(chunks) >= 1


def test_chunk_boundaries_at_line_zero():
    """Test chunk boundaries starting at line 0."""
    md = "# Title\nContent\n"
    structure = extract_structure(md)
    strategy = ChunkingStrategy(strategy_type="custom_boundaries", boundaries=[0, 2])
    chunks = chunk_by_strategy(md, structure, strategy, min_tokens=1, max_tokens=100)
    verify_content_preservation(md, chunks)
    assert len(chunks) >= 1


def test_chunk_boundaries_at_last_line():
    """Test chunk boundaries at last line."""
    md = "Line 1\nLine 2\nLine 3"
    structure = extract_structure(md)
    strategy = ChunkingStrategy(strategy_type="custom_boundaries", boundaries=[0, 3])
    chunks = chunk_by_strategy(md, structure, strategy, min_tokens=1, max_tokens=100)
    verify_content_preservation(md, chunks)


def test_adjacent_boundaries_no_content():
    """Test adjacent boundaries that create empty chunks."""
    md = "Line 1\nLine 2\nLine 3\n"
    structure = extract_structure(md)
    strategy = ChunkingStrategy(
        strategy_type="custom_boundaries", boundaries=[0, 1, 1, 2]
    )
    chunks = chunk_by_strategy(md, structure, strategy, min_tokens=1, max_tokens=100)
    verify_content_preservation(md, chunks)
    # Empty chunks should be filtered by _make_chunk_from_range


# ============================================================================
# Additional Edge Cases
# ============================================================================


def test_headings_in_code_blocks_not_recognized():
    """Test that # in code blocks are not recognized as headings.

    Expected: Lines starting with # inside code blocks should NOT be
    recognized as headings. Only the actual heading should be detected.

    See TASK_CODE_BLOCK_HEADING_FILTER.md for implementation details.
    """
    content = (
        "# Real Heading\n"
        "```\n"
        "# This is code, not a heading\n"
        "print('# comment')\n"
        "```\n"
        "More content."
    )
    structure = extract_structure(content)
    # Should only find the real heading
    # Lines with # inside code blocks should be ignored
    assert len(structure.headings) == 1
    assert structure.headings[0].title == "Real Heading"


def test_multiple_undersized_chunks_merge():
    """Test that multiple undersized chunks are merged correctly."""
    content = (
        "# Section 1\nTiny.\n"
        "## Section 2\nAlso tiny.\n"
        "## Section 3\nSmall.\n"
        "## Section 4\nMinimal."
    )
    chunks = chunk_markdown(content, min_tokens=100, max_tokens=200)
    verify_content_preservation(content, chunks)
    # Small sections should be merged to meet min_tokens
    for chunk in chunks:
        tokens = estimate_tokens(chunk.content)
        # After merging, chunks should meet min_tokens (or be the last chunk)
        if chunk != chunks[-1]:  # Last chunk might be smaller
            assert tokens >= 100 or len(chunks) == 1


def test_oversized_chunk_with_no_break_points():
    """Test oversized chunk with no natural break points."""
    # Very long content with no paragraphs, headings, or lists
    long_content = "Word " * 5000
    chunk = Chunk(id=1, title="Test", level=1, content=long_content)
    split_chunks = _split_oversized_chunk(chunk, max_tokens=100)
    # Should fall back to character-based splitting
    assert len(split_chunks) > 1
    verify_content_preservation(long_content, split_chunks)
    verify_token_constraints(split_chunks, 1, 100)


def test_content_with_only_newlines():
    """Test content that is only newlines."""
    content = "\n\n\n"
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)


def test_headings_with_only_hashes():
    """Test edge case where heading line has only hashes."""
    content = "######\nContent here."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    structure = extract_structure(content)
    # Should be recognized as heading with empty title
    assert len(structure.headings) == 1
    assert structure.headings[0].title == ""


def test_nested_lists_preserved():
    """Test that nested lists are preserved correctly."""
    content = (
        "# Title\n"
        "- Item 1\n"
        "  - Nested 1\n"
        "    - Deep nested\n"
        "- Item 2\n"
    )
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=100)
    verify_content_preservation(content, chunks)
    all_content = "".join(c.content for c in chunks)
    assert "  - Nested 1" in all_content
    assert "    - Deep nested" in all_content

