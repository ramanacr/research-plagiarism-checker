"""
Lexical matching metrics: token Jaccard, containment, and edit similarity.
"""

from typing import Set, Tuple
from difflib import SequenceMatcher
from src.plagiarism.documents.normalize import tokenize_words
from src.plagiarism.indexing.lexical.shingles import (
    generate_shingle_strings,
    compute_shingle_containment,
    compute_shingle_jaccard,
)


def compute_token_jaccard(text1: str, text2: str) -> float:
    """Computes Jaccard similarity over unique word tokens."""
    tokens1 = set(tokenize_words(text1))
    tokens2 = set(tokenize_words(text2))
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return round(len(intersection) / len(union), 4) if union else 0.0


def compute_token_containment(query_text: str, source_text: str) -> float:
    """Computes containment of query word tokens in source: |T_q ∩ T_s| / |T_q|."""
    tokens_q = set(tokenize_words(query_text))
    tokens_s = set(tokenize_words(source_text))
    if not tokens_q:
        return 0.0
    intersection = tokens_q.intersection(tokens_s)
    return round(len(intersection) / len(tokens_q), 4)


def compute_edit_similarity(text1: str, text2: str) -> float:
    """
    Computes sequence edit similarity ratio over word tokens using SequenceMatcher.
    Returns float in [0.0, 1.0].
    """
    words1 = tokenize_words(text1)
    words2 = tokenize_words(text2)
    if not words1 or not words2:
        return 0.0
    matcher = SequenceMatcher(None, words1, words2)
    return round(matcher.ratio(), 4)
