import unittest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock

from src.attention.database import Base
from src.attention.models import ResearchWork, WorkIdentifier, AttentionJob, SourceRefresh
from src.attention.worker import process_one_job
from src.config import RESEARCH_ATTENTION_DATABASE_URL

class TestRetryPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(RESEARCH_ATTENTION_DATABASE_URL)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.session = self.Session()
        self.session.query(AttentionJob).delete()
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
    def test_unexpected_connector_exception_captured(self, mock_collect):
        # Set mock collect to raise exception
        mock_collect.side_effect = Exception("API connection dropped")
        
        processed = process_one_job()
        
        self.assertTrue(processed)
        
        # Verify SourceRefresh status records exception info safely
        refresh_db = self.session.query(SourceRefresh).filter_by(work_id="wrk_test123", source="wikipedia").first()
        self.assertIsNotNone(refresh_db)
        self.assertEqual(refresh_db.state, "failed")
        self.assertEqual(refresh_db.error_code, "UNEXPECTED_CONNECTOR_ERROR")
        self.assertIn("API connection dropped", refresh_db.error_message)

if __name__ == "__main__":
    unittest.main()
