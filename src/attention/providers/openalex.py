import requests
import datetime
from typing import Optional
from src.attention.providers.base import IdentityProvider, normalize_doi, normalize_pmid
from src.attention.schemas import ResolvedWork

class OpenAlexProvider(IdentityProvider):
    def __init__(self):
        self.url = "https://api.openalex.org/works/"

    def _parse_work(self, item: dict) -> Optional[ResolvedWork]:
        try:
            title = item.get("title", "Unknown Title")
            if not title:
                title = "Unknown Title"
            title = title.strip()
            
            journal = item.get("primary_location", {}).get("source", {}).get("display_name", None)
            if journal:
                journal = journal.strip()
                
            pub_date = None
            date_str = item.get("publication_date")  # YYYY-MM-DD
            if date_str:
                try:
                    pub_date = datetime.date.fromisoformat(date_str)
                except ValueError:
                    pass
                    
            authors = []
            authorships = item.get("authorships", [])
            for authorship in authorships:
                author_name = authorship.get("author", {}).get("display_name")
                if author_name:
                    authors.append(author_name.strip())
                    
            ids = item.get("ids", {})
            pmid = normalize_pmid(ids.get("pmid"))
            doi = normalize_doi(ids.get("doi"))
            pmcid = ids.get("pmcid")
            if pmcid:
                pmcid = pmcid.strip()
                if not pmcid.startswith("PMC"):
                    pmcid = f"PMC{pmcid}"
            openalex_id = item.get("id")

            return ResolvedWork(
                title=title,
                journal=journal,
                publication_date=pub_date,
                authors=authors,
                pmid=pmid,
                doi=doi,
                pmcid=pmcid,
                openalex_id=openalex_id
            )
        except Exception:
            return None

    def resolve_doi(self, doi: str) -> Optional[ResolvedWork]:
        normalized = normalize_doi(doi)
        if not normalized:
            return None
        try:
            response = requests.get(
                f"{self.url}https://doi.org/{normalized}",
                headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0 (mailto:agent@google.com)"},
                timeout=10
            )
            if response.status_code == 200:
                return self._parse_work(response.json())
        except Exception:
            pass
        return None

    def resolve_pmid(self, pmid: str) -> Optional[ResolvedWork]:
        normalized = normalize_pmid(pmid)
        if not normalized:
            return None
        try:
            response = requests.get(
                f"{self.url}pmid:{normalized}",
                headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0 (mailto:agent@google.com)"},
                timeout=10
            )
            if response.status_code == 200:
                return self._parse_work(response.json())
        except Exception:
            pass
        return None
