"""
Semantic candidate retrieval channel using dense embeddings and VectorIndex.
"""

from typing import List, Dict, Any, Optional
import numpy as np

from src.plagiarism.documents.models import Passage
from src.plagiarism.indexing.vector.embedder import EmbeddingService
from src.plagiarism.indexing.vector.faiss_index import VectorIndex


class SemanticRetriever:
    """
    Retrieves candidate source passages using Sentence Transformer embeddings.
    """

    def __init__(
        self,
        embedder: EmbeddingService,
        vector_index: VectorIndex,
        top_k: int = 30,
        threshold: float = 0.50,
    ):
        self.embedder = embedder
        self.vector_index = vector_index
        self.top_k = top_k
        self.threshold = threshold

    def retrieve_candidates(
        self,
        query_passage: Passage,
        query_vector: Optional[np.ndarray] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top dense semantic candidates for query_passage.
        """
        k = top_k or self.top_k
        
        if query_vector is None:
            vecs = self.embedder.encode_texts([query_passage.normalized_text])
            if len(vecs) == 0:
                return []
            q_vec = vecs[0]
        else:
            q_vec = query_vector

        raw_results = self.vector_index.search(q_vec, top_k=k, threshold=self.threshold)

        candidates = []
        for r in raw_results:
            candidates.append({
                "query_passage_id": query_passage.passage_id,
                "source_passage_id": r["passage_id"],
                "document_id": r["document_id"],
                "channel": "semantic",
                "semantic_score": r["similarity"],
                "metadata": r.get("metadata", {}),
            })
        return candidates
