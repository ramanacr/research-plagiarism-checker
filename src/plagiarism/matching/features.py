"""
Multi-signal feature extraction and passage aggregation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Any
import numpy as np

from src.plagiarism.documents.models import Passage
from src.plagiarism.indexing.lexical.shingles import (
    generate_shingle_strings,
    compute_shingle_containment,
    compute_shingle_jaccard,
)
from src.plagiarism.matching.exact import compute_exact_token_overlap, find_longest_common_phrase
from src.plagiarism.matching.lexical import (
    compute_token_jaccard,
    compute_token_containment,
    compute_edit_similarity,
)
from src.plagiarism.matching.semantic import compute_semantic_score
from src.plagiarism.indexing.vector.embedder import EmbeddingService


@dataclass
class MatchFeatures:
    exact_overlap: float
    longest_copied_phrase: str
    longest_copied_tokens: int
    shingle_containment: float
    jaccard_similarity: float
    edit_similarity: float
    semantic_similarity: float
    matched_token_count: int
    query_token_count: int
    source_token_count: int
    matching_phrases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exact_overlap": self.exact_overlap,
            "longest_copied_phrase": self.longest_copied_phrase,
            "longest_copied_tokens": self.longest_copied_tokens,
            "shingle_containment": self.shingle_containment,
            "jaccard_similarity": self.jaccard_similarity,
            "edit_similarity": self.edit_similarity,
            "semantic_similarity": self.semantic_similarity,
            "matched_token_count": self.matched_token_count,
            "query_token_count": self.query_token_count,
            "source_token_count": self.source_token_count,
            "matching_phrases": self.matching_phrases,
        }


class MatchFeatureExtractor:
    """
    Extracts multi-signal matching features for a candidate passage pair.
    """

    def __init__(self, embedder: Optional[EmbeddingService] = None, shingle_size: int = 5):
        self.embedder = embedder
        self.shingle_size = shingle_size

    def extract_features(
        self,
        query_passage: Passage,
        source_passage: Passage,
        query_vector: Optional[np.ndarray] = None,
        source_vector: Optional[np.ndarray] = None,
    ) -> MatchFeatures:
        q_text = query_passage.normalized_text
        s_text = source_passage.normalized_text

        # 1. Exact overlap & longest contiguous sequence
        overlap_ratio, matched_tokens, phrases = compute_exact_token_overlap(q_text, s_text)
        longest_phrase, longest_len = find_longest_common_phrase(q_text, s_text)

        # 2. Shingles
        q_shingles = generate_shingle_strings(q_text, k=self.shingle_size)
        s_shingles = generate_shingle_strings(s_text, k=self.shingle_size)
        shingle_containment = compute_shingle_containment(q_shingles, s_shingles)

        # 3. Lexical Jaccard & Edit similarity
        jaccard = compute_token_jaccard(q_text, s_text)
        edit_sim = compute_edit_similarity(q_text, s_text)

        # 4. Semantic similarity
        sem_score = 0.0
        if self.embedder is not None:
            sem_score = compute_semantic_score(
                query_text=q_text,
                source_text=s_text,
                embedder=self.embedder,
                query_vector=query_vector,
                source_vector=source_vector,
            )
        elif query_vector is not None and source_vector is not None:
            sem_score = float(np.dot(query_vector, source_vector))

        return MatchFeatures(
            exact_overlap=round(overlap_ratio, 4),
            longest_copied_phrase=longest_phrase,
            longest_copied_tokens=longest_len,
            shingle_containment=round(shingle_containment, 4),
            jaccard_similarity=round(jaccard, 4),
            edit_similarity=round(edit_sim, 4),
            semantic_similarity=round(sem_score, 4),
            matched_token_count=matched_tokens,
            query_token_count=query_passage.token_count,
            source_token_count=source_passage.token_count,
            matching_phrases=phrases,
        )


class PassageAggregator:
    """
    Merges adjacent matching query and source passages into unified evidence spans.
    """

    @staticmethod
    def aggregate_matches(
        raw_matches: List[Dict[str, Any]],
        max_passage_gap: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Groups pairwise passage matches by document and merges consecutive passages.
        """
        if not raw_matches:
            return []

        # Sort matches by document_id and query start_offset
        sorted_matches = sorted(
            raw_matches,
            key=lambda m: (
                m.get("source_document_id", ""),
                m.get("query_span", {}).get("start", 0),
            ),
        )

        aggregated: List[Dict[str, Any]] = []

        for m in sorted_matches:
            if not aggregated:
                aggregated.append(dict(m))
                continue

            last = aggregated[-1]
            same_doc = last.get("source_document_id") == m.get("source_document_id")
            
            last_end = last.get("query_span", {}).get("end", 0)
            curr_start = m.get("query_span", {}).get("start", 0)

            # Check if adjacent or overlapping
            if same_doc and (curr_start <= last_end + 100):
                # Merge spans
                last["query_span"]["end"] = max(last["query_span"]["end"], m["query_span"]["end"])
                
                # Combine matching phrases
                last_phrases = set(last.get("evidence", {}).get("matching_phrases", []))
                new_phrases = set(m.get("evidence", {}).get("matching_phrases", []))
                combined_phrases = list(last_phrases.union(new_phrases))
                
                if "evidence" in last:
                    last["evidence"]["matching_phrases"] = combined_phrases
                    # Maximize features
                    for feat in ["exact_overlap", "shingle_containment", "semantic_similarity"]:
                        if feat in m.get("evidence", {}):
                            last["evidence"][feat] = max(
                                last["evidence"].get(feat, 0.0),
                                m["evidence"].get(feat, 0.0),
                            )
            else:
                aggregated.append(dict(m))

        return aggregated
