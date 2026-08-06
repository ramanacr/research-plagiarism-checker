import unittest
from src.attention.providers.base import normalize_doi, normalize_pmid

class TestIdentifierNormalization(unittest.TestCase):
    def test_normalize_doi_cases(self):
        # Valid DOIs with different formats
        self.assertEqual(normalize_doi("10.1000/ABC.1"), "10.1000/abc.1")
        self.assertEqual(normalize_doi("doi:10.1000/ABC.1"), "10.1000/abc.1")
        self.assertEqual(normalize_doi("https://doi.org/10.1000/ABC.1"), "10.1000/abc.1")
        self.assertEqual(normalize_doi("http://dx.doi.org/10.1000/ABC.1"), "10.1000/abc.1")
        
        # Trailing punctuation
        self.assertEqual(normalize_doi("10.1000/abc.1."), "10.1000/abc.1")
        self.assertEqual(normalize_doi("10.1000/abc.1,"), "10.1000/abc.1")
        
        # Whitespace
        self.assertEqual(normalize_doi("   10.1000/abc.1   "), "10.1000/abc.1")
        
        # Invalid DOIs
        self.assertIsNone(normalize_doi("10.1000"))
        self.assertIsNone(normalize_doi("http://example.com/10.1000/abc.1"))
        self.assertIsNone(normalize_doi("not_a_doi"))

    def test_normalize_pmid_cases(self):
        self.assertEqual(normalize_pmid("12345678"), "12345678")
        self.assertEqual(normalize_pmid("pmid:12345678"), "12345678")
        self.assertEqual(normalize_pmid("  12345678  "), "12345678")
        self.assertEqual(normalize_pmid("123a456"), "123456")
        self.assertIsNone(normalize_pmid(""))
        self.assertIsNone(normalize_pmid("abc"))

if __name__ == "__main__":
    unittest.main()
