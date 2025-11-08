from pathlib import Path

import typer
from rich import print

from . import llm
from .chunk import chunk_markdown
from .config import settings
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
    llm_strategy: bool | None = typer.Option(
        None,
        "--llm-strategy/--no-llm-strategy",
        help="Use an LLM to select a chunking strategy before chunking.",
    ),
    llm_validate: bool | None = typer.Option(
        None,
        "--llm-validate/--no-llm-validate",
        help="Validate chunk boundaries with an LLM after heuristic chunking.",
    ),
    llm_provider: str | None = typer.Option(
        None,
        help="LLM provider to use (local or openai). Defaults to configuration.",
    ),
    llm_model: str | None = typer.Option(
        None,
        help="Model identifier for the chosen LLM provider.",
    ),
    ollama_base_url: str | None = typer.Option(
        None,
        help="Base URL for Ollama when using the local provider.",
    ),
    openai_api_key: str | None = typer.Option(
        None,
        help="API key for OpenAI provider (overrides environment).",
    ),
) -> None:
    """Convert DOCX files to Markdown and chunk them for RAG systems."""
    # Validate token parameters
    if min_tokens < 1:
        print(f"[red]Error:[/red] min_tokens must be >= 1, got {min_tokens}")
        raise typer.Exit(code=1)
    if max_tokens < min_tokens:
        print(
            f"[red]Error:[/red] max_tokens ({max_tokens}) must be >= min_tokens "
            f"({min_tokens})"
        )
        raise typer.Exit(code=1)

    # Validate input path
    input_path = Path(input)
    if not input_path.exists():
        print(f"[red]Error:[/red] Path does not exist: {input_path}")
        raise typer.Exit(code=1)

    # Resolve LLM configuration overrides
    effective_llm_strategy = (
        settings.llm_strategy_enabled if llm_strategy is None else llm_strategy
    )
    effective_llm_validate = (
        settings.llm_validation_enabled if llm_validate is None else llm_validate
    )
    provider_value = (llm_provider or settings.llm_provider).lower()
    model_value = llm_model or (
        settings.local_model if provider_value == "local" else settings.openai_model
    )
    base_url_value = (
        ollama_base_url if ollama_base_url is not None else settings.ollama_base_url
    )
    api_key_value = openai_api_key or settings.openai_api_key

    # Collect targets
    targets = []
    if input_path.is_dir():
        targets = list(input_path.glob("*.docx"))
        if not targets:
            print(f"[yellow]Warning:[/yellow] No .docx files found in {input_path}")
            return
    elif input_path.is_file():
        if input_path.suffix.lower() != ".docx":
            print(
                f"[red]Error:[/red] File must be a .docx file, got: {input_path.suffix}"
            )
            raise typer.Exit(code=1)
        targets = [input_path]
    else:
        print(f"[red]Error:[/red] Path is neither a file nor a directory: {input_path}")
        raise typer.Exit(code=1)

    # Process each target
    for target in targets:
        try:
            base_dir, chunks_dir = output_paths_for(target)
            full_md_path = base_dir / f"{doc_name_from_path(target)}.md"
            if full_md_path.exists() and not force:
                print(f"[yellow]Skip existing:[/yellow] {full_md_path}")
                continue

            # Convert DOCX to Markdown
            try:
                md_text = convert_docx_to_markdown(target)
            except FileNotFoundError:
                print(f"[red]Error:[/red] File not found: {target}")
                continue
            except RuntimeError as e:
                print(f"[red]Error:[/red] Conversion failed for {target}: {e}")
                continue
            except Exception as e:
                print(f"[red]Error:[/red] Unexpected error converting {target}: {e}")
                continue

            # Write full markdown
            try:
                write_text(full_md_path, md_text)
                print(f"[green]Wrote:[/green] {full_md_path}")
            except PermissionError:
                print(f"[red]Error:[/red] Permission denied writing to {full_md_path}")
                continue
            except Exception as e:
                print(f"[red]Error:[/red] Failed to write {full_md_path}: {e}")
                continue

            chunks = None
            strategy_info = None

            if effective_llm_strategy:
                try:
                    strategy_chunks, _, strategy_info = llm.chunk_with_llm_strategy(
                        md_text,
                        min_tokens,
                        max_tokens,
                        provider=provider_value,
                        model=model_value,
                        base_url=base_url_value,
                    )
                except Exception as e:
                    print(
                        "[yellow]Warning:[/yellow] LLM strategy selection failed; "
                        f"falling back to heuristics: {e}"
                    )
                    strategy_chunks = None
                if strategy_chunks:
                    chunks = strategy_chunks
                    strategy_label = ""
                    if strategy_info:
                        if (
                            strategy_info.strategy_type == "by_level"
                            and strategy_info.level is not None
                        ):
                            strategy_label = f"level {strategy_info.level} headings"
                        elif (
                            strategy_info.strategy_type == "custom_boundaries"
                            and strategy_info.boundaries is not None
                        ):
                            strategy_label = (
                                "custom boundaries "
                                f"({len(strategy_info.boundaries)} markers)"
                            )
                        if strategy_info.reasoning:
                            strategy_label = (
                                f"{strategy_label} – {strategy_info.reasoning}"
                                if strategy_label
                                else strategy_info.reasoning
                            )
                    print(
                        "[cyan]LLM strategy:[/cyan] applied"
                        + (f" {strategy_label}" if strategy_label else "")
                    )
                elif strategy_info is not None:
                    print(
                        "[yellow]Warning:[/yellow] LLM provided a strategy that could "
                        "not be applied; using heuristic chunking"
                    )

            if chunks is None:
                try:
                    chunks = chunk_markdown(
                        md_text, min_tokens=min_tokens, max_tokens=max_tokens
                    )
                except ValueError as e:
                    print(f"[red]Error:[/red] Chunking failed for {target}: {e}")
                    continue

            if effective_llm_validate:
                try:
                    adjusted_chunks = llm.validate_and_adjust_chunks(
                        md_text,
                        chunks,
                        min_tokens,
                        max_tokens,
                        language_hint=settings.language,
                        provider=provider_value,
                        model=model_value,
                        base_url=base_url_value,
                        api_key=api_key_value,
                    )
                    chunks = adjusted_chunks
                    print(
                        "[cyan]LLM validation:[/cyan] using provider "
                        f"'{provider_value}'"
                    )
                except Exception as e:
                    print(
                        "[yellow]Warning:[/yellow] LLM validation failed, "
                        f"using heuristic chunks: {e}"
                    )

            if dry_run:
                print(
                    f"[cyan]Dry-run:[/cyan] would write {len(chunks)} chunks "
                    f"for {target.name}"
                )
            else:
                try:
                    save_chunks(target, chunks)
                    print(f"[green]Chunks:[/green] wrote {len(chunks)} files")
                except Exception as e:
                    print(f"[red]Error:[/red] Failed to save chunks for {target}: {e}")
                    continue
        except Exception as e:
            print(f"[red]Error:[/red] Unexpected error processing {target}: {e}")
            continue


def main() -> None:
    app()


if __name__ == "__main__":
    main()
