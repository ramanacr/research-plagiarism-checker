import requests
import datetime
from typing import List, Dict, Any
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork
import src.config

class CrossrefEventConnector(AttentionConnector):
    def __init__(self):
        self.api_url = "https://api.eventdata.crossref.org/v1/events"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_CROSSREF_EVENT", True):
            return ConnectorResult(
                source="crossref_event",
                state="not_configured",
                error_message="Crossref Event connector is disabled.",
                item_count=0
            )

        doi = None
        for ident in work.identifiers:
            if ident.scheme == "doi":
                doi = ident.normalized_value
                break

        if not doi:
            return ConnectorResult(source="crossref_event", state="ready", evidence=[], item_count=0)

        import time
        try:
            target_url = f"https://doi.org/{doi}"
            
            # Retry loop for transient connection timeouts
            retries = 3
            response = None
            for attempt in range(retries):
                try:
                    response = requests.get(
                        self.api_url,
                        params={"obj-id": target_url, "rows": 100},
                        headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0 (mailto:agent@google.com)"},
                        timeout=10
                    )
                    if response.status_code == 200:
                        break
                    elif response.status_code == 429: # Rate limited
                        time.sleep(2)
                except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
                    if attempt == retries - 1:
                        raise
                    time.sleep(1)
            
            if not response or response.status_code != 200:
                return ConnectorResult(source="crossref_event", state="ready", evidence=[], item_count=0)

            data = response.json()
            events = data.get("message", {}).get("events", [])

            evidence = []
            for item in events:
                subj_id = item.get("subj_id")
                source_id = item.get("source_id", "crossref")
                event_id = item.get("id")
                
                # Filter out Wikipedia events as they are indexed by the Wikipedia connector
                if source_id == "wikipedia":
                    continue

                occurred_at = None
                occurred_str = item.get("occurred_at")
                if occurred_str:
                    try:
                        dt = datetime.datetime.fromisoformat(occurred_str.replace("Z", "+00:00"))
                        occurred_at = dt.date()
                    except ValueError:
                        pass

                evidence.append({
                    "source": source_id,
                    "source_type": "mention",
                    "external_id": event_id,
                    "url": subj_id,
                    "title": f"Mentioned on {source_id.title()}",
                    "published_at": occurred_at,
                    "matched_identifier": f"doi:{doi}",
                    "match_confidence": "canonical_url",
                    "raw_reference_json": item
                })

            return ConnectorResult(
                source="crossref_event",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )

        except Exception as e:
            return ConnectorResult(
                source="crossref_event",
                state="failed",
                error_code="CROSSREF_EVENT_ERROR",
                error_message=str(e),
                item_count=0
            )
