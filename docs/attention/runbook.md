# Research Attention Analytics - Operations Runbook

This document details operational instructions, database migrations, connection details, backfill procedures, and troubleshooting strategies for the Research Attention Analytics module.

---

## 1. System Architecture & Components

The Research Attention module uses the following components:
1. **FastAPI Application Router**: Handles incoming API requests for resolvers (`/api/v1/research-attention/works/pmid/...`) and renders dashboards.
2. **Background Worker**: Polls and locks queued sync jobs to run API crawls against Wikimedia without blocking HTTP request threads.
3. **PostgreSQL Database**: Stores canonical publication metadata, identifiers, crawlers evidence log, and operational refreshes/jobs state.

---

## 2. Environment Variables & Credentials

Configure the following variables in your `.env` file or export them into the running container environment:

| Key | Description | Default / Example |
| --- | --- | --- |
| `RESEARCH_ATTENTION_ENABLED` | Toggles the entire attention tracker module. | `true` |
| `RESEARCH_ATTENTION_DATABASE_URL` | SQLAlchemy-compatible PostgreSQL connection string. | `postgresql+psycopg://postgres:postgres@localhost:5432/research_attention` |
| `RESEARCH_ATTENTION_INTERNAL_API_KEY` | Header key token for authorizing manual crawls (`X-Research-Attention-Key`). | `default-dev-key-change-me` |
| `RESEARCH_ATTENTION_ENABLE_WIKIMEDIA` | Toggles the Wikipedia crawl connector. | `true` |

---

## 3. Worker Daemon Controls

The background worker daemon polls the database for scheduled jobs.

### Starting the Worker Daemon
Run the worker directly inside the virtual environment:
```bash
.venv\Scripts\python -m src.attention.worker
```

### Stopping the Worker Daemon
Send a standard `SIGINT` (Ctrl+C) to terminate the daemon safely. The daemon completes the current sub-connector crawl and saves current progress before shutting down.

---

## 4. Database Migrations & Administration

Alembic handles table creations and schema updates.

### Check Current Migration Level
```bash
.venv\Scripts\alembic current
```

### Apply Upgrades
To apply all pending migrations up to the head revision:
```bash
.venv\Scripts\alembic upgrade head
```

---

## 5. Troubleshooting Connector Failures

### 1. Wikimedia API Rate Limits
*   **Symptoms**: Dashboard shows connector status `rate_limited` or `failed` with error code `429`.
*   **Fix**:
    *   Verify the User-Agent header in `src/attention/connectors/wikimedia.py` complies with Wikimedia's policy (must include a contact email).
    *   Increase the wait time or retry delay in job schedules.

### 2. Identifier Reconciliation Conflicts (HTTP 409)
*   **Symptoms**: Resolving a PMID/DOI returns `409 Conflict: Conflicting supplied identifiers are discovered during resolution flow.`
*   **Fix**:
    *   This occurs when external APIs map an identifier (e.g., a DOI) to a different pre-existing publication record in your local database.
    *   Inspect `work_identifiers` table to identify the conflicting `work_id` rows.
    *   Resolve manually by merging the duplicate rows or updating the identifier records.
