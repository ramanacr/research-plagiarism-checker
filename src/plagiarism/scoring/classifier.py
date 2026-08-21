"""
Evidence classifier implementing calibrated deterministic rules for match classification.
"""

from typing import Tuple, Optional
from src.plagiarism.scoring.models import MatchClass, MatchEvidence
from src.plagiarism.config.settings import ScoringThresholds


class EvidenceClassifier:
    """
    Deterministic rule-based evidence classifier.
    Combines lexical, semantic, citation, quotation, and boilerplate signals to classify matches.
    """

    def __init__(self, thresholds: Optional[ScoringThresholds] = None):
        self.thresholds = thresholds or ScoringThresholds()

    def classify_match(
        self,
        evidence: MatchEvidence,
        is_reference_section: bool = False,
    ) -> Tuple[MatchClass, float]:
        """
        Evaluates MatchEvidence and returns (MatchClass, confidence_score).
        """
        th = self.thresholds

        # 1. Reference / Bibliography overlap
        if is_reference_section:
            return MatchClass.REFERENCE_ONLY, 0.95

        # 2. Properly Quoted text
        if evidence.quoted_text and (
            evidence.exact_overlap >= 0.40 or evidence.shingle_containment >= 0.40 or evidence.semantic_similarity >= 0.75
        ):
            confidence = min(0.99, max(evidence.exact_overlap, evidence.semantic_similarity))
            return MatchClass.PROPERLY_QUOTED, confidence

        # 3. Cited Overlap (cited source with academic attribution)
        if evidence.citation_present and (
            evidence.exact_overlap >= 0.35 or evidence.shingle_containment >= 0.40 or evidence.semantic_similarity >= 0.75
        ):
            confidence = min(0.95, max(evidence.exact_overlap, evidence.semantic_similarity))
            return MatchClass.CITED_OVERLAP, confidence

        # 4. Common Scientific Phrase / Methods Boilerplate
        if evidence.boilerplate_score >= 0.80 or (
            evidence.matched_token_count <= th.common_phrase_max_tokens and evidence.boilerplate_score >= 0.50
        ):
            return MatchClass.COMMON_PHRASE, 0.90

        # 5. Exact Copy
        if (
            evidence.exact_overlap >= th.exact_copy_overlap_ratio
            and evidence.shingle_containment >= th.exact_copy_containment
            and evidence.matched_token_count >= th.min_suspicious_tokens
        ):
            confidence = min(0.99, 0.5 * evidence.exact_overlap + 0.5 * evidence.shingle_containment)
            return MatchClass.EXACT_COPY, confidence

        # 6. Near-Exact Copy
        if (
            evidence.shingle_containment >= th.near_exact_containment
            and evidence.edit_similarity >= th.near_exact_edit_similarity
            and evidence.matched_token_count >= th.min_suspicious_tokens
        ):
            confidence = min(0.95, 0.5 * evidence.shingle_containment + 0.5 * evidence.edit_similarity)
            return MatchClass.NEAR_EXACT_COPY, confidence

        # 7. Likely Paraphrase (Strong semantic + moderate lexical/token overlap)
        if (
            evidence.semantic_similarity >= th.likely_paraphrase_semantic
            and (evidence.jaccard_similarity >= th.likely_paraphrase_token_overlap or evidence.shingle_containment >= 0.20)
            and evidence.query_token_count >= th.min_suspicious_tokens
        ):
            confidence = min(0.90, evidence.semantic_similarity)
            return MatchClass.LIKELY_PARAPHRASE, confidence

        # 8. Possible Paraphrase (Strong semantic only, minimal lexical overlap)
        if (
            evidence.semantic_similarity >= th.possible_paraphrase_semantic
            and evidence.query_token_count >= th.min_suspicious_tokens
        ):
            confidence = min(0.75, evidence.semantic_similarity * 0.85)
            return MatchClass.POSSIBLE_PARAPHRASE, confidence

        # 9. Low Significance (Sub-threshold overlap or short match)
        if (
            evidence.exact_overlap >= 0.15
            or evidence.shingle_containment >= 0.15
            or evidence.semantic_similarity >= 0.55
        ):
            return MatchClass.LOW_SIGNIFICANCE, 0.50

        # 10. Unrelated
        return MatchClass.UNRELATED, 0.10
