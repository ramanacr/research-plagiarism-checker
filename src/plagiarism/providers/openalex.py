"""
OpenAlex scholarly content provider for open scholarly works discovery.
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


class OpenAlexProvider(ScholarlyContentProvider):
    """
    Provider for OpenAlex API.
    Provides vast scholarly discovery, reconstructed abstracts, and OA links.
    """

    def __init__(
        self,
        base_url: str = "https://api.openalex.org/works",
        timeout: float = 12.0,
        email: str = "research@example.com",
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.email = email
        self._capabilities = ProviderCapabilities(
            search=True,
            metadata=True,
            abstracts=True,
            full_text=False,
            bulk_ingest=True,
        )

    @property
    def name(self) -> str:
        return "openalex"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def _get_headers(self) -> Dict[str, str]:
        return {"User-Agent": f"ConfidentialPlagiarismChecker/2.0 (mailto:{self.email})"}

    async def search(self, query: str, limit: int = 20) -> List[SourceRecord]:
        """Searches OpenAlex works."""
        if not query.strip():
            return []

        params = {
            "search": query,
            "per_page": limit,
        }

        async with httpx.AsyncClient(timeout=self.timeout, headers=self._get_headers()) as client:
            try:
                resp = await client.get(self.base_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                return self.parse_works(results)
            except Exception:
                return []

    async def get_metadata(self, source_id: str) -> Optional[SourceRecord]:
        clean_id = source_id.strip()
        if not clean_id:
            return None

        url = f"{self.base_url}/{clean_id}"
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._get_headers()) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                work = resp.json()
                records = self.parse_works([work])
                return records[0] if records else None
            except Exception:
                return None

    async def get_full_text(self, source_id: str) -> Optional[SourceDocument]:
        rec = await self.get_metadata(source_id)
        if not rec:
            return None
        return SourceDocument(
            document_id=f"openalex:{rec.source_id}",
            provider=self.name,
            provider_source_id=rec.source_id,
            doi=rec.doi,
            title=rec.title,
            abstract=rec.abstract,
            authors=rec.authors,
            publication_year=rec.publication_year,
            rights_id="cc_by" if rec.extra_metadata.get("is_oa") else "abstract_fair_use",
            full_text_available=False,
        )

    async def health_check(self) -> ProviderHealth:
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0, headers=self._get_headers()) as client:
                resp = await client.get("https://api.openalex.org/works?per_page=1")
                latency = (time.time() - start) * 1000
                return ProviderHealth(is_healthy=resp.status_code == 200, provider_name=self.name, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, provider_name=self.name, error_message=str(e))

    def parse_works(self, works: List[Dict[str, Any]]) -> List[SourceRecord]:
        records = []
        for w in works:
            title = w.get("title", "") or w.get("display_name", "")
            if not title:
                continue

            openalex_id = w.get("id", "").split("/")[-1]
            doi = w.get("doi", "")
            if doi and doi.startswith("https://doi.org/"):
                doi = doi.replace("https://doi.org/", "")

            # Reconstruct abstract from abstract_inverted_index if present
            abstract = None
            inv_idx = w.get("abstract_inverted_index")
            if inv_idx and isinstance(inv_idx, dict):
                positions: Dict[int, str] = {}
                for word, pos_list in inv_idx.items():
                    for pos in pos_list:
                        positions[pos] = word
                if positions:
                    sorted_words = [positions[i] for i in sorted(positions.keys())]
                    abstract = " ".join(sorted_words)

            authors = []
            for authorship in w.get("authorships", []):
                author_name = authorship.get("author", {}).get("display_name", "")
                if author_name:
                    authors.append(author_name)

            pub_year = w.get("publication_year")
            is_oa = w.get("open_access", {}).get("is_oa", False)

            records.append(
                SourceRecord(
                    provider=self.name,
                    source_id=openalex_id or doi or title[:40],
                    doi=doi if doi else None,
                    title=title,
                    abstract=abstract,
                    authors=tuple(authors),
                    publication_year=pub_year,
                    url=w.get("doi") or w.get("id"),
                    extra_metadata={"is_oa": is_oa, "cited_by_count": w.get("cited_by_count", 0)},
                )
            )
        return records
