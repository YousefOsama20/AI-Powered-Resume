"""
EmbeddingController
───────────────────
Wraps sentence-transformers as a lazy singleton so the model is loaded
only once per process lifetime.

Model: configurable via EMBEDDING_MODEL_NAME (default all-MiniLM-L6-v2)
Output: L2-normalised 384-dim float vectors
"""

from __future__ import annotations

import logging
from typing import List

from sentence_transformers import SentenceTransformer

from .BaseController import BaseController

logger = logging.getLogger("uvicorn.error")


class EmbeddingController(BaseController):
    """Produces dense embeddings from plain-text strings."""

    # Class-level cache so the model is shared across all controller instances
    _model: SentenceTransformer | None = None

    def __init__(self):
        # Type: Sub-function
        super().__init__()
        self._ensure_model_loaded()

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _ensure_model_loaded(self) -> None:
        # Type: Sub-function
        """Load the sentence-transformer model once and cache it at class level."""
        if EmbeddingController._model is None:
            model_name = self.app_settings.EMBEDDING_MODEL_NAME
            logger.info(f"[EmbeddingController] Loading model: {model_name}")
            EmbeddingController._model = SentenceTransformer(model_name)
            logger.info("[EmbeddingController] Model ready.")

    @property
    def model(self) -> SentenceTransformer:
        # Type: Main function
        return EmbeddingController._model  # type: ignore[return-value]

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def embed_text(self, text: str) -> List[float]:
        # Type: Main function
        """
        Embed a single text string.

        Returns:
            A list of floats (L2-normalised, 384-dim for all-MiniLM-L6-v2).
        """
        if not text or not text.strip():
            return []
        vector = self.model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        # Type: Main function
        """
        Embed a batch of text strings.

        Args:
            texts: List of non-empty strings.

        Returns:
            List of embedding vectors in the same order as *texts*.
        """
        if not texts:
            return []

        batch_size = self.app_settings.EMBEDDING_BATCH_SIZE
        vectors = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vectors]
