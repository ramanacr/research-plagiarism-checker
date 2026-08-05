import requests
from typing import List, Dict, Any

class EuropePMCClient:
    def __init__(self):
        self.search_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        self.headers = {"User-Agent": "ConfidentialPlagiarismChecker/1.0"}

    def search_and_fetch(self, keywords: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Searches Europe PMC using anonymous keywords and returns parsed article details.
        Uses resultType=core to fetch abstracts and metadata in a single request.
        """
        if not keywords:
            return []

        # Construct AND query, e.g., (sodium AND tenapanor AND kidney)
        query = " AND ".join([f'"{kw}"' for kw in keywords])
        
        params = {
            "query": query,
            "format": "json",
            "resultType": "core",
            "pageSize": max_results
        }

        try:
            response = requests.get(self.search_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("resultList", {}).get("result", [])
            
            # Fallback: relax query if 0 results
            if not results and len(keywords) > 2:
                relaxed_query = " AND ".join([f'"{kw}"' for kw in keywords[:3]])
                params["query"] = relaxed_query
                response = requests.get(self.search_url, params=params, headers=self.headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                results = data.get("resultList", {}).get("result", [])
                
            return self._parse_results(results)
        except Exception as e:
            print(f"Error querying Europe PMC: {e}")
            return []

    def _parse_results(self, raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parses the JSON response from Europe PMC search API."""
        parsed_articles = []
        for res in raw_results:
            # Authors parsing: can be authorString or authorList
            authors = []
            author_string = res.get("authorString", "")
            if author_string:
                authors = [a.strip() for a in author_string.split(",") if a.strip()]
            else:
                author_list = res.get("authorList", {}).get("author", [])
                for auth in author_list:
                    fullName = auth.get("fullName", "")
                    if fullName:
                        authors.append(fullName)

            # Abstract extraction
            abstract = res.get("abstractText", "")
            
            # Journal Name
            journal = res.get("journalTitle") or res.get("journalInfo", {}).get("journal", {}).get("title", "")
            
            # Date
            pub_date = res.get("pubYear", "")
            if not pub_date:
                pub_date = res.get("journalInfo", {}).get("printPublicationDate", "Unknown Date")

            details = {
                "pmid": res.get("pmid", ""),
                "pmcid": res.get("pmcid", ""),
                "title": res.get("title", "").strip(),
                "abstract": abstract.strip() if abstract else "",
                "authors": authors,
                "journal": journal or "Unknown Journal",
                "pub_date": pub_date,
                "doi": res.get("doi", ""),
                "source": "Europe PMC"
            }
            
            # Only append if we have at least a title and either abstract or PMID
            if details["title"] and (details["abstract"] or details["pmid"]):
                parsed_articles.append(details)
                
        return parsed_articles
