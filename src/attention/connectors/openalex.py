import requests
import datetime
from typing import List, Dict, Any
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork
import src.config

from src.attention.scoring import check_self_citation

class OpenAlexConnector(AttentionConnector):
    def __init__(self):
        self.api_url = "https://api.openalex.org/works"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_OPENALEX", True):
            return ConnectorResult(
                source="openalex",
                state="not_configured",
                error_message="OpenAlex connector is disabled.",
                item_count=0
            )

        doi = None
        pmid = None
        openalex_id = None
        for ident in work.identifiers:
            if ident.scheme == "doi":
                doi = ident.normalized_value
            elif ident.scheme == "pmid":
                pmid = ident.normalized_value
            elif ident.scheme == "openalex_id":
                openalex_id = ident.normalized_value

        if not doi and not pmid and not openalex_id:
            return ConnectorResult(source="openalex", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            # 1. Fetch work record to obtain OpenAlex ID and cited_by URL
            work_id_clean = openalex_id.split('/')[-1] if openalex_id else None
            citing_works = []
            
            if work_id_clean:
                # Query citing works directly
                resp = requests.get(
                    self.api_url,
                    params={"filter": f"cites:{work_id_clean}", "per_page": 50},
                    headers={"User-Agent": "LifeSciencesSuite/1.0 (mailto:admin@example.com)"},
                    timeout=8
                )
                if resp.status_code == 200:
                    citing_works = resp.json().get("results", [])

            if not citing_works:
                query_term = f"https://doi.org/{doi}" if doi else f"pmid:{pmid}"
                response = requests.get(
                    f"{self.api_url}/{query_term}",
                    headers={"User-Agent": "LifeSciencesSuite/1.0 (mailto:admin@example.com)"},
                    timeout=8
                )
                if response.status_code == 200:
                    work_data = response.json()
                    oa_clean = work_data.get("id", "").split("/")[-1]
                    cited_by_url = work_data.get("cited_by_api_url")
                    if cited_by_url:
                        c_resp = requests.get(
                            cited_by_url,
                            headers={"User-Agent": "LifeSciencesSuite/1.0 (mailto:admin@example.com)"},
                            timeout=8
                        )
                        if c_resp.status_code == 200:
                            citing_works = c_resp.json().get("results", [])
                    elif oa_clean:
                        c_resp = requests.get(
                            self.api_url,
                            params={"filter": f"cites:{oa_clean}", "per_page": 50},
                            headers={"User-Agent": "LifeSciencesSuite/1.0 (mailto:admin@example.com)"},
                            timeout=8
                        )
                        if c_resp.status_code == 200:
                            citing_works = c_resp.json().get("results", [])


            for item in citing_works:
                citing_doi = item.get("doi")
                citing_title = item.get("title", "Untitled Citing Paper")
                citing_id = item.get("id")
                
                # Extract citing authors
                citing_authors = []
                for a in item.get("authorships", []):
                    author_name = a.get("author", {}).get("display_name")
                    if author_name:
                        citing_authors.append(author_name)

                # Check self-citation
                is_self = check_self_citation(work.authors, citing_authors)
                
                pub_date = None
                pub_date_str = item.get("publication_date")
                if pub_date_str:
                    try:
                        pub_date = datetime.date.fromisoformat(pub_date_str)
                    except ValueError:
                        pass

                url = citing_doi if citing_doi else f"https://openalex.org/{citing_id.split('/')[-1]}"
                venue = item.get("primary_location", {}).get("source", {}).get("display_name")

                evidence.append({
                    "source": "openalex",
                    "source_type": "academic_citation",
                    "external_id": str(citing_id),
                    "url": url,
                    "title": f"Cited in: {citing_title}",
                    "published_at": pub_date,
                    "matched_identifier": f"doi:{doi}" if doi else f"pmid:{pmid}",
                    "match_confidence": "exact_identifier",
                    "raw_reference_json": {
                        **item,
                        "citing_authors": citing_authors,
                        "venue": venue,
                        "is_self_citation": is_self,
                        "citation_count": 1
                    }
                })

            return ConnectorResult(
                source="openalex",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )

        except Exception:
            return ConnectorResult(
                source="openalex",
                state="ready",
                evidence=[],
                item_count=0
            )

