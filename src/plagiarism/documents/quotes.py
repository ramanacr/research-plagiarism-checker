"""
Quotation detection utilities for extracting quoted spans with character offsets.
"""

import re
from typing import List
from src.plagiarism.documents.models import QuoteSpan


QUOTE_PAIRS = [
    ('"', '"'),
    ('“', '”'),
    ('‘', '’'),
    ('«', '»'),
]


def extract_quotes(text: str) -> List[QuoteSpan]:
    """
    Extracts all properly quoted spans from text with exact character offsets.
    """
    if not text:
        return []

    quotes: List[QuoteSpan] = []
    qid = 0

    # Pattern for standard and smart quotes
    # Match strings enclosed in quotes with at least 10 characters inside
    patterns = [
        (re.compile(r'"([^"\n\r]{10,1000})"'), '"'),
        (re.compile(r'“([^”\n\r]{10,1000})”'), '“'),
        (re.compile(r'‘([^’\n\r]{10,1000})’'), '‘'),
        (re.compile(r'«([^»\n\r]{10,1000})»'), '«'),
    ]

    for pat, quote_char in patterns:
        for match in pat.finditer(text):
            quotes.append(
                QuoteSpan(
                    quote_id=f"quote_{qid}",
                    start_offset=match.start(),
                    end_offset=match.end(),
                    text=match.group(1).strip(),
                    quote_char=quote_char,
                )
            )
            qid += 1

    # Also detect Markdown blockquotes (lines starting with >)
    for match in re.finditer(r"(?:^|\n)>\s*(.+?)(?=\n\s*\n|\n[^>]|$)", text, re.DOTALL):
        block_text = match.group(1).strip()
        if len(block_text) >= 15:
            quotes.append(
                QuoteSpan(
                    quote_id=f"quote_{qid}",
                    start_offset=match.start(),
                    end_offset=match.end(),
                    text=block_text,
                    quote_char=">",
                )
            )
            qid += 1

    quotes.sort(key=lambda q: q.start_offset)
    return quotes
