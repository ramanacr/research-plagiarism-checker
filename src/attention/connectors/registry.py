from typing import List, Dict, Type, Optional
from src.attention.connectors.base import AttentionConnector

class ConnectorRegistry:
    def __init__(self):
        self._connectors: Dict[str, Type[AttentionConnector]] = {}
        
        # Register Wikimedia/Wikipedia
        from src.attention.connectors.wikimedia import WikimediaConnector
        self._connectors["wikipedia"] = WikimediaConnector

        # Register OpenAlex
        from src.attention.connectors.openalex import OpenAlexConnector
        self._connectors["openalex"] = OpenAlexConnector

        # Register Crossref Event
        from src.attention.connectors.crossref_event import CrossrefEventConnector
        self._connectors["crossref_event"] = CrossrefEventConnector

        # Register PubPeer
        from src.attention.connectors.pubpeer import PubPeerConnector
        self._connectors["pubpeer"] = PubPeerConnector

    def get_connector(self, source: str) -> Optional[AttentionConnector]:
        conn_cls = self._connectors.get(source)
        if not conn_cls:
            return None
        return conn_cls()

    def is_enabled(self, source: str) -> bool:
        import src.config
        if source == "wikipedia":
            return getattr(src.config, "RESEARCH_ATTENTION_ENABLE_WIKIMEDIA", True)
        elif source == "openalex":
            return getattr(src.config, "RESEARCH_ATTENTION_ENABLE_OPENALEX", True)
        elif source == "crossref_event":
            return getattr(src.config, "RESEARCH_ATTENTION_ENABLE_CROSSREF_EVENT", True)
        elif source == "pubpeer":
            return getattr(src.config, "RESEARCH_ATTENTION_ENABLE_PUBPEER", True)
        return False

    def get_all_sources(self) -> List[str]:
        return list(self._connectors.keys())
