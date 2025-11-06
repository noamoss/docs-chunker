import hashlib
from pathlib import Path

from .config import settings


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def doc_name_from_path(input_path: Path) -> str:
    return input_path.stem


def output_paths_for(input_path: Path) -> tuple[Path, Path]:
    name = doc_name_from_path(input_path)
    # Use absolute path if settings.output_dir is absolute, otherwise relative to cwd
    output_base = Path(settings.output_dir)
    if not output_base.is_absolute():
        output_base = Path.cwd() / output_base
    base_dir = output_base / name
    chunks_dir = base_dir / "chunks"
    return base_dir, chunks_dir


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
