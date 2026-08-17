import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class FacebookConnector(AttentionConnector):
    """
    Table 1 Source: Facebook
    Collection method: Facebook Graph API
    Update frequency: Daily
    Notes: An American for-profit corporation and an online social media and social networking service.
    """
    def __init__(self):
        self.api_url = "https://graph.facebook.com/v19.0"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_FACEBOOK", True):
            return ConnectorResult(
                source="facebook",
                state="not_configured",
                error_message="Facebook connector is disabled.",
                item_count=0
            )

        doi = None
        for ident in work.identifiers:
            if ident.scheme == "doi":
                doi = ident.normalized_value
                break

        if not doi:
            return ConnectorResult(source="facebook", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            access_token = getattr(src.config, "FACEBOOK_ACCESS_TOKEN", None)
            target_url = f"https://doi.org/{doi}"
            
            if access_token:
                params = {
                    "id": target_url,
                    "fields": "engagement,og_object",
                    "access_token": access_token
                }
                resp = requests.get(self.api_url, params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    engagement = data.get("engagement", {})
                    share_count = engagement.get("share_count", 0)
                    if share_count > 0:
                        evidence.append({
                            "source": "facebook",
                            "source_type": "post",
                            "external_id": data.get("id", target_url),
                            "url": target_url,
                            "title": f"Facebook engagement: {share_count} shares/mentions",
                            "published_at": None,
                            "matched_identifier": f"doi:{doi}",
                            "match_confidence": "canonical_url",
                            "raw_reference_json": data
                        })

            return ConnectorResult(
                source="facebook",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )
        except Exception as e:
            return ConnectorResult(
                source="facebook",
                state="failed",
                error_code="FACEBOOK_ERROR",
                error_message=str(e),
                item_count=0
            )
