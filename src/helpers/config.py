from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache


class Settings(BaseSettings):

    # ── Application ────────────────────────────────────────────────────────────
    APP_NAME: str
    APP_VERSION: str

    # ── Database ───────────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── Security & Authentication ──────────────────────────────────────────────
    JWT_SECRET_KEY: str 
    JWT_ALGORITHM: str 
    ACCESS_TOKEN_EXPIRE_MINUTES: int 

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

    # ── LLM Generation (OpenAI-compatible API) ────────────────────────────────
    GENERATION_BACKEND: str = None
    GENERATION_API_KEY: str = None
    GENERATION_API_URL: str = None
    GENERATION_MODEL_ID: str = None
    GENERATION_MAX_TOKENS: int = None
    GENERATION_TEMPERATURE: float = None
    INPUT_DAFAULT_MAX_CHARACTERS: int = None
    # ── Template Configs ───────────────────────────────────────────────────────
    PRIMARY_LANG: str
    DEFAULT_LANG: str

    class Config:
        import os
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


@lru_cache()
def get_settings() -> Settings:
    # Type: Main function
    return Settings()
