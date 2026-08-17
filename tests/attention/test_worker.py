import unittest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock

from src.attention.database import Base, SessionLocal
from src.attention.models import ResearchWork, WorkIdentifier, AttentionJob, SourceRefresh, AttentionEvidence
from src.attention.worker import process_one_job
from src.config import RESEARCH_ATTENTION_DATABASE_URL

class TestWorker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(RESEARCH_ATTENTION_DATABASE_URL)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.session = self.Session()
        self.session.query(AttentionJob).delete()
        self.session.query(AttentionEvidence).delete()
        self.session.query(SourceRefresh).delete()
        self.session.query(WorkIdentifier).delete()
        self.session.query(ResearchWork).delete()
        self.session.commit()

        # Create work & identifiers
        self.work = ResearchWork(id="wrk_test123", normalized_title="test title")
        self.session.add(self.work)
        self.session.add(WorkIdentifier(work_id="wrk_test123", scheme="pmid", normalized_value="12345", display_value="12345"))
        
        # Create queued job
        self.job = AttentionJob(
            id="job_test123",
            work_id="wrk_test123",
            job_kind="full_refresh",
            state="queued",
            scheduled_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
        )
        self.session.add(self.job)
        self.session.commit()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    @patch("src.attention.connectors.wikimedia.WikimediaConnector.collect")
    def test_process_job_success(self, mock_collect):
        # Setup mock Wikimedia collect result
        from src.attention.connectors.base import ConnectorResult
        mock_collect.return_value = ConnectorResult(
            source="wikipedia",
            state="ready",
            evidence=[
                {
                    "source": "wikipedia",
                    "source_type": "reference",
                    "url": "https://en.wikipedia.org/wiki/Page1",
                    "title": "Page 1 Title",
                    "matched_identifier": "pmid:12345",
                    "match_confidence": "exact_identifier"
                }
            ],
            item_count=1
        )
        
        # Run worker processing
        processed = process_one_job()
        
        self.assertTrue(processed)
        
        # Query job and refreshes
        job_db = self.session.query(AttentionJob).filter_by(id="job_test123").first()
        self.assertEqual(job_db.state, "completed")
        
        refresh_db = self.session.query(SourceRefresh).filter_by(work_id="wrk_test123", source="wikipedia").first()
        self.assertIsNotNone(refresh_db)
        self.assertEqual(refresh_db.state, "ready")
        self.assertEqual(refresh_db.item_count, 1)
        
        evidence_db = self.session.query(AttentionEvidence).filter_by(work_id="wrk_test123", source="wikipedia").all()
        self.assertEqual(len(evidence_db), 1)
        self.assertEqual(evidence_db[0].url, "https://en.wikipedia.org/wiki/Page1")


    @patch("src.attention.connectors.wikimedia.WikimediaConnector.collect")
    def test_process_job_connector_failure(self, mock_collect):
        from src.attention.connectors.base import ConnectorResult
        mock_collect.return_value = ConnectorResult(
            source="wikipedia",
            state="failed",
            error_code="RATE_LIMIT",
            error_message="Too many requests",
            item_count=0
        )
        
        processed = process_one_job()
        self.assertTrue(processed)
        
        job_db = self.session.query(AttentionJob).filter_by(id="job_test123").first()
        self.assertEqual(job_db.state, "completed")  # Job completed but connector failed
        
        refresh_db = self.session.query(SourceRefresh).filter_by(work_id="wrk_test123", source="wikipedia").first()
        self.assertEqual(refresh_db.state, "failed")
        self.assertEqual(refresh_db.error_message, "Too many requests")

if __name__ == "__main__":
    unittest.main()
