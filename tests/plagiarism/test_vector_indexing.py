"""
Tests for persistent dense vector indexing and embedding service.
"""

import unittest
import tempfile
import shutil
import os
import numpy as np

from src.plagiarism.indexing.vector.faiss_index import VectorIndex
from src.plagiarism.indexing.vector.embedder import EmbeddingService


class TestVectorIndexing(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_vector_index_operations(self):
        dim = 128
        index = VectorIndex(dimension=dim, model_name="test-model", index_version="v1")
        
        # Create synthetic vectors
        v1 = np.zeros(dim, dtype=np.float32)
        v1[0] = 1.0
        
        v2 = np.zeros(dim, dtype=np.float32)
        v2[1] = 1.0

        v_similar = np.zeros(dim, dtype=np.float32)
        v_similar[0] = 0.95
        v_similar[1] = 0.05

        index.insert("p1", v1, "doc1", {"title": "Doc 1"})
        index.insert("p2", v2, "doc2", {"title": "Doc 2"})

        self.assertEqual(index.total_vectors, 2)

        # Search for vector similar to v1
        results = index.search(v_similar, top_k=5, threshold=0.7)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["passage_id"], "p1")
        self.assertGreater(results[0]["similarity"], 0.90)

        # Batch insert
        v3 = np.zeros(dim, dtype=np.float32)
        v3[2] = 1.0
        index.insert_batch(["p3"], np.array([v3]), ["doc3"], [{"title": "Doc 3"}])
        self.assertEqual(index.total_vectors, 3)

        # Persistence save and reload
        save_file = os.path.join(self.temp_dir, "vector_index.pkl")
        index.save(save_file)
        
        loaded = VectorIndex.load(save_file)
        self.assertEqual(loaded.total_vectors, 3)
        self.assertEqual(loaded.dimension, dim)
        
        loaded_results = loaded.search(v_similar, top_k=5, threshold=0.7)
        self.assertEqual(len(loaded_results), 1)
        self.assertEqual(loaded_results[0]["passage_id"], "p1")

        # Deletion
        deleted = loaded.delete_document("doc1")
        self.assertEqual(deleted, 1)
        self.assertEqual(loaded.total_vectors, 2)

    def test_embedding_service_cosine_math(self):
        service = EmbeddingService()
        v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v3 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        
        sim1 = service.compute_cosine_similarity(v1, v2)
        sim2 = service.compute_cosine_similarity(v1, v3)
        
        self.assertAlmostEqual(sim1, 1.0)
        self.assertAlmostEqual(sim2, 0.0)


if __name__ == "__main__":
    unittest.main()
