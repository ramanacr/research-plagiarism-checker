import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class SinaWeiboConnector(AttentionConnector):
    """
    Table 1 Footnote Source: Sina Weibo
    Coverage ended: 7/24/15. Retains historical data archive mentions.
    """
    def __init__(self):
        self.api_url = "https://api.eventdata.crossref.org/v1/events"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_SINA_WEIBO", True):
            return ConnectorResult(
                source="sina_weibo",
                state="not_configured",
                error_message="Sina Weibo connector is disabled.",
                item_count=0
            )

        doi = None
        for ident in work.identifiers:
            if ident.scheme == "doi":
                doi = ident.normalized_value
                break

        if not doi:
            return ConnectorResult(source="sina_weibo", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            target_url = f"https://doi.org/{doi}"
            resp = requests.get(
                self.api_url,
                params={"obj-id": target_url, "source": "weibo", "rows": 25},
                headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0 (mailto:agent@google.com)"},
                timeout=10
            )
            if resp.status_code == 200:
                events = resp.json().get("message", {}).get("events", [])
                for item in events:
                    subj_id = item.get("subj_id")
                    event_id = item.get("id")
                    evidence.append({
                        "source": "sina_weibo",
                        "source_type": "microblog_post",
                        "external_id": str(event_id),
                        "url": subj_id or target_url,
                        "title": f"Sina Weibo Post for {doi}",
                        "published_at": None,
                        "matched_identifier": f"doi:{doi}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": item
                    })

            return ConnectorResult(source="sina_weibo", state="ready", evidence=evidence, item_count=len(evidence))
        except Exception as e:
            return ConnectorResult(source="sina_weibo", state="failed", error_code="SINA_WEIBO_ERROR", error_message=str(e), item_count=0)


class CiteULikeConnector(AttentionConnector):
    """
    Table 1 Footnote Source: CiteULike
    Coverage ended: 12/14. Historical bookmark archive.
    """
    def __init__(self):
        self.api_url = "https://api.eventdata.crossref.org/v1/events"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_CITEULIKE", True):
            return ConnectorResult(
                source="citeulike",
                state="not_configured",
                error_message="CiteULike connector is disabled.",
                item_count=0
            )

        doi = None
        for ident in work.identifiers:
            if ident.scheme == "doi":
                doi = ident.normalized_value
                break

        if not doi:
            return ConnectorResult(source="citeulike", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            target_url = f"https://doi.org/{doi}"
            resp = requests.get(
                self.api_url,
                params={"obj-id": target_url, "source": "citeulike", "rows": 25},
                headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0 (mailto:agent@google.com)"},
                timeout=10
            )
            if resp.status_code == 200:
                events = resp.json().get("message", {}).get("events", [])
                for item in events:
                    subj_id = item.get("subj_id")
                    event_id = item.get("id")
                    evidence.append({
                        "source": "citeulike",
                        "source_type": "bookmark",
                        "external_id": str(event_id),
                        "url": subj_id or target_url,
                        "title": f"CiteULike Bookmark for {doi}",
                        "published_at": None,
                        "matched_identifier": f"doi:{doi}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": item
                    })

            return ConnectorResult(source="citeulike", state="ready", evidence=evidence, item_count=len(evidence))
        except Exception as e:
            return ConnectorResult(source="citeulike", state="failed", error_code="CITEULIKE_ERROR", error_message=str(e), item_count=0)


class PinterestConnector(AttentionConnector):
    """
    Table 1 Footnote Source: Pinterest
    Coverage ended: 6/20/13. Historical pin mentions.
    """
    def __init__(self):
        self.api_url = "https://api.eventdata.crossref.org/v1/events"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_PINTEREST", True):
            return ConnectorResult(
                source="pinterest",
                state="not_configured",
                error_message="Pinterest connector is disabled.",
                item_count=0
            )

        doi = None
        for ident in work.identifiers:
            if ident.scheme == "doi":
                doi = ident.normalized_value
                break

        if not doi:
            return ConnectorResult(source="pinterest", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            target_url = f"https://doi.org/{doi}"
            resp = requests.get(
                self.api_url,
                params={"obj-id": target_url, "source": "pinterest", "rows": 25},
                headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0 (mailto:agent@google.com)"},
                timeout=10
            )
            if resp.status_code == 200:
                events = resp.json().get("message", {}).get("events", [])
                for item in events:
                    subj_id = item.get("subj_id")
                    event_id = item.get("id")
                    evidence.append({
                        "source": "pinterest",
                        "source_type": "pin",
                        "external_id": str(event_id),
                        "url": subj_id or target_url,
                        "title": f"Pinterest Pin for {doi}",
                        "published_at": None,
                        "matched_identifier": f"doi:{doi}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": item
                    })

            return ConnectorResult(source="pinterest", state="ready", evidence=evidence, item_count=len(evidence))
        except Exception as e:
            return ConnectorResult(source="pinterest", state="failed", error_code="PINTEREST_ERROR", error_message=str(e), item_count=0)


class LinkedInConnector(AttentionConnector):
    """
    Table 1 Footnote Source: LinkedIn
    Coverage ended: 3/12/14. Historical scholarly share mentions.
    """
    def __init__(self):
        self.api_url = "https://api.eventdata.crossref.org/v1/events"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_LINKEDIN", True):
            return ConnectorResult(
                source="linkedin",
                state="not_configured",
                error_message="LinkedIn connector is disabled.",
                item_count=0
            )

        doi = None
        for ident in work.identifiers:
            if ident.scheme == "doi":
                doi = ident.normalized_value
                break

        if not doi:
            return ConnectorResult(source="linkedin", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            target_url = f"https://doi.org/{doi}"
            resp = requests.get(
                self.api_url,
                params={"obj-id": target_url, "source": "linkedin", "rows": 25},
                headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0 (mailto:agent@google.com)"},
                timeout=10
            )
            if resp.status_code == 200:
                events = resp.json().get("message", {}).get("events", [])
                for item in events:
                    subj_id = item.get("subj_id")
                    event_id = item.get("id")
                    evidence.append({
                        "source": "linkedin",
                        "source_type": "share",
                        "external_id": str(event_id),
                        "url": subj_id or target_url,
                        "title": f"LinkedIn Share for {doi}",
                        "published_at": None,
                        "matched_identifier": f"doi:{doi}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": item
                    })

            return ConnectorResult(source="linkedin", state="ready", evidence=evidence, item_count=len(evidence))
        except Exception as e:
            return ConnectorResult(source="linkedin", state="failed", error_code="LINKEDIN_ERROR", error_message=str(e), item_count=0)
