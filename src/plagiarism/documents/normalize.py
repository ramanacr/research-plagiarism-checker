"""
Text normalization utilities with offset preservation.
"""

import unicodedata
import re
from typing import List, Tuple, Dict, Any


def normalize_unicode(text: str) -> str:
    """Applies NFKC Unicode normalization."""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text)


def normalize_whitespace(text: str) -> str:
    """Replaces sequences of whitespace characters with a single space."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def normalize_for_lexical(text: str) -> str:
    """
    Normalizes text for lexical matching:
    - Unicode NFKC
    - Lowercase
    - Punctuation removal/simplification
    - Whitespace normalization
    """
    if not text:
        return ""
    norm = normalize_unicode(text).lower()
    # Replace non-alphanumeric chars (except single spaces) with spaces
    norm = re.sub(r"[^\w\s]", " ", norm)
    return normalize_whitespace(norm)


def tokenize_words(text: str) -> List[str]:
    """Tokenizes text into lowercase word tokens."""
    if not text:
        return []
    return re.findall(r"\b\w+\b", text.lower())


def tokenize_with_spans(text: str) -> List[Tuple[str, int, int]]:
    """
    Tokenizes text into (token, start_char, end_char) tuples
    preserving exact character offsets against the input text.
    """
    if not text:
        return []
    tokens = []
    for match in re.finditer(r"\b\w+\b", text):
        tokens.append((match.group().lower(), match.start(), match.end()))
    return tokens


class TextOffsetMapper:
    """
    Maps positions from normalized or transformed text back to the original raw text.
    """

    def __init__(self, raw_text: str):
        self.raw_text = raw_text

    def find_span(self, query_phrase: str, search_start: int = 0) -> Tuple[int, int]:
        """
        Finds exact or whitespace-tolerant character bounds of query_phrase in raw_text.
        Returns (start_idx, end_idx) or (-1, -1).
        """
        if not query_phrase or not self.raw_text:
            return -1, -1

        # Direct search
        idx = self.raw_text.lower().find(query_phrase.lower(), search_start)
        if idx != -1:
            return idx, idx + len(query_phrase)

        # Regex flexible whitespace search
        words = re.findall(r"\b\w+\b", query_phrase.lower())
        if not words:
            return -1, -1

        pattern = r"\b" + r"\s+".join(re.escape(w) for w in words) + r"\b"
        match = re.search(pattern, self.raw_text[search_start:], re.IGNORECASE)
        if match:
            return search_start + match.start(), search_start + match.end()

        return -1, -1
