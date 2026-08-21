"""
Embedding service for batch vector generation and model versioning.
"""

from typing import List, Optional, Union, Any
import numpy as np
from src.plagiarism.config.settings import SemanticSettings


class EmbeddingService:
    """
    Service for generating dense sentence/passage embeddings.
    Uses lazy loading so instantiation does not block module imports.
    """

    def __init__(self, settings: Optional[SemanticSettings] = None):
        self.settings = settings or SemanticSettings()
        self.model_name = self.settings.model_name
        self.model_revision = self.settings.model_revision
        self.batch_size = self.settings.batch_size
        self._model = None
        self._dimension: Optional[int] = None

    @property
    def model(self):
        """Lazy loads SentenceTransformer model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        """Returns embedding vector dimension."""
        if self._dimension is None:
            # Most common dimension for all-mpnet-base-v2 is 768
            if "mpnet" in self.model_name.lower():
                self._dimension = 768
            else:
                sample = self.encode_texts(["test"])
                self._dimension = sample.shape[1]
        return self._dimension

    def encode_texts(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
    ) -> np.ndarray:
        """
        Encodes a list of text strings into normalized NumPy vectors.
        """
        if not texts:
            dim = self.dimension
            return np.empty((0, dim), dtype=np.float32)

        bs = batch_size or self.batch_size
        embeddings = self.model.encode(
            texts,
            batch_size=bs,
            normalize_embeddings=normalize_embeddings,
            convert_to_numpy=True,
            show_progress_bar=show_progress_bar,
        )
        return np.asarray(embeddings, dtype=np.float32)

    def encode_passages(
        self,
        passages: List[Any],
        batch_size: Optional[int] = None,
        normalize_embeddings: bool = True,
    ) -> np.ndarray:
        """Encodes a list of Passage objects."""
        texts = [p.normalized_text if hasattr(p, "normalized_text") else str(p) for p in passages]
        return self.encode_texts(
            texts,
            batch_size=batch_size,
            normalize_embeddings=normalize_embeddings,
        )

    def compute_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Computes cosine similarity between two 1D normalized vectors."""
        dot = float(np.dot(vec1, vec2))
        return max(0.0, min(1.0, dot))
