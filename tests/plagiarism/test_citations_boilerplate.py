"""
Tests for citation context analysis and scientific boilerplate suppression.
"""

import unittest
from src.plagiarism.documents.models import Document, Passage, SectionType
from src.plagiarism.scoring.citations import CitationAnalyzer, CitationContext
from src.plagiarism.scoring.boilerplate import BoilerplateDetector, COMMON_SCIENTIFIC_BOILERPLATES


class TestCitationsAndBoilerplate(unittest.TestCase):
    def test_citation_analyzer_doi_match(self):
        doc = Document(
            document_id="doc1",
            title="Trial Paper",
            raw_text="The therapy followed protocols in doi: 10.1016/j.ophtha.2020.01.001.",
            normalized_text="the therapy followed protocols in doi 10 1016 j ophtha 2020 01 001",
            word_count=10,
        )
        p = Passage(
            passage_id="p1",
            document_id="doc1",
            section="Methods",
            section_type=SectionType.METHODS,
            paragraph_index=0,
            text="The therapy followed protocols in doi: 10.1016/j.ophtha.2020.01.001.",
            normalized_text="the therapy followed protocols in doi 10 1016 j ophtha 2020 01 001",
            start_offset=0,
            end_offset=50,
            token_count=8,
        )

        meta = {"doi": "10.1016/j.ophtha.2020.01.001", "authors": ["Alice Smith"]}
        ctx = CitationAnalyzer.evaluate_citation_context(p, doc, meta)
        self.assertTrue(ctx.is_cited)
        self.assertEqual(ctx.citation_type, "DOI_REFERENCE")

    def test_citation_analyzer_author_match(self):
        doc = Document(
            document_id="doc2",
            title="Review",
            raw_text="As shown previously by Smith et al. (2020), anti-VEGF therapy is potent.",
            normalized_text="as shown previously by smith et al 2020 anti vegf therapy is potent",
            word_count=12,
        )
        p = Passage(
            passage_id="p1",
            document_id="doc2",
            section="Intro",
            section_type=SectionType.BODY,
            paragraph_index=0,
            text="As shown previously by Smith et al. (2020), anti-VEGF therapy is potent.",
            normalized_text="as shown previously by smith et al 2020 anti vegf therapy is potent",
            start_offset=0,
            end_offset=60,
            token_count=12,
        )

        meta = {"authors": ["John Smith", "Jane Doe"], "title": "VEGF in Retinopathy"}
        ctx = CitationAnalyzer.evaluate_citation_context(p, doc, meta)
        self.assertTrue(ctx.is_cited)
        self.assertEqual(ctx.matched_author, "John Smith")

    def test_boilerplate_detector(self):
        detector = BoilerplateDetector(corpus_phrase_frequencies={"frequent generic phrase": 10})
        
        # Known boilerplate
        self.assertTrue(detector.is_boilerplate("All experiments were performed in triplicate"))
        self.assertTrue(detector.is_boilerplate("The study protocol was approved by the institutional review board"))
        self.assertEqual(detector.compute_boilerplate_score("all experiments were performed in triplicate"), 1.0)

        # High frequency phrase
        self.assertTrue(detector.is_boilerplate("frequent generic phrase"))

        # Non-boilerplate substantive phrase
        substantive = "Ranibizumab intravitreal injection significantly reduced central foveal thickness in diabetic patients"
        self.assertFalse(detector.is_boilerplate(substantive))
        self.assertEqual(detector.compute_boilerplate_score(substantive), 0.0)


if __name__ == "__main__":
    unittest.main()
