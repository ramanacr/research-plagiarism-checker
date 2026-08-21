"""
End-to-end integration tests for v2 PlagiarismService, Agent, and API endpoints.
"""

import unittest
import tempfile
import shutil
import os
from fastapi.testclient import TestClient

from src.plagiarism.config.settings import EngineConfig, get_default_config
from src.plagiarism.services.plagiarism_service import PlagiarismService
from src.plagiarism.providers.base import SourceDocument
from src.agent import ResearchGuardrailAgent
from src.api import app, agent


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config = get_default_config()
        self.config.storage_dir = self.temp_dir

        self.service = PlagiarismService(config=self.config)

        # Pre-seed index with a published paper
        source_text = (
            "Patients with center-involved diabetic macular edema were treated with monthly "
            "intravitreal ranibizumab injections across five clinical trial sites. "
            "Visual acuity significantly improved from baseline over twelve months of treatment."
        )
        s_doc = SourceDocument(
            document_id="src:trial_001",
            provider="pubmed",
            provider_source_id="10001",
            pmid="10001",
            title="Ranibizumab in Center-Involved Diabetic Macular Edema",
            abstract=source_text,
            full_text=source_text,
            authors=("Brown DM", "Kaiser PK"),
            journal="Ophthalmology",
            publication_year=2021,
            rights_id="cc_by",
        )
        self.service.ingestion_service.ingest_source_document(s_doc)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_plagiarism_service_detects_exact_and_near_exact(self):
        query_text = (
            "Abstract\n"
            "This study investigates anti-VEGF therapies.\n\n"
            "Introduction\n"
            "Patients with center-involved diabetic macular edema were treated with monthly "
            "intravitreal ranibizumab injections across five clinical trial sites. "
            "Visual acuity significantly improved from baseline over twelve months of treatment.\n\n"
            "Methods\n"
            "Standard surgical and diagnostic procedures were followed in all clinics.\n"
        )

        report = self.service.check_text(query_text, title="Manuscript Submission", options={"sources": []})

        self.assertIsNotNone(report.check_id)
        self.assertGreater(report.suspicious_coverage, 20.0)
        self.assertIn(report.risk_level, ["MODERATE", "HIGH"])
        self.assertGreaterEqual(len(report.matches), 1)

        exact_matches = [m for m in report.matches if m.classification.value == "EXACT_COPY"]
        self.assertGreaterEqual(len(exact_matches), 1)
        self.assertEqual(exact_matches[0].source_document_id, "src:trial_001")
        self.assertGreater(exact_matches[0].evidence.exact_overlap, 0.80)

    def test_agent_v2_integration(self):
        agent = ResearchGuardrailAgent()
        sample_bytes = b"Patients with center-involved diabetic macular edema were treated with monthly intravitreal ranibizumab injections."
        
        report = agent.analyze_document_v2(sample_bytes, "test_manuscript.txt", options={"sources": []})
        self.assertIsNotNone(report.check_id)
        self.assertEqual(report.engine_version, "2.0.0")

    def test_fastapi_v2_endpoints(self):
        client = TestClient(app)

        # 1. Test /api/plagiarism/v2/status
        status_resp = client.get("/api/plagiarism/v2/status")
        self.assertEqual(status_resp.status_code, 200)
        status_data = status_resp.json()
        self.assertEqual(status_data["engine_version"], "2.0.0")
        self.assertIn("providers", status_data)

        # 2. Test /api/plagiarism/v2/check with mocked search to run in-memory
        from unittest.mock import patch
        with patch.object(agent.plagiarism_service.provider_registry, "search_all_sync", return_value=([], [])):
            files = {"file": ("test.txt", b"Sample text for plagiarism check.", "text/plain")}
            check_resp = client.post("/api/plagiarism/v2/check", files=files)
            self.assertEqual(check_resp.status_code, 200)
            check_data = check_resp.json()
            self.assertIn("check_id", check_data)
            self.assertIn("risk_level", check_data)
            self.assertEqual(check_data["engine_version"], "2.0.0")


if __name__ == "__main__":
    unittest.main()
