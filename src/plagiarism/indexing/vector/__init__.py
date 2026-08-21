"""
Vector indexing package for embedding generation and dense ANN search.
"""

from src.plagiarism.indexing.vector.embedder import EmbeddingService
from src.plagiarism.indexing.vector.faiss_index import VectorIndex
from src.plagiarism.indexing.vector.qdrant_index import QdrantVectorIndex

__all__ = [
    "EmbeddingService",
    "VectorIndex",
    "QdrantVectorIndex",
]
