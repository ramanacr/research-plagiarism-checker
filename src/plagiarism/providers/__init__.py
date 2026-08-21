"""
Providers package for scholarly content retrieval.
"""

from src.plagiarism.providers.base import (
    ScholarlyContentProvider,
    ProviderCapabilities,
    ProviderHealth,
    SourceRecord,
    SourceDocument,
)
from src.plagiarism.providers.pubmed import PubMedProvider
from src.plagiarism.providers.europe_pmc import EuropePMCProvider
from src.plagiarism.providers.registry import ProviderRegistry, create_default_registry

__all__ = [
    "ScholarlyContentProvider",
    "ProviderCapabilities",
    "ProviderHealth",
    "SourceRecord",
    "SourceDocument",
    "PubMedProvider",
    "EuropePMCProvider",
    "ProviderRegistry",
    "create_default_registry",
]
