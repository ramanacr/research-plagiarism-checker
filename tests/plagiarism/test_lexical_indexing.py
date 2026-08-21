"""
Tests for persistent lexical indexing, MinHash LSH, shingles, and CorpusIndexer.
"""

import unittest
import tempfile
import os
import shutil

from src.plagiarism.indexing.lexical.shingles import (
    generate_word_shingles,
    generate_shingle_strings,
    compute_shingle_containment,
    compute_shingle_jaccard,
)
from src.plagiarism.indexing.lexical.minhash import MinHashGenerator
from src.plagiarism.indexing.lexical.lsh import PersistentLexicalIndex
from src.plagiarism.indexing.corpus_indexer import CorpusIndexer
from src.plagiarism.config.settings import EngineConfig


SAMPLE_SOURCE_DOC_1 = """
Diabetic retinopathy is a microvascular complication of diabetes leading to severe vision loss.
Treatment with ranibizumab significantly reduces macular edema and improves visual outcomes in clinical trials.
Vascular endothelial growth factor inhibition is a proven therapeutic mechanism.
"""

SAMPLE_SOURCE_DOC_2 = """
Water purification systems using deep gravity carbon filtration provide clean drinking water in developing areas.
Mechanical stability and low cost make gravity filters optimal for rural infrastructure.
"""

SAMPLE_QUERY_COPIED = """
Patients with diabetic retinopathy experience severe vision loss.
Treatment with ranibizumab significantly reduces macular edema and improves visual outcomes in clinical trials.
"""


class TestLexicalIndexing(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_shingle_metrics(self):
        text1 = "patients with diabetic retinopathy were treated with ranibizumab"
        text2 = "patients with diabetic retinopathy were treated with laser photocoagulation"
        
        shingles1 = generate_shingle_strings(text1, k=4)
        shingles2 = generate_shingle_strings(text2, k=4)
        
        containment = compute_shingle_containment(shingles1, shingles2)
        jaccard = compute_shingle_jaccard(shingles1, shingles2)
        
        self.assertGreater(containment, 0.4)
        self.assertGreater(jaccard, 0.2)

    def test_minhash_serialization(self):
        gen = MinHashGenerator(num_perm=128)
        shingles = {"diabetic retinopathy", "ranibizumab therapy", "macular edema"}
        m1 = gen.compute_minhash(shingles)
        
        raw_bytes = gen.serialize_minhash(m1)
        self.assertIsInstance(raw_bytes, bytes)
        
        m2 = gen.deserialize_minhash(raw_bytes)
        j = gen.estimate_jaccard(m1, m2)
        self.assertAlmostEqual(j, 1.0)

    def test_persistent_lexical_index_operations(self):
        index = PersistentLexicalIndex(shingle_size=4, num_perm=128, lsh_threshold=0.3)
        
        index.insert_passage("p1", SAMPLE_SOURCE_DOC_1, "doc1", {"title": "Doc 1"})
        index.insert_passage("p2", SAMPLE_SOURCE_DOC_2, "doc2", {"title": "Doc 2"})
        
        self.assertEqual(index.total_passages, 2)
        self.assertEqual(index.total_documents, 2)

        # Query containment
        q_shingles = generate_shingle_strings(SAMPLE_QUERY_COPIED, k=4)
        results = index.query_containment(q_shingles, top_k=10, threshold=0.2)
        
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["passage_id"], "p1")
        self.assertGreater(results[0]["containment"], 0.3)

        # Persistence save and load
        save_path = os.path.join(self.temp_dir, "lex_index.pkl")
        index.save(save_path)
        
        loaded = PersistentLexicalIndex.load(save_path)
        self.assertEqual(loaded.total_passages, 2)
        
        results_loaded = loaded.query_containment(q_shingles, top_k=10, threshold=0.2)
        self.assertEqual(results_loaded[0]["passage_id"], "p1")

        # Deletion
        deleted = loaded.delete_document("doc1")
        self.assertEqual(deleted, 1)
        self.assertEqual(loaded.total_passages, 1)

    def test_corpus_indexer(self):
        cfg = EngineConfig(storage_dir=self.temp_dir)
        indexer = CorpusIndexer(config=cfg)
        
        p_count = indexer.index_raw_text("doc_bio_1", SAMPLE_SOURCE_DOC_1, title="Ranibizumab in Retinopathy")
        self.assertGreater(p_count, 0)
        self.assertEqual(len(indexer.document_registry), 1)

        # Incremental skip check
        same_count = indexer.index_raw_text("doc_bio_1", SAMPLE_SOURCE_DOC_1, title="Ranibizumab in Retinopathy")
        self.assertEqual(same_count, p_count)

        # Save all and reload
        indexer.save_all()
        
        new_indexer = CorpusIndexer(config=cfg)
        new_indexer.load_all()
        self.assertEqual(len(new_indexer.document_registry), 1)
        self.assertIn("doc_bio_1", new_indexer.document_registry)


if __name__ == "__main__":
    unittest.main()
