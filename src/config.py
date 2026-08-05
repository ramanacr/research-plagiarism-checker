import os

# Security & Storage Configuration
# The uploaded content is processed entirely in memory and never persisted.
UPLOAD_TEMP_DIR = None  # None indicates in-memory processing only

# Local AI Models
# Using a lightweight, high-performance local embedding model
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
SPACY_MODEL_NAME = "en_core_web_sm"

# Similarity thresholds
SEMANTIC_SIMILARITY_THRESHOLD = 0.75  # Trigger flag if sentence similarity exceeds this
PLAGIARISM_JACCARD_THRESHOLD = 0.60   # Trigger flag if Jaccard similarity of n-grams exceeds this

# PubMed API limits and endpoints
PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
MAX_PUBMED_RESULTS = 10  # Number of academic references to fetch and check

# Server settings
API_HOST = "127.0.0.1"
API_PORT = 8000
