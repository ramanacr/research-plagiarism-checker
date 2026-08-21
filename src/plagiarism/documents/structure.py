"""
Section-aware scientific structure detection and parsing.
"""

import re
from typing import List, Tuple
from src.plagiarism.documents.models import Section, SectionType


SECTION_HEADER_PATTERNS: List[Tuple[re.Pattern, SectionType]] = [
    (re.compile(r"^(?:abstract|summary)\b", re.IGNORECASE), SectionType.ABSTRACT),
    (re.compile(r"^(?:1\.?\s*)?(?:introduction|background)\b", re.IGNORECASE), SectionType.INTRODUCTION),
    (re.compile(r"^(?:2\.?\s*)?(?:methods|materials\s+and\s+methods|methodology|experimental\s+procedures)\b", re.IGNORECASE), SectionType.METHODS),
    (re.compile(r"^(?:3\.?\s*)?(?:results|findings)\b", re.IGNORECASE), SectionType.RESULTS),
    (re.compile(r"^(?:4\.?\s*)?(?:discussion)\b", re.IGNORECASE), SectionType.DISCUSSION),
    (re.compile(r"^(?:5\.?\s*)?(?:conclusion|conclusions|concluding\s+remarks)\b", re.IGNORECASE), SectionType.CONCLUSION),
    (re.compile(r"^(?:references|bibliography|literature\s+cited|works\s+cited)\b", re.IGNORECASE), SectionType.REFERENCES),
    (re.compile(r"^(?:acknowledgements?|funding|competing\s+interests|declaration\s+of\s+interests)\b", re.IGNORECASE), SectionType.ACKNOWLEDGEMENTS),
]


def detect_sections(text: str) -> List[Section]:
    """
    Parses a manuscript text into structural sections.
    Identifies standard academic headers or creates a default BODY section.
    """
    if not text.strip():
        return []

    lines = text.split("\n")
    headers: List[Tuple[int, int, str, SectionType]] = []
    
    current_char_offset = 0
    for line in lines:
        line_len = len(line) + 1  # newline account
        clean_line = line.strip()

        # Check if line looks like a header (short, capitalized or title case or matches standard headers)
        if clean_line and len(clean_line) < 80:
            for pattern, sec_type in SECTION_HEADER_PATTERNS:
                if pattern.match(clean_line):
                    headers.append((current_char_offset, current_char_offset + len(line), clean_line, sec_type))
                    break

        current_char_offset += line_len

    if not headers:
        # Single body section if no explicit headers found
        return [
            Section(
                section_id="sec_0",
                name="Body",
                section_type=SectionType.BODY,
                start_offset=0,
                end_offset=len(text),
                text=text,
            )
        ]

    sections: List[Section] = []
    
    # Text before the first detected header (e.g. Title / Abstract)
    first_header_start = headers[0][0]
    if first_header_start > 0:
        prefix_text = text[:first_header_start].strip()
        if prefix_text:
            sections.append(
                Section(
                    section_id="sec_0",
                    name="Title/Header",
                    section_type=SectionType.TITLE,
                    start_offset=0,
                    end_offset=first_header_start,
                    text=text[:first_header_start],
                )
            )

    for i, (h_start, h_end, h_name, sec_type) in enumerate(headers):
        content_start = h_start
        content_end = headers[i + 1][0] if i + 1 < len(headers) else len(text)
        sec_text = text[content_start:content_end]

        sections.append(
            Section(
                section_id=f"sec_{len(sections)}",
                name=h_name,
                section_type=sec_type,
                start_offset=content_start,
                end_offset=content_end,
                text=sec_text,
            )
        )

    return sections
