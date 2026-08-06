import urllib.parse
import requests
import datetime
from typing import List, Dict, Any
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class WikimediaConnector(AttentionConnector):
    def __init__(self):
        self.api_url = "https://en.wikipedia.org/w/api.php"

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not src.config.RESEARCH_ATTENTION_ENABLE_WIKIMEDIA:
            return ConnectorResult(
                source="wikipedia",
                state="not_configured",
                error_message="Wikimedia connector is disabled.",
                item_count=0
            )

        # 1. Collect all valid identifiers to search
        search_terms = []
        
        # We need to query work identifiers
        # We can extract them directly from work.identifiers
        for ident in work.identifiers:
            val = ident.normalized_value
            if ident.scheme == "doi":
                search_terms.append((f"doi:{val}", f'"{val}"'))
            elif ident.scheme == "pmid":
                search_terms.append((f"pmid:{val}", f'"pmid {val}"'))
            elif ident.scheme == "pmcid":
                search_terms.append((f"pmcid:{val}", f'"{val}"'))
                # If PMC prefix is present, also search for contextual keywords with raw number
                raw_pmc = val.replace("PMC", "")
                search_terms.append((f"pmcid:{val}", f'"pmcid {raw_pmc}"'))
                search_terms.append((f"pmcid:{val}", f'"pmc {raw_pmc}"'))

        if not search_terms:
            return ConnectorResult(source="wikipedia", state="ready", evidence=[], item_count=0)

        # 2. Run searches on Wikipedia API and coalesce results at pageid level
        evidence_by_pageid: Dict[int, Dict[str, Any]] = {}

        for matched_id, query_term in search_terms:
            try:
                response = requests.get(
                    self.api_url,
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": query_term,
                        "format": "json",
                        "srlimit": 50
                    },
                    headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0 (mailto:agent@google.com)"},
                    timeout=10
                )
                if response.status_code != 200:
                    continue
                
                data = response.json()
                search_results = data.get("query", {}).get("search", [])
                
                for res in search_results:
                    pageid = res.get("pageid")
                    title = res.get("title")
                    if not pageid or not title:
                        continue
                    
                    # Deduplicate: if already found via another identifier, skip or keep first
                    if pageid not in evidence_by_pageid:
                        # Construct Wikipedia URL
                        safe_title = urllib.parse.quote(title.replace(" ", "_"))
                        url = f"https://en.wikipedia.org/wiki/{safe_title}"
                        
                        # Timestamp
                        timestamp_str = res.get("timestamp")
                        published_at = None
                        if timestamp_str:
                            try:
                                # ISO string conversion
                                dt = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                                published_at = dt.date()
                            except ValueError:
                                pass

                        evidence_by_pageid[pageid] = {
                            "source": "wikipedia",
                            "source_type": "reference",
                            "external_id": str(pageid),
                            "url": url,
                            "title": title,
                            "published_at": published_at,
                            "matched_identifier": matched_id,
                            "match_confidence": "exact_identifier",
                            "raw_reference_json": res
                        }
            except Exception:
                # We log or ignore individual query term network issues and proceed to next term
                pass

        evidence_list = list(evidence_by_pageid.values())
        return ConnectorResult(
            source="wikipedia",
            state="ready",
            evidence=evidence_list,
            item_count=len(evidence_list)
        )
