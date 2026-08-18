import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class MendeleyConnector(AttentionConnector):
    """
    Table 1 Source: Mendeley
    Collection method: Mendeley API
    Update frequency: Daily
    Notes: A desktop and web program produced by Elsevier for managing and sharing research papers,
           discovering research data and collaborating online.
    """
    def __init__(self):
        self.api_url = "https://api.mendeley.com/catalog"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_MENDELEY", True):
            return ConnectorResult(
                source="mendeley",
                state="not_configured",
                error_message="Mendeley connector is disabled.",
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
            return ConnectorResult(source="mendeley", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            access_token = getattr(src.config, "MENDELEY_ACCESS_TOKEN", None)
            headers = {"Accept": "application/vnd.mendeley-document.1+json"}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

            params = {"view": "stats"}
            if doi:
                params["doi"] = doi
            elif pmid:
                params["pmid"] = pmid

            resp = requests.get(self.api_url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                results = resp.json()
                if isinstance(results, list) and results:
                    doc = results[0]
                    reader_count = doc.get("reader_count", 0)
                    doc_id = doc.get("id")
                    if reader_count > 0 or doc_id:
                        evidence.append({
                            "source": "mendeley",
                            "source_type": "readership",
                            "external_id": str(doc_id) if doc_id else f"mendeley_{doi or pmid}",
                            "url": doc.get("link") or f"https://www.mendeley.com/catalogue/{doc_id}/",
                            "title": f"Mendeley Readers: {reader_count}",
                            "published_at": None,
                            "matched_identifier": f"doi:{doi}" if doi else f"pmid:{pmid}",
                            "match_confidence": "exact_identifier",
                            "raw_reference_json": doc
                        })

            return ConnectorResult(
                source="mendeley",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )
        except Exception:
            return ConnectorResult(
                source="mendeley",
                state="ready",
                evidence=[],
                item_count=0
            )

