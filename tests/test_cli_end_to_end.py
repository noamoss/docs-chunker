from types import SimpleNamespace

from typer.testing import CliRunner

from docs_chunker.cli import app


class FakeMarkItDown:
    def convert(self, path: str):
        text = "# Title\n\n## A\ntext\n\n### A.1\nmore\n\n## ב\nעברית\n\n"
        return SimpleNamespace(text_content=text)


def test_cli_end_to_end_writes_full_md_and_chunks(monkeypatch, tmp_path):
    from docs_chunker import convert as convert_mod

    monkeypatch.setattr(convert_mod, "MarkItDown", FakeMarkItDown)
    input_doc = tmp_path / "mix.docx"
    input_doc.write_bytes(b"fake")

    runner = CliRunner()
    result = runner.invoke(app, [str(input_doc), "--force", "--min-tokens", "1"])
    assert result.exit_code == 0, result.output

    # Check outputs
    from docs_chunker.io import output_paths_for

    out_base, chunks_dir = output_paths_for(input_doc)
    full_md = out_base / f"{input_doc.stem}.md"
    assert full_md.exists()
    files = sorted(list(chunks_dir.glob("*.md")))
    assert len(files) >= 2
    content0 = files[0].read_text(encoding="utf-8")
    assert content0.startswith("---\n") and "checksum:" in content0
