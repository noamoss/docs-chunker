import textwrap

from docs_chunker.chunk import chunk_markdown, estimate_tokens

SAMPLE_MD = (
    textwrap.dedent(
        """
    # כותרת ראשית
    intro text line one.
    intro line two.

    ## Section 1
    Paragraph EN 1.
    More text here.

    ### סעיף 1.1
    פסקה HE.

    ## סעיף 2
    More content.
    """
    ).strip()
    + "\n"
)


def test_chunk_markdown_headings_and_hebrew_preserved():
    chunks = chunk_markdown(SAMPLE_MD, min_tokens=5, max_tokens=200)

    # Titles and levels are recognized
    titles = [c.title for c in chunks]
    assert any("כותרת" in t for t in titles)
    assert any("Section 1" in t for t in titles)
    assert any("סעיף" in t for t in titles)

    # Reconstruct content to ensure no loss
    reconstructed = "".join(c.content for c in chunks)
    assert reconstructed.strip() == SAMPLE_MD.strip()

    # Token estimates are positive
    for c in chunks:
        assert estimate_tokens(c.content) > 0


def test_paragraph_splitting_preserves_exact_whitespace():
    """Test that splitting by paragraphs preserves exact whitespace."""
    # Create content with varying whitespace between paragraphs
    content = (
        "First paragraph.\n\n"
        "Second paragraph.\n\n\n"  # Three newlines
        "Third paragraph.\n  \n"  # Newline with spaces
        "Fourth paragraph."
    )

    # Create a chunk that will be split by paragraphs
    from docs_chunker.chunk import Chunk, _split_oversized_chunk

    chunk = Chunk(id=1, title="Test", level=1, content=content)

    # Force splitting by paragraphs by setting a low max_tokens
    # Each paragraph is small, so they should be grouped, preserving separators
    split_chunks = _split_oversized_chunk(chunk, max_tokens=10)

    # Reconstruct the content from chunks
    reconstructed = "".join(c.content for c in split_chunks)

    # Verify exact byte-for-byte reconstruction
    assert reconstructed == content, (
        f"Content mismatch:\n"
        f"Original: {repr(content)}\n"
        f"Reconstructed: {repr(reconstructed)}"
    )


def test_oversized_paragraph_with_separator():
    """Test that oversized paragraphs preserve trailing separators."""
    from docs_chunker.chunk import Chunk, _split_oversized_chunk

    # Create a very long paragraph that exceeds max_tokens
    long_para = "Word " * 2000  # ~10,000 chars, exceeds max_tokens
    content = f"{long_para}\n\nNext paragraph here."

    chunk = Chunk(id=1, title="Test", level=1, content=content)
    split_chunks = _split_oversized_chunk(chunk, max_tokens=100)

    # Reconstruct content
    reconstructed = "".join(c.content for c in split_chunks)
    assert reconstructed == content
    assert "\n\nNext" in reconstructed  # Separator preserved


def test_oversized_paragraph_preserves_separator_exact():
    """Test separator preservation with exact format from PR review comment."""
    from docs_chunker.chunk import Chunk, _split_oversized_chunk

    # Exact test case from PR review comment
    long_para = "A" * 5000 + "\n\nNext paragraph."
    chunk = Chunk(id=1, title="Test", level=1, content=long_para)
    split_chunks = _split_oversized_chunk(chunk, max_tokens=100)

    # Verify byte-for-byte reconstruction
    reconstructed = "".join(c.content for c in split_chunks)
    assert reconstructed == long_para


def test_chunk_markdown_invalid_min_tokens():
    """Test validation for min_tokens < 1."""
    import pytest

    with pytest.raises(ValueError, match="min_tokens must be >= 1"):
        chunk_markdown(SAMPLE_MD, min_tokens=0, max_tokens=200)

    with pytest.raises(ValueError, match="min_tokens must be >= 1"):
        chunk_markdown(SAMPLE_MD, min_tokens=-1, max_tokens=200)


def test_chunk_markdown_invalid_max_tokens():
    """Test validation for max_tokens < min_tokens."""
    import pytest

    with pytest.raises(ValueError, match="max_tokens.*must be >= min_tokens"):
        chunk_markdown(SAMPLE_MD, min_tokens=200, max_tokens=100)


def test_chunk_markdown_empty_document():
    """Test handling of empty documents."""
    chunks = chunk_markdown("", min_tokens=5, max_tokens=200)
    assert len(chunks) == 1
    assert chunks[0].content.strip() == ""
    assert chunks[0].title == "Untitled" or chunks[0].title == ""


