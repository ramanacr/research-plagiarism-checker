"""
Tests for document domain models, normalization, structure parsing, quotes, citations, and passage segmentation.
"""

import unittest
from src.plagiarism.documents.models import SectionType
from src.plagiarism.documents.normalize import (
    normalize_unicode,
    normalize_whitespace,
    normalize_for_lexical,
    tokenize_words,
    tokenize_with_spans,
    TextOffsetMapper,
)
from src.plagiarism.documents.structure import detect_sections
from src.plagiarism.documents.quotes import extract_quotes
from src.plagiarism.documents.references import extract_inline_citations, extract_references_from_text
from src.plagiarism.documents.segmentation import process_document, split_sentences_fast


SAMPLE_MANUSCRIPT = """
A Clinical Study of Ranibizumab in Diabetic Retinopathy

Abstract
Diabetic retinopathy is a significant cause of vision impairment globally. This randomized study evaluated ranibizumab intravitreal injections versus laser photocoagulation. Significant functional visual improvements were documented in the anti-VEGF group.

1. Introduction
Ocular angiogenesis plays a central role in diabetic retinal complications [1]. Previous investigations by Smith et al. (Smith et al., 2020) demonstrated that vascular endothelial growth factor (VEGF) inhibition restores vascular stability. According to prior consensus, "vascular endothelial growth factor inhibition provides superior visual restoration in clinical settings" [2].

2. Methods
Patients with center-involved diabetic macular edema were enrolled across five clinical centers. Monthly ranibizumab injections (0.5 mg) were administered under sterile conditions. Primary endpoints included best-corrected visual acuity (BCVA) at 12 months.

3. Results
A total of 150 patients completed the 12-month protocol. The ranibizumab cohort demonstrated a mean increase of +12.4 ETDRS letters compared to +4.2 letters in the control arm (p < 0.001).

4. Discussion
These results reinforce the efficacy of early anti-VEGF intervention in proliferative retinopathy. No unexpected ocular adverse events were reported.

References
[1] Brown DM, Kaiser PK, Michels M. Ranibizumab versus verteporfin for neovascular age-related macular degeneration. N Engl J Med. 2006;355(14):1432-1444. doi: 10.1056/NEJMoa062655
[2] Smith J, Doe A, Williams R. Anti-VEGF therapy in retinal disorders. Ophthalmology. 2020;127(4):500-510. doi: 10.1016/j.ophtha.2019.10.015
"""


class TestDocumentProcessing(unittest.TestCase):
    def test_normalization_and_tokenization(self):
        raw = "Ranibizumab\u00A0(0.5\u2009mg)   therapy\n\tproved effective!"
        norm = normalize_unicode(raw)
        self.assertIn("0.5 mg", norm)
        
        lex_norm = normalize_for_lexical(raw)
        self.assertEqual(lex_norm, "ranibizumab 0 5 mg therapy proved effective")

        tokens = tokenize_words(raw)
        self.assertEqual(tokens, ["ranibizumab", "0", "5", "mg", "therapy", "proved", "effective"])

        spans = tokenize_with_spans("Diabetic retinopathy trial")
        self.assertEqual(len(spans), 3)
        self.assertEqual(spans[0], ("diabetic", 0, 8))
        self.assertEqual(spans[1], ("retinopathy", 9, 20))

    def test_offset_mapper(self):
        text = "The quick brown fox jumps over the lazy dog."
        mapper = TextOffsetMapper(text)
        start, end = mapper.find_span("brown fox")
        self.assertEqual(text[start:end], "brown fox")
        self.assertEqual(start, 10)
        self.assertEqual(end, 19)

    def test_section_detection(self):
        sections = detect_sections(SAMPLE_MANUSCRIPT)
        types = [s.section_type for s in sections]
        self.assertIn(SectionType.TITLE, types)
        self.assertIn(SectionType.ABSTRACT, types)
        self.assertIn(SectionType.INTRODUCTION, types)
        self.assertIn(SectionType.METHODS, types)
        self.assertIn(SectionType.RESULTS, types)
        self.assertIn(SectionType.DISCUSSION, types)
        self.assertIn(SectionType.REFERENCES, types)

    def test_inline_citation_extraction(self):
        citations = extract_inline_citations(SAMPLE_MANUSCRIPT)
        self.assertGreaterEqual(len(citations), 2)
        texts = [c.text for c in citations]
        self.assertIn("[1]", texts)
        self.assertIn("[2]", texts)
        self.assertTrue(any("Smith et al., 2020" in c.text for c in citations))

    def test_quote_extraction(self):
        quotes = extract_quotes(SAMPLE_MANUSCRIPT)
        self.assertGreaterEqual(len(quotes), 1)
        self.assertIn("vascular endothelial growth factor inhibition provides superior visual restoration in clinical settings", quotes[0].text)

    def test_reference_item_extraction(self):
        sections = detect_sections(SAMPLE_MANUSCRIPT)
        ref_sec = next(s for s in sections if s.section_type == SectionType.REFERENCES)
        refs = extract_references_from_text(ref_sec.text, base_offset=ref_sec.start_offset)
        self.assertEqual(len(refs), 2)
        
        self.assertEqual(refs[0].year, 2006)
        self.assertEqual(refs[0].doi, "10.1056/NEJMoa062655")
        self.assertIn("Brown DM", refs[0].authors)
        
        self.assertEqual(refs[1].year, 2020)
        self.assertEqual(refs[1].doi, "10.1016/j.ophtha.2019.10.015")
        self.assertIn("Smith J", refs[1].authors)

    def test_full_document_processing_and_passages(self):
        doc = process_document("doc_001", SAMPLE_MANUSCRIPT)
        self.assertEqual(doc.document_id, "doc_001")
        self.assertGreater(doc.word_count, 100)
        self.assertGreater(len(doc.passages), 0)
        self.assertEqual(len(doc.quotes), 1)
        self.assertEqual(len(doc.references), 2)

        # Check passage properties
        intro_passages = [p for p in doc.passages if p.section_type == SectionType.INTRODUCTION]
        self.assertGreaterEqual(len(intro_passages), 1)
        self.assertTrue(any(p.citation_present for p in intro_passages))

        ref_passages = [p for p in doc.passages if p.section_type == SectionType.REFERENCES]
        self.assertTrue(all(p.is_reference for p in ref_passages))


if __name__ == "__main__":
    unittest.main()
