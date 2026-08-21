"""
Document domain package for normalization, structure parsing, quotes, citations, and segmentation.
"""

from src.plagiarism.documents.models import (
    Document,
    Passage,
    Section,
    SectionType,
    QuoteSpan,
    CitationSpan,
    ReferenceItem,
)
from src.plagiarism.documents.normalize import (
    normalize_unicode,
    normalize_whitespace,
    normalize_for_lexical,
    tokenize_words,
    tokenize_with_spans,
    TextOffsetMapper,
)
from src.plagiarism.documents.structure import detect_sections
from src.plagiarism.documents.quotes import extract_quotes
from src.plagiarism.documents.references import (
    extract_inline_citations,
    extract_references_from_text,
)
from src.plagiarism.documents.segmentation import (
    process_document,
    segment_section_into_passages,
    split_sentences_fast,
)

__all__ = [
    "Document",
    "Passage",
    "Section",
    "SectionType",
    "QuoteSpan",
    "CitationSpan",
    "ReferenceItem",
    "normalize_unicode",
    "normalize_whitespace",
    "normalize_for_lexical",
    "tokenize_words",
    "tokenize_with_spans",
    "TextOffsetMapper",
    "detect_sections",
    "extract_quotes",
    "extract_inline_citations",
    "extract_references_from_text",
    "process_document",
    "segment_section_into_passages",
    "split_sentences_fast",
]
