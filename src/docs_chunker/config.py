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
        return cls(
            documents_dir=os.getenv("DOCS_CHUNKER_DOCUMENTS_DIR", "documents"),
            output_dir=os.getenv("DOCS_CHUNKER_OUTPUT_DIR", "output"),
            language=os.getenv("DOCS_CHUNKER_LANGUAGE", "auto"),  # type: ignore
            min_tokens=int(os.getenv("DOCS_CHUNKER_MIN_TOKENS", "200")),
            max_tokens=int(os.getenv("DOCS_CHUNKER_MAX_TOKENS", "1200")),
            llm_provider=os.getenv("DOCS_CHUNKER_LLM_PROVIDER", "local"),  # type: ignore
            openai_api_key=os.getenv("DOCS_CHUNKER_OPENAI_API_KEY"),
            local_model=os.getenv("DOCS_CHUNKER_LOCAL_MODEL", "llama3.1:8b"),
        )


settings = Settings.from_env()
