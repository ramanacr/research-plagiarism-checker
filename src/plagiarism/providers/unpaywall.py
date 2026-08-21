"""
Unpaywall open access location resolver provider.
"""

import time
from typing import List, Optional, Dict, Any
import httpx

from src.plagiarism.providers.base import (
    ScholarlyContentProvider,
    ProviderCapabilities,
    ProviderHealth,
    SourceRecord,
    SourceDocument,
)


class UnpaywallProvider(ScholarlyContentProvider):
    """
    Provider for Unpaywall OA resolution API.
    Resolves legal open access full text locations for DOIs.
    """

    def __init__(
        self,
        base_url: str = "https://api.unpaywall.org/v2",
        email: str = "research@example.com",
        timeout: float = 10.0,
    ):
        self.base_url = base_url
        self.email = email
        self.timeout = timeout
        self._capabilities = ProviderCapabilities(
            search=False,
            metadata=True,
            abstracts=False,
            full_text=True,
            bulk_ingest=False,
        )

    @property
    def name(self) -> str:
        return "unpaywall"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def search(self, query: str, limit: int = 20) -> List[SourceRecord]:
        """Unpaywall does not support general keyword search."""
        return []

    async def get_metadata(self, source_id: str) -> Optional[SourceRecord]:
        """Looks up DOI in Unpaywall."""
        clean_doi = source_id.strip()
        if not clean_doi:
            return None

        url = f"{self.base_url}/{clean_doi}"
        params = {"email": self.email}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                
                title = data.get("title", "")
                doi = data.get("doi", clean_doi)
                year = data.get("year")
                journal = data.get("journal_name")
                is_oa = data.get("is_oa", False)
                best_oa = data.get("best_oa_location", {}) or {}
                oa_url = best_oa.get("url_for_pdf") or best_oa.get("url")

                return SourceRecord(
                    provider=self.name,
                    source_id=doi,
                    doi=doi,
                    title=title,
                    publication_year=year,
                    journal=journal,
                    url=oa_url,
                    extra_metadata={"is_oa": is_oa, "best_oa_location": best_oa},
                )
            except Exception:
                return None

    async def get_full_text(self, source_id: str) -> Optional[SourceDocument]:
        rec = await self.get_metadata(source_id)
        if not rec or not rec.extra_metadata.get("is_oa"):
            return None

        return SourceDocument(
            document_id=f"unpaywall:{rec.source_id}",
            provider=self.name,
            provider_source_id=rec.source_id,
            doi=rec.doi,
            title=rec.title,
            rights_id="cc_by",
            full_text_available=True,
            extra_metadata=rec.extra_metadata,
        )

    async def health_check(self) -> ProviderHealth:
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/10.1038/nature12373", params={"email": self.email})
                latency = (time.time() - start) * 1000
                return ProviderHealth(is_healthy=resp.status_code == 200, provider_name=self.name, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, provider_name=self.name, error_message=str(e))
