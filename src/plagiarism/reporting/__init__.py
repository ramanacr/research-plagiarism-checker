"""
Reporting package for plagiarism analysis outputs.
"""

from src.plagiarism.reporting.models import (
    PlagiarismMatch,
    PlagiarismReport,
    MatchClass,
    MatchEvidence,
)
from src.plagiarism.reporting.builder import ReportBuilder

__all__ = [
    "PlagiarismMatch",
    "PlagiarismReport",
    "MatchClass",
    "MatchEvidence",
    "ReportBuilder",
]
