import os

# Security & Storage Configuration
# The uploaded content is processed entirely in memory and never persisted.
UPLOAD_TEMP_DIR = None  # None indicates in-memory processing only

# Local AI Models
# Using a lightweight, high-performance local embedding model
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
SPACY_MODEL_NAME = "en_core_web_trf"

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

# Research Attention Module Configuration
RESEARCH_ATTENTION_ENABLED = os.environ.get("RESEARCH_ATTENTION_ENABLED", "true").lower() == "true"
# We default to postgresql connection URL (using psycopg v3 driver), but let it be overridden by environment variables
RESEARCH_ATTENTION_DATABASE_URL = os.environ.get("RESEARCH_ATTENTION_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/research_attention")
RESEARCH_ATTENTION_INTERNAL_API_KEY = os.environ.get("RESEARCH_ATTENTION_INTERNAL_API_KEY", "default-dev-key-change-me")

# Connectors Activation Flags
RESEARCH_ATTENTION_ENABLE_WIKIMEDIA = os.environ.get("RESEARCH_ATTENTION_ENABLE_WIKIMEDIA", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_OPENALEX = os.environ.get("RESEARCH_ATTENTION_ENABLE_OPENALEX", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_CROSSREF_EVENT = os.environ.get("RESEARCH_ATTENTION_ENABLE_CROSSREF_EVENT", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_PUBPEER = os.environ.get("RESEARCH_ATTENTION_ENABLE_PUBPEER", "true").lower() == "true"

# Default refresh intervals in seconds (e.g. daily, weekly)
RESEARCH_ATTENTION_DAILY_REFRESH_INTERVAL = 86400
RESEARCH_ATTENTION_WEEKLY_REFRESH_INTERVAL = 604800

