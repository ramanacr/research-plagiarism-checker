import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class YouTubeConnector(AttentionConnector):
    """
    Table 1 Source: YouTube
    Collection method: YouTube Data API
    Update frequency: Daily
    Notes: An American video-sharing website. Scans for links to scholarly outputs in video comments & descriptions.
    """
    def __init__(self):
        self.api_url = "https://www.googleapis.com/youtube/v3/search"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_YOUTUBE", True):
            return ConnectorResult(
                source="youtube",
                state="not_configured",
                error_message="YouTube connector is disabled.",
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
            return ConnectorResult(source="youtube", state="ready", evidence=[], item_count=0)

        query = doi if doi else pmid
        evidence = []

        try:
            api_key = getattr(src.config, "YOUTUBE_API_KEY", None)
            if api_key:
                params = {
                    "part": "snippet",
                    "q": f'"{query}"',
                    "type": "video",
                    "maxResults": 25,
                    "key": api_key
                }
                resp = requests.get(self.api_url, params=params, timeout=10)
                if resp.status_code == 200:
                    items = resp.json().get("items", [])
                    for item in items:
                        video_id = item.get("id", {}).get("videoId")
                        snippet = item.get("snippet", {})
                        title = snippet.get("title", "YouTube Video")
                        channel_title = snippet.get("channelTitle", "Channel")
                        published_at = None
                        if snippet.get("publishedAt"):
                            try:
                                dt = datetime.datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
                                published_at = dt.date()
                            except ValueError:
                                pass

                        if video_id:
                            evidence.append({
                                "source": "youtube",
                                "source_type": "video_mention",
                                "external_id": video_id,
                                "url": f"https://www.youtube.com/watch?v={video_id}",
                                "title": f"{title} (by {channel_title})",
                                "published_at": published_at,
                                "matched_identifier": f"doi:{doi}" if doi else f"pmid:{pmid}",
                                "match_confidence": "exact_identifier",
                                "raw_reference_json": item
                            })

            return ConnectorResult(
                source="youtube",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )
        except Exception as e:
            return ConnectorResult(
                source="youtube",
                state="failed",
                error_code="YOUTUBE_ERROR",
                error_message=str(e),
                item_count=0
            )
