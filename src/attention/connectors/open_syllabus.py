import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class OpenSyllabusConnector(AttentionConnector):
    """
    Table 1 Source: Open Syllabus
    Collection method: Static Import from Open Syllabus / API
    Update frequency: Quarterly
    Notes: Academic data mining project based at Columbia University that analyzes over 1 million college course syllabi.
    """
    def __init__(self):
        self.api_url = "https://api.opensyllabus.org/v1/works"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_OPEN_SYLLABUS", True):
            return ConnectorResult(
                source="open_syllabus",
                state="not_configured",
                error_message="Open Syllabus connector is disabled.",
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
            return ConnectorResult(source="open_syllabus", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            api_key = getattr(src.config, "OPEN_SYLLABUS_API_KEY", None)
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            params = {}
            if doi:
                params["doi"] = doi
            elif pmid:
                params["pmid"] = pmid

            resp = requests.get(self.api_url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                syllabi = data.get("syllabi", []) if isinstance(data, dict) else []
                for s in syllabi:
                    syllabus_id = str(s.get("id"))
                    course_title = s.get("course_title", "College Course Syllabus")
                    institution = s.get("institution", "Academic Institution")
                    evidence.append({
                        "source": "open_syllabus",
                        "source_type": "syllabus_citation",
                        "external_id": syllabus_id,
                        "url": s.get("url") or f"https://opensyllabus.org/doc/{syllabus_id}",
                        "title": f"{course_title} ({institution})",
                        "published_at": None,
                        "matched_identifier": f"doi:{doi}" if doi else f"pmid:{pmid}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": s
                    })

            return ConnectorResult(
                source="open_syllabus",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )
        except Exception as e:
            return ConnectorResult(
                source="open_syllabus",
                state="failed",
                error_code="OPEN_SYLLABUS_ERROR",
                error_message=str(e),
                item_count=0
            )
