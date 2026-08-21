"""
Token-aware passage segmentation and document processing.
"""

import re
from typing import List, Optional, Tuple, Dict, Any

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
)
from src.plagiarism.documents.structure import detect_sections
from src.plagiarism.documents.quotes import extract_quotes
from src.plagiarism.documents.references import extract_inline_citations, extract_references_from_text
from src.plagiarism.config.settings import SegmentationSettings


def split_sentences_fast(text: str) -> List[Tuple[str, int, int]]:
    """
    Splits text into clean sentences with exact start and end offsets.
    Fast, lightweight, does not require heavy transformer weights.
    """
    if not text.strip():
        return []

    # Sentence boundary regex handling common abbreviations
    sentence_end = re.compile(
        r"(?<=[.!?])\s+(?=[A-Z0-9\(\[\"“])",
        re.UNICODE
    )

    sentences: List[Tuple[str, int, int]] = []
    current_pos = 0

    for part in sentence_end.split(text):
        if not part:
            continue
        start_idx = text.find(part, current_pos)
        if start_idx == -1:
            start_idx = current_pos
        end_idx = start_idx + len(part)
        clean_text = part.strip()
        if len(clean_text) > 0:
            sentences.append((clean_text, start_idx, end_idx))
        current_pos = end_idx

    if not sentences and text.strip():
        sentences.append((text.strip(), 0, len(text)))

    return sentences


def segment_section_into_passages(
    document_id: str,
    section: Section,
    settings: Optional[SegmentationSettings] = None,
    quotes: Optional[List[QuoteSpan]] = None,
    citations: Optional[List[CitationSpan]] = None,
    start_passage_index: int = 0,
) -> List[Passage]:
    """
    Segments a single section into token-aware, sentence-aligned passages.
    Target 80-200 tokens (default 150) with ~25 token overlap.
    """
    cfg = settings or SegmentationSettings()
    target_tokens = cfg.target_tokens
    overlap_tokens = cfg.overlap_tokens
    min_tokens = cfg.min_passage_tokens

    sec_text = section.text
    if not sec_text.strip():
        return []

    sec_sentences = split_sentences_fast(sec_text)
    if not sec_sentences:
        return []

    passages: List[Passage] = []
    
    # Track sentence token counts and absolute offsets
    sentence_info = []
    for s_text, s_rel_start, s_rel_end in sec_sentences:
        abs_start = section.start_offset + s_rel_start
        abs_end = section.start_offset + s_rel_end
        tokens = tokenize_words(s_text)
        sentence_info.append({
            "text": s_text,
            "start": abs_start,
            "end": abs_end,
            "tokens": tokens,
            "count": len(tokens),
        })

    p_idx = start_passage_index
    sent_idx = 0
    num_sents = len(sentence_info)

    while sent_idx < num_sents:
        window_tokens: List[str] = []
        window_sents = []
        w_start = sentence_info[sent_idx]["start"]
        w_end = sentence_info[sent_idx]["end"]

        cur_sent_idx = sent_idx
        while cur_sent_idx < num_sents:
            info = sentence_info[cur_sent_idx]
            # Add sentence if within target or window is empty
            if not window_sents or (len(window_tokens) + info["count"] <= target_tokens + 30):
                window_sents.append(info)
                window_tokens.extend(info["tokens"])
                w_end = info["end"]
                cur_sent_idx += 1
            else:
                # Target window reached
                break

        if not window_sents:
            break

        p_text = sec_text[window_sents[0]["start"] - section.start_offset : window_sents[-1]["end"] - section.start_offset].strip()
        norm_text = normalize_for_lexical(p_text)

        # Check quotes and citations
        is_quoted = False
        if quotes:
            for q in quotes:
                if q.start_offset <= w_start and q.end_offset >= w_end:
                    is_quoted = True
                    break
                elif (min(q.end_offset, w_end) - max(q.start_offset, w_start)) > 0.5 * (w_end - w_start):
                    is_quoted = True
                    break

        has_citation = False
        if citations:
            for c in citations:
                if w_start <= c.start_offset <= w_end:
                    has_citation = True
                    break

        passage = Passage(
            passage_id=f"{document_id}#p_{p_idx:03d}",
            document_id=document_id,
            section=section.name,
            section_type=section.section_type,
            paragraph_index=p_idx,
            text=p_text,
            normalized_text=norm_text,
            start_offset=w_start,
            end_offset=w_end,
            token_count=len(window_tokens),
            is_reference=(section.section_type == SectionType.REFERENCES),
            is_quoted=is_quoted,
            citation_present=has_citation,
            tokens=window_tokens,
        )

        if passage.token_count >= min_tokens or not passages:
            passages.append(passage)
            p_idx += 1

        # Advance window with overlap
        if cur_sent_idx >= num_sents:
            break

        # Calculate how many sentences to rewind for overlap
        accumulated_overlap = 0
        rewind_idx = cur_sent_idx - 1
        while rewind_idx > sent_idx and accumulated_overlap < overlap_tokens:
            accumulated_overlap += sentence_info[rewind_idx]["count"]
            rewind_idx -= 1

        sent_idx = max(rewind_idx + 1, sent_idx + 1)

    return passages


def process_document(
    document_id: str,
    text: str,
    title: str = "",
    settings: Optional[SegmentationSettings] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Document:
    """
    Fully processes a raw text manuscript into a structured Document domain object:
    - Unicode and whitespace normalization
    - Scientific section detection
    - Inline citation extraction
    - Quote extraction
    - Bibliography item extraction
    - Passage segmentation
    """
    raw_text = text
    norm_text = normalize_unicode(text)
    word_tokens = tokenize_words(norm_text)
    word_count = len(word_tokens)

    # 1. Detect sections
    sections = detect_sections(raw_text)

    # 2. Extract quotes
    quotes = extract_quotes(raw_text)

    # 3. Extract citations
    citations = extract_inline_citations(raw_text)

    # 4. Extract references from reference sections
    references: List[ReferenceItem] = []
    for sec in sections:
        if sec.section_type == SectionType.REFERENCES:
            references.extend(extract_references_from_text(sec.text, base_offset=sec.start_offset))

    # 5. Segment sections into passages
    passages: List[Passage] = []
    current_p_idx = 0
    for sec in sections:
        sec_passages = segment_section_into_passages(
            document_id=document_id,
            section=sec,
            settings=settings,
            quotes=quotes,
            citations=citations,
            start_passage_index=current_p_idx,
        )
        passages.extend(sec_passages)
        current_p_idx = len(passages)

    # If document has title in first section, use it if title was empty
    doc_title = title
    if not doc_title and sections and sections[0].section_type == SectionType.TITLE:
        doc_title = sections[0].text.strip().split("\n")[0][:150]
    if not doc_title:
        doc_title = document_id

    return Document(
        document_id=document_id,
        title=doc_title,
        raw_text=raw_text,
        normalized_text=norm_text,
        word_count=word_count,
        sections=sections,
        passages=passages,
        quotes=quotes,
        citations=citations,
        references=references,
        metadata=metadata or {},
    )
