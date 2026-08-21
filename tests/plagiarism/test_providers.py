"""
Tests for scholarly content provider abstraction, PubMed and Europe PMC providers, and registry.
"""

import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

from src.plagiarism.providers.base import (
    SourceRecord,
    SourceDocument,
    ProviderCapabilities,
    ProviderHealth,
)
from src.plagiarism.providers.pubmed import PubMedProvider
from src.plagiarism.providers.europe_pmc import EuropePMCProvider
from src.plagiarism.providers.registry import ProviderRegistry, create_default_registry


SAMPLE_PUBMED_XML = b"""<?xml version="1.0"?>
<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2019//EN" "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_190101.dtd">
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>Ranibizumab Treatment for Diabetic Retinopathy</ArticleTitle>
        <Journal>
          <Title>Ophthalmology Clinical Journal</Title>
          <JournalIssue>
            <PubDate>
              <Year>2023</Year>
              <Month>Apr</Month>
            </PubDate>
          </JournalIssue>
        </Journal>
        <Abstract>
          <AbstractText Label="BACKGROUND">Diabetic retinopathy is a major cause of blindness.</AbstractText>
          <AbstractText Label="METHODS">Patients received monthly ranibizumab injections.</AbstractText>
          <AbstractText Label="RESULTS">Significant improvements in visual acuity were observed.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author>
            <LastName>Smith</LastName>
            <ForeName>John</ForeName>
          </Author>
          <Author>
            <LastName>Doe</LastName>
            <ForeName>Jane</ForeName>
          </Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">12345678</ArticleId>
        <ArticleId IdType="doi">10.1016/j.ophtha.2023.01.001</ArticleId>
        <ArticleId IdType="pmc">PMC1234567</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""

SAMPLE_EPMC_JSON_RESULTS = [
    {
        "pmid": "12345678",
        "pmcid": "PMC1234567",
        "doi": "10.1016/j.ophtha.2023.01.001",
        "title": "Ranibizumab Treatment for Diabetic Retinopathy",
        "abstractText": "Diabetic retinopathy is a major cause of blindness. Patients received ranibizumab.",
        "authorString": "Smith J, Doe J",
        "journalTitle": "Ophthalmology Clinical Journal",
        "pubYear": "2023",
        "isOpenAccess": "Y",
        "inEPMC": "Y",
    },
    {
        "pmid": "87654321",
        "doi": "10.1038/nature12345",
        "title": "Novel VEGF Inhibitors in Ocular Diseases",
        "abstractText": "A review of therapeutic antibodies.",
        "authorList": {"author": [{"fullName": "Alice Wonder"}]},
        "journalTitle": "Nature Reviews Ophthalmology",
        "pubYear": "2022",
        "isOpenAccess": "N",
        "inEPMC": "Y",
    },
]


class TestScholarlyProviders(unittest.TestCase):
    def test_source_record_model(self):
        rec = SourceRecord(
            provider="pubmed",
            source_id="123",
            doi="10.1000/182",
            pmid="123",
            title="Test Title",
            abstract="Test Abstract",
            authors=("Alice", "Bob"),
            publication_year=2023,
            journal="Test Journal",
        )
        self.assertEqual(rec.provider, "pubmed")
        self.assertEqual(rec.source_id, "123")
        self.assertEqual(len(rec.authors), 2)
        d = rec.to_dict()
        self.assertEqual(d["title"], "Test Title")
        self.assertEqual(d["authors"], ["Alice", "Bob"])

    def test_pubmed_xml_parsing(self):
        provider = PubMedProvider()
        records = provider.parse_pubmed_xml(SAMPLE_PUBMED_XML)
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r.pmid, "12345678")
        self.assertEqual(r.doi, "10.1016/j.ophtha.2023.01.001")
        self.assertEqual(r.pmcid, "PMC1234567")
        self.assertEqual(r.title, "Ranibizumab Treatment for Diabetic Retinopathy")
        self.assertEqual(r.publication_year, 2023)
        self.assertIn("John Smith", r.authors)
        self.assertIn("Jane Doe", r.authors)
        self.assertIn("BACKGROUND: Diabetic retinopathy", r.abstract)
        self.assertIn("RESULTS: Significant improvements", r.abstract)

    def test_europe_pmc_json_parsing(self):
        provider = EuropePMCProvider()
        records = provider.parse_json_results(SAMPLE_EPMC_JSON_RESULTS)
        self.assertEqual(len(records), 2)
        r1, r2 = records[0], records[1]
        self.assertEqual(r1.pmid, "12345678")
        self.assertEqual(r1.authors, ("Smith J", "Doe J"))
        self.assertEqual(r2.pmid, "87654321")
        self.assertEqual(r2.authors, ("Alice Wonder",))
        self.assertTrue(r1.extra_metadata.get("isOpenAccess"))

    def test_registry_registration_and_get(self):
        registry = create_default_registry()
        self.assertIn("pubmed", registry.list_providers())
        self.assertIn("europe_pmc", registry.list_providers())
        self.assertIsNotNone(registry.get("pubmed"))
        self.assertIsNotNone(registry.get("europe_pmc"))

    def test_registry_deduplication(self):
        records = [
            SourceRecord(
                provider="pubmed",
                source_id="123",
                pmid="123",
                doi="10.1000/1",
                title="Diabetic Retinopathy Treatment",
            ),
            SourceRecord(
                provider="europe_pmc",
                source_id="123",
                pmid="123",
                doi="10.1000/1",
                title="Diabetic Retinopathy Treatment",
            ),
            SourceRecord(
                provider="europe_pmc",
                source_id="456",
                pmid="456",
                doi="10.1000/2",
                title="Different Study",
            ),
        ]
        deduped = ProviderRegistry.deduplicate_records(records)
        self.assertEqual(len(deduped), 2)
        self.assertEqual(deduped[0].pmid, "123")
        self.assertEqual(deduped[1].pmid, "456")

    def test_registry_search_all_failure_isolation(self):
        async def run_test():
            registry = ProviderRegistry()
            good_provider = PubMedProvider()
            failing_provider = EuropePMCProvider()

            # Mock search on good provider
            good_provider.search = AsyncMock(
                return_value=[
                    SourceRecord(
                        provider="pubmed",
                        source_id="101",
                        pmid="101",
                        title="Study One",
                    )
                ]
            )
            # Mock search error on failing provider
            failing_provider.search = AsyncMock(side_effect=Exception("Europe PMC network timeout"))

            registry.register(good_provider)
            registry.register(failing_provider)

            records, warnings = await registry.search_all("retinopathy")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].pmid, "101")
            self.assertEqual(len(warnings), 1)
            self.assertIn("Europe PMC network timeout", warnings[0])

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
