import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class PublonsConnector(AttentionConnector):
    """
    Table 1 Source: Post-publication peer reviews (Publons / Web of Science Peer Review)
    Collection method: Publons API
    Update frequency: Daily
    Notes: Peer review comments collected from item records and associated by unique identifier.
    """
    def __init__(self):
        self.api_url = "https://publons.com/api/v2/academic/publication"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_PUBLONS", True):
            return ConnectorResult(
                source="publons",
                state="not_configured",
                error_message="Publons connector is disabled.",
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
            return ConnectorResult(source="publons", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            api_key = getattr(src.config, "PUBLONS_API_KEY", None)
            headers = {"Authorization": f"Token {api_key}"} if api_key else {}
            params = {}
            if doi:
                params["doi"] = doi
            elif pmid:
                params["pmid"] = pmid

            resp = requests.get(self.api_url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                reviews = data.get("reviews", []) if isinstance(data, dict) else []
                for review in reviews:
                    review_id = str(review.get("id"))
                    reviewer = review.get("reviewer", {}).get("name", "Anonymous Reviewer")
                    created_at = None
                    if review.get("created_date"):
                        try:
                            created_at = datetime.date.fromisoformat(review["created_date"])
                        except ValueError:
                            pass

                    evidence.append({
                        "source": "publons",
                        "source_type": "peer_review",
                        "external_id": review_id,
                        "url": review.get("url") or f"https://publons.com/review/{review_id}",
                        "title": f"Publons Peer Review by {reviewer}",
                        "published_at": created_at,
                        "matched_identifier": f"doi:{doi}" if doi else f"pmid:{pmid}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": review
                    })

            return ConnectorResult(
                source="publons",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )
        except Exception as e:
            return ConnectorResult(
                source="publons",
                state="failed",
                error_code="PUBLONS_ERROR",
                error_message=str(e),
                item_count=0
            )
