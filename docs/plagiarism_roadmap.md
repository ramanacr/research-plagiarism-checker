# Plagiarism Similarity Engine Accuracy & Scaling Roadmap

This document outlines structural upgrades to enhance semantic accuracy and scalability for the local-first plagiarism detection engine.

---

## 🔬 Plagiarism Detection Accuracy Upgrades

To scale our plagiarism detection engine and eliminate errors in similarity scoring, we outline three key structural upgrades:

### Upgrade 1: Switch to `spacy-transformers` (Contextual NER and Preprocessing) [COMPLETED]
- **Concept**: Switch the spaCy pipeline model loading from static word vectors (`en_core_web_sm`/`en_core_web_lg`) to a transformer-based model like `en_core_web_trf`.
- **Implementation**:
  - Installed `spacy-transformers` dependency.
  - Configured `SPACY_MODEL_NAME = "en_core_web_trf"` inside `src/config.py`.
  - Implemented boundary-aligned document chunking in `get_sentences` (processing text in 50,000-character segments split cleanly at sentence endings) to prevent CPU/GPU memory saturation and OOMs.
  - Capped keyword extraction text slices at 50,000 characters.
- **Why**: The `.similarity()` method now evaluates context dynamically using a BERT-based transformer model. This provides far more precise part-of-speech tag annotations, syntactic boundaries, and noun-chunk segments during Named Entity Recognition (NER) preprocessing.

### Upgrade 2: Integrate `sentence-transformers` (The Semantic Industry Standard)
- **Concept**: Continue our decoupling of text processing from vector space mapping:
  - Use spaCy strictly for sentence segmentation and parsing.
  - Pass cleaned sentences to an SBERT model (such as `all-mpnet-base-v2` or domain-specific equivalents like `SciBERT`).
  - Run a cosine similarity check on the sentence vectors.
- **Why**: Catches semantic plagiarism and clever word substitution effortlessly, matching or exceeding commercial standards.

### Upgrade 3: Text Shingling + MinHash LSH (For Large-Scale Indexing)
- **Concept**: When scanning a document against databases containing thousands of reference works:
  - Tokenize the text into $k$-word overlapping shingles (phrases).
  - Apply MinHash signatures to represent the shingles.
  - Index the signatures in a Local Sensitive Hashing (LSH) database (using the `datasketch` library).
- **Why**: Allows sub-millisecond retrieval of candidate matches from a library of millions of sentences, bypassing $O(N^2)$ pairwise vector comparisons.
