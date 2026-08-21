"""
Domain models for documents, sections, passages, quotes, and citations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple


class SectionType(str, Enum):
    TITLE = "TITLE"
    ABSTRACT = "ABSTRACT"
    INTRODUCTION = "INTRODUCTION"
    BACKGROUND = "BACKGROUND"
    METHODS = "METHODS"
    RESULTS = "RESULTS"
    DISCUSSION = "DISCUSSION"
    CONCLUSION = "CONCLUSION"
    REFERENCES = "REFERENCES"
    ACKNOWLEDGEMENTS = "ACKNOWLEDGEMENTS"
    BODY = "BODY"
    OTHER = "OTHER"


@dataclass(frozen=True)
class Section:
    section_id: str
    name: str
    section_type: SectionType
    start_offset: int
    end_offset: int
    text: str


@dataclass(frozen=True)
class QuoteSpan:
    quote_id: str
    start_offset: int
    end_offset: int
    text: str
    quote_char: str = '"'


@dataclass(frozen=True)
class CitationSpan:
    citation_id: str
    start_offset: int
    end_offset: int
    text: str
    normalized_keys: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReferenceItem:
    reference_id: str
    raw_text: str
    authors: Tuple[str, ...] = field(default_factory=tuple)
    title: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    start_offset: int = 0
    end_offset: int = 0


@dataclass
class Passage:
    passage_id: str
    document_id: str
    section: Optional[str]
    section_type: SectionType
    paragraph_index: int
    text: str
    normalized_text: str
    start_offset: int
    end_offset: int
    token_count: int
    is_reference: bool = False
    is_quoted: bool = False
    citation_present: bool = False
    tokens: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passage_id": self.passage_id,
            "document_id": self.document_id,
            "section": self.section,
            "section_type": self.section_type.value,
            "paragraph_index": self.paragraph_index,
            "text": self.text,
            "normalized_text": self.normalized_text,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "token_count": self.token_count,
            "is_reference": self.is_reference,
            "is_quoted": self.is_quoted,
            "citation_present": self.citation_present,
        }


@dataclass
class Document:
    document_id: str
    title: str
    raw_text: str
    normalized_text: str
    word_count: int
    sections: List[Section] = field(default_factory=list)
    passages: List[Passage] = field(default_factory=list)
    quotes: List[QuoteSpan] = field(default_factory=list)
    citations: List[CitationSpan] = field(default_factory=list)
    references: List[ReferenceItem] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
