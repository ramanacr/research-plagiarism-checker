import requests
import datetime
from typing import List, Dict, Any
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork
import src.config

class PubPeerConnector(AttentionConnector):
    def __init__(self):
        self.api_url = "https://pubpeer.com/api/v1/publications"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_PUBPEER", True):
            return ConnectorResult(
                source="pubpeer",
                state="not_configured",
                error_message="PubPeer connector is disabled.",
                item_count=0
            )

        doi = None
        for ident in work.identifiers:
            if ident.scheme == "doi":
                doi = ident.normalized_value
                break

        if not doi:
            return ConnectorResult(source="pubpeer", state="ready", evidence=[], item_count=0)

        try:
            response = requests.get(
                f"{self.api_url}/{doi}",
                headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0 (mailto:agent@google.com)"},
                timeout=10
            )
            if response.status_code == 404:
                return ConnectorResult(source="pubpeer", state="ready", evidence=[], item_count=0)
            elif response.status_code != 200:
                return ConnectorResult(source="pubpeer", state="ready", evidence=[], item_count=0)

            data = response.json()
            comments = data.get("comments", [])

            evidence = []
            for item in comments:
                comment_id = str(item.get("id"))
                title = item.get("title", "PubPeer Comment")
                comment_url = item.get("url", f"https://pubpeer.com/publications/{doi}")
                
                created_at = None
                created_str = item.get("created_at")
                if created_str:
                    try:
                        dt = datetime.datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        created_at = dt.date()
                    except ValueError:
                        pass

                evidence.append({
                    "source": "pubpeer",
                    "source_type": "review",
                    "external_id": comment_id,
                    "url": comment_url,
                    "title": title,
                    "published_at": created_at,
                    "matched_identifier": f"doi:{doi}",
                    "match_confidence": "exact_identifier",
                    "raw_reference_json": item
                })

            return ConnectorResult(
                source="pubpeer",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )

        except Exception as e:
            return ConnectorResult(
                source="pubpeer",
                state="failed",
                error_code="PUBPEER_ERROR",
                error_message=str(e),
                item_count=0
            )
