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
                
                # Query by PMID first, then DOI
                entries = []
                if pmid:
                    resp_pmid = requests.get(self.api_url, headers=headers, params={"query": f"PMID({pmid})"}, timeout=10)
                    if resp_pmid.status_code == 200:
                        entries = resp_pmid.json().get("search-results", {}).get("entry", [])
                
                if not entries and doi:
                    resp_doi = requests.get(self.api_url, headers=headers, params={"query": f"DOI({doi})"}, timeout=10)
                    if resp_doi.status_code == 200:
                        entries = resp_doi.json().get("search-results", {}).get("entry", [])


                if entries:
                    for entry in entries:
                        scopus_id = entry.get("dc:identifier") or entry.get("eid")
                        title = entry.get("dc:title", "Scopus Document")
                        citedby_count = int(entry.get("citedby-count", 0))
                        pub_date = None
                        cover_date = entry.get("prism:coverDate")
                        if cover_date:
                            try:
                                pub_date = datetime.date.fromisoformat(cover_date)
                            except ValueError:
                                pass


                        citedby_link = None
                        for l in entry.get("link", []):
                            if l.get("@ref") == "scopus-citedby":
                                citedby_link = l.get("@href")
                            elif not citedby_link and l.get("@ref") == "scopus":
                                citedby_link = l.get("@href")

                        evidence.append({
                            "source": "scopus",
                            "source_type": "citation_record",
                            "external_id": str(scopus_id),
                            "url": citedby_link or f"https://www.scopus.com/record/display.uri?eid={scopus_id}",
                            "title": f"Scopus Inbound Citations ({citedby_count} citing articles)",
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
