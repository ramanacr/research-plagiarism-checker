import math
from typing import List, Dict, Any, Optional
from collections import defaultdict

# Research Attention score base weight table
SOURCE_WEIGHTS: Dict[str, float] = {
    "news": 8.0,
    "blogs": 5.0,
    "policy_documents": 3.0,
    "policy": 3.0,
    "wikipedia": 3.0,
    "openalex": 1.0,
    "scopus": 1.0,
    "web_of_science": 1.0,
    "crossref_event": 1.0,
    "pubpeer": 1.0,
    "publons": 1.0,
    "f1000": 1.0,
    "open_syllabus": 1.0,
    "twitter": 1.0,
    "google_plus": 1.0,
    "sina_weibo": 1.0,
    "reddit": 0.25,
    "stackoverflow": 0.25,
    "facebook": 0.25,
    "youtube": 0.25,
    "pinterest": 0.25,
    "linkedin": 0.25,
    # Readership counts are tracked separately in readership metrics
    "mendeley": 0.0,
}


# Distinct Attention Channel Colors for Visualization Wheel
DONUT_COLORS: Dict[str, str] = {
    "policy_documents": "#762a83",  # Purple
    "policy": "#762a83",
    "news": "#d73027",              # Red
    "blogs": "#fee08b",             # Yellow
    "twitter": "#4575b4",           # Light Blue
    "pubpeer": "#66c2a5",           # Pale Teal / Post-publication peer-reviews
    "publons": "#66c2a5",
    "facebook": "#1877f2",          # Dark Blue
    "sina_weibo": "#f46d43",        # Light Orange
    "wikipedia": "#7f7f7f",         # Grey
    "google_plus": "#c51b7d",       # Magenta / Purple
    "linkedin": "#0077b5",          # Medium Blue
    "reddit": "#ff4500",            # Coral / Red-orange
    "f1000": "#fc8d59",             # Orange (Faculty1000)
    "stackoverflow": "#f48024",     # Orange (Q&A Stack Overflow)
    "youtube": "#e41a1c",           # Video Red
    "pinterest": "#bd0026",         # Dark Red
    "open_syllabus": "#31a354",     # Green / Cyan
    "mendeley": "#2b83ba",          # Teal Blue (Readership)
    "scopus": "#2b83ba",            # Citation Slate
    "web_of_science": "#2b83ba",    # Citation Slate
    "openalex": "#2b83ba",
    "crossref_event": "#8073ac"
}

def get_normalized_last_name(name: str) -> str:
    """
    Extracts canonical lower-case last name for author matching.
    Handles 'Liegel, John', 'John Liegel', 'Liegel J', 'Liegel'.
    """
    name = name.strip().lower()
    if "," in name:
        return name.split(",")[0].strip()
    parts = name.split()
    if len(parts) > 1 and len(parts[-1]) > 1:
        return parts[-1]
    return parts[0]

def check_self_citation(work_authors: List[str], citing_authors: List[str]) -> bool:
    """
    Returns True if any author of the citing paper matches an author of the original work.
    """
    if not work_authors or not citing_authors:
        return False
    work_last_names = {get_normalized_last_name(a) for a in work_authors if a}
    for ca in citing_authors:
        if get_normalized_last_name(ca) in work_last_names:
            return True
    return False

def extract_author_identifier(evidence_item: Dict[str, Any]) -> str:
    """
    Extracts or derives a unique author / poster identifier for Volume deduplication.
    Volume rule: Only 1 mention from each person per source is counted.
    """
    raw = evidence_item.get("raw_reference_json") or {}
    
    # Check common author fields across providers
    if isinstance(raw, dict):
        if "author" in raw and raw["author"]:
            if isinstance(raw["author"], str):
                return raw["author"].strip().lower()
            elif isinstance(raw["author"], dict) and "name" in raw["author"]:
                return str(raw["author"]["name"]).strip().lower()
        if "author_id" in raw:
            return str(raw["author_id"]).strip().lower()
        if "user" in raw and isinstance(raw["user"], dict) and "screen_name" in raw["user"]:
            return f"@{raw['user']['screen_name']}".lower()
        if "user" in raw and isinstance(raw["user"], str):
            return raw["user"].strip().lower()
        if "user_id" in raw:
            return str(raw["user_id"]).strip().lower()
        if "channel_id" in raw:
            return str(raw["channel_id"]).strip().lower()
        if "subreddit" in raw:
            return f"r/{raw['subreddit']}".lower()

    # Fallback to external_id or URL hostname
    ext_id = evidence_item.get("external_id")
    if ext_id:
        return str(ext_id).strip().lower()
        
    url = evidence_item.get("url", "")
    return url.strip().lower()

