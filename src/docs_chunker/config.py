import os
from typing import Literal

from pydantic import BaseModel


class Settings(BaseModel):
    documents_dir: str = "documents"
    output_dir: str = "output"
    language: Literal["auto", "en", "he"] = "auto"
    min_tokens: int = 200
    max_tokens: int = 1200
    llm_provider: Literal["local", "openai"] = "local"
    openai_api_key: str | None = None
    local_model: str = "llama3.1:8b"

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings with environment variable overrides."""
        # Parse min_tokens with validation
        min_tokens_str = os.getenv("DOCS_CHUNKER_MIN_TOKENS", "200")
        try:
            min_tokens = int(min_tokens_str)
            if min_tokens < 1:
                raise ValueError(
                    f"DOCS_CHUNKER_MIN_TOKENS must be >= 1, got {min_tokens}"
                )
        except ValueError as e:
            raise ValueError(
                f"Invalid value for DOCS_CHUNKER_MIN_TOKENS: {min_tokens_str}. {e}"
            ) from e

        # Parse max_tokens with validation
        max_tokens_str = os.getenv("DOCS_CHUNKER_MAX_TOKENS", "1200")
        try:
            max_tokens = int(max_tokens_str)
        except ValueError as e:
            raise ValueError(
                f"Invalid value for DOCS_CHUNKER_MAX_TOKENS: {max_tokens_str}. {e}"
            ) from e

        # Validate max_tokens >= min_tokens
        if max_tokens < min_tokens:
            raise ValueError(
                f"DOCS_CHUNKER_MAX_TOKENS ({max_tokens}) must be >= "
                f"DOCS_CHUNKER_MIN_TOKENS ({min_tokens})"
            )

        return cls(
            documents_dir=os.getenv("DOCS_CHUNKER_DOCUMENTS_DIR", "documents"),
            output_dir=os.getenv("DOCS_CHUNKER_OUTPUT_DIR", "output"),
            language=os.getenv("DOCS_CHUNKER_LANGUAGE", "auto"),  # type: ignore
            min_tokens=min_tokens,
            max_tokens=max_tokens,
            llm_provider=os.getenv("DOCS_CHUNKER_LLM_PROVIDER", "local"),  # type: ignore
            openai_api_key=os.getenv("DOCS_CHUNKER_OPENAI_API_KEY"),
            local_model=os.getenv("DOCS_CHUNKER_LOCAL_MODEL", "llama3.1:8b"),
        )


settings = Settings.from_env()
