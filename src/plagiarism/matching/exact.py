"""
Exact token overlap and longest common contiguous subsequence matching.
"""

from typing import List, Tuple, Dict, Set
from difflib import SequenceMatcher
from src.plagiarism.documents.normalize import tokenize_words


def find_longest_common_phrase(text1: str, text2: str) -> Tuple[str, int]:
    """
    Finds the longest contiguous sequence of matching words between text1 and text2.
    Returns (phrase_string, token_count).
    """
    words1 = tokenize_words(text1)
    words2 = tokenize_words(text2)

    if not words1 or not words2:
        return "", 0

    matcher = SequenceMatcher(None, words1, words2)
    match = matcher.find_longest_match(0, len(words1), 0, len(words2))

    if match.size == 0:
        return "", 0

    matched_words = words1[match.a : match.a + match.size]
    return " ".join(matched_words), match.size


def compute_exact_token_overlap(query_text: str, source_text: str) -> Tuple[float, int, List[str]]:
    """
    Computes exact verbatim word overlap ratio relative to query length.
    Returns (overlap_ratio, matched_token_count, matching_phrases).
    """
    words_q = tokenize_words(query_text)
    words_s = tokenize_words(source_text)

    if not words_q or not words_s:
        return 0.0, 0, []

    matcher = SequenceMatcher(None, words_q, words_s)
    matching_blocks = matcher.get_matching_blocks()

    total_matched_tokens = 0
    phrases = []

    for block in matching_blocks:
        if block.size >= 3:  # Only count sequences of 3 or more words
            phrase = " ".join(words_q[block.a : block.a + block.size])
            phrases.append(phrase)
            total_matched_tokens += block.size

    overlap_ratio = total_matched_tokens / len(words_q) if words_q else 0.0
    return min(1.0, round(overlap_ratio, 4)), total_matched_tokens, phrases
