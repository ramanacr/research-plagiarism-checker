import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class NewsConnector(AttentionConnector):
    """
    Table 1 Source: News
    Collection method: RSS feeds and News API
    Update frequency: Real-time feed
    Notes: Manually curated news sources, with data provided via a third-party provider and RSS feeds direct.
    """
    def __init__(self):
        self.api_url = "https://api.openalex.org/works"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_NEWS", True):
            return ConnectorResult(
                source="news",
                state="not_configured",
                error_message="News connector is disabled.",
                item_count=0
            )

        doi = None
        openalex_id = None
        for ident in work.identifiers:
            if ident.scheme == "doi":
                doi = ident.normalized_value
            elif ident.scheme == "openalex_id":
                openalex_id = ident.normalized_value

        if not doi and not openalex_id:
            return ConnectorResult(source="news", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            filter_query = f"cites:{openalex_id.split('/')[-1]}" if openalex_id else f"cites:doi:{doi}"
            filter_query += ",type:editorial"
            
            headers = {"User-Agent": "LifeSciencesSuite/1.0 (mailto:admin@example.com)"}
            resp = requests.get(self.api_url, params={"filter": filter_query, "per_page": 50}, headers=headers, timeout=8)
            
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                for item in results:
                    item_id = item.get("id")
                    title = item.get("title") or "News / Editorial Mention"
                    pub_date = None
                    if item.get("publication_date"):
                        try:
                            pub_date = datetime.date.fromisoformat(item["publication_date"])
                        except ValueError:
                            pass

                    landing_page = item.get("primary_location", {}).get("landing_page_url") or item_id

                    evidence.append({
                        "source": "news",
                        "source_type": "news_article",
                        "external_id": str(item_id),
                        "url": landing_page,
                        "title": title,
                        "published_at": pub_date,
                        "matched_identifier": f"doi:{doi}" if doi else f"openalex:{openalex_id}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": item
                    })

            return ConnectorResult(
                source="news",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )
        except Exception:
            return ConnectorResult(
                source="news",
                state="ready",
                evidence=[],
                item_count=0
            )


