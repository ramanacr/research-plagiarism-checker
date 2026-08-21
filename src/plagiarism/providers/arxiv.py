"""
arXiv preprint scholarly content provider.
"""

import time
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any
import httpx

from src.plagiarism.providers.base import (
    ScholarlyContentProvider,
    ProviderCapabilities,
    ProviderHealth,
    SourceRecord,
    SourceDocument,
)


class ArXivProvider(ScholarlyContentProvider):
    """
    Provider for arXiv preprint API (Atom feed / XML).
    """

    def __init__(
        self,
        base_url: str = "http://export.arxiv.org/api/query",
        timeout: float = 12.0,
        user_agent: str = "ConfidentialPlagiarismChecker/2.0",
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.user_agent = user_agent
        self._capabilities = ProviderCapabilities(
            search=True,
            metadata=True,
            abstracts=True,
            full_text=False,
            bulk_ingest=False,
        )

    @property
    def name(self) -> str:
        return "arxiv"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def search(self, query: str, limit: int = 20) -> List[SourceRecord]:
        """Queries arXiv API."""
        if not query.strip():
            return []

        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
        }

        async with httpx.AsyncClient(timeout=self.timeout, headers={"User-Agent": self.user_agent}) as client:
            try:
                resp = await client.get(self.base_url, params=params)
                resp.raise_for_status()
                return self.parse_atom_feed(resp.content)
            except Exception:
                return []

    async def get_metadata(self, source_id: str) -> Optional[SourceRecord]:
        clean_id = source_id.strip()
        if not clean_id:
            return None

        params = {"id_list": clean_id}
        async with httpx.AsyncClient(timeout=self.timeout, headers={"User-Agent": self.user_agent}) as client:
            try:
                resp = await client.get(self.base_url, params=params)
                resp.raise_for_status()
                records = self.parse_atom_feed(resp.content)
                return records[0] if records else None
            except Exception:
                return None

    async def get_full_text(self, source_id: str) -> Optional[SourceDocument]:
        rec = await self.get_metadata(source_id)
        if not rec:
            return None
        return SourceDocument(
            document_id=f"arxiv:{rec.source_id}",
            provider=self.name,
            provider_source_id=rec.source_id,
            doi=rec.doi,
            title=rec.title,
            abstract=rec.abstract,
            authors=rec.authors,
            publication_year=rec.publication_year,
            rights_id="cc_by",
            full_text_available=False,
        )

    async def health_check(self) -> ProviderHealth:
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0, headers={"User-Agent": self.user_agent}) as client:
                resp = await client.get(self.base_url, params={"search_query": "all:quantum", "max_results": 1})
                latency = (time.time() - start) * 1000
                return ProviderHealth(is_healthy=resp.status_code == 200, provider_name=self.name, latency_ms=latency)
        except Exception as e:
            return ProviderHealth(is_healthy=False, provider_name=self.name, error_message=str(e))

    def parse_atom_feed(self, xml_bytes: bytes) -> List[SourceRecord]:
        records = []
        try:
            root = ET.fromstring(xml_bytes)
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

            for entry in root.findall("atom:entry", ns):
                id_el = entry.find("atom:id", ns)
                raw_id = id_el.text.strip().split("/")[-1] if id_el is not None and id_el.text else ""

                title_el = entry.find("atom:title", ns)
                title = " ".join(title_el.text.split()) if title_el is not None and title_el.text else ""

                summary_el = entry.find("atom:summary", ns)
                abstract = " ".join(summary_el.text.split()) if summary_el is not None and summary_el.text else None

                authors = []
                for author_el in entry.findall("atom:author", ns):
                    name_el = author_el.find("atom:name", ns)
                    if name_el is not None and name_el.text:
                        authors.append(name_el.text.strip())

                published_el = entry.find("atom:published", ns)
                pub_year = None
                if published_el is not None and published_el.text:
                    try:
                        pub_year = int(published_el.text[:4])
                    except ValueError:
                        pass

                doi_el = entry.find("arxiv:doi", ns)
                doi = doi_el.text.strip() if doi_el is not None and doi_el.text else None

                records.append(
                    SourceRecord(
                        provider=self.name,
                        source_id=raw_id or title[:40],
                        doi=doi,
                        title=title,
                        abstract=abstract,
                        authors=tuple(authors),
                        publication_year=pub_year,
                        journal="arXiv Preprint",
                        url=f"https://arxiv.org/abs/{raw_id}" if raw_id else None,
                    )
                )
        except Exception:
            pass
        return records
