import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class WebOfScienceConnector(AttentionConnector):
    """
    Table 1 Source: Web of Science
    Collection method: Clarivate Analytics API
    Update frequency: Real-time feed
    Notes: Citation counts and indexing from peer-reviewed literature.
    """
    def __init__(self):
        self.api_url = "https://api.clarivate.com/api/wos"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_WEB_OF_SCIENCE", True):
            return ConnectorResult(
                source="web_of_science",
                state="not_configured",
                error_message="Web of Science connector is disabled.",
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
            return ConnectorResult(source="web_of_science", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            api_key = getattr(src.config, "WOS_API_KEY", None)
            if api_key:
                headers = {
                    "X-ApiKey": api_key,
                    "Accept": "application/json"
                }
                usr_query = f"DO={doi}" if doi else f"PMID={pmid}"
                params = {
                    "databaseId": "WOS",
                    "usrQuery": usr_query,
                    "count": 10,
                    "firstRecord": 1
                }
                resp = requests.get(self.api_url, headers=headers, params=params, timeout=10)
                if resp.status_code == 200:
                    records = resp.json().get("Data", {}).get("Records", {}).get("records", {}).get("REC", [])
                    if isinstance(records, dict):
                        records = [records]
                    for rec in records:
                        wos_uid = rec.get("UID")
                        static_data = rec.get("static_data", {})
                        summary = static_data.get("summary", {})
                        pub_info = summary.get("pub_info", {})
                        title = summary.get("titles", {}).get("title", [{}])[0].get("content", "Web of Science Record")
                        citation_data = rec.get("dynamic_data", {}).get("citation_related", {}).get("tc_list", {}).get("silo_tc", {})
                        times_cited = int(citation_data.get("local_count", 0))

                        evidence.append({
                            "source": "web_of_science",
                            "source_type": "citation_record",
                            "external_id": str(wos_uid),
                            "url": f"https://www.webofscience.com/wos/woscc/full-record/{wos_uid}",
                            "title": f"{title} (Web of Science Citations: {times_cited})",
                            "published_at": None,
                            "matched_identifier": f"doi:{doi}" if doi else f"pmid:{pmid}",
                            "match_confidence": "exact_identifier",
                            "raw_reference_json": {**rec, "citation_count": times_cited}
                        })

            return ConnectorResult(
                source="web_of_science",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )
        except Exception as e:
            return ConnectorResult(
                source="web_of_science",
                state="failed",
                error_code="WOS_ERROR",
                error_message=str(e),
                item_count=0
            )
