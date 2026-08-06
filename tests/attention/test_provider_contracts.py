import unittest
from src.attention.providers.pubmed import PubMedProvider
from src.attention.providers.europe_pmc import EuropePMCProvider
from src.attention.providers.crossref import CrossrefProvider
from src.attention.providers.openalex import OpenAlexProvider
from src.attention.providers.base import IdentityProvider

class TestProviderContracts(unittest.TestCase):
    def test_provider_subclass_contracts(self):
        providers = [
            PubMedProvider(),
            EuropePMCProvider(),
            CrossrefProvider(),
            OpenAlexProvider()
        ]
        for provider in providers:
            self.assertTrue(isinstance(provider, IdentityProvider))
            self.assertTrue(hasattr(provider, "resolve_pmid"))
            self.assertTrue(hasattr(provider, "resolve_doi"))

if __name__ == "__main__":
    unittest.main()
