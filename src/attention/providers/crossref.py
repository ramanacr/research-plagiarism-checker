import requests
import datetime
from typing import Optional
from src.attention.providers.base import IdentityProvider, normalize_doi, normalize_pmid
from src.attention.schemas import ResolvedWork

class CrossrefProvider(IdentityProvider):
    def __init__(self):
        self.url = "https://api.crossref.org/works/"

    def resolve_doi(self, doi: str) -> Optional[ResolvedWork]:
        normalized = normalize_doi(doi)
        if not normalized:
            return None
        try:
            response = requests.get(
                f"{self.url}{normalized}",
                headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0 (mailto:agent@google.com)"},
                timeout=10
            )
            if response.status_code != 200:
                return None
            
            data = response.json()
            message = data.get("message", {})
            
            # Parse title
            titles = message.get("title", [])
            title = titles[0].strip() if titles else "Unknown Title"
            
            # Parse journal
            containers = message.get("container-title", [])
            journal = containers[0].strip() if containers else None
            
            # Parse date
            pub_date = None
            date_parts = message.get("published", {}).get("date-parts", [])
            if not date_parts:
                date_parts = message.get("created", {}).get("date-parts", [])
            if date_parts and date_parts[0]:
                parts = date_parts[0]
                try:
                    year = int(parts[0])
                    month = int(parts[1]) if len(parts) > 1 else 1
                    day = int(parts[2]) if len(parts) > 2 else 1
                    pub_date = datetime.date(year, month, day)
                except (ValueError, TypeError):
                    pass
            
            # Parse authors
            authors = []
            author_list = message.get("author", [])
            for author in author_list:
                given = author.get("given", "")
                family = author.get("family", "")
                if family:
                    authors.append(f"{given} {family}".strip())

            return ResolvedWork(
                title=title,
                journal=journal,
                publication_date=pub_date,
                authors=authors,
                doi=normalized
            )
        except Exception:
            return None

    def resolve_pmid(self, pmid: str) -> Optional[ResolvedWork]:
        # Crossref works by DOI, not by PMID.
        return None
