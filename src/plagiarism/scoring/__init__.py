"""
Scoring and classification package for evidence-based plagiarism assessment.
"""

from src.plagiarism.scoring.models import (
    MatchClass,
    MatchEvidence,
    PlagiarismMatch,
    PlagiarismReport,
)
from src.plagiarism.scoring.classifier import EvidenceClassifier
from src.plagiarism.scoring.aggregate import ScoreAggregator, merge_spans
from src.plagiarism.scoring.citations import CitationAnalyzer, CitationContext
from src.plagiarism.scoring.boilerplate import BoilerplateDetector

__all__ = [
    "MatchClass",
    "MatchEvidence",
    "PlagiarismMatch",
    "PlagiarismReport",
    "EvidenceClassifier",
    "ScoreAggregator",
    "merge_spans",
    "CitationAnalyzer",
    "CitationContext",
    "BoilerplateDetector",
]
