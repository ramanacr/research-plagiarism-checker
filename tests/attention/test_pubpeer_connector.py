import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.attention.database import Base
from src.attention.models import ResearchWork, WorkIdentifier
from src.attention.connectors.pubpeer import PubPeerConnector
from src.config import RESEARCH_ATTENTION_DATABASE_URL

class TestPubPeerConnector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(RESEARCH_ATTENTION_DATABASE_URL)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.session = self.Session()
        self.session.query(WorkIdentifier).delete()
        self.session.query(ResearchWork).delete()
        self.session.commit()

        # Create work
        self.work = ResearchWork(id="wrk_pubpeer123", normalized_title="test pubpeer")
        self.session.add(self.work)
        self.session.add(WorkIdentifier(work_id="wrk_pubpeer123", scheme="doi", normalized_value="10.1000/peer", display_value="10.1000/peer"))
        self.session.commit()

        self.connector = PubPeerConnector()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    @patch("requests.get")
    def test_collect_pubpeer_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "comments": [
                {
                    "id": 1122,
                    "title": "First peer comment",
                    "url": "https://pubpeer.com/publications/10.1000/peer#comment-1122",
                    "created_at": "2026-06-01T12:00:00Z"
                }
            ]
        }
        mock_get.return_value = mock_response

        result = self.connector.collect(self.work)
        self.assertEqual(result.state, "ready")
        self.assertEqual(len(result.evidence), 1)
        self.assertEqual(result.evidence[0]["external_id"], "1122")
        self.assertEqual(result.evidence[0]["title"], "First peer comment")

    @patch("src.config.RESEARCH_ATTENTION_ENABLE_PUBPEER", False)
    def test_collect_disabled(self):
        result = self.connector.collect(self.work)
        self.assertEqual(result.state, "not_configured")

if __name__ == "__main__":
    unittest.main()
