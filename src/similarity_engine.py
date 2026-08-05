import re
import numpy as np
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
from src.config import EMBEDDING_MODEL_NAME, SEMANTIC_SIMILARITY_THRESHOLD, PLAGIARISM_JACCARD_THRESHOLD

class SimilarityEngine:
    def __init__(self):
        # Initialize the SentenceTransformer model locally
        # This will download the model to a local cache directory on first run and run entirely locally thereafter.
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    def compute_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Computes cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))

    def check_semantic_similarity(
        self, 
        doc_sentences: List[str], 
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Compares each sentence in the uploaded document against candidate abstracts/text.
        All vector operations run strictly locally.
        """
        if not doc_sentences or not candidates:
            return []

        # Embed all document sentences
        doc_embeddings = self.model.encode(doc_sentences, convert_to_numpy=True)
        
        matches = []
        
        for candidate in candidates:
            abstract = candidate.get("abstract", "")
            if not abstract:
                continue
                
            # Split candidate abstract into sentences
            cand_sentences = [s.strip() for s in re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', abstract) if len(s.strip()) > 10]
            if not cand_sentences:
                continue
                
            # Embed candidate sentences
            cand_embeddings = self.model.encode(cand_sentences, convert_to_numpy=True)
            
            # Find matching sentence pairs
            for i, doc_emb in enumerate(doc_embeddings):
                doc_sent = doc_sentences[i]
                for j, cand_emb in enumerate(cand_embeddings):
                    cand_sent = cand_sentences[j]
                    
                    score = self.compute_cosine_similarity(doc_emb, cand_emb)
                    if score >= SEMANTIC_SIMILARITY_THRESHOLD:
                        matches.append({
                            "source_sentence": doc_sent,
                            "matching_sentence": cand_sent,
                            "score": round(score, 3),
                            "pmid": candidate.get("pmid"),
                            "title": candidate.get("title"),
                            "doi": candidate.get("doi"),
                            "authors": candidate.get("authors", []),
                            "journal": candidate.get("journal"),
                            "pub_date": candidate.get("pub_date")
                        })
                        
        # Sort matches by score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches

    def check_verbatim_plagiarism(
        self, 
        doc_text: str, 
        candidates: List[Dict[str, Any]], 
        n_gram_size: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Checks for verbatim copy-pasted blocks using n-gram shingling.
        Computes Jaccard Similarity and identifies overlapping n-grams locally.
        """
        if not doc_text or not candidates:
            return []

        doc_shingles = self._get_ngrams(doc_text, n_gram_size)
        if not doc_shingles:
            return []

        plagiarism_reports = []

        for candidate in candidates:
            abstract = candidate.get("abstract", "")
            if not abstract:
                continue

            cand_shingles = self._get_ngrams(abstract, n_gram_size)
            if not cand_shingles:
                continue

            # Calculate Overlap Coefficient of n-grams (relative to candidate abstract size)
            # This prevents dilution of verbatim overlaps when checking large documents
            intersection = doc_shingles.intersection(cand_shingles)
            jaccard_score = len(intersection) / len(cand_shingles) if cand_shingles else 0.0

            # Find matching verbatim phrases
            matching_phrases = self._find_matching_phrases(doc_text, abstract, n_gram_size)

            if jaccard_score >= PLAGIARISM_JACCARD_THRESHOLD or matching_phrases:
                plagiarism_reports.append({
                    "pmid": candidate.get("pmid"),
                    "title": candidate.get("title"),
                    "jaccard_score": round(jaccard_score, 3),
                    "matching_phrases": matching_phrases,
                    "doi": candidate.get("doi")
                })

        plagiarism_reports.sort(key=lambda x: x["jaccard_score"], reverse=True)
        return plagiarism_reports

    def _get_ngrams(self, text: str, n: int) -> set:
        """Tokenizes text and returns a set of n-grams (shingles)."""
        words = re.findall(r'\b\w+\b', text.lower())
        if len(words) < n:
            return set()
        return set(tuple(words[i:i+n]) for i in range(len(words) - n + 1))

    def _find_matching_phrases(self, text1: str, text2: str, n: int) -> List[str]:
        """Finds overlapping verbatim sequences of at least n words."""
        words1 = re.findall(r'\b\w+\b', text1.lower())
        words2 = re.findall(r'\b\w+\b', text2.lower())
        
        shingles2 = set(tuple(words2[i:i+n]) for i in range(len(words2) - n + 1))
        
        matches = []
        i = 0
        while i <= len(words1) - n:
            shingle = tuple(words1[i:i+n])
            if shingle in shingles2:
                # Found a match, let's extend it as long as possible
                match_words = list(shingle)
                i += n
                while i < len(words1):
                    extended_shingle = tuple(words1[i-n+1:i+1])
                    # Check if the extended sequence exists as a contiguous block in text2
                    sequence = " ".join(match_words + [words1[i]])
                    # Check if sequence is in normalized text2
                    normalized_text2 = " ".join(words2)
                    if sequence in normalized_text2:
                        match_words.append(words1[i])
                        i += 1
                    else:
                        break
                matches.append(" ".join(match_words))
            else:
                i += 1
                
        # Deduplicate overlapping matches
        clean_matches = []
        for m in sorted(matches, key=len, reverse=True):
            if not any(m in existing for existing in clean_matches):
                clean_matches.append(m)
                
        return clean_matches
