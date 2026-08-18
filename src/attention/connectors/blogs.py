import datetime
from typing import List, Dict, Any, Optional
import requests
import src.config
from src.attention.connectors.base import AttentionConnector, ConnectorResult
from src.attention.models import ResearchWork

class BlogsConnector(AttentionConnector):
    """
    Table 1 Source: Blogs
    Collection method: RSS feeds & Curated Academic Blog Directories
    Update frequency: Daily
    Notes: Tracks a curated whitelist of scientific and academic blogs 
           via direct RSS feeds (e.g. PLOS Blogs, BioMed Central, ScienceBlogs, Nature Communities,
           The Node, Retraction Watch, Hypotheses.org) and scholarly commentary indices.
    """
    # Curated life sciences and academic blog feeds
    CURATED_BLOG_FEEDS = [
        {"name": "PLOS Blogs", "feed": "https://blogs.plos.org/feed/", "url": "https://blogs.plos.org"},
        {"name": "BioMed Central Blogs", "feed": "https://blogs.biomedcentral.com/feed/", "url": "https://blogs.biomedcentral.com"},
        {"name": "ScienceBlogs", "feed": "https://scienceblogs.com/feed", "url": "https://scienceblogs.com"},
        {"name": "The Node (Biology)", "feed": "https://thenode.biologists.com/feed/", "url": "https://thenode.biologists.com"},
        {"name": "Retraction Watch", "feed": "https://retractionwatch.com/feed/", "url": "https://retractionwatch.com"},
        {"name": "Nature Ecology & Evolution", "feed": "https://natureecoevocommunity.nature.com/feed", "url": "https://natureecoevocommunity.nature.com"}
    ]

    def __init__(self):
        self.openalex_api = "https://api.openalex.org/works"
        self.feeds = self.CURATED_BLOG_FEEDS

    def collect(self, work: ResearchWork) -> ConnectorResult:
        if not getattr(src.config, "RESEARCH_ATTENTION_ENABLE_BLOGS", True):
            return ConnectorResult(
                source="blogs",
                state="not_configured",
                error_message="Blogs connector is disabled.",
                item_count=0
            )

        doi = None
        openalex_id = None
        for ident in work.identifiers:
            if ident.scheme == "doi":
                doi = ident.normalized_value
            elif ident.scheme == "openalex_id":
                openalex_id = ident.normalized_value

        if not doi and not openalex_id:
            return ConnectorResult(source="blogs", state="ready", evidence=[], item_count=0)

        evidence = []
        headers = {"User-Agent": "LifeSciencesSuite/1.0 (mailto:admin@example.com)"}

        # 1. Query OpenAlex Scholarly Commentary & Academic Letters
        try:
            filter_query = f"cites:{openalex_id.split('/')[-1]}" if openalex_id else f"cites:doi:{doi}"
            filter_query += ",type:letter"
            resp = requests.get(self.openalex_api, params={"filter": filter_query, "per_page": 50}, headers=headers, timeout=8)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                for item in results:
                    item_id = item.get("id")
                    title = item.get("title") or "Academic Blog / Commentary Post"
                    pub_date = None
                    if item.get("publication_date"):
                        try:
                            pub_date = datetime.date.fromisoformat(item["publication_date"])
                        except ValueError:
                            pass

                    landing_page = item.get("primary_location", {}).get("landing_page_url") or item_id

                    evidence.append({
                        "source": "blogs",
                        "source_type": "blog_post",
                        "external_id": str(item_id),
                        "url": landing_page,
                        "title": title,
                        "published_at": pub_date,
                        "matched_identifier": f"doi:{doi}" if doi else f"openalex:{openalex_id}",
                        "match_confidence": "exact_identifier",
                        "raw_reference_json": item
                    })
        except Exception:
            pass

        # 2. Check Curated Life Sciences RSS Feeds (Scanning recent posts for DOI or Title match)
        search_terms = [doi.lower()] if doi else []
        if work.normalized_title and len(work.normalized_title) > 20:
            search_terms.append(work.normalized_title[:40].lower())

        for blog in self.feeds:
            try:
                feed_resp = requests.get(blog["feed"], headers=headers, timeout=4)
                if feed_resp.status_code == 200:
                    text_content = feed_resp.text.lower()
                    for term in search_terms:
                        if term in text_content:
                            evidence.append({
                                "source": "blogs",
                                "source_type": "blog_post",
                                "external_id": f"{blog['name']}_{doi or work.id}",
                                "url": blog["url"],
                                "title": f"Mentioned on {blog['name']}",
                                "published_at": datetime.date.today(),
                                "matched_identifier": f"doi:{doi}" if doi else f"work:{work.id}",
                                "match_confidence": "text_mention",
                                "raw_reference_json": {"blog": blog["name"], "feed": blog["feed"]}
                            })
                            break
            except Exception:
                continue

        return ConnectorResult(
            source="blogs",
            state="ready",
            evidence=evidence,
            item_count=len(evidence)
        )



