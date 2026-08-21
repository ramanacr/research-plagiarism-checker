"""
Evidence and scoring models for plagiarism classification and reporting.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


class MatchClass(str, Enum):
    EXACT_COPY = "EXACT_COPY"
    NEAR_EXACT_COPY = "NEAR_EXACT_COPY"
    LIKELY_PARAPHRASE = "LIKELY_PARAPHRASE"
    POSSIBLE_PARAPHRASE = "POSSIBLE_PARAPHRASE"
    COMMON_PHRASE = "COMMON_PHRASE"
    PROPERLY_QUOTED = "PROPERLY_QUOTED"
    CITED_OVERLAP = "CITED_OVERLAP"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    LOW_SIGNIFICANCE = "LOW_SIGNIFICANCE"
    UNRELATED = "UNRELATED"


@dataclass
class MatchEvidence:
    query_passage_id: str
    source_passage_id: str
    exact_overlap: float = 0.0
    shingle_containment: float = 0.0
    jaccard_similarity: float = 0.0
    edit_similarity: float = 0.0
    semantic_similarity: float = 0.0
    cross_encoder_score: Optional[float] = None
    rare_phrase_weight: float = 1.0
    matched_token_count: int = 0
    query_token_count: int = 0
    source_token_count: int = 0
    longest_copied_tokens: int = 0
    longest_copied_phrase: str = ""
    citation_present: bool = False
    quoted_text: bool = False
    boilerplate_score: float = 0.0
    matching_phrases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exact_overlap": self.exact_overlap,
            "shingle_containment": self.shingle_containment,
            "jaccard_similarity": self.jaccard_similarity,
            "edit_similarity": self.edit_similarity,
            "semantic_similarity": self.semantic_similarity,
            "cross_encoder_score": self.cross_encoder_score,
            "rare_phrase_weight": self.rare_phrase_weight,
            "matched_token_count": self.matched_token_count,
            "query_token_count": self.query_token_count,
            "source_token_count": self.source_token_count,
            "longest_copied_tokens": self.longest_copied_tokens,
            "longest_copied_phrase": self.longest_copied_phrase,
            "citation_present": self.citation_present,
            "quoted_text": self.quoted_text,
            "boilerplate_score": self.boilerplate_score,
            "matching_phrases": self.matching_phrases,
        }


@dataclass
class PlagiarismMatch:
    match_id: str
    classification: MatchClass
    confidence: float
    query_span: Dict[str, int]  # {"start": int, "end": int}
    source_document_id: str
    source: Dict[str, Any]
    evidence: MatchEvidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "classification": self.classification.value,
            "confidence": round(self.confidence, 4),
            "query_span": self.query_span,
            "source_document_id": self.source_document_id,
            "source": self.source,
            "evidence": self.evidence.to_dict(),
        }


@dataclass
class PlagiarismReport:
    check_id: str
    engine_version: str
    threshold_version: str
    overall_matched_coverage: float
    suspicious_coverage: float
    quoted_or_cited_coverage: float
    common_phrase_coverage: float
    risk_level: str
    matches: List[PlagiarismMatch] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "engine_version": self.engine_version,
            "threshold_version": self.threshold_version,
            "overall_matched_coverage": round(self.overall_matched_coverage, 2),
            "suspicious_coverage": round(self.suspicious_coverage, 2),
            "quoted_or_cited_coverage": round(self.quoted_or_cited_coverage, 2),
            "common_phrase_coverage": round(self.common_phrase_coverage, 2),
            "risk_level": self.risk_level,
            "matches": [m.to_dict() for m in self.matches],
            "metadata": self.metadata,
            "warnings": self.warnings,
        }
