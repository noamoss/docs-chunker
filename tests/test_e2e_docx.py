import yaml
from typer.testing import CliRunner

from docs_chunker.cli import app


def test_e2e_docx_to_chunks(monkeypatch, tmp_path):
    # Mock MarkItDown to return a structured markdown with Hebrew
    from docs_chunker import convert as convert_mod

    class FakeMarkItDown:
        def convert(self, path: str):
            class R:
                text_content = (
                    "# כותרת\n\n" "Intro.\n\n" "## A\n" "One.\n\n" "## סעיף 2\n" "שתיים.\n"
                )

            return R()

    monkeypatch.setattr(convert_mod, "MarkItDown", FakeMarkItDown)

    input_doc = tmp_path / "end2end.docx"
    input_doc.write_bytes(b"fake")

    runner = CliRunner()
    res = runner.invoke(
        app,
        [
            str(input_doc),
            "--min-tokens",
            "1",
            "--max-tokens",
            "100",
        ],
    )
    assert res.exit_code == 0, res.output

    from docs_chunker.io import output_paths_for

    base_dir, chunks_dir = output_paths_for(input_doc)
    # Full MD exists
    assert (base_dir / "end2end.md").exists()

    # Chunks exist with front matter
    files = sorted(chunks_dir.glob("*.md"))
    assert len(files) >= 2
    sample = files[0].read_text(encoding="utf-8")
    assert sample.startswith("---\n")
    fm, body = sample.split("---\n", 2)[1:]
    meta = yaml.safe_load(fm)
    assert meta["id"] >= 1
    assert meta["token_count"] > 0
    assert len(meta["checksum"]) == 64
