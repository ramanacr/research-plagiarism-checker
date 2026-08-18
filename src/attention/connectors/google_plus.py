import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class GooglePlusConnector(AttentionConnector):
    """
    Table 1 Source: Google+
    Collection method: Google+ Public archive
    Update frequency: Daily
    Notes: An internet based social network. Public posts only (discontinued platform archive).
    """
    def __init__(self):
        # Historical archive index
        self.archive_endpoint = "https://archive.org/advancedsearch.php"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_GOOGLE_PLUS", True):
            return ConnectorResult(
                source="google_plus",
                state="not_configured",
                error_message="Google+ connector is disabled.",
                item_count=0
            )

        doi = None
        for ident in work.identifiers:
            if ident.scheme == "doi":
                doi = ident.normalized_value
                break

        if not doi:
            return ConnectorResult(source="google_plus", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            # Query Internet Archive / Wayback collection for historical Google+ posts referencing the DOI
            headers = {"User-Agent": "LifeSciencesSuite/1.0 (mailto:admin@example.com)"}
            resp = requests.get(
                self.archive_endpoint,
                params={
                    "q": f'collection:(googleplus) AND ("{doi}")',
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
                    title = doc.get("title") or f"Google+ Public Post for {doi}"
                    pub_date = None
                    if doc.get("publicdate"):
                        try:
                            pub_date = datetime.date.fromisoformat(doc["publicdate"][:10])
                        except ValueError:
                            pass

                    evidence.append({
                        "source": "google_plus",
                        "source_type": "post",
                        "external_id": str(doc_id),
                        "url": f"https://archive.org/details/{doc_id}",
                        "title": title,
                        "published_at": pub_date,
                        "matched_identifier": f"doi:{doi}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": doc
                    })

            return ConnectorResult(
                source="google_plus",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )
        except Exception:
            return ConnectorResult(
                source="google_plus",
                state="ready",
                evidence=[],
                item_count=0
            )
