import io
import re
from typing import List, Tuple
from pypdf import PdfReader
from docx import Document
import spacy
from src.config import SPACY_MODEL_NAME

class DocumentExtractor:
    def __init__(self):
        # Load spaCy model for NLP processing
        try:
            self.nlp = spacy.load(SPACY_MODEL_NAME)
        except OSError:
            # Fallback if spaCy model is not downloaded yet
            self.nlp = None

    def extract_text_from_bytes(self, file_bytes: bytes, filename: str) -> str:
        """Extracts text from PDF, DOCX, or TXT files completely in-memory."""
        ext = filename.split(".")[-1].lower()
        if ext == "pdf":
            reader = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        elif ext in ["docx", "doc"]:
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs])
        else:
            # Default to plain text
            return file_bytes.decode("utf-8", errors="ignore")

    def get_sentences(self, text: str) -> List[str]:
        """Splits text into clean sentences using spaCy or fallback regex."""
        # Clean white spaces
        cleaned_text = re.sub(r'\s+', ' ', text).strip()
        if not cleaned_text:
            return []

        if self.nlp:
            # spaCy sentence tokenizer handles abbreviations and medical terms better
            doc = self.nlp(cleaned_text[:1000000])  # limit to 1M characters to avoid spaCy OOM
            return [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 10]
        else:
            # Fallback simple regex sentence splitter if spaCy model is not ready
            sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', cleaned_text)
            return [s.strip() for s in sentences if len(s.strip()) > 10]

    def extract_anonymized_keywords(self, text: str, max_keywords: int = 8) -> List[str]:
        """
        Extracts key noun chunks, noun entities, and medical keywords.
        Ensures strict confidentiality:
        - No full sentences or original text patterns are preserved.
        - Verbs, prepositions, pronouns, and small words are excluded.
        - Limits phrase length to 3 words max to prevent sentence leakage.
        """
        if not text:
            return []

        # If spaCy model is not loaded, fallback to regex word frequency
        if not self.nlp:
            return self.fallback_keyword_extraction(text, max_keywords)

        # Process the first 100,000 characters for keyword extraction (more than enough for theme)
        doc = self.nlp(text[:100000].lower())
        
        candidates = []
        
        # 1. Extract Named Entities (e.g. diseases, chemicals, work domains)
        for ent in doc.ents:
            # Avoid names (PERSON) or dates/quantities for database search
            if ent.label_ not in ["PERSON", "DATE", "TIME", "MONEY", "QUANTITY", "CARDINAL"]:
                clean_ent = ent.text.strip()
                if len(clean_ent) > 3 and len(clean_ent.split()) <= 3:
                    candidates.append(clean_ent)
                    
        # 2. Extract Noun Chunks (concepts)
        for chunk in doc.noun_chunks:
            # Filter out chunks containing pronouns
            if any(token.pos_ == "PRON" for token in chunk):
                continue
            clean_chunk = " ".join([t.text for t in chunk if t.pos_ in ["NOUN", "PROPN", "ADJ"]])
            clean_chunk = clean_chunk.strip()
            if len(clean_chunk) > 3 and len(clean_chunk.split()) <= 3:
                candidates.append(clean_chunk)
                
        # 3. Extract individual relevant nouns/adjectives
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN"] and not token.is_stop and len(token.text) > 3:
                candidates.append(token.text)

        # Count frequencies
        freq = {}
        for item in candidates:
            freq[item] = freq.get(item, 0) + 1
            
        # Sort and take top keywords
        sorted_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        
        # Filtering helper to avoid overlapping keywords (e.g., 'lung cancer' and 'cancer')
        final_keywords = []
        for kw, _ in sorted_keywords:
            # Ensure it doesn't contain digits or special characters
            if re.search(r'[^a-zA-Z\s-]', kw):
                continue
            # Deduplicate subphrases
            if any(kw in existing or existing in kw for existing in final_keywords):
                continue
            final_keywords.append(kw)
            if len(final_keywords) >= max_keywords:
                break
                
        return final_keywords

    def fallback_keyword_extraction(self, text: str, max_keywords: int = 8) -> List[str]:
        """Simple regex-based fallback for extracting keywords based on frequency."""
        words = re.findall(r'\b[a-zA-Z]{4,15}\b', text.lower())
        stopwords = {
            "this", "that", "with", "from", "they", "have", "were", "been", "study", 
            "results", "using", "method", "analysis", "patients", "treatment", "effect"
        }
        filtered_words = [w for w in words if w not in stopwords]
        
        freq = {}
        for w in filtered_words:
            freq[w] = freq.get(w, 0) + 1
            
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:max_keywords]]
