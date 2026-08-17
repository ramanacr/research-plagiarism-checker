import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class TwitterConnector(AttentionConnector):
    """
    Table 1 Source: Twitter
    Collection method: Third party data provider / X API
    Update frequency: Real-time feed
    Notes: An online news and social networking service where users post and interact with messages, called 'tweets.'
    """
    def __init__(self):
        self.api_url = "https://api.twitter.com/2/tweets/search/recent"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_TWITTER", True):
            return ConnectorResult(
                source="twitter",
                state="not_configured",
                error_message="Twitter connector is disabled.",
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
            return ConnectorResult(source="twitter", state="ready", evidence=[], item_count=0)

        query = doi if doi else f"pmid:{pmid}"
        evidence = []

        try:
            bearer_token = getattr(src.config, "TWITTER_BEARER_TOKEN", None)
            if bearer_token:
                headers = {"Authorization": f"Bearer {bearer_token}"}
                params = {
                    "query": f'"{query}" -is:retweet',
                    "tweet.fields": "created_at,author_id,text,public_metrics",
                    "max_results": 25
                }
                resp = requests.get(self.api_url, headers=headers, params=params, timeout=10)
                if resp.status_code == 200:
                    tweets_data = resp.json().get("data", [])
                    for tweet in tweets_data:
                        tweet_id = str(tweet.get("id"))
                        created_at = None
                        if tweet.get("created_at"):
                            try:
                                created_at = datetime.datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00")).date()
                            except ValueError:
                                pass

                        evidence.append({
                            "source": "twitter",
                            "source_type": "tweet",
                            "external_id": tweet_id,
                            "url": f"https://twitter.com/i/web/status/{tweet_id}",
                            "title": tweet.get("text", "")[:120],
                            "published_at": created_at,
                            "matched_identifier": f"doi:{doi}" if doi else f"pmid:{pmid}",
                            "match_confidence": "exact_identifier",
                            "raw_reference_json": tweet
                        })
            
            return ConnectorResult(
                source="twitter",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )
        except Exception as e:
            return ConnectorResult(
                source="twitter",
                state="failed",
                error_code="TWITTER_ERROR",
                error_message=str(e),
                item_count=0
            )
