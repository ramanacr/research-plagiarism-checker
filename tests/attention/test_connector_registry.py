import unittest
from src.attention.connectors.registry import ConnectorRegistry
from src.config import RESEARCH_ATTENTION_ENABLE_WIKIMEDIA

class TestConnectorRegistry(unittest.TestCase):
    def test_registry_lookups(self):
        registry = ConnectorRegistry()
        sources = registry.get_all_sources()
        self.assertIn("wikipedia", sources)
        
        # Verify fetching connector
        conn = registry.get_connector("wikipedia")
        self.assertIsNotNone(conn)
        
        # Verify disabled lookup
        self.assertIsNone(registry.get_connector("unknown"))
        
        # Verify is_enabled state matches config setting
        self.assertEqual(registry.is_enabled("wikipedia"), RESEARCH_ATTENTION_ENABLE_WIKIMEDIA)

if __name__ == "__main__":
    unittest.main()
