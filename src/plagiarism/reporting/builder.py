"""
Report builder constructing formatted JSON contracts and text summaries.
"""

from typing import Dict, Any
from src.plagiarism.scoring.models import PlagiarismReport, MatchClass


class ReportBuilder:
    """
    Builds API response contracts and text reports adhering to 17_API_AND_REPORT_CONTRACTS.md.
    """

    @staticmethod
    def build_api_contract(report: PlagiarismReport) -> Dict[str, Any]:
        """Formats the report matching API Contract v2."""
        return report.to_dict()

    @staticmethod
    def build_text_summary(report: PlagiarismReport) -> str:
        """Constructs human-readable console audit report."""
        lines = [
            "=" * 60,
            "  SCHOLARLY PLAGIARISM & SIMILARITY AUDIT REPORT (v2.0)",
            "=" * 60,
            f"Check ID:                  {report.check_id}",
            f"Engine Version:            {report.engine_version} (Thresholds: {report.threshold_version})",
            f"Overall Matched Coverage:  {report.overall_matched_coverage:.1f}%",
            f"Suspicious Coverage:       {report.suspicious_coverage:.1f}%",
            f"Quoted / Cited Coverage:   {report.quoted_or_cited_coverage:.1f}%",
            f"Common Phrase Coverage:    {report.common_phrase_coverage:.1f}%",
            f"Plagiarism Risk Level:     {report.risk_level} RISK",
            "-" * 60,
            f"Total Matches Flagged:     {len(report.matches)}",
        ]

        if report.matches:
            lines.append("-" * 60)
            lines.append("MATCH EVIDENCE BREAKDOWN:")
            for idx, m in enumerate(report.matches, 1):
                src = m.source
                ev = m.evidence
                lines.append(
                    f"\n[{idx}] {m.classification.value} (Confidence: {int(m.confidence*100)}%)"
                )
                lines.append(f"    Source:   {src.get('title', 'Unknown')} (PMID: {src.get('pmid', 'N/A')}, DOI: {src.get('doi', 'N/A')})")
                lines.append(f"    Evidence: Exact: {int(ev.exact_overlap*100)}% | Shingles: {int(ev.shingle_containment*100)}% | Semantic: {int(ev.semantic_similarity*100)}%")
                if ev.matching_phrases:
                    lines.append(f"    Overlapping Spans: \"{ev.matching_phrases[0][:80]}...\"")

        if report.warnings:
            lines.append("-" * 60)
            lines.append("WARNINGS / PROVIDER NOTICES:")
            for w in report.warnings:
                lines.append(f"  [!] {w}")

        lines.append("=" * 60)
        return "\n".join(lines)
