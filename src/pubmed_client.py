import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from src.config import PUBMED_ESEARCH_URL, PUBMED_EFETCH_URL, MAX_PUBMED_RESULTS

class PubMedClient:
    def __init__(self):
        # We can add an email or API key parameter if needed for higher rate limits
        self.headers = {"User-Agent": "ConfidentialPlagiarismChecker/1.0"}

    def search_articles(self, keywords: List[str]) -> List[str]:
        """
        Searches PubMed using anonymous keywords linked with AND.
        Returns a list of PubMed IDs (PMIDs).
        """
        if not keywords:
            return []

        # Construct term query: quote each keyword to ensure exact phrase matching, joined by AND
        quoted_terms = [f'"{kw}"' for kw in keywords]
        query = " AND ".join(quoted_terms)

        params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": MAX_PUBMED_RESULTS
        }

        try:
            response = requests.get(PUBMED_ESEARCH_URL, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])
            
            # Fallback: if zero results, try relaxing the search (using OR or fewer keywords)
            if not id_list and len(keywords) > 2:
                # Try with top 3 keywords
                query_relaxed = " AND ".join([f'"{kw}"' for kw in keywords[:3]])
                params["term"] = query_relaxed
                response = requests.get(PUBMED_ESEARCH_URL, params=params, headers=self.headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                id_list = data.get("esearchresult", {}).get("idlist", [])
                
            return id_list
        except Exception as e:
            print(f"Error searching PubMed: {e}")
            return []

    def fetch_article_details(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetches detailed information (Title, Abstract, Authors, Journal, DOI)
        for a list of PMIDs using official EFetch XML API.
        """
        if not pmids:
            return []

        pmids_str = ",".join(pmids)
        params = {
            "db": "pubmed",
            "id": pmids_str,
            "retmode": "xml"
        }

        try:
            response = requests.get(PUBMED_EFETCH_URL, params=params, headers=self.headers, timeout=15)
            response.raise_for_status()
            return self._parse_pubmed_xml(response.content)
        except Exception as e:
            print(f"Error fetching details from PubMed: {e}")
            return []

    def _parse_pubmed_xml(self, xml_content: bytes) -> List[Dict[str, Any]]:
        """Parses the XML returned by NCBI EFetch to extract relevant fields."""
        articles = []
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            print(f"XML parse error: {e}")
            return []

        for article_element in root.findall(".//PubmedArticle"):
            details = {}
            
            # PMID
            pmid_el = article_element.find(".//PMID")
            details["pmid"] = pmid_el.text if pmid_el is not None else ""
            
            # Title
            title_el = article_element.find(".//ArticleTitle")
            details["title"] = "".join(title_el.itertext()).strip() if title_el is not None else ""
            
            # Abstract
            abstract_texts = []
            abstract_el = article_element.find(".//Abstract")
            if abstract_el is not None:
                for text_el in abstract_el.findall("AbstractText"):
                    label = text_el.get("Label")
                    text_content = "".join(text_el.itertext()).strip()
                    if label:
                        abstract_texts.append(f"{label}: {text_content}")
                    else:
                        abstract_texts.append(text_content)
            details["abstract"] = "\n".join(abstract_texts) if abstract_texts else ""
            
            # Authors
            authors = []
            author_list = article_element.find(".//AuthorList")
            if author_list is not None:
                for author in author_list.findall("Author"):
                    fore = author.find("ForeName")
                    last = author.find("LastName")
                    if last is not None:
                        fore_name = fore.text if fore is not None else ""
                        last_name = last.text if last is not None else ""
                        authors.append(f"{fore_name} {last_name}".strip())
            details["authors"] = authors
            
            # Journal Name
            journal_el = article_element.find(".//Journal/Title")
            details["journal"] = journal_el.text if journal_el is not None else ""
            
            # Pub Date
            pub_date = ""
            year_el = article_element.find(".//JournalIssue/PubDate/Year")
            month_el = article_element.find(".//JournalIssue/PubDate/Month")
            if year_el is not None:
                pub_date = year_el.text
                if month_el is not None:
                    pub_date += f" {month_el.text}"
            else:
                medline_date_el = article_element.find(".//JournalIssue/PubDate/MedlineDate")
                if medline_date_el is not None:
                    pub_date = medline_date_el.text
            details["pub_date"] = pub_date or "Unknown Date"
            
            # DOI
            doi = ""
            for el in article_element.findall(".//ArticleIdList/ArticleId"):
                if el.get("IdType") == "doi":
                    doi = el.text
                    break
            details["doi"] = doi
            
            articles.append(details)
            
        return articles
