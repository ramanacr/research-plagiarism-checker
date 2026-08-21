"""
Semantic feature calculation for detailed passage matching.
"""

from typing import Optional
import numpy as np
from src.plagiarism.indexing.vector.embedder import EmbeddingService


def compute_semantic_score(
    query_text: str,
    source_text: str,
    embedder: EmbeddingService,
    query_vector: Optional[np.ndarray] = None,
    source_vector: Optional[np.ndarray] = None,
) -> float:
    """
    Computes dense semantic cosine similarity between query and source passages.
    """
    q_vec = query_vector
    if q_vec is None:
        q_vecs = embedder.encode_texts([query_text])
        q_vec = q_vecs[0] if len(q_vecs) > 0 else np.zeros(embedder.dimension, dtype=np.float32)

    s_vec = source_vector
    if s_vec is None:
        s_vecs = embedder.encode_texts([source_text])
        s_vec = s_vecs[0] if len(s_vecs) > 0 else np.zeros(embedder.dimension, dtype=np.float32)

    return embedder.compute_cosine_similarity(q_vec, s_vec)
