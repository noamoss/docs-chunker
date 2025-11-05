from typing import Literal

from pydantic import BaseModel


class Settings(BaseModel):
    documents_dir: str = "/home/noam/docs-chunker/documents"
    output_dir: str = "/home/noam/docs-chunker/output"
    language: Literal["auto", "en", "he"] = "auto"
    min_tokens: int = 200
    max_tokens: int = 1200
    llm_provider: Literal["local", "openai"] = "local"
    openai_api_key: str | None = None
    local_model: str = "llama3.1:8b"


settings = Settings()
