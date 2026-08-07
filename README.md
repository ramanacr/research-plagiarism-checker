# Secure Life Sciences Research Suite & Attention Analytics Engine

A secure, **local-first** life sciences plagiarism engine combined with an automated **Digital Footprint & Attention Analytics** crawler. This portal provides research integrity checks and tracks citation analytics against global registries (PubMed, Europe PMC, Crossref, OpenAlex, Wikimedia, PubPeer) in a unified interface.

> **Competing at Altmetric-level accuracy** — every connector and similarity model is designed for zero-error precision.

---

## 🏛️ Navigation Portal

The suite is served via a responsive pre-page hub containing visual navigation tiles for fast access.

| URL | Interface |
|-----|-----------|
| `http://127.0.0.1:8000/` | **Portal Hub** – unified landing pre-page |
| `http://127.0.0.1:8000/plagiarism` | **Plagiarism Checker** – upload documents for analysis |
| `http://127.0.0.1:8000/attention` | **Attention & Citation Analytics** – D3.js charts, manual crawler triggers |

Both sub-interfaces contain a **Portal Hub** back-link for seamless navigation.

---

## 🛡️ Plagiarism Checker

### Core Confidentiality Guardrails

To ensure uploaded documents **never reach the outside world** during similarity checks, the system enforces strict local sandboxing:

1. **Local-First Processing** – Document parsing, sentence segmentation, and vector embeddings are computed entirely in local memory; no document text leaves the machine.
2. **Anonymized Entity Search** – Technical keywords (drug names, gene/protein identifiers, medical concepts) are extracted via the local spaCy NER transformer pipeline. Only these anonymous concepts are sent to PubMed and Europe PMC APIs to locate matching publications.
3. **Smart Citation Filter** – Legitimate citations containing author names or DOIs listed in the text are classified separately and **excluded from plagiarism risk score calculations**.

### Plagiarism Detection Pipeline

```
Uploaded Document
       │
       ▼
 DocumentExtractor          ← spaCy en_core_web_trf (Upgrade 1)
 (boundary-aligned chunking, 50k-char segments)
       │
  ┌────┴─────────────────────────────┐
  │                                  │
  ▼                                  ▼
get_sentences()           extract_anonymized_keywords()
(Transformer NER)         (50k-char limit, 3-word max)
       │                                  │
       │                    PubMed + EuropePMC API search
       │                    (anonymous keywords only)
       │                                  │
       └──────────────┬───────────────────┘
                      ▼
              Candidate Abstracts
                      │
              ┌───────┴────────────────┐
              │ > 20 candidates?        │
              │ MinHash LSH Filter      │  ← Upgrade 3 (datasketch)
              │ (sub-millisecond prune) │
              └───────────────────────┘
                      │
        ┌─────────────┴──────────────────┐
        ▼                                ▼
 check_semantic_similarity()   check_verbatim_plagiarism()
 (SBERT all-mpnet-base-v2)    (n-gram shingling + Jaccard)
 (Blank spaCy sentencizer      ← Upgrade 2
  for candidate splitting)
        │                                │
        └─────────────┬──────────────────┘
                      ▼
              Similarity Report
```

### AI Models Used

| Model | Role | Notes |
|-------|------|-------|
| `en_core_web_trf` | Document NER & sentence segmentation | spaCy transformer pipeline (BERT-backed) |
| `all-mpnet-base-v2` | Semantic sentence embeddings | 768-dim SBERT — industry best-in-class |
| `spacy.blank("en") + sentencizer` | Candidate abstract splitting | Lightweight, zero GPU overhead |

### Plagiarism Upgrades Roadmap Status

| Upgrade | Status |
|---------|--------|
| **Upgrade 1** – Switch to `spacy-transformers` / `en_core_web_trf` | ✅ Completed |
| **Upgrade 2** – SBERT `all-mpnet-base-v2` + blank spaCy sentencizer | ✅ Completed |
| **Upgrade 3** – MinHash LSH indexing via `datasketch` | ✅ Completed |

---

## 📊 Research Attention Analytics Module

Tracks citations and digital mentions of resolved publications across global digital channels.

