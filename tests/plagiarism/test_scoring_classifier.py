"""
Tests for EvidenceClassifier, MatchEvidence, ScoreAggregator, and PlagiarismReport.
"""

import unittest
from src.plagiarism.documents.models import Document
from src.plagiarism.scoring.models import MatchClass, MatchEvidence, PlagiarismMatch
from src.plagiarism.scoring.classifier import EvidenceClassifier
from src.plagiarism.scoring.aggregate import ScoreAggregator, merge_spans


class TestScoringClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = EvidenceClassifier()

    def test_classify_exact_copy(self):
        evidence = MatchEvidence(
            query_passage_id="q1",
            source_passage_id="s1",
            exact_overlap=0.90,
            shingle_containment=0.92,
            jaccard_similarity=0.88,
            semantic_similarity=0.95,
            matched_token_count=25,
            query_token_count=28,
        )
        cls, conf = self.classifier.classify_match(evidence)
        self.assertEqual(cls, MatchClass.EXACT_COPY)
        self.assertGreater(conf, 0.85)

    def test_classify_near_exact_copy(self):
        evidence = MatchEvidence(
            query_passage_id="q1",
            source_passage_id="s1",
            exact_overlap=0.60,
            shingle_containment=0.75,
            edit_similarity=0.80,
            semantic_similarity=0.90,
            matched_token_count=18,
            query_token_count=24,
        )
        cls, conf = self.classifier.classify_match(evidence)
        self.assertEqual(cls, MatchClass.NEAR_EXACT_COPY)

    def test_classify_likely_paraphrase(self):
        evidence = MatchEvidence(
            query_passage_id="q1",
            source_passage_id="s1",
            exact_overlap=0.10,
            shingle_containment=0.15,
            jaccard_similarity=0.28,
            semantic_similarity=0.86,
            matched_token_count=5,
            query_token_count=22,
        )
        cls, conf = self.classifier.classify_match(evidence)
        self.assertEqual(cls, MatchClass.LIKELY_PARAPHRASE)

    def test_classify_quoted_and_cited(self):
        # Quoted
        ev_quoted = MatchEvidence(
            query_passage_id="q1",
            source_passage_id="s1",
            exact_overlap=0.85,
            shingle_containment=0.85,
            quoted_text=True,
            matched_token_count=20,
            query_token_count=20,
        )
        cls_q, _ = self.classifier.classify_match(ev_quoted)
        self.assertEqual(cls_q, MatchClass.PROPERLY_QUOTED)

        # Cited
        ev_cited = MatchEvidence(
            query_passage_id="q1",
            source_passage_id="s1",
            exact_overlap=0.70,
            shingle_containment=0.70,
            citation_present=True,
            matched_token_count=15,
            query_token_count=20,
        )
        cls_c, _ = self.classifier.classify_match(ev_cited)
        self.assertEqual(cls_c, MatchClass.CITED_OVERLAP)

    def test_classify_common_phrase(self):
        ev_common = MatchEvidence(
            query_passage_id="q1",
            source_passage_id="s1",
            exact_overlap=0.80,
            shingle_containment=0.80,
            boilerplate_score=0.95,
            matched_token_count=8,
            query_token_count=10,
        )
        cls_bp, _ = self.classifier.classify_match(ev_common)
        self.assertEqual(cls_bp, MatchClass.COMMON_PHRASE)

    def test_merge_spans(self):
        spans = [(0, 50), (40, 90), (120, 160), (150, 200)]
        merged = merge_spans(spans)
        self.assertEqual(merged, [(0, 90), (120, 200)])

    def test_score_aggregator_report(self):
        raw_text = "A" * 1000  # 1000 character document
        doc = Document(
            document_id="doc_test",
            title="Test Document",
            raw_text=raw_text,
            normalized_text=raw_text,
            word_count=150,
        )

        matches = [
            PlagiarismMatch(
                match_id="m1",
                classification=MatchClass.EXACT_COPY,
                confidence=0.98,
                query_span={"start": 0, "end": 150},
                source_document_id="src_doc_1",
                source={"title": "Source 1", "pmid": "11111"},
                evidence=MatchEvidence(
                    query_passage_id="q1",
                    source_passage_id="s1",
                    exact_overlap=0.95,
                    matched_token_count=25,
                ),
            ),
            PlagiarismMatch(
                match_id="m2",
                classification=MatchClass.PROPERLY_QUOTED,
                confidence=0.95,
                query_span={"start": 200, "end": 300},
                source_document_id="src_doc_2",
                source={"title": "Source 2", "pmid": "22222"},
                evidence=MatchEvidence(
                    query_passage_id="q2",
                    source_passage_id="s2",
                    quoted_text=True,
                ),
            ),
        ]

        report = ScoreAggregator.aggregate_report(
            check_id="chk_123",
            document=doc,
            matches=matches,
        )

        self.assertEqual(report.check_id, "chk_123")
        self.assertAlmostEqual(report.suspicious_coverage, 15.0)
        self.assertAlmostEqual(report.quoted_or_cited_coverage, 10.0)
        self.assertAlmostEqual(report.overall_matched_coverage, 25.0)
        self.assertEqual(report.risk_level, "MODERATE")

        d = report.to_dict()
        self.assertEqual(len(d["matches"]), 2)
        self.assertEqual(d["matches"][0]["classification"], "EXACT_COPY")


if __name__ == "__main__":
    unittest.main()
