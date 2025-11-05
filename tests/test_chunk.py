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
