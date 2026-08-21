"""
Retrieval package for lexical, semantic, exact, and hybrid candidate fusion.
"""

from src.plagiarism.retrieval.lexical import LexicalRetriever
from src.plagiarism.retrieval.semantic import SemanticRetriever
from src.plagiarism.retrieval.exact import ExactPhraseRetriever
from src.plagiarism.retrieval.fusion import CandidateHit, HybridRetriever

__all__ = [
    "LexicalRetriever",
    "SemanticRetriever",
    "ExactPhraseRetriever",
    "CandidateHit",
    "HybridRetriever",
]
