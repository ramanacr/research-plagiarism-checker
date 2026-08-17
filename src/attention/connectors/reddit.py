import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class RedditConnector(AttentionConnector):
    """
    Table 1 Source: Reddit
    Collection method: Reddit API
    Update frequency: Daily
    Notes: An American social news aggregation, web content rating, and discussion website.
           Registered members submit content such as links, text posts, and images.
    """
    def __init__(self):
        self.api_url = "https://www.reddit.com/search.json"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_REDDIT", True):
            return ConnectorResult(
                source="reddit",
                state="not_configured",
                error_message="Reddit connector is disabled.",
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
            return ConnectorResult(source="reddit", state="ready", evidence=[], item_count=0)

        query = f'"{doi}"' if doi else f'"{pmid}"'
        evidence = []

        try:
            headers = {"User-Agent": "ResearchAttentionBot/1.0 (contact: agent@google.com)"}
            resp = requests.get(
                self.api_url,
                headers=headers,
                params={"q": query, "sort": "relevance", "limit": 25},
                timeout=10
            )
            if resp.status_code == 200:
                children = resp.json().get("data", {}).get("children", [])
                for item in children:
                    post_data = item.get("data", {})
                    post_id = post_data.get("id")
                    title = post_data.get("title", "Reddit Post")
                    permalink = post_data.get("permalink", "")
                    created_utc = post_data.get("created_utc")
                    pub_date = None
                    if created_utc:
                        try:
                            pub_date = datetime.datetime.fromtimestamp(created_utc, tz=datetime.timezone.utc).date()
                        except Exception:
                            pass

                    evidence.append({
                        "source": "reddit",
                        "source_type": "post",
                        "external_id": str(post_id),
                        "url": f"https://www.reddit.com{permalink}" if permalink.startswith("/") else permalink,
                        "title": title,
                        "published_at": pub_date,
                        "matched_identifier": f"doi:{doi}" if doi else f"pmid:{pmid}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": post_data
                    })

            return ConnectorResult(
                source="reddit",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )
        except Exception as e:
            return ConnectorResult(
                source="reddit",
                state="failed",
                error_code="REDDIT_ERROR",
                error_message=str(e),
                item_count=0
            )
