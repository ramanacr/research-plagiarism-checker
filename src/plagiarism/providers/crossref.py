"""
Crossref scholarly content provider for DOI resolution and metadata discovery.
"""

import time
import re
from typing import List, Optional, Dict, Any
import httpx

from src.plagiarism.providers.base import (
    ScholarlyContentProvider,
    ProviderCapabilities,
    ProviderHealth,
    SourceRecord,
    SourceDocument,
)


class CrossrefProvider(ScholarlyContentProvider):
    """
    Provider for Crossref REST API.
    Provides DOI resolution, bibliographic metadata, and available abstracts.
    """

    def __init__(
        self,
        base_url: str = "https://api.crossref.org/works",
        timeout: float = 12.0,
        mailto: str = "research@example.com",
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.mailto = mailto
        self._capabilities = ProviderCapabilities(
            search=True,
            metadata=True,
            abstracts=True,
            full_text=False,
            bulk_ingest=False,
        )

    @property
    def name(self) -> str:
        return "crossref"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def _get_headers(self) -> Dict[str, str]:
        return {"User-Agent": f"ConfidentialPlagiarismChecker/2.0 (mailto:{self.mailto})"}

    async def search(self, query: str, limit: int = 20) -> List[SourceRecord]:
        """Queries Crossref works search."""
        if not query.strip():
            return []

        params = {
            "query": query,
            "rows": limit,
            "select": "DOI,title,abstract,author,published-print,published-online,container-title",
        }

        async with httpx.AsyncClient(timeout=self.timeout, headers=self._get_headers()) as client:
            try:
                resp = await client.get(self.base_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                items = data.get("message", {}).get("items", [])
                return self.parse_items(items)
            except Exception:
                return []

    async def get_metadata(self, source_id: str) -> Optional[SourceRecord]:
        """Fetches metadata for a specific DOI."""
        clean_doi = source_id.strip()
        if not clean_doi:
            return None

        url = f"{self.base_url}/{clean_doi}"
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._get_headers()) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                item = data.get("message", {})
                records = self.parse_items([item])
                return records[0] if records else None
            except Exception:
                return None

    async def get_full_text(self, source_id: str) -> Optional[SourceDocument]:
        rec = await self.get_metadata(source_id)
        if not rec:
            return None
        return SourceDocument(
            document_id=f"crossref:{rec.source_id}",
            provider=self.name,
            provider_source_id=rec.source_id,
            doi=rec.doi,
            title=rec.title,
            abstract=rec.abstract,
            authors=rec.authors,
            journal=rec.journal,
            publication_year=rec.publication_year,
            rights_id="abstract_fair_use",
            full_text_available=False,
        )

    async def health_check(self) -> ProviderHealth:
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0, headers=self._get_headers()) as client:
                resp = await client.get("https://api.crossref.org/heartbeat")
                latency = (time.time() - start) * 1000
                return ProviderHealth(is_healthy=resp.status_code == 200, provider_name=self.name, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, provider_name=self.name, error_message=str(e))

    def parse_items(self, items: List[Dict[str, Any]]) -> List[SourceRecord]:
        records = []
        for it in items:
            doi = it.get("DOI", "").strip()
            title_list = it.get("title", [])
            title = title_list[0].strip() if title_list else ""
            if not title:
                continue

            # Authors
            authors = []
            for a in it.get("author", []):
                given = a.get("given", "")
                family = a.get("family", "")
                name = f"{given} {family}".strip()
                if name:
                    authors.append(name)

            # Abstract (often JATS XML in Crossref)
            raw_abstract = it.get("abstract", "")
            abstract = re.sub(r"<[^>]+>", "", raw_abstract).strip() if raw_abstract else None

            # Year
            pub_year = None
            date_parts = it.get("published-print", {}).get("date-parts", []) or it.get("published-online", {}).get("date-parts", [])
            if date_parts and len(date_parts[0]) > 0:
                try:
                    pub_year = int(date_parts[0][0])
                except (ValueError, TypeError):
                    pass

            journal_list = it.get("container-title", [])
            journal = journal_list[0].strip() if journal_list else None

            records.append(
                SourceRecord(
                    provider=self.name,
                    source_id=doi or title[:40],
                    doi=doi if doi else None,
                    title=title,
                    abstract=abstract,
                    authors=tuple(authors),
                    publication_year=pub_year,
                    journal=journal,
                    url=f"https://doi.org/{doi}" if doi else None,
                )
            )
        return records
