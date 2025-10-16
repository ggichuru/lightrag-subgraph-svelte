from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # API configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ])

    # LightRAG configuration
    LIGHTRAG_WORKING_DIR: str = "./lightrag_storage"
    LIGHTRAG_MODEL: str = "gpt-4o-mini"
    LIGHTRAG_MAX_ASYNC: int = 4
    LIGHTRAG_MAX_TOKENS: int = 32_000
    MAX_PARALLEL_INSERT: int = 4

    # OpenAI configuration (required when using OpenAI-powered LightRAG)
    OPENAI_API_KEY: str
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"
    OPENAI_EMBEDDING_DIM: int = 3072

    # Graph configuration
    MAX_GRAPH_NODES: int = 100
    MAX_HOPS: int = 2
    TEMPORAL_DECAY_RATE: float = 0.95
    ENTITY_FREQUENCY_WEIGHT: float = 0.3
    RECENCY_WEIGHT: float = 0.2
    CENTRALITY_WEIGHT: float = 0.3
    FOCAL_WEIGHT: float = 0.2

    # Document ingestion
    CORPUS_DIR: str = "./data/corpus"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    @property
    def corpus_path(self) -> Path:
        return Path(self.CORPUS_DIR).resolve()

    @property
    def lightrag_working_path(self) -> Path:
        return Path(self.LIGHTRAG_WORKING_DIR).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""

    return Settings()


__all__ = ["Settings", "get_settings"]
