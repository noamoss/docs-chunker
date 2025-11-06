import hashlib
from pathlib import Path

from .config import settings


def validate_path(path: Path) -> Path:
    """
    Validate and resolve a path, preventing path traversal attacks.

    Args:
        path: Path to validate

    Returns:
        Resolved absolute Path

    Raises:
        ValueError: If path contains traversal components or is invalid
        FileNotFoundError: If path does not exist (for input paths)
    """
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {path}. {e}") from e

    # Prevent path traversal - check if resolved path contains parent directory
    # references. This is a basic check; the resolve() above should handle most
    # cases
    path_str = str(resolved)
    if ".." in path_str or path_str.startswith("~"):
        # Additional check: ensure we're not trying to escape
        cwd = Path.cwd().resolve()
        try:
            resolved.relative_to(cwd)
        except ValueError:
            raise ValueError(
                f"Path traversal detected or path outside working directory: {path}"
            ) from None

    return resolved


def ensure_dir(path: Path) -> None:
    """Create directory and parents if they don't exist."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        raise PermissionError(
            f"Permission denied creating directory: {path}. {e}"
        ) from e
    except OSError as e:
        raise OSError(f"Failed to create directory: {path}. {e}") from e


def doc_name_from_path(input_path: Path) -> str:
    return input_path.stem


def output_paths_for(input_path: Path) -> tuple[Path, Path]:
    """
    Generate output paths for a document, using path hash to prevent collisions.

    Args:
        input_path: Path to the input document

    Returns:
        Tuple of (base_dir, chunks_dir) paths

    Raises:
        ValueError: If path is invalid or contains traversal components
    """
    # Normalize the input path to absolute and resolve symlinks
    # Note: We don't require the file to exist here, as it might be created later
    try:
        normalized_path = input_path.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid input path: {input_path}. {e}") from e

    # Create a hash of the normalized path to prevent collisions
    # Use first 8 characters of SHA256 for a reasonable directory name
    path_hash = hashlib.sha256(str(normalized_path).encode("utf-8")).hexdigest()[:8]

    # Combine stem with hash: {stem}_{hash}
    name = f"{input_path.stem}_{path_hash}"

    # Use absolute path if settings.output_dir is absolute, otherwise relative to cwd
    output_base = Path(settings.output_dir)
    if not output_base.is_absolute():
        output_base = Path.cwd() / output_base
    base_dir = output_base / name
    chunks_dir = base_dir / "chunks"
    return base_dir, chunks_dir


def write_text(path: Path, content: str) -> None:
    """
    Write text content to a file, creating parent directories if needed.

    Args:
        path: Path to write to
        content: Text content to write

    Raises:
        PermissionError: If permission denied
        OSError: If write fails
    """
    ensure_dir(path.parent)
    try:
        path.write_text(content, encoding="utf-8")
    except PermissionError as e:
        raise PermissionError(f"Permission denied writing to: {path}. {e}") from e
    except OSError as e:
        raise OSError(f"Failed to write to: {path}. {e}") from e


def checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
