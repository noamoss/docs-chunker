from types import SimpleNamespace

from docs_chunker.cli import app
from docs_chunker.convert import convert_docx_to_markdown
from docs_chunker.io import doc_name_from_path, output_paths_for


class FakeMarkItDown:
    def convert(self, path: str):
        # Simulate a simple conversion with Hebrew and English, headings preserved
        text = (
            """# כותרת ראשית\n\n## Section 1\nParagraph EN.\n\n## סעיף 2\nפסקה HE.\n"""
        )
        return SimpleNamespace(text_content=text)


def test_convert_docx_to_markdown_monkeypatch(monkeypatch, tmp_path):
    # Arrange: fake markitdown and fake input path
    from docs_chunker import convert as convert_mod

    monkeypatch.setattr(convert_mod, "MarkItDown", FakeMarkItDown)
    fake_input = tmp_path / "sample.docx"
    fake_input.write_bytes(b"fake docx bytes")

    # Act
    md = convert_docx_to_markdown(fake_input)

    # Assert
    assert md.startswith("# ")
    assert "כותרת" in md  # Hebrew preserved
    assert "Section 1" in md
    assert md.endswith("\n")


def test_cli_writes_expected_output(monkeypatch, tmp_path):
    # Arrange
    from typer.testing import CliRunner

    from docs_chunker import convert as convert_mod

    monkeypatch.setattr(convert_mod, "MarkItDown", FakeMarkItDown)
    input_doc = tmp_path / "example.docx"
    input_doc.write_bytes(b"fake")

    # Act
    runner = CliRunner()
    result = runner.invoke(app, [str(input_doc)])
    assert result.exit_code == 0, result.output

    # Assert output path exists
    name = doc_name_from_path(input_doc)
    base_dir, _ = output_paths_for(input_doc)
    full_md = base_dir / f"{name}.md"
    assert full_md.exists()
    content = full_md.read_text(encoding="utf-8")
    assert "Section 1" in content and "סעיף" in content


def test_convert_file_not_found(monkeypatch, tmp_path):
    """Test FileNotFoundError handling."""
    import pytest

    from docs_chunker.convert import convert_docx_to_markdown

    non_existent = tmp_path / "nonexistent.docx"
    with pytest.raises(FileNotFoundError, match="File not found"):
        convert_docx_to_markdown(non_existent)


def test_convert_invalid_file_format(monkeypatch, tmp_path):
    """Test handling of non-DOCX files."""
    import pytest

    from docs_chunker import convert as convert_mod
    from docs_chunker.convert import convert_docx_to_markdown

    monkeypatch.setattr(convert_mod, "MarkItDown", FakeMarkItDown)
    txt_file = tmp_path / "example.txt"
    txt_file.write_text("Not a docx file")

    with pytest.raises(ValueError, match="Expected .docx file"):
        convert_docx_to_markdown(txt_file)


def test_convert_markitdown_unavailable(monkeypatch, tmp_path):
    """Test RuntimeError when markitdown unavailable."""
    import pytest

    from docs_chunker import convert as convert_mod
    from docs_chunker.convert import convert_docx_to_markdown

    monkeypatch.setattr(convert_mod, "MarkItDown", None)
    docx_file = tmp_path / "example.docx"
    docx_file.write_bytes(b"fake")

    with pytest.raises(RuntimeError, match="markitdown is not available"):
        convert_docx_to_markdown(docx_file)
