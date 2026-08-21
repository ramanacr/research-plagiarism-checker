"""
Tests for detailed multi-signal matching and passage aggregation.
"""

import unittest
from src.plagiarism.documents.models import Passage, SectionType
from src.plagiarism.matching.exact import find_longest_common_phrase, compute_exact_token_overlap
from src.plagiarism.matching.lexical import (
    compute_token_jaccard,
    compute_token_containment,
    compute_edit_similarity,
)
from src.plagiarism.matching.features import MatchFeatureExtractor, PassageAggregator


class TestMatchingFeatures(unittest.TestCase):
    def test_longest_common_phrase(self):
        text1 = "Patients with center-involved diabetic macular edema were enrolled across five clinical centers."
        text2 = "In this trial, patients with center-involved diabetic macular edema were evaluated for treatment."

        phrase, length = find_longest_common_phrase(text1, text2)
        self.assertEqual(phrase, "patients with center involved diabetic macular edema were")
        self.assertEqual(length, 8)

    def test_exact_token_overlap(self):
        q = "Patients with center-involved diabetic macular edema received ranibizumab."
        s = "Patients with center-involved diabetic macular edema were treated with laser."

        ratio, count, phrases = compute_exact_token_overlap(q, s)
        self.assertGreater(ratio, 0.5)
        self.assertGreaterEqual(count, 5)
        self.assertTrue(any("diabetic macular edema" in p for p in phrases))

    def test_lexical_metrics(self):
        text1 = "monthly ranibizumab injections significantly improved visual acuity"
        text2 = "monthly ranibizumab injections improved visual acuity outcomes"

        j = compute_token_jaccard(text1, text2)
        c = compute_token_containment(text1, text2)
        edit = compute_edit_similarity(text1, text2)

        self.assertGreater(j, 0.6)
        self.assertGreater(c, 0.7)
        self.assertGreater(edit, 0.7)

    def test_feature_extractor(self):
        extractor = MatchFeatureExtractor(embedder=None, shingle_size=4)

        qp = Passage(
            passage_id="q1",
            document_id="qdoc",
            section="Methods",
            section_type=SectionType.METHODS,
            paragraph_index=0,
            text="Patients with diabetic retinopathy received monthly ranibizumab injections.",
            normalized_text="patients with diabetic retinopathy received monthly ranibizumab injections",
            start_offset=0,
            end_offset=74,
            token_count=9,
        )

        sp = Passage(
            passage_id="s1",
            document_id="sdoc",
            section="Methods",
            section_type=SectionType.METHODS,
            paragraph_index=0,
            text="Patients with diabetic retinopathy received monthly ranibizumab injections.",
            normalized_text="patients with diabetic retinopathy received monthly ranibizumab injections",
            start_offset=100,
            end_offset=174,
            token_count=9,
        )

        feats = extractor.extract_features(qp, sp)
        self.assertEqual(feats.exact_overlap, 1.0)
        self.assertEqual(feats.shingle_containment, 1.0)
        self.assertEqual(feats.jaccard_similarity, 1.0)
        self.assertEqual(feats.matched_token_count, 8)

    def test_passage_aggregator(self):
        matches = [
            {
                "source_document_id": "doc_123",
                "query_span": {"start": 0, "end": 100},
                "evidence": {
                    "matching_phrases": ["diabetic retinopathy study"],
                    "exact_overlap": 0.8,
                    "shingle_containment": 0.9,
                    "semantic_similarity": 0.85,
                }
            },
            {
                "source_document_id": "doc_123",
                "query_span": {"start": 105, "end": 220},
                "evidence": {
                    "matching_phrases": ["ranibizumab visual acuity"],
                    "exact_overlap": 0.7,
                    "shingle_containment": 0.8,
                    "semantic_similarity": 0.88,
                }
            },
            {
                "source_document_id": "doc_999",
                "query_span": {"start": 300, "end": 400},
                "evidence": {
                    "matching_phrases": ["unrelated study phrase"],
                    "exact_overlap": 0.4,
                    "shingle_containment": 0.4,
                    "semantic_similarity": 0.5,
                }
            }
        ]

        aggregated = PassageAggregator.aggregate_matches(matches)
        self.assertEqual(len(aggregated), 2)
        # First two merged into single block
        self.assertEqual(aggregated[0]["source_document_id"], "doc_123")
        self.assertEqual(aggregated[0]["query_span"]["start"], 0)
        self.assertEqual(aggregated[0]["query_span"]["end"], 220)
        self.assertEqual(len(aggregated[0]["evidence"]["matching_phrases"]), 2)


if __name__ == "__main__":
    unittest.main()
