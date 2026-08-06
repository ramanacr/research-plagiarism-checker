from typing import List, Dict, Type, Optional
from src.attention.connectors.base import AttentionConnector
from src.config import RESEARCH_ATTENTION_ENABLE_WIKIMEDIA

class ConnectorRegistry:
    def __init__(self):
        self._connectors: Dict[str, Type[AttentionConnector]] = {}
        
        # Register Wikimedia/Wikipedia
        from src.attention.connectors.wikimedia import WikimediaConnector
        self._connectors["wikipedia"] = WikimediaConnector

    def get_connector(self, source: str) -> Optional[AttentionConnector]:
        conn_cls = self._connectors.get(source)
        if not conn_cls:
            return None
        return conn_cls()

    def is_enabled(self, source: str) -> bool:
        if source == "wikipedia":
            return RESEARCH_ATTENTION_ENABLE_WIKIMEDIA
        return False

    def get_all_sources(self) -> List[str]:
        return list(self._connectors.keys())
