"""
Rights management package for copyright, licensing, and access policies.
"""

from src.plagiarism.rights.models import RightsRecord, RightsDecision
from src.plagiarism.rights.policies import STANDARD_POLICIES
from src.plagiarism.rights.resolver import RightsResolver

__all__ = [
    "RightsRecord",
    "RightsDecision",
    "STANDARD_POLICIES",
    "RightsResolver",
]
