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
        self.archive_endpoint = "https://archive.org/advancedsearch.php"

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
            headers = {"User-Agent": "LifeSciencesSuite/1.0 (mailto:admin@example.com)"}
            resp = requests.get(
                self.archive_endpoint,
                params={
                    "q": f'collection:(weibo OR sinanews) AND ("{doi}")',
                    "fl[]": "identifier,title,publicdate",
                    "output": "json",
                    "rows": 10
                },
                headers=headers,
                timeout=6
            )
            if resp.status_code == 200:
                docs = resp.json().get("response", {}).get("docs", [])
                for doc in docs:
                    doc_id = doc.get("identifier")
                    title = doc.get("title") or f"Sina Weibo Historical Post for {doi}"
                    pub_date = None
                    if doc.get("publicdate"):
                        try:
                            pub_date = datetime.date.fromisoformat(doc["publicdate"][:10])
                        except ValueError:
                            pass

                    evidence.append({
                        "source": "sina_weibo",
                        "source_type": "microblog_post",
                        "external_id": str(doc_id),
                        "url": f"https://archive.org/details/{doc_id}",
                        "title": title,
                        "published_at": pub_date,
                        "matched_identifier": f"doi:{doi}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": doc
                    })

            return ConnectorResult(source="sina_weibo", state="ready", evidence=evidence, item_count=len(evidence))
        except Exception:
            return ConnectorResult(source="sina_weibo", state="ready", evidence=[], item_count=0)


class CiteULikeConnector(AttentionConnector):
    """
    Table 1 Footnote Source: CiteULike
    Coverage ended: 12/14. Historical bookmark archive.
    """
    def __init__(self):
        self.archive_endpoint = "https://archive.org/advancedsearch.php"

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
            headers = {"User-Agent": "LifeSciencesSuite/1.0 (mailto:admin@example.com)"}
            resp = requests.get(
                self.archive_endpoint,
                params={
                    "q": f'collection:(citeulike) AND ("{doi}")',
                    "fl[]": "identifier,title,publicdate",
                    "output": "json",
                    "rows": 10
                },
                headers=headers,
                timeout=6
            )
            if resp.status_code == 200:
                docs = resp.json().get("response", {}).get("docs", [])
                for doc in docs:
                    doc_id = doc.get("identifier")
                    title = doc.get("title") or f"CiteULike Bookmark for {doi}"
                    pub_date = None
                    if doc.get("publicdate"):
                        try:
                            pub_date = datetime.date.fromisoformat(doc["publicdate"][:10])
                        except ValueError:
                            pass

                    evidence.append({
                        "source": "citeulike",
                        "source_type": "bookmark",
                        "external_id": str(doc_id),
                        "url": f"https://archive.org/details/{doc_id}",
                        "title": title,
                        "published_at": pub_date,
                        "matched_identifier": f"doi:{doi}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": doc
                    })

            return ConnectorResult(source="citeulike", state="ready", evidence=evidence, item_count=len(evidence))
        except Exception:
            return ConnectorResult(source="citeulike", state="ready", evidence=[], item_count=0)


class PinterestConnector(AttentionConnector):
    """
    Table 1 Footnote Source: Pinterest
    Coverage ended: 6/20/13. Historical pin mentions.
    """
    def __init__(self):
        self.archive_endpoint = "https://archive.org/advancedsearch.php"

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
            headers = {"User-Agent": "LifeSciencesSuite/1.0 (mailto:admin@example.com)"}
            resp = requests.get(
                self.archive_endpoint,
                params={
                    "q": f'collection:(pinterest) AND ("{doi}")',
                    "fl[]": "identifier,title,publicdate",
                    "output": "json",
                    "rows": 10
                },
                headers=headers,
                timeout=6
            )
            if resp.status_code == 200:
                docs = resp.json().get("response", {}).get("docs", [])
                for doc in docs:
                    doc_id = doc.get("identifier")
                    title = doc.get("title") or f"Pinterest Pin for {doi}"
                    pub_date = None
                    if doc.get("publicdate"):
                        try:
                            pub_date = datetime.date.fromisoformat(doc["publicdate"][:10])
                        except ValueError:
                            pass

                    evidence.append({
                        "source": "pinterest",
                        "source_type": "pin",
                        "external_id": str(doc_id),
                        "url": f"https://archive.org/details/{doc_id}",
                        "title": title,
                        "published_at": pub_date,
                        "matched_identifier": f"doi:{doi}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": doc
                    })

            return ConnectorResult(source="pinterest", state="ready", evidence=evidence, item_count=len(evidence))
        except Exception:
            return ConnectorResult(source="pinterest", state="ready", evidence=[], item_count=0)


class LinkedInConnector(AttentionConnector):
    """
    Table 1 Footnote Source: LinkedIn
    Coverage ended: 3/12/14. Historical scholarly share mentions.
    """
    def __init__(self):
        self.archive_endpoint = "https://archive.org/advancedsearch.php"

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
            headers = {"User-Agent": "LifeSciencesSuite/1.0 (mailto:admin@example.com)"}
            resp = requests.get(
                self.archive_endpoint,
                params={
                    "q": f'collection:(linkedin) AND ("{doi}")',
                    "fl[]": "identifier,title,publicdate",
                    "output": "json",
                    "rows": 10
                },
                headers=headers,
                timeout=6
            )
            if resp.status_code == 200:
                docs = resp.json().get("response", {}).get("docs", [])
                for doc in docs:
                    doc_id = doc.get("identifier")
                    title = doc.get("title") or f"LinkedIn Share for {doi}"
                    pub_date = None
                    if doc.get("publicdate"):
                        try:
                            pub_date = datetime.date.fromisoformat(doc["publicdate"][:10])
                        except ValueError:
                            pass

                    evidence.append({
                        "source": "linkedin",
                        "source_type": "share",
                        "external_id": str(doc_id),
                        "url": f"https://archive.org/details/{doc_id}",
                        "title": title,
                        "published_at": pub_date,
                        "matched_identifier": f"doi:{doi}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": doc
                    })

            return ConnectorResult(source="linkedin", state="ready", evidence=evidence, item_count=len(evidence))
        except Exception:
            return ConnectorResult(source="linkedin", state="ready", evidence=[], item_count=0)


