import types

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


def test_cli_convert_with_llm_validation(monkeypatch, tmp_path):
    from docs_chunker import convert as convert_mod

    class FakeMarkItDown:
        def convert(self, path: str):
            class R:
                text_content = "# Title\n\n## A\nOne.\n"

            return R()

    monkeypatch.setattr(convert_mod, "MarkItDown", FakeMarkItDown)

    from docs_chunker import llm as llm_mod

    called = {}

    def fake_validate(markdown_text, chunks, *args, **kwargs):
        called["invoked"] = True
        return chunks

    monkeypatch.setattr(llm_mod, "validate_and_adjust_chunks", fake_validate)

    input_doc = tmp_path / "demo.docx"
    input_doc.write_bytes(b"fake")

    runner = CliRunner()
    res = runner.invoke(
        app,
        [
            str(input_doc),
            "--force",
            "--min-tokens",
            "1",
            "--llm-validate",
            "--llm-provider",
            "local",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    assert called.get("invoked") is True


def test_cli_convert_with_llm_strategy(monkeypatch, tmp_path):
    from docs_chunker import convert as convert_mod

    class FakeMarkItDown:
        def convert(self, path: str):
            class R:
                text_content = "# Title\n\n## A\nOne.\n"

            return R()

    monkeypatch.setattr(convert_mod, "MarkItDown", FakeMarkItDown)

    from docs_chunker import llm as llm_mod
    from docs_chunker.chunk import Chunk

    called = {}

    def fake_chunk_strategy(markdown_text, *args, **kwargs):
        called["invoked"] = True
        strategy = types.SimpleNamespace(
            strategy_type="by_level",
            level=1,
            reasoning="test",
        )
        chunk = Chunk(id=1, title="Title", level=1, content=markdown_text)
        return [chunk], None, strategy

    monkeypatch.setattr(llm_mod, "chunk_with_llm_strategy", fake_chunk_strategy)

    input_doc = tmp_path / "demo.docx"
    input_doc.write_bytes(b"fake")

    runner = CliRunner()
    res = runner.invoke(
        app,
        [
            str(input_doc),
            "--force",
            "--min-tokens",
            "1",
            "--llm-strategy",
        ],
        catch_exceptions=False,
    )
    assert res.exit_code == 0, res.output
    assert called.get("invoked") is True
