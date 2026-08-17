import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class StackOverflowConnector(AttentionConnector):
    """
    Table 1 Source: Stack Overflow Q&A
    Collection method: Stack Overflow / Stack Exchange API
    Update frequency: Daily
    Notes: A platform for users to ask and answer questions. Mentions of scholarly outputs in Q&A posts.
    """
    def __init__(self):
        self.api_url = "https://api.stackexchange.com/2.3/search/excerpts"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_STACKOVERFLOW", True):
            return ConnectorResult(
                source="stackoverflow",
                state="not_configured",
                error_message="Stack Overflow connector is disabled.",
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
            return ConnectorResult(source="stackoverflow", state="ready", evidence=[], item_count=0)

        query = doi if doi else pmid
        evidence = []

        try:
            params = {
                "site": "stackoverflow",
                "q": query,
                "pagesize": 25,
                "order": "desc",
                "sort": "relevance"
            }
            api_key = getattr(src.config, "STACKEXCHANGE_API_KEY", None)
            if api_key:
                params["key"] = api_key

            resp = requests.get(self.api_url, params=params, timeout=10)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                for item in items:
                    post_id = str(item.get("question_id") or item.get("answer_id") or item.get("item_id"))
                    item_type = item.get("item_type", "post")
                    title = item.get("title", f"Stack Overflow {item_type.capitalize()}")
                    creation_date = item.get("creation_date")
                    pub_date = None
                    if creation_date:
                        try:
                            pub_date = datetime.datetime.fromtimestamp(creation_date, tz=datetime.timezone.utc).date()
                        except Exception:
                            pass

                    url = f"https://stackoverflow.com/q/{post_id}"
                    evidence.append({
                        "source": "stackoverflow",
                        "source_type": item_type,
                        "external_id": post_id,
                        "url": url,
                        "title": title,
                        "published_at": pub_date,
                        "matched_identifier": f"doi:{doi}" if doi else f"pmid:{pmid}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": item
                    })

            return ConnectorResult(
                source="stackoverflow",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )
        except Exception as e:
            return ConnectorResult(
                source="stackoverflow",
                state="failed",
                error_code="STACKOVERFLOW_ERROR",
                error_message=str(e),
                item_count=0
            )
