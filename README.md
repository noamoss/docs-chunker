# Docs Chunker

A Python service that converts DOCX/PDF documents to Markdown and performs structure-aware chunking optimized for RAG (Retrieval-Augmented Generation) systems.

## Features

- **Document Conversion**: Converts DOCX files to Markdown using MarkItDown
- **Intelligent Chunking**: Structure-aware chunking based on document headings, sections, and subsections
- **Hebrew Support**: Full support for Hebrew/RTL text with proper UTF-8 handling
- **Configurable Token Limits**: Adjustable min/max token counts per chunk
- **YAML Front Matter**: Each chunk includes metadata (id, title, level, token_count, checksum)
- **Content Preservation**: Ensures no content loss during chunking

## Installation

```bash
# Clone the repository
git clone https://github.com/noamoss/docs-chunker.git
cd docs-chunker

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Install DOCX support
pip install "markitdown[docx]"
```

## Usage

### CLI

```bash
# Convert and chunk a single DOCX file
python -m docs_chunker.cli documents/example.docx

# Convert and chunk all DOCX files in a directory
python -m docs_chunker.cli documents/

# With custom token limits
python -m docs_chunker.cli documents/example.docx --min-tokens 200 --max-tokens 1200

# Force overwrite existing outputs
python -m docs_chunker.cli documents/example.docx --force

# Dry run (preview without writing)
python -m docs_chunker.cli documents/example.docx --dry-run
```

### Output Structure

```
output/
└── <document-name>/
    ├── <document-name>.md          # Full markdown conversion
    └── chunks/
        ├── 001_<title-slug>.md     # Individual chunks with YAML front matter
        ├── 002_<title-slug>.md
        └── ...
```

Each chunk file contains:
- YAML front matter with metadata (id, title, level, token_count, checksum)
- Markdown content

## Development

```bash
# Run tests
make test
# or
pytest

# Run linters
make lint

# Format code
make fmt

# Type checking
make type
```

## Project Structure

```
docs-chunker/
├── src/docs_chunker/
│   ├── __init__.py
│   ├── cli.py              # CLI interface
│   ├── config.py           # Configuration settings
│   ├── convert.py          # DOCX to Markdown conversion
│   ├── chunk.py            # Chunking logic
│   ├── writer.py           # Chunk file writing
│   ├── io.py               # File I/O utilities
│   └── llm.py              # LLM validation (future)
├── tests/                  # Test suite
├── documents/              # Input documents (add your own)
└── output/                 # Generated outputs (gitignored)
```

## Chunking Strategy

The chunker uses a hierarchical approach:

1. **Heading-based partitioning**: Splits documents by markdown headings (#, ##, ###, etc.)
2. **Token-aware merging**: Merges undersized chunks (< min_tokens)
3. **Smart splitting**: Splits oversized chunks (> max_tokens) by:
   - Subheadings (if available)
   - Numbered lists (1., 2., etc.)
   - Bold headings (**text**)
   - Paragraph boundaries
4. **Title extraction**: Automatically extracts titles from headings or content

## Requirements

- Python >= 3.10
- markitdown (with [docx] extra for DOCX support)
- typer (for CLI)
- pydantic (for configuration)
- pyyaml (for chunk metadata)

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]