```mermaid
graph TD
    User([User Client]) -->|Queries PMID/DOI| API[FastAPI Server]
    API -->|1. Resolve Metadata| Resolver[Work Resolver]

    subgraph Identity Resolution Chain
        Resolver -->|PubMed| PM[PubMed E-Utilities]
        Resolver -->|Europe PMC| EPMC[Europe PMC Search]
        Resolver -->|Crossref| CR[Crossref Works]
        Resolver -->|OpenAlex| OA[OpenAlex Works API]
    end

    Resolver -->|2. Database Caching| DB[(PostgreSQL Cache)]

    API -->|3. Schedule Job| DB
    Worker[Background Worker Daemon] -->|4. Pull Queued Job| DB

    subgraph Attention Connectors
        Worker -->|Crawl| Wiki[Wikimedia / Wikipedia]
        Worker -->|Crawl| CEv[Crossref Event Data]
        Worker -->|Crawl| OAlx[OpenAlex Citations]
        Worker -->|Crawl| PP[PubPeer Comments]
    end

    Worker -->|5. Save Deduplicated Evidence| DB
    User -->|6. View Analytics| D3[D3.js Donut & Timeline Charts]
```

### Connector Coverage

| Connector | Source | Type |
|-----------|--------|------|
| **Wikimedia / Wikipedia** | Mentions in article text | Digital evidence |
| **Crossref Event Data** | Science blog & forum mentions | Digital evidence |
| **OpenAlex** | Life sciences citation graph | Citations |
| **PubPeer** | Post-publication peer commentary & retraction flags | Peer review |

#### Wikimedia Accuracy Hardening
Wikipedia searches use **contextual prefix matching** (`"pmid {id}"`, `"pmcid {id}"`, `"pmc {id}"`) to prevent false matches on plain integer IDs (zip codes, asteroid numbers, etc.). A **batch wikitext content verification** step (`_verify_pages`) further discards any page that contains the ID but lacks contextual citation terms (`pmid`, `pubmed`, `ncbi`, etc.), eliminating false-positive evidence entries.

### Identity Resolution & Deduplication
- Resolves via PubMed, Europe PMC, Crossref, OpenAlex sequentially.
- Normalizes all identifier values (`pmid`, `doi`, `pmcid`, `openalex_id`) with full **conflict detection** (yields HTTP 409 if resolved identifiers map to different pre-existing records).
- **Page-level deduplication**: multiple mentions on the same Wikipedia page are merged into a single evidence record.
- **Confidence tiers**: `exact_identifier` and `canonical_url` matches are `active=True`; `probable` matches are flagged `active=False` for human audit.

### Connector Retry Resilience
All connectors include a **3-attempt retry loop** with configurable connection and read timeouts to handle transient third-party server failures gracefully (tested against Crossref Event Data timeouts).

---

## 💻 Full Technology Stack

### Backend (Python 3.11)

| Library | Version | Purpose |
|---------|---------|---------|
| `fastapi` | ≥ 0.95 | HTTP API framework |
| `uvicorn` | ≥ 0.20 | ASGI web server |
| `sqlalchemy` | ≥ 2.0 | ORM / database session management |
| `alembic` | ≥ 1.11 | Schema migration management |
| `psycopg[binary]` | ≥ 3.1 | Modern PostgreSQL adapter (v3) |
| `httpx` | ≥ 0.24 | Async-capable HTTP client for connector crawlers |
| `requests` | ≥ 2.28 | Synchronous HTTP calls |
| `pydantic` | ≥ 2.0 | Data validation and API schema |
| `python-multipart` | ≥ 0.0.5 | File upload handling |
| `pypdf` | ≥ 3.0 | PDF text extraction |
| `python-docx` | ≥ 0.8.11 | DOCX text extraction |
| `spacy` | ≥ 3.5 | NLP pipeline framework |
| `spacy-transformers` | ≥ 1.2 | Transformer backend for spaCy (`en_core_web_trf`) |
| `sentence-transformers` | ≥ 2.2 | SBERT embedding model (`all-mpnet-base-v2`) |
| `datasketch` | ≥ 1.5 | MinHash LSH indexing for large-scale candidate pruning |
| `pytest` | ≥ 7.0 | Automated test suite (37 tests) |

