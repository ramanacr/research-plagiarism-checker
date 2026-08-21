"""
PubMed scholarly content provider wrapping NCBI E-Utilities.
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


class PubMedProvider(ScholarlyContentProvider):
    """
    Provider for PubMed (NCBI Entrez E-Utilities).
    Provides search, metadata retrieval, and abstract ingestion.
    """

    def __init__(
        self,
        esearch_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        efetch_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        timeout: float = 12.0,
        user_agent: str = "ConfidentialPlagiarismChecker/2.0",
        api_key: Optional[str] = None,
    ):
        self.esearch_url = esearch_url
        self.efetch_url = efetch_url
        self.timeout = timeout
        self.user_agent = user_agent
        self.api_key = api_key
        self._capabilities = ProviderCapabilities(
            search=True,
            metadata=True,
            abstracts=True,
            full_text=False,
            bulk_ingest=False,
        )

    @property
    def name(self) -> str:
        return "pubmed"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def _get_headers(self) -> Dict[str, str]:
        headers = {"User-Agent": self.user_agent}
        return headers

    async def search(self, query: str, limit: int = 20) -> List[SourceRecord]:
        """
        Searches PubMed using a formatted query or keyword string.
        Fetches PMIDs then retrieves article metadata via EFetch.
        """
        if not query.strip():
            return []

        # If query contains multiple space-separated words, format for PubMed ESearch
        terms = [t.strip().strip('"') for t in query.split() if len(t.strip()) > 2]
        if not terms:
            terms = [query.strip()]

        quoted_terms = [f'"{t}"' for t in terms]
        search_term = " AND ".join(quoted_terms)

        params: Dict[str, Any] = {
            "db": "pubmed",
            "term": search_term,
            "retmode": "json",
            "retmax": limit,
        }
        if self.api_key:
            params["api_key"] = self.api_key

        async with httpx.AsyncClient(timeout=self.timeout, headers=self._get_headers()) as client:
            try:
                resp = await client.get(self.esearch_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                id_list = data.get("esearchresult", {}).get("idlist", [])

                # Fallback: relax query if 0 results
                if not id_list and len(terms) > 2:
                    relaxed_term = " AND ".join([f'"{t}"' for t in terms[:3]])
                    params["term"] = relaxed_term
                    resp = await client.get(self.esearch_url, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    id_list = data.get("esearchresult", {}).get("idlist", [])

                if not id_list:
                    return []

                # Fetch details for PMIDs
                return await self._fetch_records_by_pmids(client, id_list)
            except Exception:
                return []

    async def get_metadata(self, source_id: str) -> Optional[SourceRecord]:
        """Fetches metadata for a given PMID."""
        clean_id = source_id.strip()
        if not clean_id:
            return None

        async with httpx.AsyncClient(timeout=self.timeout, headers=self._get_headers()) as client:
            records = await self._fetch_records_by_pmids(client, [clean_id])
            return records[0] if records else None

    async def get_full_text(self, source_id: str) -> Optional[SourceDocument]:
        """PubMed only provides abstracts. Full text is not hosted directly on PubMed."""
        record = await self.get_metadata(source_id)
        if not record:
            return None

        content = record.abstract or ""
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        return SourceDocument(
            document_id=f"pubmed:{record.source_id}",
            provider="pubmed",
            provider_source_id=record.source_id,
            doi=record.doi,
            pmid=record.pmid,
            pmcid=record.pmcid,
            title=record.title,
            abstract=record.abstract,
            full_text=record.abstract,
            authors=record.authors,
            journal=record.journal,
            publication_year=record.publication_year,
            language=record.language,
            content_hash=content_hash,
            rights_id="pubmed_abstract_fair_use",
            full_text_available=False,
            extra_metadata=record.extra_metadata,
        )

    async def health_check(self) -> ProviderHealth:
        """Checks NCBI PubMed health."""
        start_time = time.time()
        params = {
            "db": "pubmed",
            "term": "cancer",
            "retmode": "json",
            "retmax": 1,
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=5.0, headers=self._get_headers()) as client:
                resp = await client.get(self.esearch_url, params=params)
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

    async def _fetch_records_by_pmids(
        self, client: httpx.AsyncClient, pmids: List[str]
    ) -> List[SourceRecord]:
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            resp = await client.get(self.efetch_url, params=params)
            resp.raise_for_status()
            return self.parse_pubmed_xml(resp.content)
        except Exception:
            return []

    def parse_pubmed_xml(self, xml_content: bytes) -> List[SourceRecord]:
        """Parses NCBI XML into structured SourceRecords."""
        records = []
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            return []

        for article_element in root.findall(".//PubmedArticle"):
            # PMID
            pmid_el = article_element.find(".//PMID")
            pmid = pmid_el.text.strip() if pmid_el is not None and pmid_el.text else ""

            # Title
            title_el = article_element.find(".//ArticleTitle")
            title = "".join(title_el.itertext()).strip() if title_el is not None else ""

            # Abstract
            abstract_texts = []
            abstract_el = article_element.find(".//Abstract")
            if abstract_el is not None:
                for text_el in abstract_el.findall("AbstractText"):
                    label = text_el.get("Label")
                    text_content = "".join(text_el.itertext()).strip()
                    if label:
                        abstract_texts.append(f"{label}: {text_content}")
                    else:
                        abstract_texts.append(text_content)
            abstract = "\n".join(abstract_texts) if abstract_texts else None

            # Authors
            authors = []
            author_list = article_element.find(".//AuthorList")
            if author_list is not None:
                for author in author_list.findall("Author"):
                    fore = author.find("ForeName")
                    last = author.find("LastName")
                    if last is not None:
                        fore_name = fore.text.strip() if fore is not None and fore.text else ""
                        last_name = last.text.strip() if last is not None and last.text else ""
                        authors.append(f"{fore_name} {last_name}".strip())

            # Journal
            journal_el = article_element.find(".//Journal/Title")
            journal = journal_el.text.strip() if journal_el is not None and journal_el.text else None

            # Year
            pub_year = None
            year_el = article_element.find(".//JournalIssue/PubDate/Year")
            if year_el is not None and year_el.text and year_el.text.isdigit():
                pub_year = int(year_el.text)

            # DOI & PMCID
            doi = None
            pmcid = None
            for el in article_element.findall(".//ArticleIdList/ArticleId"):
                id_type = el.get("IdType")
                if id_type == "doi" and el.text:
                    doi = el.text.strip()
                elif id_type == "pmc" and el.text:
                    pmcid = el.text.strip()

            record = SourceRecord(
                provider=self.name,
                source_id=pmid or f"pm_{hashlib.md5(title.encode('utf-8')).hexdigest()[:10]}",
                doi=doi,
                pmid=pmid if pmid else None,
                pmcid=pmcid,
                title=title,
                abstract=abstract,
                authors=tuple(authors),
                publication_year=pub_year,
                journal=journal,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
            )
            records.append(record)

        return records
