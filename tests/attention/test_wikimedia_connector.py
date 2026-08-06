import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.attention.database import Base
from src.attention.models import ResearchWork, WorkIdentifier
from src.attention.connectors.wikimedia import WikimediaConnector
from src.config import RESEARCH_ATTENTION_DATABASE_URL
import datetime

class TestWikimediaConnector(unittest.TestCase):
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

        # Create work with PMID and DOI
        self.work = ResearchWork(id="wrk_test123", normalized_title="test title")
        self.session.add(self.work)
        self.session.add(WorkIdentifier(work_id="wrk_test123", scheme="pmid", normalized_value="12345678", display_value="12345678"))
        self.session.add(WorkIdentifier(work_id="wrk_test123", scheme="doi", normalized_value="10.1000/test", display_value="10.1000/test"))
        self.session.commit()
        
        self.connector = WikimediaConnector()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    @patch("requests.get")
    def test_collect_success_and_deduplicate(self, mock_get):
        # 1. Mock search queries response
        mock_search_response = MagicMock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            "query": {
                "search": [
                    {
                        "pageid": 51234,
                        "title": "Tenapanor page",
                        "timestamp": "2026-08-05T10:00:00Z"
                    }
                ]
            }
        }
        
        # 2. Mock revision query response (verifies DOI exist in page wikitext)
        mock_revisions_response = MagicMock()
        mock_revisions_response.status_code = 200
        mock_revisions_response.json.return_value = {
            "query": {
                "pages": {
                    "51234": {
                        "pageid": 51234,
                        "revisions": [
                            {
                                "slots": {
                                    "main": {
                                        "*": "This page mentions DOI 10.1000/test in references."
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        mock_get.side_effect = [mock_search_response, mock_search_response, mock_revisions_response]
        
        res = self.connector.collect(self.work)
        
        self.assertEqual(res.source, "wikipedia")
        self.assertEqual(res.state, "ready")
        # Assert page deduplication: should merge into a single evidence item
        self.assertEqual(len(res.evidence), 1)
        self.assertEqual(res.evidence[0]["external_id"], "51234")
        self.assertEqual(res.evidence[0]["title"], "Tenapanor page")
        self.assertEqual(res.evidence[0]["url"], "https://en.wikipedia.org/wiki/Tenapanor_page")

    @patch("src.config.RESEARCH_ATTENTION_ENABLE_WIKIMEDIA", False)
    def test_collect_disabled(self):
        res = self.connector.collect(self.work)
        self.assertEqual(res.state, "not_configured")

if __name__ == "__main__":
    unittest.main()
