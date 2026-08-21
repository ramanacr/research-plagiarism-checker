"""
Exact and rare phrase retrieval channel using inverted shingle indexes.
"""

from typing import List, Dict, Any, Optional
from src.plagiarism.documents.models import Passage
from src.plagiarism.indexing.lexical.lsh import PersistentLexicalIndex
from src.plagiarism.indexing.lexical.shingles import generate_shingle_strings


class ExactPhraseRetriever:
    """
    Retrieves candidates having exact verbatim phrase matches.
    """

    def __init__(self, lexical_index: PersistentLexicalIndex, top_k: int = 20):
        self.lexical_index = lexical_index
        self.top_k = top_k

    def retrieve_candidates(self, query_passage: Passage, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Queries inverted index for exact matching shingle sequences.
        """
        k = top_k or self.top_k
        shingles = generate_shingle_strings(query_passage.normalized_text, k=self.lexical_index.shingle_size)
        if not shingles:
            return []

        counts: Dict[str, int] = {}
        for s in shingles:
            pids = self.lexical_index.inverted_index.get(s, set())
            for pid in pids:
                counts[pid] = counts.get(pid, 0) + 1

        results = []
        for pid, count in counts.items():
            overlap_ratio = count / len(shingles)
            if overlap_ratio >= 0.20 or count >= 3:
                results.append({
                    "query_passage_id": query_passage.passage_id,
                    "source_passage_id": pid,
                    "document_id": self.lexical_index.passage_doc_map.get(pid, ""),
                    "channel": "exact",
                    "exact_score": round(overlap_ratio, 4),
                    "matched_shingles": count,
                    "metadata": self.lexical_index.passage_metadata.get(pid, {}),
                })

        results.sort(key=lambda x: x["exact_score"], reverse=True)
        return results[:k]
