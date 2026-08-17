import os

# Security & Storage Configuration
# The uploaded content is processed entirely in memory and never persisted.
UPLOAD_TEMP_DIR = None  # None indicates in-memory processing only

# Local AI Models
# Using a lightweight, high-performance local embedding model
EMBEDDING_MODEL_NAME = "all-mpnet-base-v2"
SPACY_MODEL_NAME = "en_core_web_trf"

# Similarity thresholds
SEMANTIC_SIMILARITY_THRESHOLD = 0.75  # Trigger flag if sentence similarity exceeds this
PLAGIARISM_JACCARD_THRESHOLD = 0.60   # Trigger flag if Jaccard similarity of n-grams exceeds this

# PubMed API limits and endpoints
PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
MAX_PUBMED_RESULTS = 10  # Number of life sciences references to fetch and check

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

# Table 1: Altmetric Data Collection Sources Flags
RESEARCH_ATTENTION_ENABLE_TWITTER = os.environ.get("RESEARCH_ATTENTION_ENABLE_TWITTER", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_FACEBOOK = os.environ.get("RESEARCH_ATTENTION_ENABLE_FACEBOOK", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_POLICY_DOCUMENTS = os.environ.get("RESEARCH_ATTENTION_ENABLE_POLICY_DOCUMENTS", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_NEWS = os.environ.get("RESEARCH_ATTENTION_ENABLE_NEWS", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_BLOGS = os.environ.get("RESEARCH_ATTENTION_ENABLE_BLOGS", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_MENDELEY = os.environ.get("RESEARCH_ATTENTION_ENABLE_MENDELEY", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_SCOPUS = os.environ.get("RESEARCH_ATTENTION_ENABLE_SCOPUS", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_PUBLONS = os.environ.get("RESEARCH_ATTENTION_ENABLE_PUBLONS", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_REDDIT = os.environ.get("RESEARCH_ATTENTION_ENABLE_REDDIT", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_STACKOVERFLOW = os.environ.get("RESEARCH_ATTENTION_ENABLE_STACKOVERFLOW", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_F1000 = os.environ.get("RESEARCH_ATTENTION_ENABLE_F1000", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_GOOGLE_PLUS = os.environ.get("RESEARCH_ATTENTION_ENABLE_GOOGLE_PLUS", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_YOUTUBE = os.environ.get("RESEARCH_ATTENTION_ENABLE_YOUTUBE", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_OPEN_SYLLABUS = os.environ.get("RESEARCH_ATTENTION_ENABLE_OPEN_SYLLABUS", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_WEB_OF_SCIENCE = os.environ.get("RESEARCH_ATTENTION_ENABLE_WEB_OF_SCIENCE", "true").lower() == "true"

# Discontinued / Historical Sources Flags (Footnote)
RESEARCH_ATTENTION_ENABLE_SINA_WEIBO = os.environ.get("RESEARCH_ATTENTION_ENABLE_SINA_WEIBO", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_CITEULIKE = os.environ.get("RESEARCH_ATTENTION_ENABLE_CITEULIKE", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_PINTEREST = os.environ.get("RESEARCH_ATTENTION_ENABLE_PINTEREST", "true").lower() == "true"
RESEARCH_ATTENTION_ENABLE_LINKEDIN = os.environ.get("RESEARCH_ATTENTION_ENABLE_LINKEDIN", "true").lower() == "true"

# Optional Connector Credentials (read from environment)
TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN", None)
FACEBOOK_ACCESS_TOKEN = os.environ.get("FACEBOOK_ACCESS_TOKEN", None)
MENDELEY_ACCESS_TOKEN = os.environ.get("MENDELEY_ACCESS_TOKEN", None)
SCOPUS_API_KEY = os.environ.get("SCOPUS_API_KEY", None)
PUBLONS_API_KEY = os.environ.get("PUBLONS_API_KEY", None)
STACKEXCHANGE_API_KEY = os.environ.get("STACKEXCHANGE_API_KEY", None)
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", None)
OPEN_SYLLABUS_API_KEY = os.environ.get("OPEN_SYLLABUS_API_KEY", None)
WOS_API_KEY = os.environ.get("WOS_API_KEY", None)

# Update frequency intervals in seconds (Table 1)
RESEARCH_ATTENTION_REALTIME_REFRESH_INTERVAL = 3600       # Real-time / hourly feed poll
RESEARCH_ATTENTION_DAILY_REFRESH_INTERVAL = 86400         # Daily feed (24h)
RESEARCH_ATTENTION_WEEKLY_REFRESH_INTERVAL = 604800       # Weekly (7d)
RESEARCH_ATTENTION_QUARTERLY_REFRESH_INTERVAL = 7776000   # Quarterly (~90d) for Open Syllabus
RESEARCH_ATTENTION_LEGACY_REFRESH_INTERVAL = 31536000     # Static / Discontinued (yearly check)




