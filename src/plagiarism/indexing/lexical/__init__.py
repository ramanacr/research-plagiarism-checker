"""
Lexical indexing package with shingles, MinHash, and persistent LSH.
"""

from src.plagiarism.indexing.lexical.shingles import (
    generate_word_shingles,
    generate_shingle_strings,
    generate_ordered_shingle_positions,
    compute_shingle_containment,
    compute_shingle_jaccard,
)
from src.plagiarism.indexing.lexical.minhash import MinHashGenerator
from src.plagiarism.indexing.lexical.lsh import PersistentLexicalIndex

__all__ = [
    "generate_word_shingles",
    "generate_shingle_strings",
    "generate_ordered_shingle_positions",
    "compute_shingle_containment",
    "compute_shingle_jaccard",
    "MinHashGenerator",
    "PersistentLexicalIndex",
]
