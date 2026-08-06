import requests
import datetime
from typing import List, Dict, Any
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork
import src.config

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
        for ident in work.identifiers:
            if ident.scheme == "doi":
                doi = ident.normalized_value
            elif ident.scheme == "pmid":
                pmid = ident.normalized_value

        if not doi and not pmid:
            return ConnectorResult(source="openalex", state="ready", evidence=[], item_count=0)

        try:
            query_term = f"https://doi.org/{doi}" if doi else f"pmid:{pmid}"
            response = requests.get(
                f"{self.api_url}/{query_term}",
                headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0 (mailto:agent@google.com)"},
                timeout=10
            )
            if response.status_code != 200:
                return ConnectorResult(source="openalex", state="ready", evidence=[], item_count=0)

            work_data = response.json()
            cited_by_url = work_data.get("cited_by_api_url")
            if not cited_by_url:
                return ConnectorResult(source="openalex", state="ready", evidence=[], item_count=0)

            citations_resp = requests.get(
                cited_by_url,
                headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0 (mailto:agent@google.com)"},
                timeout=10
            )
            if citations_resp.status_code != 200:
                return ConnectorResult(source="openalex", state="ready", evidence=[], item_count=0)

            citations_data = citations_resp.json()
            citing_works = citations_data.get("results", [])

            evidence = []
            for item in citing_works:
                citing_doi = item.get("doi")
                citing_title = item.get("title", "Untitled Citing Paper")
                citing_id = item.get("id")
                
                pub_date = None
                pub_date_str = item.get("publication_date")
                if pub_date_str:
                    try:
                        pub_date = datetime.date.fromisoformat(pub_date_str)
                    except ValueError:
                        pass

                url = citing_doi if citing_doi else f"https://openalex.org/{citing_id.split('/')[-1]}"

                evidence.append({
                    "source": "openalex",
                    "source_type": "citation",
                    "external_id": citing_id,
                    "url": url,
                    "title": citing_title,
                    "published_at": pub_date,
                    "matched_identifier": f"doi:{doi}" if doi else f"pmid:{pmid}",
                    "match_confidence": "exact_identifier",
                    "raw_reference_json": item
                })

            return ConnectorResult(
                source="openalex",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )

        except Exception as e:
            return ConnectorResult(
                source="openalex",
                state="failed",
                error_code="OPENALEX_ERROR",
                error_message=str(e),
                item_count=0
            )
