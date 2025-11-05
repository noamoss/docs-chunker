import yaml

from docs_chunker.chunk import Chunk
from docs_chunker.io import output_paths_for
from docs_chunker.writer import save_chunks


def test_save_chunks_creates_files_with_front_matter(tmp_path):
    # Arrange: fake input path and sample chunks
    input_doc = tmp_path / "contract.docx"
    input_doc.write_bytes(b"fake")
    chunks = [
        Chunk(id=1, title="Introduction", level=1, content="# Introduction\nHello\n"),
        Chunk(id=2, title="סעיף 1", level=2, content="## סעיף 1\nתוכן\n"),
    ]

    # Act
    base_dir, chunks_dir = output_paths_for(input_doc)
    save_chunks(input_doc, chunks)

    # Assert: files exist and include YAML front-matter and content
    saved = sorted(list(chunks_dir.glob("*.md")))
    assert len(saved) == 2

    first = saved[0].read_text(encoding="utf-8")
    assert first.startswith("---\n")
    fm, body = first.split("---\n", 2)[1:]  # between first and second '---\n'
    meta = yaml.safe_load(fm)
    assert meta["id"] == 1
    assert meta["title"]
    assert meta["level"] == 1
    assert meta["token_count"] > 0
    assert len(meta["checksum"]) == 64
    assert body.lstrip().startswith("# ")
