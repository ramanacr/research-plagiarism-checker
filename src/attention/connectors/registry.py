from typing import List, Dict, Type, Optional
from src.attention.connectors.base import AttentionConnector

class ConnectorRegistry:
    def __init__(self):
        self._connectors: Dict[str, Type[AttentionConnector]] = {}
        
        # Core & existing connectors
        from src.attention.connectors.wikimedia import WikimediaConnector
        self._connectors["wikipedia"] = WikimediaConnector

        from src.attention.connectors.openalex import OpenAlexConnector
        self._connectors["openalex"] = OpenAlexConnector

        from src.attention.connectors.crossref_event import CrossrefEventConnector
        self._connectors["crossref_event"] = CrossrefEventConnector

        from src.attention.connectors.pubpeer import PubPeerConnector
        self._connectors["pubpeer"] = PubPeerConnector

        # Table 1: Altmetric Data Collection Sources
        from src.attention.connectors.twitter import TwitterConnector
        self._connectors["twitter"] = TwitterConnector

        from src.attention.connectors.facebook import FacebookConnector
        self._connectors["facebook"] = FacebookConnector

        from src.attention.connectors.policy_documents import PolicyDocumentsConnector
        self._connectors["policy_documents"] = PolicyDocumentsConnector

        from src.attention.connectors.news import NewsConnector
        self._connectors["news"] = NewsConnector

        from src.attention.connectors.blogs import BlogsConnector
        self._connectors["blogs"] = BlogsConnector

        from src.attention.connectors.mendeley import MendeleyConnector
        self._connectors["mendeley"] = MendeleyConnector

        from src.attention.connectors.scopus import ScopusConnector
        self._connectors["scopus"] = ScopusConnector

        from src.attention.connectors.publons import PublonsConnector
        self._connectors["publons"] = PublonsConnector

        from src.attention.connectors.reddit import RedditConnector
        self._connectors["reddit"] = RedditConnector

        from src.attention.connectors.stackoverflow import StackOverflowConnector
        self._connectors["stackoverflow"] = StackOverflowConnector

        from src.attention.connectors.f1000 import F1000Connector
        self._connectors["f1000"] = F1000Connector

        from src.attention.connectors.google_plus import GooglePlusConnector
        self._connectors["google_plus"] = GooglePlusConnector

        from src.attention.connectors.youtube import YouTubeConnector
        self._connectors["youtube"] = YouTubeConnector

        from src.attention.connectors.open_syllabus import OpenSyllabusConnector
        self._connectors["open_syllabus"] = OpenSyllabusConnector

        from src.attention.connectors.web_of_science import WebOfScienceConnector
        self._connectors["web_of_science"] = WebOfScienceConnector

        # Table 1 Footnote: Discontinued / Historical Sources
        from src.attention.connectors.legacy_sources import (
            SinaWeiboConnector,
            CiteULikeConnector,
            PinterestConnector,
            LinkedInConnector
        )
        self._connectors["sina_weibo"] = SinaWeiboConnector
        self._connectors["citeulike"] = CiteULikeConnector
        self._connectors["pinterest"] = PinterestConnector
        self._connectors["linkedin"] = LinkedInConnector

    def get_connector(self, source: str) -> Optional[AttentionConnector]:
        conn_cls = self._connectors.get(source)
        if not conn_cls:
            return None
        return conn_cls()

    def is_enabled(self, source: str) -> bool:
        import src.config
        flag_name = f"RESEARCH_ATTENTION_ENABLE_{source.upper()}"
        if source == "wikipedia":
            flag_name = "RESEARCH_ATTENTION_ENABLE_WIKIMEDIA"
        return getattr(src.config, flag_name, True)

    def get_all_sources(self) -> List[str]:
        return list(self._connectors.keys())

