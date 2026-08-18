import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.attention.database import Base
from src.attention.models import ResearchWork, WorkIdentifier
from src.attention.connectors.crossref_event import CrossrefEventConnector
from src.config import RESEARCH_ATTENTION_DATABASE_URL

class TestCrossrefEventConnector(unittest.TestCase):
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
        self.work = ResearchWork(id="wrk_crossref123", normalized_title="test crossref")
        self.session.add(self.work)
        self.session.add(WorkIdentifier(work_id="wrk_crossref123", scheme="doi", normalized_value="10.1000/cross", display_value="10.1000/cross"))
        self.session.commit()

        self.connector = CrossrefEventConnector()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    @patch("requests.get")
    def test_collect_crossref_events_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "relation": {
                    "is-supplemented-by": [
                        {
                            "id": "10.1000/dataset_001",
                            "id-type": "doi",
                            "asserted-by": "subject"
                        }
                    ]
                },
                "assertion": [
                    {
                        "name": "articlelink",
                        "label": "Publisher maintained version",
                        "value": "https://doi.org/10.1000/example"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        result = self.connector.collect(self.work)
        self.assertEqual(result.state, "ready")
        
        self.assertEqual(len(result.evidence), 1)
        self.assertEqual(result.evidence[0]["external_id"], "10.1000/dataset_001")
        self.assertEqual(result.evidence[0]["source_type"], "inbound_relation")



    @patch("src.config.RESEARCH_ATTENTION_ENABLE_CROSSREF_EVENT", False)
    def test_collect_disabled(self):
        result = self.connector.collect(self.work)
        self.assertEqual(result.state, "not_configured")

if __name__ == "__main__":
    unittest.main()
