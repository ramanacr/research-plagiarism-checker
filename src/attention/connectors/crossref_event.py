import requests
import datetime
from typing import List, Dict, Any
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork
import src.config

class CrossrefEventConnector(AttentionConnector):
    def __init__(self):
        self.api_url = "https://api.crossref.org/works"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_CROSSREF_EVENT", True):
            return ConnectorResult(
                source="crossref_event",
                state="not_configured",
                error_message="Crossref Event connector is disabled.",
                item_count=0
            )

        doi = None
        for ident in work.identifiers:
            if ident.scheme == "doi":
                doi = ident.normalized_value
                break

        if not doi:
            return ConnectorResult(source="crossref_event", state="ready", evidence=[], item_count=0)

        evidence = []
        try:
            headers = {"User-Agent": "LifeSciencesSuite/1.0 (mailto:admin@example.com)"}
            resp = requests.get(f"{self.api_url}/{doi}", headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json().get("message", {})
                
                # Check Crossref third-party inbound relationships (cited-by, supplemented-by, referenced-by)
                INBOUND_RELATION_TYPES = {
                    "is-cited-by",
                    "is-supplemented-by",
                    "is-referenced-by",
                    "is-documented-by",
                    "is-compiled-by"
                }
                relations = data.get("relation", {})
                for rel_type, items in relations.items():
                    if rel_type.lower() in INBOUND_RELATION_TYPES:
                        for item in items:
                            item_id = item.get("id")
                            evidence.append({
                                "source": "crossref_event",
                                "source_type": "inbound_relation",
                                "external_id": str(item_id),
                                "url": item_id if str(item_id).startswith("http") else f"https://doi.org/{item_id}",
                                "title": f"Crossref {rel_type.replace('-', ' ').title()}",
                                "published_at": None,
                                "matched_identifier": f"doi:{doi}",
                                "match_confidence": "canonical_url",
                                "raw_reference_json": item
                            })

                # Check Crossref third-party registered components (clinical trials, external data repositories)
                assertions = data.get("assertion", [])
                for ast in assertions:
                    if ast.get("name") in ["clinical-trial-number", "data-availability", "supplementary-material"]:
                        evidence.append({
                            "source": "crossref_event",
                            "source_type": "inbound_assertion",
                            "external_id": f"{ast.get('name')}_{ast.get('value', '')}",
                            "url": ast.get("value") if str(ast.get("value", "")).startswith("http") else f"https://doi.org/{doi}",
                            "title": ast.get("label", ast.get("name")),
                            "published_at": None,
                            "matched_identifier": f"doi:{doi}",
                            "match_confidence": "canonical_url",
                            "raw_reference_json": ast
                        })


            return ConnectorResult(
                source="crossref_event",
                state="ready",
                evidence=evidence,
                item_count=len(evidence)
            )

        except Exception as e:
            return ConnectorResult(
                source="crossref_event",
                state="ready",
                evidence=[],
                item_count=0
            )


