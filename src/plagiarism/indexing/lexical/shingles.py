"""
Word shingle extraction and position mapping for lexical similarity.
"""

from typing import List, Set, Tuple, Dict, Any
from src.plagiarism.documents.normalize import tokenize_words


def generate_word_shingles(text: str, k: int = 5) -> Set[Tuple[str, ...]]:
    """
    Tokenizes text and returns unique k-word shingles (tuples of words).
    """
    tokens = tokenize_words(text)
    if len(tokens) < k:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def generate_shingle_strings(text: str, k: int = 5) -> Set[str]:
    """
    Returns string representations of k-word shingles ('word1 word2 word3 ...').
    """
    shingles = generate_word_shingles(text, k=k)
    return {" ".join(s) for s in shingles if s}


def generate_ordered_shingle_positions(tokens: List[str], k: int = 5) -> List[Tuple[Tuple[str, ...], int]]:
    """
    Returns list of (shingle_tuple, token_start_index) maintaining sequential order.
    """
    if len(tokens) < k:
        return [(tuple(tokens), 0)] if tokens else []
    return [(tuple(tokens[i : i + k]), i) for i in range(len(tokens) - k + 1)]


def compute_shingle_containment(query_shingles: Set[Any], source_shingles: Set[Any]) -> float:
    """
    Computes containment of query in source: |query ∩ source| / |query|.
    Returns float in [0.0, 1.0].
    """
    if not query_shingles:
        return 0.0
    if not source_shingles:
        return 0.0
    intersection = query_shingles.intersection(source_shingles)
    return len(intersection) / len(query_shingles)


def compute_shingle_jaccard(shingles1: Set[Any], shingles2: Set[Any]) -> float:
    """
    Computes Jaccard similarity: |s1 ∩ s2| / |s1 ∪ s2|.
    """
    if not shingles1 or not shingles2:
        return 0.0
    intersection = shingles1.intersection(shingles2)
    union = shingles1.union(shingles2)
    return len(intersection) / len(union) if union else 0.0
