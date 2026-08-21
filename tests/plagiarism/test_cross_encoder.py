"""
Tests for optional cross-encoder candidate reranker.
"""

import unittest
from unittest.mock import MagicMock
from src.plagiarism.documents.models import Passage, SectionType
from src.plagiarism.retrieval.fusion import CandidateHit
from src.plagiarism.matching.cross_encoder import CrossEncoderReranker
from src.plagiarism.config.settings import RerankerSettings


class TestCrossEncoder(unittest.TestCase):
    def test_disabled_by_default_pass_through(self):
        reranker = CrossEncoderReranker(RerankerSettings(enabled=False))
        self.assertFalse(reranker.enabled)

        qp = Passage(
            passage_id="q1",
            document_id="doc1",
            section="Intro",
            section_type=SectionType.BODY,
            paragraph_index=0,
            text="Query text",
            normalized_text="query text",
            start_offset=0,
            end_offset=10,
            token_count=2,
        )

        hits = [
            CandidateHit(query_passage_id="q1", source_passage_id="s1", document_id="d1", fusion_score=0.9),
            CandidateHit(query_passage_id="q1", source_passage_id="s2", document_id="d2", fusion_score=0.5),
        ]

        reranked = reranker.rerank(qp, hits)
        self.assertEqual(len(reranked), 2)
        self.assertEqual(reranked[0].source_passage_id, "s1")

    def test_enabled_reranking(self):
        reranker = CrossEncoderReranker(RerankerSettings(enabled=True, top_k=5))
        reranker._model = MagicMock()
        reranker._model.predict.return_value = [0.1, 0.95]

        qp = Passage(
            passage_id="q1",
            document_id="doc1",
            section="Intro",
            section_type=SectionType.BODY,
            paragraph_index=0,
            text="Query text",
            normalized_text="query text",
            start_offset=0,
            end_offset=10,
            token_count=2,
        )

        hits = [
            CandidateHit(
                query_passage_id="q1",
                source_passage_id="s1",
                document_id="d1",
                fusion_score=0.8,
                metadata={"text": "Source 1 text"},
            ),
            CandidateHit(
                query_passage_id="q1",
                source_passage_id="s2",
                document_id="d2",
                fusion_score=0.5,
                metadata={"text": "Source 2 text"},
            ),
        ]

        reranked = reranker.rerank(qp, hits)
        self.assertEqual(len(reranked), 2)
        # s2 had score 0.95 vs s1 score 0.1, so s2 is top
        self.assertEqual(reranked[0].source_passage_id, "s2")
        self.assertEqual(reranked[0].cross_encoder_score, 0.95)


if __name__ == "__main__":
    unittest.main()
