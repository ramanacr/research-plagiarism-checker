import unittest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from src.attention.database import Base
from src.attention.models import ResearchWork, WorkIdentifier, AttentionEvidence
from src.config import RESEARCH_ATTENTION_DATABASE_URL

class TestDatabaseModels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(RESEARCH_ATTENTION_DATABASE_URL)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.session = self.Session()
        # Clean up database tables before each test
        self.session.query(AttentionEvidence).delete()
        self.session.query(WorkIdentifier).delete()
        self.session.query(ResearchWork).delete()
        self.session.commit()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_create_work_with_identifiers_and_evidence(self):
        # Create work
        work = ResearchWork(
            id="wrk_test123",
            normalized_title="a study of ranibizumab in diabetic retinopathy",
            journal="Retina Journal",
            publication_date=datetime.date(2023, 1, 1),
            authors=["John Doe"]
        )
        self.session.add(work)
        
        # Add identifier
        identifier = WorkIdentifier(
            work_id="wrk_test123",
            scheme="pmid",
            normalized_value="12345678",
            display_value="12345678",
            source="pubmed"
        )
        self.session.add(identifier)
        
        # Add evidence
        url = "https://en.wikipedia.org/wiki/Ranibizumab"
        url_hash = AttentionEvidence.compute_url_hash(url)
        evidence = AttentionEvidence(
            id="evd_test123",
            work_id="wrk_test123",
            source="wikipedia",
            source_type="reference",
            external_id="11111",
            url=url,
            url_hash=url_hash,
            title="Ranibizumab Wiki",
            matched_identifier="pmid:12345678",
            match_confidence="exact_identifier"
        )
        self.session.add(evidence)
        self.session.commit()
        
        # Query and assert
        queried = self.session.query(ResearchWork).filter_by(id="wrk_test123").first()
        self.assertIsNotNone(queried)
        self.assertEqual(len(queried.identifiers), 1)
        self.assertEqual(queried.identifiers[0].normalized_value, "12345678")
        self.assertEqual(len(queried.evidence), 1)
        self.assertEqual(queried.evidence[0].url_hash, url_hash)

    def test_duplicate_identifier_fails(self):
        work = ResearchWork(
            id="wrk_test123",
            normalized_title="title test",
            journal="Retina Journal",
            publication_date=datetime.date(2023, 1, 1),
            authors=["John Doe"]
        )
        self.session.add(work)
        
        identifier1 = WorkIdentifier(
            work_id="wrk_test123",
            scheme="pmid",
            normalized_value="12345678",
            display_value="12345678",
            source="pubmed"
        )
        self.session.add(identifier1)
        self.session.commit()

        # Adding same identifier for a different work (or same work) should trigger unique constraint failure
        work2 = ResearchWork(
            id="wrk_test456",
            normalized_title="another title",
            journal="Retina Journal",
            publication_date=datetime.date(2023, 1, 1),
            authors=["Jane Doe"]
        )
        self.session.add(work2)
        
        identifier2 = WorkIdentifier(
            work_id="wrk_test456",
            scheme="pmid",
            normalized_value="12345678",
            display_value="12345678",
            source="europe_pmc"
        )
        self.session.add(identifier2)
        
        with self.assertRaises(IntegrityError):
            self.session.commit()

if __name__ == "__main__":
    unittest.main()
