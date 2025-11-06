# LLM Integration Plan

## Overview
Integrate Ollama (local) and OpenAI (cloud) LLM providers to validate and optimize chunk boundaries after heuristic chunking.

## Goals
1. **Primary**: Use LLM to suggest merge/split operations to improve chunk quality
2. **Fallback**: Gracefully handle LLM unavailability (return original chunks)
3. **Dual Provider**: Support both Ollama (local) and OpenAI (cloud)
4. **Hebrew Support**: Ensure LLM prompts work well with Hebrew/RTL text

---

## Architecture

### Current Flow
```
DOCX → Markdown → Heuristic Chunking → Save Chunks
```

### New Flow
```
DOCX → Markdown → Heuristic Chunking → LLM Validation → Save Chunks
                                              ↓ (if unavailable)
                                    Return original chunks
```

### Integration Points
1. **CLI**: Add option to enable/disable LLM validation (`--llm-validate`, default: True)
2. **LLM Module**: Implement actual provider calls
3. **Config**: Use existing settings for provider selection

---

## Implementation Steps

### Phase 1: Dependencies & Setup

#### 1.1 Add Required Packages
- **Ollama**: `ollama` (Python client for Ollama API)
- **OpenAI**: `openai` (already in dependencies via httpx, but need explicit client)
- **Environment**: Support optional dependencies

**Files to modify:**
- `pyproject.toml` (or recreate if missing)
  - Add `ollama` to dependencies
  - Add `openai` to dependencies (if not already present)
  - Make them optional dependencies for flexibility

**Dependencies:**
```toml
[project]
dependencies = [
    # ... existing ...
    "ollama >= 0.1.0",  # Ollama Python client
    "openai >= 1.0.0",  # OpenAI Python client
]

[project.optional-dependencies]
llm = [
    "ollama >= 0.1.0",
    "openai >= 1.0.0",
]
```

#### 1.2 Ollama Installation & Setup
- Document Ollama installation steps
- Verify Ollama service is running (`ollama serve`)
- Test model availability (`ollama list`, `ollama pull llama3.1:8b`)

**Documentation needed:**
- README section on LLM setup
- How to install Ollama
- How to pull required models
- How to verify Ollama is running

---

### Phase 2: LLM Provider Implementation

#### 2.1 Create Provider Interface
**File: `src/docs_chunker/llm_providers.py`** (new file)

**Structure:**
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class LLMProvider(ABC):
    @abstractmethod
    def propose_chunk_operations(
        self, 
        markdown_text: str,
        chunks_schema: List[Dict[str, Any]],
        max_tokens: int,
        language_hint: str
    ) -> Optional[Dict[str, Any]]:
        """Propose merge/split operations for chunks"""
        pass

class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "llama3.1:8b", base_url: str = "http://localhost:11434"):
        # Initialize Ollama client
    
class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        # Initialize OpenAI client
```

#### 2.2 Implement Ollama Provider
**Functions:**
- `_build_prompt()`: Create prompt for chunk optimization
- `_call_ollama()`: Make API call to Ollama
- `_parse_response()`: Parse JSON response from LLM

**Prompt Design:**
- Include chunk metadata (id, title, level, token_count)
- Include sample of chunk content (truncated if needed)
- Request JSON response with operations array
- Support both English and Hebrew prompts

**Example Prompt Structure:**
```
You are a document chunking expert. Review these chunks and suggest optimizations.

Chunks:
{chunks_schema_json}

Requirements:
- Target: {max_tokens} tokens per chunk
- Preserve semantic boundaries
- Merge small chunks that are related
- Split large chunks at natural boundaries

Return JSON: {"operations": [{"type": "merge", "range": [1, 3]}, ...]}
```

**Error Handling:**
- Connection errors → return None
- Invalid JSON → return None
- Timeout → return None
- Model not found → return None

#### 2.3 Implement OpenAI Provider
**Similar structure to Ollama:**
- Use OpenAI chat completion API
- Same prompt structure
- Handle API key errors
- Handle rate limits

**Differences:**
- Use `openai.ChatCompletion` or `openai.chat.completions.create`
- Different error types (API errors, quota, etc.)
- May need different model selection

#### 2.4 Provider Factory
**File: `src/docs_chunker/llm.py`** (modify)

**Function:**
```python
def _get_provider(provider: str, **kwargs) -> Optional[LLMProvider]:
    """Factory function to get appropriate LLM provider"""
    if provider == "local":
        try:
            return OllamaProvider(model=kwargs.get("model", "llama3.1:8b"))
        except Exception:
            return None
    elif provider == "openai":
        api_key = kwargs.get("api_key")
        if not api_key:
            return None
        try:
            return OpenAIProvider(api_key=api_key, model=kwargs.get("model", "gpt-4o-mini"))
        except Exception:
            return None
    return None
