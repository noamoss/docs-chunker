from pathlib import Path

try:
    # Lazy import; in tests we can mock this interface
    from markitdown import MarkItDown  # type: ignore
except Exception:  # pragma: no cover - optional at test-time
    MarkItDown = None  # type: ignore


def convert_docx_to_markdown(input_path: Path) -> str:
    """
    Convert a DOCX file to Markdown format.

    Args:
        input_path: Path to the DOCX file to convert

    Returns:
        Markdown content as a string

    Raises:
        FileNotFoundError: If the input file does not exist
        RuntimeError: If markitdown is not available or conversion fails
        ValueError: If the file is not a valid DOCX file
    """
    # Check if file exists
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    # Check if markitdown is available
    if MarkItDown is None:
        raise RuntimeError(
            "markitdown is not available. Please install it with: "
            "pip install markitdown"
        )

    # Validate file extension
    if input_path.suffix.lower() != ".docx":
        raise ValueError(
            f"Expected .docx file, got: {input_path.suffix}. " f"File: {input_path}"
        )

    try:
        md = MarkItDown()
        result = md.convert(input_path.as_posix())
        if result is None:
            raise RuntimeError(f"Conversion returned None for file: {input_path}")
        text = result.text_content or ""
        # Basic normalization: unify line endings, strip trailing spaces
        lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
        return "\n".join(lines).strip() + "\n"
    except Exception as e:
        if isinstance(e, FileNotFoundError | RuntimeError | ValueError):
            raise
        raise RuntimeError(f"Failed to convert {input_path} to Markdown: {e}") from e
