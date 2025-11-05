from pathlib import Path

import typer
from rich import print

from .chunk import chunk_markdown
from .convert import convert_docx_to_markdown
from .io import doc_name_from_path, output_paths_for, write_text
from .writer import save_chunks

app = typer.Typer(help="Docs Chunker CLI")


@app.command()
def convert(
    input: str = typer.Argument(..., help="Path to .docx file or directory"),
    force: bool = typer.Option(False, help="Overwrite existing outputs"),
    dry_run: bool = typer.Option(False, help="Do not write chunk files; only report"),
    min_tokens: int = typer.Option(200, help="Minimum tokens per chunk (heuristic)"),
    max_tokens: int = typer.Option(1200, help="Maximum tokens per chunk (heuristic)"),
) -> None:
    input_path = Path(input)
    targets = []
    if input_path.is_dir():
        targets = list(input_path.glob("*.docx"))
    else:
        targets = [input_path]

    for target in targets:
        base_dir, chunks_dir = output_paths_for(target)
        full_md_path = base_dir / f"{doc_name_from_path(target)}.md"
        if full_md_path.exists() and not force:
            print(f"[yellow]Skip existing:[/yellow] {full_md_path}")
            continue
        md_text = convert_docx_to_markdown(target)
        write_text(full_md_path, md_text)
        print(f"[green]Wrote:[/green] {full_md_path}")

        # Heuristic chunking
        chunks = chunk_markdown(md_text, min_tokens=min_tokens, max_tokens=max_tokens)
        if dry_run:
            print(f"[cyan]Dry-run:[/cyan] would write {len(chunks)} chunks for {target.name}")
        else:
            save_chunks(target, chunks)
            print(f"[green]Chunks:[/green] wrote {len(chunks)} files")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