### AI / ML Models

| Model | Library | Dimensions | Role |
|-------|---------|------------|------|
| `en_core_web_trf` | spaCy + spacy-transformers | — | Document NER, POS tagging, sentence chunking |
| `all-mpnet-base-v2` | sentence-transformers | 768 | Semantic similarity embeddings |
| `spacy.blank("en") + sentencizer` | spaCy | — | Fast candidate abstract sentence splitting |

### Frontend

| Technology | Purpose |
|------------|---------|
| **D3.js v7** | Interactive donut charts & monthly bar timeline visualizations |
| **Glassmorphic CSS** | Premium dark-theme layouts with smooth hover transitions |
| **Vanilla JS** | Polling, alerts, and connector trigger interactions |

---

## 🚀 Installation & Database Setup

### 1. Create Virtual Environment & Install Packages

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Download spaCy Transformer Model

```bash
python -m spacy download en_core_web_trf
```

> The `all-mpnet-base-v2` SBERT model is downloaded automatically on first run and cached locally via Hugging Face Hub.

### 3. Configure PostgreSQL Database

Start a local PostgreSQL container:

```bash
docker run -d \
  --name research-attention-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=research_attention \
  -p 5432:5432 \
  postgres:15
```

### 4. Run Alembic Database Migrations

```bash
.venv\Scripts\alembic upgrade head
```

---

## 🛠️ Operational Commands

### Start the FastAPI Web Server

```bash
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```

Open **`http://127.0.0.1:8000`** to access the Portal Hub.

### Start the Background Attention Crawler Worker

```bash
python -m src.attention.worker
```

### Run the Automated Test Suite

```bash
python -m pytest tests/ -v
```

> **37 tests** across plagiarism, attention, connectors, resolver, worker, and API isolation suites.

---

## 🌐 Research Attention API Reference

### Publication Lookup

Retrieves cached details, identifiers, and sync states. If uncached, resolves and triggers an ingest job automatically.

```
GET /api/v1/research-attention/works/pmid/{pmid}
GET /api/v1/research-attention/works/doi/{doi:path}
GET /api/v1/research-attention/works/{work_id}
```

### Visual Analytics Data

Returns grouped counts for D3 charts and monthly timeline buckets.

```
GET /api/v1/research-attention/works/{work_id}/analytics
```

### Force Ingestion Sync

Queues a manual crawler run. Requires API key verification.

```
POST /api/v1/research-attention/works/{work_id}/refresh
X-Research-Attention-Key: default-dev-key-change-me
```

---

## 📂 Project Structure

```
.
├── src/
│   ├── api.py                        # FastAPI routes & app entry point
│   ├── agent.py                      # Plagiarism orchestration agent
│   ├── extractor.py                  # Document parsing & spaCy NER chunking
│   ├── similarity_engine.py          # SBERT cosine + Jaccard + MinHash LSH
│   ├── pubmed_client.py              # PubMed E-Utilities integration
│   ├── europe_pmc_client.py          # Europe PMC search integration
│   ├── config.py                     # Central configuration (models, thresholds)
│   ├── dashboard.html                # Attention analytics UI (D3.js)
│   └── attention/
│       ├── worker.py                 # Background crawler daemon
│       ├── resolver.py               # Multi-source identity resolution
│       ├── models.py                 # SQLAlchemy ORM models
│       └── connectors/
│           ├── registry.py           # Connector registry & toggle map
│           ├── wikimedia.py          # Wikipedia mention crawler
│           ├── crossref_event.py     # Crossref Event Data crawler
│           ├── openalex.py           # OpenAlex citation crawler
│           └── pubpeer.py            # PubPeer commentary crawler
├── tests/
│   ├── test_agent.py                 # Plagiarism + LSH unit tests
│   └── attention/                    # Attention module test suite
├── docs/
│   ├── plagiarism_roadmap.md         # Plagiarism accuracy upgrade roadmap
│   └── attention/roadmap.md          # Attention analytics roadmap
├── alembic/                          # DB migration scripts
└── requirements.txt
```