class AttentionScoreCalculator:
    """
    Calculates the Research Attention Score, author volume deduplication,
    and self-citation vs independent citation isolation.
    """

    @classmethod
    def calculate_score(cls, evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculates the Research Attention Score from active evidence items.
        Applies:
        - Source-level weighting
        - Unique author per source volume deduplication
        - Visual wheel representation mapping
        - Separation of independent citations and author self-citations
        """

        # Deduplicate mentions per author per source
        source_authors: Dict[str, set] = defaultdict(set)
        source_effective_mentions: Dict[str, int] = defaultdict(int)
        source_subscores: Dict[str, float] = defaultdict(float)
        
        # Readers and citations are tracked alongside attention score
        mendeley_readers = 0
        citation_counts = 0
        independent_citations = 0
        self_citations = 0

        for item in evidence_list:
            # Only consider active evidence
            if not item.get("active", True):
                continue

            source = (item.get("source") or "unknown").lower()
            source_type = (item.get("source_type") or "").lower()
            raw = item.get("raw_reference_json") or {}
            
            # Special category tracking: Readership
            if source == "mendeley":
                readers = raw.get("reader_count", 1) if isinstance(raw, dict) else 1
                mendeley_readers += int(readers)
                continue

            # Special category tracking: Academic Citations (OpenAlex, Scopus, Web of Science, CrossRef)
            if source_type in ("citation", "academic_citation", "citation_record") or source in ("scopus", "web_of_science", "openalex"):
                is_self = raw.get("is_self_citation", False) if isinstance(raw, dict) else False
                count = raw.get("citation_count", 1) if isinstance(raw, dict) and "citation_count" in raw else 1
                
                citation_counts += int(count)
                if is_self:
                    self_citations += int(count)
                else:
                    independent_citations += int(count)
                    # Independent scholarly citations feed into the research attention score
                    author_id = extract_author_identifier(item)
                    if author_id not in source_authors[source]:
                        source_authors[source].add(author_id)
                        source_effective_mentions[source] += 1
                        weight = SOURCE_WEIGHTS.get(source, 1.0)
                        source_subscores[source] += weight
                continue


            author_id = extract_author_identifier(item)
            
            # Volume rule: 1 mention per author per source counted
            if author_id not in source_authors[source]:
                source_authors[source].add(author_id)
                source_effective_mentions[source] += 1
                weight = SOURCE_WEIGHTS.get(source, 1.0)
                source_subscores[source] += weight

        raw_score = sum(source_subscores.values())
        # Rounds up to nearest whole integer when > 0
        integer_score = math.ceil(raw_score) if raw_score > 0 else 0

        # Formulate donut breakdown
        donut_slices = []
        for source, subscore in source_subscores.items():
            if subscore > 0:
                percentage = round((subscore / raw_score) * 100, 2) if raw_score > 0 else 0
                donut_slices.append({
                    "source": source,
                    "color": DONUT_COLORS.get(source, "#7f7f7f"),
                    "unique_authors": len(source_authors[source]),
                    "subscore": round(subscore, 2),
                    "percentage": percentage
                })

        # Sort donut slices by subscore descending
        donut_slices.sort(key=lambda s: s["subscore"], reverse=True)

        return {
            "score": round(raw_score, 2),
            "integer_score": integer_score,
            "donut": {
                "total_score": integer_score,
                "slices": donut_slices
            },
            "metrics": {
                "mendeley_readers": mendeley_readers,
                "citation_counts": citation_counts,
                "independent_citations": independent_citations,
                "self_citations": self_citations,
                "total_unique_contributors": sum(len(authors) for authors in source_authors.values())
            }
        }


# Backward-compatibility alias
AltmetricScoreCalculator = AttentionScoreCalculator


