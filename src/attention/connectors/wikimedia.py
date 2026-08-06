import urllib.parse
import requests
import datetime
from typing import List, Dict, Any, Set
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

        pageids = list(evidence_by_pageid.keys())
        verified_pageids = self._verify_pages(pageids, work)
        
        final_evidence = [
            evidence_by_pageid[pid]
            for pid in pageids
            if pid in verified_pageids
        ]
        
        return ConnectorResult(
            source="wikipedia",
            state="ready",
            evidence=final_evidence,
            item_count=len(final_evidence)
        )

    def _verify_pages(self, pageids: List[int], work: ResearchWork) -> Set[int]:
        from typing import Set
        if not pageids:
            return set()

        verified_ids = set()
        
        # Build verification criteria
        dois = []
        pmids = []
        pmcids = []
        for ident in work.identifiers:
            val = ident.normalized_value
            if ident.scheme == "doi":
                dois.append(val.lower())
            elif ident.scheme == "pmid":
                pmids.append(val)
            elif ident.scheme == "pmcid":
                pmcids.append(val.lower())
                pmcids.append(val.replace("PMC", "").lower())

        # Chunk queries by 50 (MediaWiki API limit for pageids)
        chunk_size = 50
        for i in range(0, len(pageids), chunk_size):
            chunk = pageids[i:i+chunk_size]
            try:
                response = requests.get(
                    self.api_url,
                    params={
                        "action": "query",
                        "pageids": "|".join(str(pid) for pid in chunk),
                        "prop": "revisions",
                        "rvprop": "content",
                        "rvslots": "main",
                        "format": "json"
                    },
                    headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0 (mailto:agent@google.com)"},
                    timeout=10
                )
                if response.status_code != 200:
                    verified_ids.update(chunk)
                    continue
                
                data = response.json()
                pages = data.get("query", {}).get("pages", {})
                
                for pid_str, page_info in pages.items():
                    pid = int(pid_str)
                    revisions = page_info.get("revisions", [])
                    if not revisions:
                        continue
                    
                    content = ""
                    rev = revisions[0]
                    if "slots" in rev and "main" in rev["slots"] and "*" in rev["slots"]["main"]:
                        content = rev["slots"]["main"]["*"]
                    elif "*" in rev:
                        content = rev["*"]
                    
                    if not content:
                        continue
                        
                    content_lower = content.lower()
                    is_valid = False
                    
                    # 1. Validate DOIs
                    for doi in dois:
                        if doi in content_lower:
                            is_valid = True
                            break
                    if is_valid:
                        verified_ids.add(pid)
                        continue
                        
                    # 2. Validate PMIDs (must have number AND citation context keywords)
                    for pmid in pmids:
                        if pmid in content_lower:
                            keywords = ["pmid", "pubmed", "ncbi", "cite journal", "citation", "doi", "journal"]
                            if any(kw in content_lower for kw in keywords):
                                is_valid = True
                                break
                    if is_valid:
                        verified_ids.add(pid)
                        continue

                    # 3. Validate PMCIDs
                    for pmcid in pmcids:
                        if pmcid in content_lower:
                            if pmcid.startswith("pmc") or any(kw in content_lower for kw in ["pmc", "pmcid", "pubmed", "ncbi"]):
                                is_valid = True
                                break
                    if is_valid:
                        verified_ids.add(pid)
                        continue

            except Exception:
                # Keep matching pages on transient API error to avoid false negatives
                verified_ids.update(chunk)
                
        return verified_ids
