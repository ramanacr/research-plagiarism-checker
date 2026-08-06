import xml.etree.ElementTree as ET
import requests
import datetime
from typing import Optional
from src.attention.providers.base import IdentityProvider, normalize_doi, normalize_pmid
from src.attention.schemas import ResolvedWork
from src.config import PUBMED_EFETCH_URL

class PubMedProvider(IdentityProvider):
    def __init__(self):
        self.url = PUBMED_EFETCH_URL

    def resolve_pmid(self, pmid: str) -> Optional[ResolvedWork]:
        normalized = normalize_pmid(pmid)
        if not normalized:
            return None
        
        try:
            response = requests.get(
                self.url,
                params={"db": "pubmed", "id": normalized, "retmode": "xml"},
                headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0"},
                timeout=10
            )
            if response.status_code != 200:
                return None
            
            root = ET.fromstring(response.content)
            article = root.find(".//PubmedArticle")
            if article is None:
                return None
            
            # Parse title
            title_node = article.find(".//ArticleTitle")
            title = "".join(title_node.itertext()).strip() if title_node is not None else "Unknown Title"
            
            # Parse journal
            journal_node = article.find(".//Journal/Title")
            journal = journal_node.text.strip() if journal_node is not None else None
            
            # Parse date
            pub_date = None
            date_node = article.find(".//JournalIssue/PubDate")
            if date_node is not None:
                year_node = date_node.find("Year")
                month_node = date_node.find("Month")
                day_node = date_node.find("Day")
                if year_node is not None and year_node.text:
                    try:
                        year = int(year_node.text)
                        month = 1
                        if month_node is not None and month_node.text:
                            m_str = month_node.text.lower()
                            months = {
                                "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                                "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
                            }
                            month = months.get(m_str[:3], 1)
                        day = 1
                        if day_node is not None and day_node.text:
                            try:
                                day = int(day_node.text)
                            except ValueError:
                                pass
                        pub_date = datetime.date(year, month, day)
                    except ValueError:
                        pass
                        
            # Parse authors
            authors = []
            author_nodes = article.findall(".//AuthorList/Author")
            for author in author_nodes:
                last_name = author.find("LastName")
                fore_name = author.find("ForeName")
                if last_name is not None and last_name.text:
                    fn = fore_name.text if fore_name is not None and fore_name.text else ""
                    authors.append(f"{fn} {last_name.text}".strip())
                    
            # Extract IDs (DOI, PMCID)
            doi = None
            el_ids = article.findall(".//ArticleIdList/ArticleId")
            for el_id in el_ids:
                if el_id.attrib.get("IdType") == "doi" and el_id.text:
                    doi = normalize_doi(el_id.text.strip())
                    break
                    
            pmcid = None
            for el_id in el_ids:
                if el_id.attrib.get("IdType") == "pmc" and el_id.text:
                    pmcid = el_id.text.strip()
                    if not pmcid.startswith("PMC"):
                        pmcid = f"PMC{pmcid}"
                    break

            return ResolvedWork(
                title=title,
                journal=journal,
                publication_date=pub_date,
                authors=authors,
                pmid=normalized,
                doi=doi,
                pmcid=pmcid
            )
            
        except Exception:
            return None

    def resolve_doi(self, doi: str) -> Optional[ResolvedWork]:
        normalized = normalize_doi(doi)
        if not normalized:
            return None
        try:
            url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            response = requests.get(
                url,
                params={"db": "pubmed", "term": f'"{normalized}"[AID]', "retmode": "json"},
                headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                id_list = data.get("esearchresult", {}).get("idlist", [])
                if id_list:
                    return self.resolve_pmid(id_list[0])
        except Exception:
            pass
        return None
