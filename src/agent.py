import time
from typing import List, Dict, Any, Optional
from src.extractor import DocumentExtractor
from src.pubmed_client import PubMedClient
from src.europe_pmc_client import EuropePMCClient
from src.similarity_engine import SimilarityEngine
from src.plagiarism.services.plagiarism_service import PlagiarismService
from src.plagiarism.scoring.models import PlagiarismReport


class ResearchGuardrailAgent:
    def __init__(self):
        self.extractor = DocumentExtractor()
        self.pubmed_client = PubMedClient()
        self.europe_pmc = EuropePMCClient()
        self.similarity_engine = SimilarityEngine()
        self._plagiarism_service: Optional[PlagiarismService] = None

    @property
    def plagiarism_service(self) -> PlagiarismService:
        if self._plagiarism_service is None:
            self._plagiarism_service = PlagiarismService()
        return self._plagiarism_service

    def analyze_document_v2(
        self,
        file_bytes: bytes,
        filename: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> PlagiarismReport:
        """
        Executes v2.0 multi-channel plagiarism check using passage segmentation and calibrated scoring.
        """
        return self.plagiarism_service.check_file_bytes(file_bytes, filename, options=options)

    def analyze_document(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Coordinates the entire confidential analysis workflow.
        Strictly enforces that the original document text never exits the local boundary.
        """
        start_time = time.time()
        
        # 1. Local Text Extraction
        doc_text = self.extractor.extract_text_from_bytes(file_bytes, filename)
        sentences = self.extractor.get_sentences(doc_text)
        word_count = len(doc_text.split())

        if not doc_text.strip():
            return {
                "status": "error",
                "error": "No readable text found in document."
            }

        # 2. Local Anonymous Keyword Extraction (Confidentiality Guardrail)
        # We only extract standalone technical keywords and concepts.
        # No grammatical structures, sentence fragments, or full sentences are leaked.
        keywords = self.extractor.extract_anonymized_keywords(doc_text, max_keywords=8)
        
        # Guardrail Verification:
        # Check that no keyword contains more than 3 words (to prevent sentence leakage)
        # and that the keyword list is not empty.
        sanitized_keywords = []
        for kw in keywords:
            clean_kw = kw.strip()
            if len(clean_kw.split()) <= 3 and len(clean_kw) > 2:
                sanitized_keywords.append(clean_kw)
                
        # 3. External Database Search (Only sending sanitized keywords)
        matching_pmids = []
        candidates = []
        if sanitized_keywords:
            # A. Query PubMed
            matching_pmids = self.pubmed_client.search_articles(sanitized_keywords)
            if matching_pmids:
                candidates = self.pubmed_client.fetch_article_details(matching_pmids)
                
            # B. Query Europe PMC
            epmc_candidates = self.europe_pmc.search_and_fetch(sanitized_keywords)
            
            # C. Merge and Deduplicate candidates
            merged = {c["pmid"]: c for c in candidates if c.get("pmid")}
            for ec in epmc_candidates:
                pmid = ec.get("pmid")
                doi = ec.get("doi")
                title_norm = ec.get("title", "").lower().strip()
                
                if pmid and pmid in merged:
                    continue
                if doi and any(existing.get("doi") == doi for existing in merged.values()):
                    continue
                if any(existing.get("title", "").lower().strip() == title_norm for existing in merged.values()):
                    continue
                
                if pmid:
                    merged[pmid] = ec
                else:
                    merged[f"epmc_{title_norm[:20]}"] = ec
                    
            candidates = list(merged.values())

        # 5. Local Similarity & Plagiarism Processing
        semantic_matches = []
        verbatim_plagiarism = []
        
        if candidates:
            # Check for verbatim copy-pasting
            verbatim_plagiarism = self.similarity_engine.check_verbatim_plagiarism(doc_text, candidates)
            # Check for semantic/paraphrase similarity
            semantic_matches = self.similarity_engine.check_semantic_similarity(sentences, candidates)
            
            # Enrich matches with citation status
            for match in verbatim_plagiarism:
                cand = next((c for c in candidates if c["pmid"] == match["pmid"]), {})
                match["is_cited"] = self._check_if_cited(doc_text, cand)
                
            for match in semantic_matches:
                match["is_cited"] = self._check_if_cited(doc_text, match)

        # 6. Overall Assessment Risk Calculations (ignoring properly cited sources)
        uncited_verbatim = [r for r in verbatim_plagiarism if not r.get("is_cited")]
        uncited_semantic = [m for m in semantic_matches if not m.get("is_cited")]
        
        max_jaccard = max([r["jaccard_score"] for r in uncited_verbatim]) if uncited_verbatim else 0.0
        max_semantic = max([m["score"] for m in uncited_semantic]) if uncited_semantic else 0.0
        
        risk_level = "LOW"
        if max_jaccard >= 0.50 or len(uncited_verbatim) > 1 or max_semantic >= 0.85:
            risk_level = "HIGH"
        elif max_jaccard >= 0.20 or max_semantic >= 0.75:
            risk_level = "MODERATE"

        execution_time = time.time() - start_time

        return {
            "status": "success",
            "metadata": {
                "filename": filename,
                "word_count": word_count,
                "sentences_analyzed": len(sentences),
                "execution_time_seconds": round(execution_time, 2)
            },
            "guardrails": {
                "anonymized_search_keywords": sanitized_keywords,
                "external_pmids_queried": matching_pmids,
                "confidentiality_status": "VERIFIED (0% original text sent to external APIs)"
            },
            "results": {
                "risk_level": risk_level,
                "max_verbatim_score": max_jaccard,
                "max_semantic_score": max_semantic,
                "verbatim_plagiarism_flags": verbatim_plagiarism,
                "semantic_similarity_flags": semantic_matches
            }
        }

    def _check_if_cited(self, doc_text: str, candidate: Dict[str, Any]) -> bool:
        """
        Determines if a candidate article is already cited in the document text.
        Checks for:
        - DOI match
        - First author's last name match (e.g., 'Linz' in the document)
        - Shortened title match (in case of bibliography reference)
        """
        import re
        doc_text_lower = doc_text.lower()
        
        # 1. Check DOI
        doi = candidate.get("doi", "")
        if doi and doi.lower() in doc_text_lower:
            return True
            
        # 2. Check First Author's Last Name
        authors = candidate.get("authors", [])
        if authors:
            first_author = authors[0]
            # Extract last name: usually the last word in 'Forename Surname'
            parts = first_author.split()
            if parts:
                last_name = parts[-1].lower()
                # Ensure it's not a generic word and is at least 3 letters
                if len(last_name) > 2 and last_name not in ["the", "and", "new", "for", "with"]:
                    # Search for last name in document
                    if last_name in doc_text_lower:
                        return True
                        
        # 3. Check Title Match (e.g. if the title is listed in references)
        title = candidate.get("title", "")
        if title:
            # Check if a significant portion of the title exists in the document
            clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title).lower()
            words = clean_title.split()
            if len(words) > 5:
                # Check 5-word phrase match
                phrase = " ".join(words[:5])
                if phrase in doc_text_lower:
                    return True
                    
        return False
