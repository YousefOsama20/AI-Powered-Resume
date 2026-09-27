from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache


class Settings(BaseSettings):

    # ── Application ────────────────────────────────────────────────────────────
    APP_NAME: str
    APP_VERSION: str

    # ── API Keys (optional – not used by the local embedding pipeline) ─────────
    OPENAI_API_KEY: str = ""

    # ── File Upload Settings ───────────────────────────────────────────────────
    FILE_ALLOWED_TYPES: List[str]
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int

    # ── Vector DB (ChromaDB) ──────────────────────────────────────────────────
    VECTOR_DB_PATH: str
    VECTOR_DB_COLLECTION: str

    # ── Embedding Model (sentence-transformers) ───────────────────────────────
    EMBEDDING_MODEL_NAME: str
    EMBEDDING_BATCH_SIZE: int = 64

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
