"""
Citation and quotation context analysis for plagiarism evidence.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from src.plagiarism.documents.models import Document, Passage


@dataclass
class CitationContext:
    is_cited: bool = False
    is_quoted: bool = False
    citation_type: Optional[str] = None
    matched_author: Optional[str] = None
    matched_doi: Optional[str] = None
    matched_title_phrase: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class CitationAnalyzer:
    """
    Analyzes whether source literature is properly cited or quoted within the manuscript.
    Prevents legitimate citations and quotations from being misclassified as plagiarism.
    """

    @staticmethod
    def evaluate_citation_context(
        query_passage: Passage,
        document: Document,
        source_metadata: Dict[str, Any],
    ) -> CitationContext:
        """
        Evaluates citation and quotation presence for a candidate match.
        """
        doc_text_lower = document.raw_text.lower()
        passage_text_lower = query_passage.text.lower()
        is_quoted = query_passage.is_quoted

        # 1. DOI Matching
        doi = source_metadata.get("doi")
        if doi and doi.lower().strip() in doc_text_lower:
            return CitationContext(
                is_cited=True,
                is_quoted=is_quoted,
                citation_type="DOI_REFERENCE",
                matched_doi=doi,
                details={"doi": doi},
            )

        # 2. Author Last Name Matching
        authors = source_metadata.get("authors", [])
        if authors:
            first_author = authors[0] if isinstance(authors, (list, tuple)) else str(authors)
            parts = first_author.split()
            if parts:
                last_name = parts[-1].lower().strip(".,;:()")
                # Filter out short generic words
                if len(last_name) > 2 and last_name not in ["the", "and", "new", "for", "with", "study"]:
                    # Check in passage or document
                    in_passage = last_name in passage_text_lower
                    in_doc = last_name in doc_text_lower

                    # Check if followed by et al. or year
                    citation_pat = re.compile(rf"\b{re.escape(last_name)}\b(?:\s+et\s+al\.?|\s*\(\s*\d{{4}}|\s*,\s*\d{{4}})?", re.IGNORECASE)
                    if citation_pat.search(document.raw_text):
                        return CitationContext(
                            is_cited=True,
                            is_quoted=is_quoted,
                            citation_type="AUTHOR_CITATION" if in_passage else "DOCUMENT_AUTHOR_REFERENCE",
                            matched_author=first_author,
                            details={"author": first_author, "in_passage": in_passage},
                        )

        # 3. Title Matching in References
        title = source_metadata.get("title", "")
        if title:
            clean_title = re.sub(r"[^a-zA-Z0-9\s]", "", title).lower()
            words = clean_title.split()
            if len(words) >= 4:
                prefix = " ".join(words[:4])
                if prefix in doc_text_lower:
                    return CitationContext(
                        is_cited=True,
                        is_quoted=is_quoted,
                        citation_type="TITLE_REFERENCE",
                        matched_title_phrase=prefix,
                        details={"title_phrase": prefix},
                    )

        # 4. Check inline citations in query passage
        if query_passage.citation_present:
            return CitationContext(
                is_cited=True,
                is_quoted=is_quoted,
                citation_type="INLINE_CITATION_MARKER",
                details={"passage_has_citation": True},
            )

        return CitationContext(
            is_cited=False,
            is_quoted=is_quoted,
            citation_type=None,
        )
