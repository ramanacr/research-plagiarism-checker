"""
Europe PMC scholarly content provider implementation.
"""

import time
import hashlib
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


class EuropePMCProvider(ScholarlyContentProvider):
    """
    Provider for Europe PMC REST APIs.
    Supports discovery, metadata, abstracts, and open-access full text.
    """

    def __init__(
        self,
        search_url: str = "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        timeout: float = 12.0,
        user_agent: str = "ConfidentialPlagiarismChecker/2.0",
    ):
        self.search_url = search_url
        self.timeout = timeout
        self.user_agent = user_agent
        self._capabilities = ProviderCapabilities(
            search=True,
            metadata=True,
            abstracts=True,
            full_text=True,
            bulk_ingest=False,
        )

    @property
    def name(self) -> str:
        return "europe_pmc"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def _get_headers(self) -> Dict[str, str]:
        return {"User-Agent": self.user_agent}

    async def search(self, query: str, limit: int = 20) -> List[SourceRecord]:
        """
        Searches Europe PMC for articles matching query/keywords.
        """
        if not query.strip():
            return []

        terms = [t.strip().strip('"') for t in query.split() if len(t.strip()) > 2]
        if not terms:
            terms = [query.strip()]

        formatted_query = " AND ".join([f'"{t}"' for t in terms])

        params = {
            "query": formatted_query,
            "format": "json",
            "resultType": "core",
            "pageSize": limit,
        }

        async with httpx.AsyncClient(timeout=self.timeout, headers=self._get_headers()) as client:
            try:
                resp = await client.get(self.search_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("resultList", {}).get("result", [])

                # Fallback: relax query if 0 results
                if not results and len(terms) > 2:
                    relaxed_query = " AND ".join([f'"{t}"' for t in terms[:3]])
                    params["query"] = relaxed_query
                    resp = await client.get(self.search_url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    results = data.get("resultList", {}).get("result", [])

                return self.parse_json_results(results)
            except Exception:
                return []

    async def get_metadata(self, source_id: str) -> Optional[SourceRecord]:
        """Fetches metadata by Europe PMC ID, PMID, or PMCID."""
        clean_id = source_id.strip()
        if not clean_id:
            return None

        # Build query for ID
        if clean_id.startswith("PMC"):
            query = f"PMCID:{clean_id}"
        elif clean_id.isdigit():
            query = f"EXT_ID:{clean_id}"
        else:
            query = clean_id

        params = {
            "query": query,
            "format": "json",
            "resultType": "core",
            "pageSize": 1,
        }

        async with httpx.AsyncClient(timeout=self.timeout, headers=self._get_headers()) as client:
            try:
                resp = await client.get(self.search_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("resultList", {}).get("result", [])
                records = self.parse_json_results(results)
                return records[0] if records else None
            except Exception:
                return None

    async def get_full_text(self, source_id: str) -> Optional[SourceDocument]:
        """
        Fetches Europe PMC full text if PMCID is available and accessible.
        Falls back to abstract.
        """
        record = await self.get_metadata(source_id)
        if not record:
            return None

        full_text = None
        full_text_available = False

        if record.pmcid:
            xml_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{record.pmcid}/fullTextXML"
            async with httpx.AsyncClient(timeout=self.timeout, headers=self._get_headers()) as client:
                try:
                    resp = await client.get(xml_url)
                    if resp.status_code == 200:
                        parsed_text = self._extract_text_from_pmc_xml(resp.content)
                        if parsed_text and len(parsed_text) > 100:
                            full_text = parsed_text
                            full_text_available = True
                except Exception:
                    pass

        content = full_text or record.abstract or ""
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        return SourceDocument(
            document_id=f"europe_pmc:{record.source_id}",
            provider="europe_pmc",
            provider_source_id=record.source_id,
            doi=record.doi,
            pmid=record.pmid,
            pmcid=record.pmcid,
            title=record.title,
            abstract=record.abstract,
            full_text=full_text or record.abstract,
            authors=record.authors,
            journal=record.journal,
            publication_year=record.publication_year,
            language=record.language,
            content_hash=content_hash,
            rights_id="europe_pmc_open_access" if full_text_available else "europe_pmc_abstract_fair_use",
            full_text_available=full_text_available,
            extra_metadata=record.extra_metadata,
        )

    def _extract_text_from_pmc_xml(self, xml_bytes: bytes) -> str:
        """Extracts readable section paragraphs from JATS/PMC XML."""
        try:
            root = ET.fromstring(xml_bytes)
            paragraphs = []
            for body in root.findall(".//body"):
                for p in body.findall(".//p"):
                    text = "".join(p.itertext()).strip()
                    if text:
                        paragraphs.append(text)
            return "\n\n".join(paragraphs)
        except Exception:
            return ""

    async def health_check(self) -> ProviderHealth:
        """Checks Europe PMC REST API health."""
        start_time = time.time()
        params = {
            "query": "malaria",
            "format": "json",
            "pageSize": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=5.0, headers=self._get_headers()) as client:
                resp = await client.get(self.search_url, params=params)
                latency = (time.time() - start_time) * 1000
                is_healthy = resp.status_code == 200
                return ProviderHealth(
                    is_healthy=is_healthy,
                    provider_name=self.name,
                    latency_ms=latency,
                    status_code=resp.status_code,
                    error_message=None if is_healthy else f"Status code {resp.status_code}",
                )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return ProviderHealth(
                is_healthy=False,
                provider_name=self.name,
                latency_ms=latency,
                error_message=str(e),
            )

    def parse_json_results(self, raw_results: List[Dict[str, Any]]) -> List[SourceRecord]:
        """Parses Europe PMC JSON payload into SourceRecords."""
        records = []
        for item in raw_results:
            title = item.get("title", "").strip()
            if not title:
                continue

            authors = []
            author_string = item.get("authorString", "")
            if author_string:
                authors = [a.strip() for a in author_string.split(",") if a.strip()]
            else:
                for auth in item.get("authorList", {}).get("author", []):
                    fullName = auth.get("fullName", "")
                    if fullName:
                        authors.append(fullName.strip())

            abstract = item.get("abstractText", "").strip() or None

            pub_year = None
            raw_year = item.get("pubYear", "")
            if raw_year and str(raw_year).isdigit():
                pub_year = int(raw_year)

            pmid = item.get("pmid")
            pmcid = item.get("pmcid")
            doi = item.get("doi")
            journal = item.get("journalTitle") or item.get("journalInfo", {}).get("journal", {}).get("title")

            source_id = pmid or pmcid or doi or f"epmc_{hashlib.md5(title.encode('utf-8')).hexdigest()[:10]}"

            record = SourceRecord(
                provider=self.name,
                source_id=source_id,
                doi=doi,
                pmid=pmid,
                pmcid=pmcid,
                title=title,
                abstract=abstract,
                authors=tuple(authors),
                publication_year=pub_year,
                journal=journal,
                url=f"https://europepmc.org/article/{'MED' if pmid else 'PMC'}/{pmid or pmcid}" if (pmid or pmcid) else None,
                extra_metadata={
                    "isOpenAccess": item.get("isOpenAccess", "N") == "Y",
                    "inEPMC": item.get("inEPMC", "N") == "Y",
                    "citedByCount": item.get("citedByCount", 0),
                }
            )
            records.append(record)

        return records
