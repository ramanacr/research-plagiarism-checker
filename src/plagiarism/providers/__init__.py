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
from src.plagiarism.providers.pmc_oa import PMCOAProvider
from src.plagiarism.providers.crossref import CrossrefProvider
from src.plagiarism.providers.openalex import OpenAlexProvider
from src.plagiarism.providers.arxiv import ArXivProvider
from src.plagiarism.providers.unpaywall import UnpaywallProvider
from src.plagiarism.providers.registry import ProviderRegistry, create_default_registry

__all__ = [
    "ScholarlyContentProvider",
    "ProviderCapabilities",
    "ProviderHealth",
    "SourceRecord",
    "SourceDocument",
    "PubMedProvider",
    "EuropePMCProvider",
    "PMCOAProvider",
    "CrossrefProvider",
    "OpenAlexProvider",
    "ArXivProvider",
    "UnpaywallProvider",
    "ProviderRegistry",
    "create_default_registry",
]
