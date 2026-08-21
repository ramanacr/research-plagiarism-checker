"""
Tests for rights management layer, fail-closed enforcement, and additional scholarly providers.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.plagiarism.rights.models import RightsRecord, RightsDecision
from src.plagiarism.rights.resolver import RightsResolver
from src.plagiarism.config.settings import RightsSettings

from src.plagiarism.providers.crossref import CrossrefProvider
from src.plagiarism.providers.openalex import OpenAlexProvider
from src.plagiarism.providers.arxiv import ArXivProvider
from src.plagiarism.providers.unpaywall import UnpaywallProvider
from src.plagiarism.providers.pmc_oa import PMCOAProvider
from src.plagiarism.providers.registry import create_default_registry


SAMPLE_ARXIV_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345v1</id>
    <title>Deep Neural Networks in Ophthalmology</title>
    <summary>We present a deep learning architecture for retinal fundus analysis.</summary>
    <author>
      <name>Alice Wang</name>
    </author>
    <published>2023-01-15T00:00:00Z</published>
    <arxiv:doi>10.48550/arXiv.2301.12345</arxiv:doi>
  </entry>
</feed>
"""

SAMPLE_CROSSREF_ITEMS = [
    {
        "DOI": "10.1000/182",
        "title": ["Clinical Study of Anti-VEGF Agents"],
        "author": [{"given": "David", "family": "Miller"}],
        "abstract": "<jats:p>Vascular endothelial growth factor plays a key role.</jats:p>",
        "published-print": {"date-parts": [[2021, 5]]},
        "container-title": ["Journal of Ophthalmology"],
    }
]

SAMPLE_OPENALEX_WORKS = [
    {
        "id": "https://openalex.org/W123456",
        "title": "Automated Plagiarism Detection in Scientific Manuscripts",
        "doi": "https://doi.org/10.1016/j.joi.2022.101234",
        "publication_year": 2022,
        "abstract_inverted_index": {
            "Automated": [0],
            "plagiarism": [1],
            "detection": [2],
            "is": [3],
            "essential": [4],
            "for": [5],
            "science": [6],
        },
        "authorships": [{"author": {"display_name": "Elena Rostova"}}],
        "open_access": {"is_oa": True},
    }
]


class TestRightsAndExtraProviders(unittest.TestCase):
    def test_rights_resolver_fail_closed(self):
        resolver = RightsResolver(RightsSettings(fail_closed=True))

        # 1. CC-BY allows indexing and raw storage
        d_cc_by = resolver.evaluate_rights("cc_by")
        self.assertTrue(d_cc_by.allowed_to_index)
        self.assertTrue(d_cc_by.allowed_to_store_raw)

        # 2. All rights reserved denies indexing and raw storage
        d_arr = resolver.evaluate_rights("all_rights_reserved")
        self.assertFalse(d_arr.allowed_to_index)
        self.assertFalse(d_arr.allowed_to_store_raw)

        # 3. Known scholarly provider with unknown license defaults to abstract fair use
        d_pubmed = resolver.evaluate_rights(None, provider="pubmed")
        self.assertTrue(d_pubmed.allowed_to_index)
        self.assertFalse(d_pubmed.allowed_to_store_raw)
        self.assertTrue(d_pubmed.allowed_to_display_snippet)

        # 4. Unknown provider with unknown license is completely denied under fail-closed
        d_unknown = resolver.evaluate_rights(None, provider="untrusted_third_party")
        self.assertFalse(d_unknown.allowed_to_index)
        self.assertFalse(d_unknown.allowed_to_store_raw)

    def test_crossref_parsing(self):
        provider = CrossrefProvider()
        records = provider.parse_items(SAMPLE_CROSSREF_ITEMS)
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r.doi, "10.1000/182")
        self.assertEqual(r.title, "Clinical Study of Anti-VEGF Agents")
        self.assertEqual(r.authors, ("David Miller",))
        self.assertEqual(r.publication_year, 2021)
        self.assertEqual(r.abstract, "Vascular endothelial growth factor plays a key role.")

    def test_openalex_abstract_reconstruction(self):
        provider = OpenAlexProvider()
        records = provider.parse_works(SAMPLE_OPENALEX_WORKS)
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r.title, "Automated Plagiarism Detection in Scientific Manuscripts")
        self.assertEqual(r.doi, "10.1016/j.joi.2022.101234")
        self.assertEqual(r.abstract, "Automated plagiarism detection is essential for science")
        self.assertEqual(r.authors, ("Elena Rostova",))
        self.assertTrue(r.extra_metadata.get("is_oa"))

    def test_arxiv_atom_parsing(self):
        provider = ArXivProvider()
        records = provider.parse_atom_feed(SAMPLE_ARXIV_XML)
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r.source_id, "2301.12345v1")
        self.assertEqual(r.title, "Deep Neural Networks in Ophthalmology")
        self.assertEqual(r.authors, ("Alice Wang",))
        self.assertEqual(r.publication_year, 2023)
        self.assertIn("retinal fundus analysis", r.abstract)

    def test_default_registry_has_all_providers(self):
        reg = create_default_registry()
        providers = reg.list_providers()
        expected = ["pubmed", "europe_pmc", "pmc_oa", "crossref", "openalex", "arxiv", "unpaywall"]
        for p in expected:
            self.assertIn(p, providers)


if __name__ == "__main__":
    unittest.main()
