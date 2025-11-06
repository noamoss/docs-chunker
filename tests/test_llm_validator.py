import textwrap

from docs_chunker.chunk import chunk_markdown
from docs_chunker.llm import validate_and_adjust_chunks

SAMPLE_MD = (
    textwrap.dedent(
        """
    # Title
    intro

    ## A
    one

    ## B
    two
    """
    ).strip()
    + "\n"
)


def test_validator_identity_when_llm_unavailable(monkeypatch):
    # Force internal proposer to return None (simulate unavailable model)
    from docs_chunker import llm as llm_mod

    def fake_propose(*args, **kwargs):
        return None

    monkeypatch.setattr(llm_mod, "_llm_propose_boundaries", fake_propose)
    chunks = chunk_markdown(SAMPLE_MD, min_tokens=1, max_tokens=100)
    adjusted = validate_and_adjust_chunks(SAMPLE_MD, chunks, 1, 100, language_hint="en")

    # No content loss
    assert "".join(c.content for c in adjusted).strip() == SAMPLE_MD.strip()
    assert len(adjusted) == len(chunks)


def test_validator_applies_merge_plan(monkeypatch):
    from docs_chunker import llm as llm_mod

    chunks = chunk_markdown(SAMPLE_MD, min_tokens=1, max_tokens=100)

    # Plan: merge last two chunks
    def fake_propose(markdown_text, chunks_schema, **kwargs):
        return {
            "operations": [{"type": "merge", "range": [len(chunks) - 1, len(chunks)]}]
        }

    monkeypatch.setattr(llm_mod, "_llm_propose_boundaries", fake_propose)
    adjusted = validate_and_adjust_chunks(SAMPLE_MD, chunks, 1, 100, language_hint="en")

    assert "".join(c.content for c in adjusted).strip() == SAMPLE_MD.strip()
    assert len(adjusted) == len(chunks) - 1
