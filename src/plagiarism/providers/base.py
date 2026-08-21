"""
Base provider abstractions for scholarly content providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple


@dataclass(frozen=True)
class ProviderCapabilities:
    search: bool = True
    metadata: bool = True
    abstracts: bool = True
    full_text: bool = False
    bulk_ingest: bool = False


@dataclass(frozen=True)
class ProviderHealth:
    is_healthy: bool
    provider_name: str
    latency_ms: float = 0.0
    status_code: Optional[int] = None
    error_message: Optional[str] = None


@dataclass(frozen=True)
class SourceRecord:
    provider: str
    source_id: str
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    title: str = ""
    abstract: Optional[str] = None
    authors: Tuple[str, ...] = field(default_factory=tuple)
    publication_year: Optional[int] = None
    journal: Optional[str] = None
    language: str = "en"
    url: Optional[str] = None
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "source_id": self.source_id,
            "doi": self.doi,
            "pmid": self.pmid,
            "pmcid": self.pmcid,
            "title": self.title,
            "abstract": self.abstract,
            "authors": list(self.authors),
            "publication_year": self.publication_year,
            "journal": self.journal,
            "language": self.language,
            "url": self.url,
            "extra_metadata": self.extra_metadata,
        }


@dataclass(frozen=True)
class SourceDocument:
    document_id: str
    provider: str
    provider_source_id: str
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    title: str = ""
    abstract: Optional[str] = None
    full_text: Optional[str] = None
    authors: Tuple[str, ...] = field(default_factory=tuple)
    journal: Optional[str] = None
    publication_date: Optional[str] = None
    publication_year: Optional[int] = None
    language: str = "en"
    content_hash: str = ""
    rights_id: Optional[str] = None
    full_text_available: bool = False
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


class ScholarlyContentProvider(ABC):
    """Abstract base class for all scholarly and external content providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier of the provider."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Declared capabilities of this provider."""
        ...

    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> List[SourceRecord]:
        """Searches the provider with a query string or keywords."""
        ...

    @abstractmethod
    async def get_metadata(self, source_id: str) -> Optional[SourceRecord]:
        """Fetches metadata for a specific source record ID."""
        ...

    @abstractmethod
    async def get_full_text(self, source_id: str) -> Optional[SourceDocument]:
        """Fetches full text if legally permissible and available."""
        ...

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Checks provider connectivity and health."""
        ...

    # Synchronous helper methods for backward compatibility & synchronous callers
    def search_sync(self, query: str, limit: int = 20) -> List[SourceRecord]:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.search(query, limit)).result()
            return loop.run_until_complete(self.search(query, limit))
        except RuntimeError:
            return asyncio.run(self.search(query, limit))

    def get_metadata_sync(self, source_id: str) -> Optional[SourceRecord]:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.get_metadata(source_id)).result()
            return loop.run_until_complete(self.get_metadata(source_id))
        except RuntimeError:
            return asyncio.run(self.get_metadata(source_id))
