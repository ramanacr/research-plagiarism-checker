"""
Coverage calculation, span merging, and risk level aggregation.
"""

from typing import List, Dict, Tuple, Set, Any, Optional
from src.plagiarism.scoring.models import PlagiarismMatch, MatchClass, PlagiarismReport
from src.plagiarism.documents.models import Document


def merge_spans(spans: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """
    Merges overlapping or contiguous [start, end] character spans.
    """
    if not spans:
        return []

    sorted_spans = sorted(spans, key=lambda x: x[0])
    merged = [sorted_spans[0]]

    for current in sorted_spans[1:]:
        prev_start, prev_end = merged[-1]
        curr_start, curr_end = current

        if curr_start <= prev_end:
            # Overlap or contiguous
            merged[-1] = (prev_start, max(prev_end, curr_end))
        else:
            merged.append(current)

    return merged


def calculate_total_span_length(merged_spans: List[Tuple[int, int]]) -> int:
    """Computes total characters covered by merged spans."""
    return sum(end - start for start, end in merged_spans)


class ScoreAggregator:
    """
    Computes overall coverage percentages and document-level plagiarism risk.
    """

    @staticmethod
    def aggregate_report(
        check_id: str,
        document: Document,
        matches: List[PlagiarismMatch],
        engine_version: str = "2.0.0",
        threshold_version: str = "v1",
        warnings: Optional[List[str]] = None,
    ) -> PlagiarismReport:
        """
        Computes non-overlapping query span coverage and builds PlagiarismReport.
        """
        doc_length = len(document.raw_text.strip())
        if doc_length == 0:
            doc_length = 1

        all_spans: List[Tuple[int, int]] = []
        suspicious_spans: List[Tuple[int, int]] = []
        quoted_cited_spans: List[Tuple[int, int]] = []
        common_spans: List[Tuple[int, int]] = []

        suspicious_classes = {
            MatchClass.EXACT_COPY,
            MatchClass.NEAR_EXACT_COPY,
            MatchClass.LIKELY_PARAPHRASE,
        }
        quoted_cited_classes = {
            MatchClass.PROPERLY_QUOTED,
            MatchClass.CITED_OVERLAP,
        }

        for m in matches:
            span = (m.query_span.get("start", 0), m.query_span.get("end", 0))
            if span[1] <= span[0]:
                continue

            if m.classification in suspicious_classes:
                suspicious_spans.append(span)
                all_spans.append(span)
            elif m.classification in quoted_cited_classes:
                quoted_cited_spans.append(span)
                all_spans.append(span)
            elif m.classification == MatchClass.COMMON_PHRASE:
                common_spans.append(span)
                all_spans.append(span)
            elif m.classification == MatchClass.POSSIBLE_PARAPHRASE:
                all_spans.append(span)

        # Merge spans
        merged_all = merge_spans(all_spans)
        merged_suspicious = merge_spans(suspicious_spans)
        merged_quoted_cited = merge_spans(quoted_cited_spans)
        merged_common = merge_spans(common_spans)

        overall_cov = min(100.0, (calculate_total_span_length(merged_all) / doc_length) * 100.0)
        suspicious_cov = min(100.0, (calculate_total_span_length(merged_suspicious) / doc_length) * 100.0)
        quoted_cited_cov = min(100.0, (calculate_total_span_length(merged_quoted_cited) / doc_length) * 100.0)
        common_cov = min(100.0, (calculate_total_span_length(merged_common) / doc_length) * 100.0)

        # Risk level determination
        risk_level = "LOW"
        has_large_exact = any(
            m.classification == MatchClass.EXACT_COPY and m.evidence.matched_token_count >= 30
            for m in matches
        )
        if suspicious_cov >= 18.0 or has_large_exact:
            risk_level = "HIGH"
        elif suspicious_cov >= 6.0 or any(m.classification == MatchClass.LIKELY_PARAPHRASE for m in matches):
            risk_level = "MODERATE"

        return PlagiarismReport(
            check_id=check_id,
            engine_version=engine_version,
            threshold_version=threshold_version,
            overall_matched_coverage=overall_cov,
            suspicious_coverage=suspicious_cov,
            quoted_or_cited_coverage=quoted_cited_cov,
            common_phrase_coverage=common_cov,
            risk_level=risk_level,
            matches=matches,
            metadata={
                "document_id": document.document_id,
                "title": document.title,
                "word_count": document.word_count,
                "passages_analyzed": len(document.passages),
            },
            warnings=warnings or [],
        )