```

---

### Phase 3: Integrate into LLM Module

#### 3.1 Update `_llm_propose_boundaries()`
**File: `src/docs_chunker/llm.py`** (modify existing function)

**Changes:**
- Replace `return None` placeholder
- Get provider from factory
- Call `provider.propose_chunk_operations()`
- Handle errors gracefully (return None)

**Implementation:**
```python
def _llm_propose_boundaries(
    markdown_text: str,
    chunks_schema: List[Dict[str, Any]],
    *,
    language_hint: str = "auto",
    provider: str = "local",
    max_tokens: int = 1200,
    model: str = "llama3.1:8b",
    api_key: str | None = None,
) -> Optional[Dict[str, Any]]:
    """Call LLM to propose chunk boundary adjustments"""
    llm_provider = _get_provider(
        provider, 
        model=model, 
        api_key=api_key
    )
    
    if not llm_provider:
        return None
    
    try:
        return llm_provider.propose_chunk_operations(
            markdown_text=markdown_text,
            chunks_schema=chunks_schema,
            max_tokens=max_tokens,
            language_hint=language_hint,
        )
    except Exception:
        # Log error if needed
        return None
```

#### 3.2 Update `validate_and_adjust_chunks()`
**File: `src/docs_chunker/llm.py`** (modify existing function)

**Changes:**
- Pass additional parameters (model, api_key) to `_llm_propose_boundaries`
- Improve error logging (optional, for debugging)

---

### Phase 4: CLI Integration

#### 4.1 Add CLI Options
**File: `src/docs_chunker/cli.py`** (modify)

**New Options:**
- `--llm-validate`: Enable LLM validation (default: True)
- `--no-llm-validate`: Disable LLM validation (flag to opt-out)
- `--llm-provider`: Choose provider ("local" or "openai", default: "local")
- `--llm-model`: Model name (default: from config)
- `--openai-api-key`: OpenAI API key (optional, can use env var)

**Changes:**
```python
@app.command()
def convert(
    input: str = typer.Argument(...),
    # ... existing options ...
    llm_validate: bool = typer.Option(True, "--llm-validate/--no-llm-validate", help="Enable/disable LLM chunk validation (default: enabled)"),
    llm_provider: str = typer.Option("local", help="LLM provider: 'local' (Ollama) or 'openai'"),
    llm_model: str = typer.Option(None, help="LLM model name"),
    openai_api_key: str = typer.Option(None, help="OpenAI API key (or use OPENAI_API_KEY env var)"),
) -> None:
    # ... existing code ...
    
    chunks = chunk_markdown(md_text, min_tokens=min_tokens, max_tokens=max_tokens)
    
    # NEW: LLM validation step
    if llm_validate:
        from .llm import validate_and_adjust_chunks
        from .config import settings
        
        model = llm_model or settings.local_model
        api_key = openai_api_key or settings.openai_api_key
        
        print(f"[cyan]Validating chunks with LLM ({llm_provider})...[/cyan]")
        chunks = validate_and_adjust_chunks(
            md_text,
            chunks,
            min_tokens=min_tokens,
            max_tokens=max_tokens,
            language_hint="auto",
            provider=llm_provider,
        )
        print(f"[green]LLM validation complete[/green]")
    
    # ... rest of existing code ...
```

#### 4.2 Environment Variables
**Support:**
- `OPENAI_API_KEY`: Fallback for OpenAI API key
- `OLLAMA_BASE_URL`: Custom Ollama server URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: Default Ollama model (default: llama3.1:8b)

**Update Config:**
**File: `src/docs_chunker/config.py`** (modify)

```python
import os
from typing import Literal

