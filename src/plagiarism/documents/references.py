"""
Reference and bibliography detection, citation parsing, and item extraction.
"""

import re
from typing import List, Tuple, Optional
from src.plagiarism.documents.models import ReferenceItem, CitationSpan


# Regex patterns for inline citations
INLINE_CITATION_PATTERNS = [
    # Bracketed numbers: [1], [1, 2], [1-4]
    re.compile(r"\[\s*(\d+(?:\s*[,-]\s*\d+)*)\s*\]"),
    # Parenthetical author-year: (Smith, 2020), (Smith et al., 2021; Jones, 2019)
    re.compile(r"\(\s*([A-Z][a-zA-Z\s.-]+(?:et\s+al\.?)?,\s*\d{4}[a-z]?(?:\s*;\s*[A-Z][a-zA-Z\s.-]+(?:et\s+al\.?)?,\s*\d{4}[a-z]?)*)\s*\)"),
]

# DOI extraction pattern
DOI_PATTERN = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b")
YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")


def extract_inline_citations(text: str) -> List[CitationSpan]:
    """
    Extracts all inline citation occurrences from text with exact offsets.
    """
    if not text:
        return []

    citations: List[CitationSpan] = []
    cid = 0

    for pattern in INLINE_CITATION_PATTERNS:
        for match in pattern.finditer(text):
            citation_text = match.group(0)
            inner = match.group(1)
            # Split keys if multiple
            keys = tuple(k.strip() for k in re.split(r"[,;]", inner) if k.strip())

            citations.append(
                CitationSpan(
                    citation_id=f"cit_{cid}",
                    start_offset=match.start(),
                    end_offset=match.end(),
                    text=citation_text,
                    normalized_keys=keys,
                )
            )
            cid += 1

    # Sort by start_offset
    citations.sort(key=lambda c: c.start_offset)
    return citations


def extract_references_from_text(ref_section_text: str, base_offset: int = 0) -> List[ReferenceItem]:
    """
    Parses bibliography entries from a references section text.
    """
    if not ref_section_text.strip():
        return []

    items: List[ReferenceItem] = []
    lines = ref_section_text.split("\n")
    
    current_entry_lines: List[str] = []
    entry_start = 0
    current_offset = base_offset

    def _flush_entry(lines_list: List[str], start_pos: int, end_pos: int, ref_idx: int):
        full_entry = " ".join(l.strip() for l in lines_list if l.strip()).strip()
        if not full_entry or len(full_entry) < 15:
            return

        # Extract DOI
        doi_match = DOI_PATTERN.search(full_entry)
        doi = doi_match.group(1) if doi_match else None

        # Extract Year
        year_match = YEAR_PATTERN.search(full_entry)
        year = int(year_match.group(1)) if year_match else None

        # Extract approximate authors (first part before year or period)
        authors = []
        author_part = re.split(r"\(\d{4}\)|\b\d{4}\b|\.", full_entry)[0]
        if author_part:
            # Strip leading citation number like [1] or 1.
            author_part = re.sub(r"^(?:\[\d+\]|\d+\.|\d+)\s*", "", author_part)
            raw_authors = re.split(r",|&|and", author_part)
            for a in raw_authors:
                clean_a = a.strip()
                if len(clean_a) > 2 and not clean_a.isdigit():
                    authors.append(clean_a)

        items.append(
            ReferenceItem(
                reference_id=f"ref_{ref_idx}",
                raw_text=full_entry,
                authors=tuple(authors),
                year=year,
                doi=doi,
                start_offset=start_pos,
                end_offset=end_pos,
            )
        )

    ref_idx = 0
    for line in lines:
        line_len = len(line) + 1
        clean = line.strip()

        # Check if line starts a new reference item (e.g. "[1]", "1.", or author name with hanging indent)
        is_new_entry = bool(re.match(r"^(?:\[\d+\]|\d+\.|\b[A-Z][a-zA-Z]+,\s+[A-Z]\.)", clean))

        if is_new_entry and current_entry_lines:
            _flush_entry(current_entry_lines, entry_start, current_offset, ref_idx)
            ref_idx += 1
            current_entry_lines = [clean]
            entry_start = current_offset
        else:
            if clean:
                if not current_entry_lines:
                    entry_start = current_offset
                current_entry_lines.append(clean)

        current_offset += line_len

    if current_entry_lines:
        _flush_entry(current_entry_lines, entry_start, current_offset, ref_idx)

    return items
