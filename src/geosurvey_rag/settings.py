from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "GeoSurveyRAG")
    knowledge_dir: Path = Path(os.getenv("KNOWLEDGE_DIR", "data/knowledge"))
    index_dir: Path = Path(os.getenv("INDEX_DIR", "data/index"))
    top_k: int = int(os.getenv("TOP_K", "4"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "650"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    vector_backend: str = os.getenv("VECTOR_BACKEND", "json")
    dense_dim: int = int(os.getenv("DENSE_DIM", "384"))
    llm_provider: str = os.getenv("LLM_PROVIDER", "local")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


settings = Settings()
