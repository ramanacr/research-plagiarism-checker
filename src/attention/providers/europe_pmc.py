import requests
import datetime
from typing import Optional
from src.attention.providers.base import IdentityProvider, normalize_doi, normalize_pmid
from src.attention.schemas import ResolvedWork

class EuropePMCProvider(IdentityProvider):
    def __init__(self):
        self.url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def _query(self, query_str: str) -> Optional[ResolvedWork]:
        try:
            response = requests.get(
                self.url,
                params={"query": query_str, "format": "json", "resultType": "core"},
                headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0"},
                timeout=10
            )
            if response.status_code != 200:
                return None
            
            data = response.json()
            results = data.get("resultList", {}).get("result", [])
            if not results:
                return None
            
            result = results[0]
            title = result.get("title", "Unknown Title").strip()
            journal = result.get("journalInfo", {}).get("journal", {}).get("title", None)
            if journal:
                journal = journal.strip()
                
            # Parse date
            pub_date = None
            first_pub_date = result.get("firstPublicationDate")  # YYYY-MM-DD
            if first_pub_date:
                try:
                    pub_date = datetime.date.fromisoformat(first_pub_date)
                except ValueError:
                    pass
            
            if not pub_date:
                pub_year = result.get("pubYear")
                if pub_year:
                    try:
                        pub_date = datetime.date(int(pub_year), 1, 1)
                    except ValueError:
                        pass
            
            # Parse authors
            authors = []
            author_list = result.get("authorList", {}).get("author", [])
            for author in author_list:
                fullName = author.get("fullName")
                if fullName:
                    authors.append(fullName.strip())
            if not authors and "authorString" in result:
                authors = [a.strip() for a in result["authorString"].split(",") if a.strip()]

            # Extract IDs
            pmid = normalize_pmid(result.get("pmid"))
            doi = normalize_doi(result.get("doi"))
            pmcid = result.get("pmcid")
            if pmcid:
                pmcid = pmcid.strip()
                if not pmcid.startswith("PMC"):
                    pmcid = f"PMC{pmcid}"

            return ResolvedWork(
                title=title,
                journal=journal,
                publication_date=pub_date,
                authors=authors,
                pmid=pmid,
                doi=doi,
                pmcid=pmcid
            )
        except Exception:
            return None

    def resolve_pmid(self, pmid: str) -> Optional[ResolvedWork]:
        normalized = normalize_pmid(pmid)
        if not normalized:
            return None
        return self._query(f"ext_id:{normalized} src:med")

    def resolve_doi(self, doi: str) -> Optional[ResolvedWork]:
        normalized = normalize_doi(doi)
        if not normalized:
            return None
        return self._query(f"doi:{normalized}")
