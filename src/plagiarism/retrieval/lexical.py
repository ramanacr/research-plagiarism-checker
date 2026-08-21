"""
Lexical candidate retrieval channel using persistent MinHash and containment indexes.
"""

from typing import List, Dict, Set, Any, Optional
from src.plagiarism.documents.models import Passage
from src.plagiarism.indexing.lexical.lsh import PersistentLexicalIndex
from src.plagiarism.indexing.lexical.shingles import generate_shingle_strings


class LexicalRetriever:
    """
    Retrieves candidate source passages using shingle overlap and MinHash containment.
    """

    def __init__(self, lexical_index: PersistentLexicalIndex, top_k: int = 30, threshold: float = 0.15):
        self.lexical_index = lexical_index
        self.top_k = top_k
        self.threshold = threshold

    def retrieve_candidates(self, query_passage: Passage, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Queries the persistent lexical index for candidates matching query_passage.
        """
        k = top_k or self.top_k
        shingles = generate_shingle_strings(query_passage.normalized_text, k=self.lexical_index.shingle_size)
        if not shingles:
            return []

        raw_results = self.lexical_index.query_containment(shingles, top_k=k, threshold=self.threshold)
        
        candidates = []
        for r in raw_results:
            candidates.append({
                "query_passage_id": query_passage.passage_id,
                "source_passage_id": r["passage_id"],
                "document_id": r["document_id"],
                "channel": "lexical",
                "lexical_score": r["containment"],
                "jaccard_score": r["jaccard"],
                "metadata": r.get("metadata", {}),
            })
        return candidates
