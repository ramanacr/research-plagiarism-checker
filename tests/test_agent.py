import unittest
from unittest.mock import patch, MagicMock
from src.extractor import DocumentExtractor
from src.pubmed_client import PubMedClient
from src.similarity_engine import SimilarityEngine
from src.agent import ResearchGuardrailAgent

class TestConfidentialPlagiarismChecker(unittest.TestCase):
    def setUp(self):
        self.extractor = DocumentExtractor()
        self.similarity_engine = SimilarityEngine()
        self.pubmed_client = PubMedClient()
        self.agent = ResearchGuardrailAgent()

    def test_document_extractor_plain_text(self):
        sample_bytes = b"Hello this is a simple text check. Machine learning in medicine."
        extracted = self.extractor.extract_text_from_bytes(sample_bytes, "test.txt")
        self.assertIn("Machine learning", extracted)

    def test_keyword_anonymization_guardrails(self):
        sample_text = (
            "Patients with diabetic retinopathy were treated with ranibizumab. "
            "The clinical trial showed significant improvements in visual acuity."
        )
        keywords = self.extractor.extract_anonymized_keywords(sample_text)
        
        # Guardrail checks:
        for kw in keywords:
            # No keyword should be longer than 3 words (to prevent sentence leakage)
            self.assertTrue(len(kw.split()) <= 3, f"Keyword phrase too long: {kw}")
            # Keywords should not contain simple pronouns or common stop words
            self.assertNotIn(kw.lower(), ["patients with", "the", "with", "were"])

    def test_similarity_engine_cosine(self):
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        vec3 = [0.0, 1.0, 0.0]
        
        sim1 = self.similarity_engine.compute_cosine_similarity(vec1, vec2)
        sim2 = self.similarity_engine.compute_cosine_similarity(vec1, vec3)
        
        self.assertAlmostEqual(sim1, 1.0)
        self.assertAlmostEqual(sim2, 0.0)

    def test_verbatim_plagiarism_detection(self):
        doc = "This is a highly confidential document about cancer immunotherapy and genomics."
        candidates = [
            {
                "pmid": "12345",
                "title": "Genomics study",
                "abstract": "This is a highly confidential document about cancer immunotherapy and genomics."
            }
        ]
        res = self.similarity_engine.check_verbatim_plagiarism(doc, candidates)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["pmid"], "12345")
        self.assertGreaterEqual(res[0]["jaccard_score"], 0.8)

    @patch('requests.get')
    def test_pubmed_client_search(self, mock_get):
        # Mock the JSON response for esearch
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "esearchresult": {
                "idlist": ["11111", "22222"]
            }
        }
        mock_get.return_value = mock_response

        pmids = self.pubmed_client.search_articles(["cancer", "immunotherapy"])
        self.assertEqual(pmids, ["11111", "22222"])
        
        # Verify query structure: ensures keywords are quoted and separated by AND
        mock_get.assert_called_with(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={
                "db": "pubmed",
                "term": '"cancer" AND "immunotherapy"',
                "retmode": "json",
                "retmax": 10
            },
            headers={"User-Agent": "ConfidentialPlagiarismChecker/1.0"},
            timeout=10
        )

    @patch('src.agent.EuropePMCClient')
    @patch('src.agent.PubMedClient')
    def test_full_agent_flow(self, mock_pubmed_class, mock_epmc_class):
        # Mock pubmed client
        mock_pubmed = mock_pubmed_class.return_value
        mock_pubmed.search_articles.return_value = ["99999"]
        mock_pubmed.fetch_article_details.return_value = [
            {
                "pmid": "99999",
                "title": "A Study of Ranibizumab in Diabetic Retinopathy",
                "abstract": "This study analyzes visual acuity changes following ranibizumab therapy for retinopathy.",
                "authors": ["John Doe"],
                "journal": "Retina Journal",
                "pub_date": "2023",
                "doi": "10.1000/xyz123"
            }
        ]

        # Mock Europe PMC client
        mock_epmc = mock_epmc_class.return_value
        mock_epmc.search_and_fetch.return_value = [
            {
                "pmid": "88888",
                "pmcid": "PMC88888",
                "title": "Europe PMC Study of Ranibizumab",
                "abstract": "Evaluation of patient visual outcomes and ranibizumab.",
                "authors": ["Jane Smith"],
                "journal": "Euro Retina",
                "pub_date": "2024",
                "doi": "10.1001/abc456"
            }
        ]

        agent = ResearchGuardrailAgent()
        
        doc_bytes = b"Diabetic retinopathy patient visual acuity improvements with ranibizumab."
        report = agent.analyze_document(doc_bytes, "doc.txt")
        
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["metadata"]["filename"], "doc.txt")
        self.assertIn("ranibizumab", report["guardrails"]["anonymized_search_keywords"])
        self.assertEqual(report["guardrails"]["external_pmids_queried"], ["99999"])
        self.assertIn("confidentiality_status", report["guardrails"])

    @patch('requests.get')
    def test_europe_pmc_client_search(self, mock_get):
        from src.europe_pmc_client import EuropePMCClient
        client = EuropePMCClient()

        # Mock JSON response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resultList": {
                "result": [
                    {
                        "pmid": "77777",
                        "title": "Mock Title",
                        "abstractText": "Mock Abstract",
                        "authorString": "A. Author, B. Author",
                        "journalTitle": "Mock Journal",
                        "pubYear": "2022",
                        "doi": "10.1234/test"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        res = client.search_and_fetch(["ranibizumab", "retinopathy"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["pmid"], "77777")
        self.assertEqual(res[0]["title"], "Mock Title")
        self.assertEqual(res[0]["authors"], ["A. Author", "B. Author"])

    def test_lsh_candidate_filtering(self):
        doc = "This is a highly confidential document about cancer immunotherapy and genomics."
        candidates = [
            {
                "pmid": "1",
                "title": "Genomics study 1",
                "abstract": "This is a highly confidential document about cancer immunotherapy and genomics."
            },
            {
                "pmid": "2",
                "title": "Unrelated study",
                "abstract": "Water purification using gravity filtering systems in remote locations."
            }
        ]
        
        filtered = self.similarity_engine.filter_candidates_via_lsh(doc, candidates, threshold=0.1)
        pmids = [c["pmid"] for c in filtered]
        self.assertIn("1", pmids)
        self.assertNotIn("2", pmids)

if __name__ == '__main__':
    unittest.main()