def test_chunk_markdown_only_headings():
    """Test documents with only headings."""
    content = "# Heading 1\n## Heading 2\n### Heading 3\n"
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=200)
    assert len(chunks) >= 1
    # All chunks should have titles from headings
    for chunk in chunks:
        assert chunk.title
        assert "Heading" in chunk.title or chunk.title == "Untitled"


def test_chunk_markdown_no_headings():
    """Test documents with no headings."""
    content = "This is just plain text.\nNo headings here.\nJust paragraphs."
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=200)
    assert len(chunks) >= 1
    # Should create at least one chunk
    reconstructed = "".join(c.content for c in chunks)
    assert "plain text" in reconstructed


def test_estimate_tokens_with_tiktoken():
    """Test tiktoken integration if available."""
    text = "This is a test sentence with multiple words."
    tokens = estimate_tokens(text, model="gpt-4")
    assert tokens >= 1
    # With tiktoken, should be more accurate than heuristic
    # For this text, should be around 10-15 tokens


def test_estimate_tokens_fallback():
    """Test that estimate_tokens works and handles errors gracefully."""
    # Since tiktoken is now a dependency, it should be available
    # But we can test that the function works correctly
    text = "This is a test sentence."
    tokens = estimate_tokens(text)
    # Should return a positive integer
    assert tokens >= 1
    assert isinstance(tokens, int)

    # Test with different models if tiktoken is available
    try:
        import importlib.util

        if importlib.util.find_spec("tiktoken") is not None:
            tokens_gpt4 = estimate_tokens(text, model="gpt-4")
            tokens_gpt35 = estimate_tokens(text, model="gpt-3.5-turbo")
            assert tokens_gpt4 >= 1
            assert tokens_gpt35 >= 1
    except ImportError:
        # If tiktoken not available, should use heuristic
        expected_heuristic = max(1, len(text) // 4)
        assert tokens == expected_heuristic


def test_chunk_markdown_mixed_ltr_rtl():
    """Test mixed LTR/RTL content."""
    content = (
        "# English Heading\n"
        "This is English text.\n\n"
        "## כותרת בעברית\n"
        "זהו טקסט בעברית.\n\n"
        "### Mixed: English and עברית\n"
        "Mixed content: English text and טקסט בעברית.\n"
    )
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=200)
    assert len(chunks) >= 1
    # Verify both languages are preserved
    all_content = "".join(c.content for c in chunks)
    assert "English" in all_content
    assert "עברית" in all_content or "כותרת" in all_content


def test_chunk_markdown_hebrew_in_filenames():
    """Test Hebrew characters in extracted titles."""
    content = "# כותרת ראשית בעברית\nפסקה ראשונה.\n\n## סעיף משני\nפסקה שנייה.\n"
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=200)
    # Titles should contain Hebrew characters
    titles = [c.title for c in chunks]
    hebrew_titles = [
        t for t in titles if any("\u0590" <= char <= "\u05ff" for char in t)
    ]
    assert len(hebrew_titles) > 0


def test_chunk_markdown_rtl_paragraph_boundaries():
    """Test RTL paragraph splitting."""
    content = (
        "פסקה ראשונה בעברית.\n\n" "פסקה שנייה בעברית.\n\n\n" "פסקה שלישית בעברית.\n"
    )
    chunks = chunk_markdown(content, min_tokens=1, max_tokens=50)
    # Reconstruct and verify paragraph boundaries preserved
    reconstructed = "".join(c.content for c in chunks)
    assert "פסקה ראשונה" in reconstructed
    assert "פסקה שנייה" in reconstructed
    assert "פסקה שלישית" in reconstructed


def test_max_depth_protection():
    """Test that max depth protection prevents infinite recursion."""
    from docs_chunker.chunk import Chunk, _split_oversized_chunk

    # Create content that would cause deep recursion without protection
    # A very long single paragraph with no natural break points
    # This should trigger max depth fallback
    long_content = "A" * 100000  # Very long content with no breaks
    chunk = Chunk(id=1, title="Test", level=1, content=long_content)

    # Use a very low max_depth to trigger the protection quickly
    split_chunks = _split_oversized_chunk(chunk, max_tokens=100, max_depth=3)

    # Should still return chunks (fallback to character-based splitting)
    assert len(split_chunks) > 0
    # Verify content is preserved
    reconstructed = "".join(c.content for c in split_chunks)
    assert reconstructed == long_content
    # Verify all chunks are within reasonable size
    for ch in split_chunks:
        assert len(ch.content) > 0