class Settings(BaseModel):
    # ... existing ...
    llm_provider: Literal["local", "openai"] = "local"
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    local_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
```

---

### Phase 5: Testing

#### 5.1 Unit Tests for Providers
**File: `tests/test_llm_providers.py`** (new)

**Test Cases:**
- Ollama provider initialization
- Ollama provider with unavailable service
- OpenAI provider initialization
- OpenAI provider with invalid API key
- Provider factory function
- Prompt building
- Response parsing

**Mocking:**
- Mock Ollama API calls
- Mock OpenAI API calls
- Test error handling

#### 5.2 Integration Tests
**File: `tests/test_llm_integration.py`** (new)

**Test Cases:**
- End-to-end with mocked Ollama
- End-to-end with mocked OpenAI
- LLM unavailable fallback
- Invalid LLM response handling
- Content preservation verification

#### 5.3 Update Existing Tests
**File: `tests/test_llm_validator.py`** (modify)

- Keep existing mocked tests
- Add tests for actual provider integration
- Test CLI integration

---

### Phase 6: Error Handling & Logging

#### 6.1 Error Handling Strategy
- **Connection Errors**: Return None, use original chunks
- **Invalid Responses**: Return None, use original chunks
- **Timeout**: Return None, use original chunks
- **Model Not Found**: Return None, print warning

#### 6.2 Logging (Optional)
**File: `src/docs_chunker/llm.py`**

- Add optional logging for debugging
- Log LLM calls (can be disabled)
- Log errors (can be disabled)

**Use Python `logging` module:**
```python
import logging

logger = logging.getLogger(__name__)

# In functions:
logger.debug(f"Calling LLM provider: {provider}")
logger.warning(f"LLM unavailable, using original chunks")
```

---

### Phase 7: Documentation

#### 7.1 Update README
**File: `README.md`** (modify)

**New Sections:**
- LLM Integration
- Installing Ollama
- Setting up OpenAI
- Usage examples with LLM
- Troubleshooting

#### 7.2 Code Documentation
- Docstrings for all new functions
- Type hints (already present)
- Examples in docstrings

---

## Implementation Order

### Sprint 1: Foundation
1. ✅ Create plan (this document)
2. Add dependencies (pyproject.toml)
3. Create provider interface
4. Implement Ollama provider (basic)
5. Basic tests for Ollama

### Sprint 2: Integration
6. Implement OpenAI provider
7. Update `_llm_propose_boundaries()`
8. CLI integration
9. Config updates

### Sprint 3: Polish
10. Error handling improvements
11. Logging
12. Comprehensive tests
13. Documentation

---

## Testing Strategy

### Manual Testing
1. **Ollama Local**:
   ```bash
   # Start Ollama
   ollama serve
   
   # Pull model
   ollama pull llama3.1:8b
   
   # Test CLI
   python -m docs_chunker.cli documents/ --llm-validate --llm-provider local
   ```

2. **OpenAI**:
   ```bash
   export OPENAI_API_KEY="sk-..."
   python -m docs_chunker.cli documents/ --llm-validate --llm-provider openai
   ```

### Automated Testing
- Mock provider calls in unit tests
- Integration tests with mocked responses
- Test error scenarios
- Test content preservation

---

## Edge Cases & Considerations

### 1. Large Documents
- **Problem**: LLM context window limits
- **Solution**: 
  - Limit chunks sent to LLM (e.g., first 50 chunks)
  - Or batch process in groups
  - Or skip LLM for very large documents

### 2. Hebrew/RTL Text
- **Problem**: LLM may not handle RTL well
- **Solution**:
  - Test with Hebrew documents
  - Adjust prompts for Hebrew
  - Consider language-specific models

### 3. LLM Response Format
- **Problem**: LLM may return invalid JSON
- **Solution**:
  - Use structured output (if available)
  - Parse with fallback
  - Validate response schema

### 4. Performance
- **Problem**: LLM calls are slow
- **Solution**:
  - Make it optional (default: on, can disable with `--no-llm-validate`)
  - Add progress indicators
  - Graceful fallback if LLM unavailable
  - Consider async calls (future)

### 5. Cost (OpenAI)
- **Problem**: API calls cost money
- **Solution**:
  - Document costs
  - Suggest using local Ollama
  - Add usage warnings

---

## Success Criteria

1. ✅ Ollama integration works end-to-end
2. ✅ OpenAI integration works end-to-end
3. ✅ Graceful fallback when LLM unavailable
4. ✅ No content loss (all tests pass)
5. ✅ CLI options work correctly
6. ✅ Documentation complete
7. ✅ Tests cover main scenarios

---

## Future Enhancements

1. **Split Operations**: Currently only merge is implemented
2. **Async Calls**: Parallel LLM calls for multiple documents
3. **Caching**: Cache LLM responses for same chunks
4. **Streaming**: Show LLM progress in real-time
5. **Custom Prompts**: Allow users to provide custom prompts
6. **Multiple Models**: Support multiple models in parallel
7. **Chunk Preview**: Show before/after in LLM validation

---

## Notes

- LLM validation is **enabled by default** (can opt-out with `--no-llm-validate`)
- Graceful fallback: if LLM unavailable, use heuristic chunks
- LLM is for **optimization**, not requirement
- Always preserve content (no loss allowed)
- Test with real Hebrew documents

