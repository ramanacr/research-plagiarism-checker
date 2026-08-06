import unittest
from fastapi.testclient import TestClient
from src.api import app

class TestOpenAPISpec(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_openapi_schema_contains_paths(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        paths = data.get("paths", {})
        self.assertIn("/api/v1/research-attention/works/pmid/{pmid}", paths)
        self.assertIn("/api/v1/research-attention/works/doi/{doi}", paths)
        self.assertIn("/api/v1/research-attention/works/{work_id}", paths)
        self.assertIn("/api/v1/research-attention/works/{work_id}/refresh", paths)
        self.assertIn("/api/v1/research-attention/works/{work_id}/analytics", paths)

if __name__ == "__main__":
    unittest.main()
