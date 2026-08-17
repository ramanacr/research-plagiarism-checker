import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class ScopusConnector(AttentionConnector):
    """
    Table 1 Source: Scopus
    Collection method: Scopus API
    Update frequency: Real-time feed
    Notes: Elsevier's abstract and citation database.
    """
    def __init__(self):
        self.api_url = "https://api.elsevier.com/content/search/scopus"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_SCOPUS", True):
            return ConnectorResult(
                source="scopus",
                state="not_configured",
                error_message="Scopus connector is disabled.",
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
            return ConnectorResult(source="scopus", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            api_key = getattr(src.config, "SCOPUS_API_KEY", None)
            if api_key:
                headers = {
                    "X-ELS-APIKey": api_key,
                    "Accept": "application/json"
                }
                query = f'DOI("{doi}")' if doi else f'PMID("{pmid}")'
                resp = requests.get(self.api_url, headers=headers, params={"query": query}, timeout=10)
                if resp.status_code == 200:
                    entries = resp.json().get("search-results", {}).get("entry", [])
                    for entry in entries:
                        scopus_id = entry.get("dc:identifier")
                        title = entry.get("dc:title", "Scopus Document")
                        citedby_count = int(entry.get("citedby-count", 0))
                        pub_date = None
                        cover_date = entry.get("prism:coverDate")
                        if cover_date:
                            try:
                                pub_date = datetime.date.fromisoformat(cover_date)
                            except ValueError:
                                pass

                        link = None
                        for l in entry.get("link", []):
                            if l.get("@ref") == "scopus":
                                link = l.get("@href")

                        evidence.append({
                            "source": "scopus",
                            "source_type": "citation_record",
                            "external_id": str(scopus_id),
                            "url": link or f"https://www.scopus.com/record/display.uri?eid={scopus_id}",
                            "title": f"{title} (Citations: {citedby_count})",
                            "published_at": pub_date,
                            "matched_identifier": f"doi:{doi}" if doi else f"pmid:{pmid}",
                            "match_confidence": "exact_identifier",
                            "raw_reference_json": {**entry, "citation_count": citedby_count}
                        })

            return ConnectorResult(
                source="scopus",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )
        except Exception as e:
            return ConnectorResult(
                source="scopus",
                state="failed",
                error_code="SCOPUS_ERROR",
                error_message=str(e),
                item_count=0
            )
