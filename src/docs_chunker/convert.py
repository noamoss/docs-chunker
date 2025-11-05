from pathlib import Path

try:
    # Lazy import; in tests we can mock this interface
    from markitdown import MarkItDown  # type: ignore
except Exception:  # pragma: no cover - optional at test-time
    MarkItDown = None  # type: ignore


def convert_docx_to_markdown(input_path: Path) -> str:
    if MarkItDown is None:
        raise RuntimeError("markitdown is not available")
    md = MarkItDown()
    result = md.convert(input_path.as_posix())
    text = result.text_content or ""
    # Basic normalization: unify line endings, strip trailing spaces
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    return "\n".join(lines).strip() + "\n"
