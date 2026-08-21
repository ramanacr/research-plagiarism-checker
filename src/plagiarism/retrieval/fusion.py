"""
Hybrid candidate retrieval and multi-channel fusion pipeline.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Any
import numpy as np

from src.plagiarism.documents.models import Passage
from src.plagiarism.retrieval.lexical import LexicalRetriever
from src.plagiarism.retrieval.semantic import SemanticRetriever
from src.plagiarism.retrieval.exact import ExactPhraseRetriever


@dataclass
class CandidateHit:
    query_passage_id: str
    source_passage_id: str
    document_id: str
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    exact_score: float = 0.0
    fusion_score: float = 0.0
    channels: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_passage_id": self.query_passage_id,
            "source_passage_id": self.source_passage_id,
            "document_id": self.document_id,
            "lexical_score": self.lexical_score,
            "semantic_score": self.semantic_score,
            "exact_score": self.exact_score,
            "fusion_score": self.fusion_score,
            "channels": self.channels,
            "metadata": self.metadata,
        }


class HybridRetriever:
    """
    Fuses candidate retrievals from lexical, semantic, and exact phrase channels.
    Applies Reciprocal Rank Fusion (RRF) and deduplication.
    """

    def __init__(
        self,
        lexical_retriever: Optional[LexicalRetriever] = None,
        semantic_retriever: Optional[SemanticRetriever] = None,
        exact_retriever: Optional[ExactPhraseRetriever] = None,
        top_k: int = 40,
        rrf_k: int = 60,
    ):
        self.lexical_retriever = lexical_retriever
        self.semantic_retriever = semantic_retriever
        self.exact_retriever = exact_retriever
        self.top_k = top_k
        self.rrf_k = rrf_k

    def retrieve(
        self,
        query_passage: Passage,
        query_vector: Optional[np.ndarray] = None,
        top_k: Optional[int] = None,
    ) -> List[CandidateHit]:
        """
        Runs all configured retrieval channels for query_passage and fuses the results.
        """
        k = top_k or self.top_k
        candidates_by_source: Dict[str, CandidateHit] = {}
        channel_ranks: Dict[str, Dict[str, int]] = {}

        # 1. Lexical retrieval
        if self.lexical_retriever:
            lex_results = self.lexical_retriever.retrieve_candidates(query_passage)
            channel_ranks["lexical"] = {}
            for rank, r in enumerate(lex_results, start=1):
                pid = r["source_passage_id"]
                channel_ranks["lexical"][pid] = rank
                if pid not in candidates_by_source:
                    candidates_by_source[pid] = CandidateHit(
                        query_passage_id=query_passage.passage_id,
                        source_passage_id=pid,
                        document_id=r["document_id"],
                        lexical_score=r["lexical_score"],
                        channels=["lexical"],
                        metadata=r.get("metadata", {}),
                    )
                else:
                    candidates_by_source[pid].lexical_score = max(
                        candidates_by_source[pid].lexical_score, r["lexical_score"]
                    )
                    if "lexical" not in candidates_by_source[pid].channels:
                        candidates_by_source[pid].channels.append("lexical")

        # 2. Semantic retrieval
        if self.semantic_retriever:
            sem_results = self.semantic_retriever.retrieve_candidates(query_passage, query_vector=query_vector)
            channel_ranks["semantic"] = {}
            for rank, r in enumerate(sem_results, start=1):
                pid = r["source_passage_id"]
                channel_ranks["semantic"][pid] = rank
                if pid not in candidates_by_source:
                    candidates_by_source[pid] = CandidateHit(
                        query_passage_id=query_passage.passage_id,
                        source_passage_id=pid,
                        document_id=r["document_id"],
                        semantic_score=r["semantic_score"],
                        channels=["semantic"],
                        metadata=r.get("metadata", {}),
                    )
                else:
                    candidates_by_source[pid].semantic_score = max(
                        candidates_by_source[pid].semantic_score, r["semantic_score"]
                    )
                    if "semantic" not in candidates_by_source[pid].channels:
                        candidates_by_source[pid].channels.append("semantic")

        # 3. Exact retrieval
        if self.exact_retriever:
            exact_results = self.exact_retriever.retrieve_candidates(query_passage)
            channel_ranks["exact"] = {}
            for rank, r in enumerate(exact_results, start=1):
                pid = r["source_passage_id"]
                channel_ranks["exact"][pid] = rank
                if pid not in candidates_by_source:
                    candidates_by_source[pid] = CandidateHit(
                        query_passage_id=query_passage.passage_id,
                        source_passage_id=pid,
                        document_id=r["document_id"],
                        exact_score=r["exact_score"],
                        channels=["exact"],
                        metadata=r.get("metadata", {}),
                    )
                else:
                    candidates_by_source[pid].exact_score = max(
                        candidates_by_source[pid].exact_score, r["exact_score"]
                    )
                    if "exact" not in candidates_by_source[pid].channels:
                        candidates_by_source[pid].channels.append("exact")

        # Compute Fusion Score: Reciprocal Rank Fusion + Raw Score Weighting
        fused_hits: List[CandidateHit] = []
        for pid, hit in candidates_by_source.items():
            rrf_score = 0.0
            for channel, ranks in channel_ranks.items():
                if pid in ranks:
                    rrf_score += 1.0 / (self.rrf_k + ranks[pid])

            # Weighted linear boost
            raw_boost = (
                0.40 * hit.semantic_score +
                0.35 * hit.lexical_score +
                0.25 * hit.exact_score
            )
            hit.fusion_score = round(rrf_score * 10.0 + raw_boost, 4)
            fused_hits.append(hit)

        fused_hits.sort(key=lambda h: h.fusion_score, reverse=True)
        return fused_hits[:k]

    @staticmethod
    def compute_recall_at_k(
        ground_truth: Dict[str, Set[str]],
        retrieved: Dict[str, List[CandidateHit]],
        k: int = 10,
    ) -> float:
        """
        Computes Mean Recall@K across queries.
        ground_truth: query_id -> set of true positive source_passage_ids
        retrieved: query_id -> list of CandidateHit
        """
        if not ground_truth:
            return 0.0

        recalls = []
        for qid, true_pids in ground_truth.items():
            if not true_pids:
                continue
            hits = retrieved.get(qid, [])[:k]
            retrieved_pids = {h.source_passage_id for h in hits}
            matched = true_pids.intersection(retrieved_pids)
            recalls.append(len(matched) / len(true_pids))

        return float(np.mean(recalls)) if recalls else 0.0
