import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class F1000Connector(AttentionConnector):
    """
    Table 1 Source: F1000 Reviews
    Collection method: F1000 API
    Update frequency: Daily
    Notes: Faculty of 1000 Research open research publishing platform peer reviews & recommendations.
    """
    def __init__(self):
        self.api_url = "https://f1000research.com/api/v1/articles"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_F1000", True):
            return ConnectorResult(
                source="f1000",
                state="not_configured",
                error_message="F1000 connector is disabled.",
                item_count=0
            )

        doi = None
        for ident in work.identifiers:
            if ident.scheme == "doi":
                doi = ident.normalized_value
                break

        if not doi:
            return ConnectorResult(source="f1000", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            resp = requests.get(
                f"{self.api_url}/{doi}",
                headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0 (mailto:agent@google.com)"},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                reviews = data.get("peer_reviews", []) if isinstance(data, dict) else []
                for review in reviews:
                    review_id = str(review.get("id"))
                    reviewer = review.get("referee_name", "F1000 Reviewer")
                    pub_date = None
                    if review.get("published_date"):
                        try:
                            pub_date = datetime.date.fromisoformat(review["published_date"])
                        except ValueError:
                            pass

                    evidence.append({
                        "source": "f1000",
                        "source_type": "peer_review",
                        "external_id": review_id,
                        "url": review.get("url") or f"https://f1000research.com/articles/{doi}#referee-response-{review_id}",
                        "title": f"F1000 Recommendation by {reviewer}",
                        "published_at": pub_date,
                        "matched_identifier": f"doi:{doi}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": review
                    })

            return ConnectorResult(
                source="f1000",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )
        except Exception as e:
            return ConnectorResult(
                source="f1000",
                state="failed",
                error_code="F1000_ERROR",
                error_message=str(e),
                item_count=0
            )
