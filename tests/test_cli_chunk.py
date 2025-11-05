from typer.testing import CliRunner

from docs_chunker.cli import app


def test_cli_convert_then_chunk(monkeypatch, tmp_path):
    # Fake converter returns markdown with headings
    from docs_chunker import convert as convert_mod

    class FakeMarkItDown:
        def convert(self, path: str):
            class R:
                text_content = "# Title\n\n## A\nOne.\n\n## B\nTwo.\n"

            return R()

    monkeypatch.setattr(convert_mod, "MarkItDown", FakeMarkItDown)

    input_doc = tmp_path / "demo.docx"
    input_doc.write_bytes(b"fake")

    runner = CliRunner()
    res = runner.invoke(
        app, [str(input_doc), "--force", "--min-tokens", "1"], catch_exceptions=False
    )
    assert res.exit_code == 0, res.output

    # Expect chunks written
    from docs_chunker.io import output_paths_for

    base_dir, chunks_dir = output_paths_for(input_doc)
    assert (base_dir / "demo.md").exists()
    files = list(chunks_dir.glob("*.md"))
    assert len(files) >= 2
