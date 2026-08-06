import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.attention.database import Base
from src.attention.models import ResearchWork, WorkIdentifier, AttentionEvidence
from src.attention.services import save_evidence
from src.config import RESEARCH_ATTENTION_DATABASE_URL

class TestEvidenceDeduplication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(RESEARCH_ATTENTION_DATABASE_URL)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.session = self.Session()
        self.session.query(AttentionEvidence).delete()
        self.session.query(WorkIdentifier).delete()
        self.session.query(ResearchWork).delete()
        self.session.commit()

        # Insert test work
        self.work = ResearchWork(id="wrk_test", normalized_title="test title")
        self.session.add(self.work)
        self.session.commit()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_deduplicate_by_url(self):
        evidence_list = [
            {
                "source": "wikipedia",
                "source_type": "reference",
                "url": "https://en.wikipedia.org/wiki/Test_Page?param=1#section",
                "title": "Title 1",
                "matched_identifier": "doi:10.1000/example",
                "match_confidence": "exact_identifier"
            }
        ]
        save_evidence(self.session, "wrk_test", evidence_list)
        
        # Query
        results = self.session.query(AttentionEvidence).all()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Title 1")
        self.assertTrue(results[0].active)

        # Ingest same URL with query parameters/fragments stripped - should update, not create new
        evidence_list2 = [
            {
                "source": "wikipedia",
                "source_type": "reference",
                "url": "https://en.wikipedia.org/wiki/Test_Page?param=2#different_section",
                "title": "Title Updated",
                "matched_identifier": "doi:10.1000/example",
                "match_confidence": "exact_identifier"
            }
        ]
        save_evidence(self.session, "wrk_test", evidence_list2)
        
        results2 = self.session.query(AttentionEvidence).all()
        self.assertEqual(len(results2), 1)
        self.assertEqual(results2[0].title, "Title Updated")

    def test_probable_match_inactive(self):
        evidence_list = [
            {
                "source": "wikipedia",
                "source_type": "reference",
                "url": "https://en.wikipedia.org/wiki/Probable_Page",
                "title": "Probable Title",
                "matched_identifier": "doi:10.1000/example",
                "match_confidence": "probable"
            }
        ]
        save_evidence(self.session, "wrk_test", evidence_list)
        
        results = self.session.query(AttentionEvidence).all()
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].active)

if __name__ == "__main__":
    unittest.main()
