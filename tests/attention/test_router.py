import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api import app
from src.attention.database import Base, get_db
from src.attention.models import ResearchWork, WorkIdentifier, SourceRefresh, AttentionJob
from src.config import RESEARCH_ATTENTION_DATABASE_URL

class TestRouter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(RESEARCH_ATTENTION_DATABASE_URL)
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)
        cls.client = TestClient(app)

    def setUp(self):
        self.session = self.Session()
        self.session.query(AttentionJob).delete()
        self.session.query(SourceRefresh).delete()
        self.session.query(WorkIdentifier).delete()
        self.session.query(ResearchWork).delete()
        self.session.commit()

        # Override get_db Dependency for test session injection
        def override_get_db():
            try:
                yield self.session
            finally:
                pass
        app.dependency_overrides[get_db] = override_get_db

    def tearDown(self):
        self.session.rollback()
        self.session.close()
        app.dependency_overrides.clear()

    @patch("src.attention.resolver.WorkResolver.resolve_work")
    def test_lookup_pmid_endpoints(self, mock_resolve):
        work = ResearchWork(id="wrk_pmid123", normalized_title="pmid title")
        self.session.add(work)
        self.session.add(WorkIdentifier(work_id="wrk_pmid123", scheme="pmid", normalized_value="12345", display_value="12345"))
        self.session.commit()
        
        mock_resolve.return_value = work
        
        response = self.client.get("/api/v1/research-attention/works/pmid/12345")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["work_id"], "wrk_pmid123")
        self.assertEqual(data["canonical_work"]["title"], "pmid title")

    def test_refresh_authentication(self):
        work = ResearchWork(id="wrk_refresh", normalized_title="title refresh")
        self.session.add(work)
        self.session.commit()
        
        # 1. No key -> 403 Forbidden
        response = self.client.post("/api/v1/research-attention/works/wrk_refresh/refresh")
        self.assertEqual(response.status_code, 403)
        
        # 2. Invalid key -> 403 Forbidden
        response = self.client.post(
            "/api/v1/research-attention/works/wrk_refresh/refresh",
            headers={"X-Research-Attention-Key": "wrong-key"}
        )
        self.assertEqual(response.status_code, 403)
        
        # 3. Valid key -> 202 Accepted
        from src.config import RESEARCH_ATTENTION_INTERNAL_API_KEY
        response = self.client.post(
            "/api/v1/research-attention/works/wrk_refresh/refresh",
            headers={"X-Research-Attention-Key": RESEARCH_ATTENTION_INTERNAL_API_KEY}
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "queued")

    def test_analytics_endpoint(self):
        # Setup work and evidence
        work = ResearchWork(id="wrk_analytics_test", normalized_title="analytics test")
        self.session.add(work)
        
        # Add active evidence
        import datetime
        from src.attention.models import AttentionEvidence
        ev = AttentionEvidence(
            id="ev_an1",
            work_id="wrk_analytics_test",
            source="wikipedia",
            source_type="reference",
            url="https://en.wikipedia.org/wiki/Test1",
            url_hash="hash1",
            published_at=datetime.date(2026, 8, 1),
            matched_identifier="doi:10.1000/test",
            match_confidence="exact_identifier",
            active=True
        )
        self.session.add(ev)
        self.session.commit()
        
        response = self.client.get("/api/v1/research-attention/works/wrk_analytics_test/analytics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["work_id"], "wrk_analytics_test")
        self.assertEqual(len(data["source_breakdown"]), 1)
        self.assertEqual(data["source_breakdown"][0]["source"], "wikipedia")
        self.assertEqual(data["source_breakdown"][0]["count"], 1)
        self.assertEqual(len(data["timeline"]), 1)
        self.assertEqual(data["timeline"][0]["timestamp"], "2026-08")

    def test_web_routes(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("portal-title", response.text)

        response = self.client.get("/plagiarism")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Research Plagiarism Checker", response.text)

        response = self.client.get("/attention")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Research Attention Engine", response.text)

if __name__ == "__main__":
    unittest.main()
