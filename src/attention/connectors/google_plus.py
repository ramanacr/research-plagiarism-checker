import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class GooglePlusConnector(AttentionConnector):
    """
    Table 1 Source: Google+
    Collection method: Google+ API / Public archive
    Update frequency: Daily
    Notes: An internet based social network. Public posts only.
    """
    def __init__(self):
        # Queries CrossRef Event Google+ archive or Google+ public snapshot index
        self.api_url = "https://api.eventdata.crossref.org/v1/events"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_GOOGLE_PLUS", True):
            return ConnectorResult(
                source="google_plus",
                state="not_configured",
                error_message="Google+ connector is disabled.",
                item_count=0
            )

        doi = None
        for ident in work.identifiers:
            if ident.scheme == "doi":
                doi = ident.normalized_value
                break

        if not doi:
            return ConnectorResult(source="google_plus", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            target_url = f"https://doi.org/{doi}"
            resp = requests.get(
                self.api_url,
                params={"obj-id": target_url, "source": "googleplus", "rows": 25},
                headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0 (mailto:agent@google.com)"},
                timeout=10
            )
            if resp.status_code == 200:
                events = resp.json().get("message", {}).get("events", [])
                for item in events:
                    subj_id = item.get("subj_id")
                    event_id = item.get("id")
                    occurred_at = None
                    if item.get("occurred_at"):
                        try:
                            dt = datetime.datetime.fromisoformat(item["occurred_at"].replace("Z", "+00:00"))
                            occurred_at = dt.date()
                        except ValueError:
                            pass

                    evidence.append({
                        "source": "google_plus",
                        "source_type": "post",
                        "external_id": str(event_id),
                        "url": subj_id or target_url,
                        "title": item.get("title", f"Google+ Public Post Mention for {doi}"),
                        "published_at": occurred_at,
                        "matched_identifier": f"doi:{doi}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": item
                    })

            return ConnectorResult(
                source="google_plus",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )
        except Exception as e:
            return ConnectorResult(
                source="google_plus",
                state="failed",
                error_code="GOOGLE_PLUS_ERROR",
                error_message=str(e),
                item_count=0
            )
