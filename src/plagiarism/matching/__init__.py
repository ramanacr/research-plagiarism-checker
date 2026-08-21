"""
Matching package for multi-signal feature comparison and passage aggregation.
"""

from src.plagiarism.matching.exact import compute_exact_token_overlap, find_longest_common_phrase
from src.plagiarism.matching.lexical import (
    compute_token_jaccard,
    compute_token_containment,
    compute_edit_similarity,
)
from src.plagiarism.matching.semantic import compute_semantic_score
from src.plagiarism.matching.features import (
    MatchFeatures,
    MatchFeatureExtractor,
    PassageAggregator,
)

__all__ = [
    "compute_exact_token_overlap",
    "find_longest_common_phrase",
    "compute_token_jaccard",
    "compute_token_containment",
    "compute_edit_similarity",
    "compute_semantic_score",
    "MatchFeatures",
    "MatchFeatureExtractor",
    "PassageAggregator",
]
