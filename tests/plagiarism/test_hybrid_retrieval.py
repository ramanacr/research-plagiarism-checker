"""
Tests for hybrid candidate retrieval, multi-channel fusion, and Recall@K evaluation.
"""

import unittest
import numpy as np

from src.plagiarism.documents.models import Passage, SectionType
from src.plagiarism.indexing.lexical.lsh import PersistentLexicalIndex
from src.plagiarism.indexing.vector.faiss_index import VectorIndex
from src.plagiarism.indexing.vector.embedder import EmbeddingService
from src.plagiarism.retrieval.lexical import LexicalRetriever
from src.plagiarism.retrieval.semantic import SemanticRetriever
from src.plagiarism.retrieval.exact import ExactPhraseRetriever
from src.plagiarism.retrieval.fusion import HybridRetriever, CandidateHit


class TestHybridRetrieval(unittest.TestCase):
    def setUp(self):
        # Setup mock / synthetic indexes
        self.lex_index = PersistentLexicalIndex(shingle_size=4, num_perm=64, lsh_threshold=0.2)
        self.vec_index = VectorIndex(dimension=8, model_name="dummy", index_version="v1")

        # Insert Source Passages
        text1 = "patients with diabetic retinopathy were treated with monthly ranibizumab injections"
        text2 = "water purification using gravity filtering systems in remote rural locations"

        self.lex_index.insert_passage("src_1", text1, "doc_1", {"title": "Study 1"})
        self.lex_index.insert_passage("src_2", text2, "doc_2", {"title": "Study 2"})

        # Synthetic embeddings
        v1 = np.array([1, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
        v2 = np.array([0, 1, 0, 0, 0, 0, 0, 0], dtype=np.float32)

        self.vec_index.insert("src_1", v1, "doc_1", {"title": "Study 1"})
        self.vec_index.insert("src_2", v2, "doc_2", {"title": "Study 2"})

        self.lex_retriever = LexicalRetriever(self.lex_index, top_k=5, threshold=0.1)
        self.exact_retriever = ExactPhraseRetriever(self.lex_index, top_k=5)

    def test_lexical_and_exact_retrieval(self):
        q_text = "patients with diabetic retinopathy were treated with monthly ranibizumab"
        q_passage = Passage(
            passage_id="q_1",
            document_id="qdoc",
            section="Intro",
            section_type=SectionType.BODY,
            paragraph_index=0,
            text=q_text,
            normalized_text=q_text,
            start_offset=0,
            end_offset=len(q_text),
            token_count=10,
        )

        lex_hits = self.lex_retriever.retrieve_candidates(q_passage)
        self.assertGreaterEqual(len(lex_hits), 1)
        self.assertEqual(lex_hits[0]["source_passage_id"], "src_1")

        exact_hits = self.exact_retriever.retrieve_candidates(q_passage)
        self.assertGreaterEqual(len(exact_hits), 1)
        self.assertEqual(exact_hits[0]["source_passage_id"], "src_1")

    def test_hybrid_fusion(self):
        q_text = "patients with diabetic retinopathy were treated with monthly ranibizumab"
        q_passage = Passage(
            passage_id="q_1",
            document_id="qdoc",
            section="Intro",
            section_type=SectionType.BODY,
            paragraph_index=0,
            text=q_text,
            normalized_text=q_text,
            start_offset=0,
            end_offset=len(q_text),
            token_count=10,
        )

        # Mock semantic retriever that returns semantic match for v_query
        class MockSemanticRetriever:
            def retrieve_candidates(self, qp, query_vector=None, top_k=None):
                return [{
                    "query_passage_id": qp.passage_id,
                    "source_passage_id": "src_1",
                    "document_id": "doc_1",
                    "channel": "semantic",
                    "semantic_score": 0.92,
                    "metadata": {},
                }]

        hybrid = HybridRetriever(
            lexical_retriever=self.lex_retriever,
            semantic_retriever=MockSemanticRetriever(),
            exact_retriever=self.exact_retriever,
            top_k=5,
        )

        fused = hybrid.retrieve(q_passage)
        self.assertGreaterEqual(len(fused), 1)
        top = fused[0]
        self.assertEqual(top.source_passage_id, "src_1")
        self.assertIn("lexical", top.channels)
        self.assertIn("semantic", top.channels)
        self.assertIn("exact", top.channels)
        self.assertGreater(top.fusion_score, 0.5)

    def test_recall_at_k_evaluation(self):
        ground_truth = {
            "q_1": {"src_1"},
            "q_2": {"src_2"},
        }
        retrieved = {
            "q_1": [
                CandidateHit(query_passage_id="q_1", source_passage_id="src_1", document_id="doc_1"),
                CandidateHit(query_passage_id="q_1", source_passage_id="src_9", document_id="doc_9"),
            ],
            "q_2": [
                CandidateHit(query_passage_id="q_2", source_passage_id="src_9", document_id="doc_9"),
                CandidateHit(query_passage_id="q_2", source_passage_id="src_2", document_id="doc_2"),
            ],
        }

        recall_at_1 = HybridRetriever.compute_recall_at_k(ground_truth, retrieved, k=1)
        recall_at_2 = HybridRetriever.compute_recall_at_k(ground_truth, retrieved, k=2)

        self.assertEqual(recall_at_1, 0.5)
        self.assertEqual(recall_at_2, 1.0)


if __name__ == "__main__":
    unittest.main()
