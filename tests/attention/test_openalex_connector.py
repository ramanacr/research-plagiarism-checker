import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.attention.database import Base
from src.attention.models import ResearchWork, WorkIdentifier
from src.attention.connectors.openalex import OpenAlexConnector
from src.config import RESEARCH_ATTENTION_DATABASE_URL

class TestOpenAlexConnector(unittest.TestCase):
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
        self.work = ResearchWork(id="wrk_alex123", normalized_title="test openalex")
        self.session.add(self.work)
        self.session.add(WorkIdentifier(work_id="wrk_alex123", scheme="doi", normalized_value="10.1000/alex", display_value="10.1000/alex"))
        self.session.commit()

        self.connector = OpenAlexConnector()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    @patch("requests.get")
    def test_collect_openalex_success(self, mock_get):
        # First call mock response: resolves work and returns cited_by_api_url
        res1 = MagicMock()
        res1.status_code = 200
        res1.json.return_value = {
            "cited_by_api_url": "https://api.openalex.org/works?filter=cites:W12345"
        }
        
        # Second call mock response: returns citation results
        res2 = MagicMock()
        res2.status_code = 200
        res2.json.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/W9999",
                    "title": "Citing paper 1",
                    "doi": "10.1000/citing1",
                    "publication_date": "2026-05-15"
                }
            ]
        }
        
        mock_get.side_effect = [res1, res2]

        result = self.connector.collect(self.work)
        self.assertEqual(result.state, "ready")
        self.assertEqual(len(result.evidence), 1)
        self.assertEqual(result.evidence[0]["title"], "Cited in: Citing paper 1")

        self.assertEqual(result.evidence[0]["url"], "10.1000/citing1")

    @patch("src.config.RESEARCH_ATTENTION_ENABLE_OPENALEX", False)
    def test_collect_disabled(self):
        result = self.connector.collect(self.work)
        self.assertEqual(result.state, "not_configured")

if __name__ == "__main__":
    unittest.main()
