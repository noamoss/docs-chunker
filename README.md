# Docs Chunker

A Python service that converts DOCX/PDF documents to Markdown and performs structure-aware chunking optimized for RAG (Retrieval-Augmented Generation) systems.

## Features

- **Document Conversion**: Converts DOCX files to Markdown using MarkItDown
- **Intelligent Chunking**: Structure-aware chunking based on document headings, sections, and subsections
- **Accurate Token Counting**: Uses tiktoken for precise token estimation (with fallback to heuristic)
- **Hebrew Support**: Full support for Hebrew/RTL text with proper UTF-8 handling
- **Configurable Token Limits**: Adjustable min/max token counts per chunk with validation
- **YAML Front Matter**: Each chunk includes metadata (id, title, level, token_count, checksum)
- **Content Preservation**: Ensures no content loss during chunking with exact whitespace preservation
- **Robust Error Handling**: Comprehensive error handling with user-friendly messages
- **Security**: Path validation to prevent traversal attacks, secret scanning in pre-commit hooks
- **LLM-Based Strategy Selection**: Uses LLM analysis to determine optimal chunking strategies

## LLM-Based Chunking Strategy

The chunker uses LLM analysis to determine optimal chunking strategies based on:
- Document structure and hierarchy
- Document length and section sizes
- RAG quality considerations (embedding-based retrieval effectiveness)

The LLM analyzes your document and decides whether to chunk by:
- **Chapters** (level 1 headings)
- **Sections** (level 2 headings)
- **Subsections** (level 3+ headings)
- **Custom boundaries** (for unstructured documents)

### Supported Providers

- **Ollama** (local, default): Run LLMs locally
- **OpenAI** (cloud): Use OpenAI's API

### Strategy Types

- **by_level**: Chunk by heading level (e.g., all `##` headings)
- **custom_boundaries**: Custom line boundaries for unstructured documents

The system automatically falls back to heuristic chunking if the LLM is unavailable, ensuring the tool always works.

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

## LLM Provider Setup

### Setting Up Ollama (Local Provider)

1. **Install Ollama:**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Start Ollama service:**
   ```bash
   ollama serve
   ```

3. **Pull required model:**
   ```bash
   ollama pull llama3.1:8b
   ```

4. **Verify installation:**
   ```bash
   ollama list
   ```

5. **Use with docs-chunker:**
   ```bash
   python -m docs_chunker.cli documents/ --llm-provider local
   ```

### Setting Up OpenAI (Cloud Provider)

1. **Get API key:**
   - Sign up at https://platform.openai.com/
   - Create API key at https://platform.openai.com/api-keys

2. **Set environment variable:**
   ```bash
   export OPENAI_API_KEY="sk-your-api-key-here"
   ```

3. **Use with docs-chunker:**
   ```bash
   python -m docs_chunker.cli documents/ --llm-provider openai
   ```

   **Note:** OpenAI API calls incur costs. See [OpenAI pricing](https://openai.com/pricing).

## Usage

### CLI

**Basic usage (LLM strategy enabled by default):**
```bash
# Convert and chunk a single DOCX file
python -m docs_chunker.cli documents/example.docx

# Convert and chunk all DOCX files in a directory
python -m docs_chunker.cli documents/
```

**Disable LLM strategy (use heuristic chunking):**
```bash
python -m docs_chunker.cli documents/ --no-llm-strategy
```

**Use OpenAI provider:**
```bash
python -m docs_chunker.cli documents/ --llm-provider openai --llm-model gpt-4o-mini
```

**Custom RAG token limits:**
```bash
python -m docs_chunker.cli documents/ --min-tokens 100 --max-tokens 800
```

**Specify Ollama model:**
```bash
python -m docs_chunker.cli documents/ --llm-provider local --llm-model llama3.2:1b
```

**Other options:**
```bash
# Force overwrite existing outputs
python -m docs_chunker.cli documents/example.docx --force

# Dry run (preview without writing)
python -m docs_chunker.cli documents/example.docx --dry-run

# Enable LLM validation (post-processing adjustment)
python -m docs_chunker.cli documents/ --llm-validate
```

### Configuration via Environment Variables

Set RAG token limits (separate from LLM provider config):

```bash
# Via environment variables
export DOCS_CHUNKER_MIN_TOKENS=200
export DOCS_CHUNKER_MAX_TOKENS=1200
```

Other available environment variables:
- `DOCS_CHUNKER_LLM_PROVIDER`: Default provider ("local" or "openai")
- `DOCS_CHUNKER_LLM_STRATEGY`: Enable LLM strategy by default ("true"/"false")
- `DOCS_CHUNKER_LLM_VALIDATE`: Enable LLM validation by default ("true"/"false")
- `DOCS_CHUNKER_OPENAI_API_KEY`: OpenAI API key
- `DOCS_CHUNKER_LOCAL_MODEL`: Default Ollama model
- `DOCS_CHUNKER_OLLAMA_BASE_URL`: Ollama base URL
- `DOCS_CHUNKER_DEBUG`: Enable debug logging ("true"/"false")

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
│   ├── chunk.py            # Chunking logic (heuristic + strategy-based)
│   ├── structure.py        # Document structure extraction
│   ├── llm_strategy.py     # LLM-based strategy decision
│   ├── llm_providers.py    # LLM provider abstractions
│   ├── llm.py              # LLM validation and orchestration
│   ├── writer.py           # Chunk file writing
│   └── io.py               # File I/O utilities
├── tests/                  # Test suite
├── documents/              # Input documents (add your own)
└── output/                 # Generated outputs (gitignored)
```

## Chunking Strategy

The chunker uses LLM-based strategy selection:

1. **Structure Analysis**: Extracts document structure (headings, hierarchy, token counts)
2. **LLM Decision**: LLM analyzes structure and decides optimal chunking strategy
3. **Strategy Application**: Applies LLM strategy to create chunks
4. **Fallback**: If LLM unavailable, uses heuristic chunking

### LLM Strategy Types

- **by_level**: Chunk by heading level (e.g., all `##` headings)
- **custom_boundaries**: Custom line boundaries for unstructured documents

### Heuristic Fallback

If LLM is unavailable, the system uses heuristic chunking:

1. **Heading-based partitioning**: Splits documents by markdown headings (#, ##, ###, etc.)
2. **Token-aware merging**: Merges undersized chunks (< min_tokens)
3. **Smart splitting**: Splits oversized chunks (> max_tokens) by:
   - Subheadings (if available)
   - Numbered lists (1., 2., etc.)
   - Bold headings (**text**)
   - Paragraph boundaries (with exact whitespace preservation)
4. **Title extraction**: Automatically extracts titles from headings or content
5. **Safety features**:
   - Max depth protection prevents infinite recursion on edge cases
   - Exact whitespace preservation ensures byte-for-byte content reconstruction
   - Path hashing prevents output directory collisions for same-named files

## Requirements

- Python >= 3.10
- markitdown (with [docx] extra for DOCX support)
- typer (for CLI)
- pydantic (for configuration)
- pyyaml (for chunk metadata)
- tiktoken (for accurate token counting)
- ollama (optional, for local LLM provider)
- openai (optional, for OpenAI provider)

## Error Handling

The service includes comprehensive error handling:

- **Input Validation**: Validates token parameters (min_tokens >= 1, max_tokens >= min_tokens)
- **File Validation**: Checks file existence, format, and permissions
- **User-Friendly Messages**: Clear, actionable error messages using Rich formatting
- **Graceful Degradation**: Continues processing other files if one fails
- **LLM Error Handling**: Logs LLM failures and automatically falls back to heuristic chunking
- **Logging**: Configurable logging with DEBUG support via `DOCS_CHUNKER_DEBUG` environment variable

## Troubleshooting

**LLM strategy not working:**
- Check Ollama is running: `ollama list`
- Verify model is available: `ollama pull llama3.1:8b`
- Check OpenAI API key is set: `echo $OPENAI_API_KEY`
- Enable debug logging: `export DOCS_CHUNKER_DEBUG=true`

**Fallback to heuristic chunking:**
- If LLM is unavailable, the system automatically falls back to heuristic chunking
- This ensures the tool always works, even without LLM
- Check logs for specific error messages

**Large documents:**
- The system automatically handles large documents by using structure-only analysis
- If issues persist, consider disabling LLM strategy for very large documents: `--no-llm-strategy`

**Hebrew/RTL text:**
- LLM strategy works with Hebrew documents
- Ensure your LLM model supports Hebrew (llama3.1:8b does)
- Heuristic chunking also fully supports Hebrew/RTL text

## Security

- **Path Validation**: Prevents path traversal attacks with `validate_path()` function
- **Secret Scanning**: detect-secrets hook in pre-commit to prevent accidental secret commits
- **Safe Output Paths**: Uses path hashing to prevent collisions and ensure deterministic outputs

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
