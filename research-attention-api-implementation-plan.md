# Research Attention API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a durable, internal, source-level research-attention API and a D3.js article analytics dashboard to the existing FastAPI plagiarism checker. It must resolve a PMID or DOI to one canonical work, return transparent evidence by source, and leave the existing `/api/analyze` confidentiality behavior unchanged.

**Architecture:** Add an `attention` module and FastAPI router alongside, not inside, `ResearchGuardrailAgent`. A resolver normalizes identifiers using PubMed, Europe PMC, Crossref, and OpenAlex; connectors collect independently verifiable external evidence; PostgreSQL retains the canonical work, refresh state, and individual mentions. A static vanilla-JavaScript dashboard consumes read-only analytics endpoints and uses locally served D3.js to visualize the source-level evidence. The API derives counts from stored evidence and deliberately exposes no composite attention score in v1.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL 15+, `requests` or `httpx`, pytest, D3.js v7 (free, locally served), and the existing PubMed/Europe PMC clients.

## Global Constraints

- Keep `POST /api/analyze` behavior and its uploaded-document privacy boundary unchanged.
- Add all new routes under `/api/v1/research-attention`; do not overload the plagiarism endpoint.
- Accept a numeric PMID or a DOI; normalize DOI case, whitespace, `doi:` prefixes, `https://doi.org/`, and trailing punctuation before lookup.
- Store source-level evidence only in v1. Do not compute, label, or imply a composite “attention score.”
- Use D3.js v7 for charts; serve a pinned local copy from the application rather than loading a third-party CDN at runtime.
- Make dashboard visuals accessible: keyboard-reachable filters, text/table alternatives, color-independent labels, tooltips that work by keyboard, and a reduced-motion mode.
- Treat every source as partial coverage. Return connector status and last-refresh time with every response.
- Persist only public publication metadata and public mention metadata. Never pass uploaded document text, extracted keywords, embeddings, or plagiarism results to this module.
- Use provider-specific rate limits, retry-after handling, exponential backoff, idempotency keys, and an auditable raw-reference payload for each mention.
- Require a source-specific legal/terms-of-use review and configured credential before enabling a restricted or commercial connector.

---

## Current Repository Baseline

The repository currently exposes one FastAPI application in `src/api.py`, with `POST /api/analyze` delegating to `ResearchGuardrailAgent`. `src/pubmed_client.py` already calls NCBI ESearch/EFetch and parses PMID, DOI, title, abstract, authors, journal, and publication date. `src/europe_pmc_client.py` already retrieves PMID, PMCID, DOI, and bibliographic fields. There is no durable database, router structure, or API-test suite yet.

This plan adds a separate capability; it does not turn document-analysis searches into attention collection.

## API Contract

### Lookup endpoints

```http
GET /api/v1/research-attention/works/pmid/{pmid}
GET /api/v1/research-attention/works/doi/{doi}
GET /api/v1/research-attention/works/{work_id}
GET /api/v1/research-attention/works/{work_id}/analytics
POST /api/v1/research-attention/works/{work_id}/refresh
GET /research-attention/dashboard/work/{work_id}
```

`GET` returns a cached record immediately. If the work is unknown, the API resolves it synchronously from identity providers, queues collection, and returns `202 Accepted` with the canonical work and `refresh_state: "queued"`. If a record exists, return `200 OK` even where individual sources are unavailable; the response must say why.

`POST .../refresh` is an internal-only operation. It queues a refresh, is idempotent for a currently queued/running work, and returns `202 Accepted`. Protect it with the existing internal API authentication mechanism; if none exists, introduce a separate `RESEARCH_ATTENTION_INTERNAL_API_KEY` header dependency before exposing the route.

`GET .../analytics` is a read-optimized projection for D3.js. It returns the same evidence semantics as the work endpoint, but groups evidence by source and day/week/month and accepts optional `from`, `to`, and repeated `source` filters. It must return an empty series rather than omit chart keys when no evidence exists.

`GET /research-attention/dashboard/work/{work_id}` serves a single-work article details dashboard. It is a presentation route only; all data comes from the API. It must never embed provider credentials or call third-party data sources directly from the browser.

### Successful response shape

```json
{
  "work_id": "wrk_01J...",
  "status": "ready",
  "canonical_work": {
    "title": "...",
    "journal": "...",
    "publication_date": "2024-06-15",
    "authors": ["First Author", "Second Author"]
  },
  "identifiers": {
    "pmid": "12345678",
    "doi": "10.1000/example",
    "pmcid": "PMC1234567",
    "openalex_id": "https://openalex.org/W..."
  },
  "attention": {
    "summary": [
      {
        "source": "wikipedia",
        "evidence_count": 2,
        "coverage_status": "complete_for_connector_scope",
        "last_refreshed_at": "2026-08-05T10:00:00Z"
      }
    ],
    "evidence": [
      {
        "evidence_id": "evd_01J...",
        "source": "wikipedia",
        "source_type": "reference",
        "url": "https://en.wikipedia.org/wiki/...",
        "title": "...",
        "published_at": null,
        "discovered_at": "2026-08-05T10:00:00Z",
        "matched_identifier": "doi:10.1000/example",
        "match_confidence": "exact_identifier"
      }
    ]
  },
  "coverage": {
    "refresh_state": "ready",
    "next_refresh_after": "2026-08-12T10:00:00Z",
    "sources": [
      { "source": "news", "state": "not_configured", "reason": "Provider credential not configured" }
    ]
  }
}
```

Use these error responses:

- `400`: invalid PMID or DOI syntax.
- `404`: no work can be resolved from any identity provider.
- `409`: conflicting supplied identifiers are discovered during an internal resolution flow; retain neither merge until reviewed.
- `429`: caller has exceeded the internal API rate limit.
- `502`: every required identity provider failed and no cached canonical record exists.

## Data Model

| Table | Purpose | Essential fields |
|---|---|---|
| `research_works` | Canonical publication record | `id`, normalized title, journal, publication date, authors JSON, creation/update timestamps |
| `work_identifiers` | One-to-many aliases, unique per identifier | `work_id`, `scheme`, `normalized_value`, `display_value`, `source` |
| `attention_evidence` | One public, source-level mention/reference | `id`, `work_id`, source, type, external ID, URL, title, published/discovered dates, matched identifier, confidence, raw reference JSON, active flag |
| `source_refreshes` | Per-work, per-source operational state | `work_id`, source, state, started/completed/next refresh times, error code, safe error message, item count |
| `attention_jobs` | Durable, idempotent background work | `id`, work ID, job kind, state, attempt count, locked timestamp, scheduled timestamp, error details |

Add unique constraints for `(scheme, normalized_value)` in `work_identifiers`, `(work_id, source, external_id)` where an external ID exists, and `(work_id, source, url_hash)` otherwise. Hash canonicalized URLs with SHA-256 so tracking parameters do not create duplicate evidence.

## Source Strategy

### Identity providers — enabled in the first increment

1. **NCBI PubMed E-utilities**: PMID authority and article metadata. Reuse parsing concepts from `PubMedClient`, but add a `fetch_by_pmid` path rather than using document keywords.
2. **Europe PMC**: PMCID, DOI, preprint, and metadata enrichment.
3. **Crossref**: DOI metadata, relation checks, retractions/corrections metadata where available.
4. **OpenAlex**: supplementary work identity, alternate IDs, and metadata reconciliation.

These services resolve the work; they must not be returned as “attention” sources.

### Evidence connectors

Implement a connector registry and enable only connectors whose API access and terms are explicitly configured. The initial implementation should include only exact-identifier collection and no broad web scraping.

| Connector | v1 status | Match rule | Notes |
|---|---|---|---|
| Wikipedia / Wikimedia | Implement | PMID/DOI literal in citation/reference content | Store revision/permalink where available; count each source page once. |
| Open news index/provider | Adapter plus configuration | DOI/PMID literal, then controlled title/author review | A provider must define coverage and retention; never claim it represents all news. |
| Open policy/guideline repository | Adapter plus configuration | Exact identifier first | Configure each repository separately; retain document URL and version/date. |
| Patent data provider | Adapter plus configuration | Exact identifier first | Enable only through an approved API/license; do not scrape Google Patents. |
| Blogs | Adapter plus configuration | Exact identifier first | Treat RSS/API feeds as bounded sources, not global blog coverage. |
| Bluesky/Mastodon/Reddit/X | Disabled by default | Provider API access and exact identifier only | Enable independently after credentials, rate limits, and ToS review. |
| Reader counts/reference managers | Disabled by default | Provider-supported work ID | Record provider aggregate as an observation, not individual reader data. |

For title-only matching, create a `candidate` evidence state and never expose it in public counts until a deterministic matching policy or human review promotes it. Exact DOI/PMID/PMCID matching is `exact_identifier`; DOI discovered from an unambiguous canonical URL is `canonical_url`; normalized title plus first author/year is `probable`, not countable in v1.

## File Structure

| Path | Change | Responsibility |
|---|---|---|
| `src/api.py` | Modify | Register the research-attention router; preserve existing routes. |
| `src/config.py` | Modify | Database URL, refresh intervals, provider endpoints, credentials, rate limits. |
| `src/attention/router.py` | Create | Public lookup/refresh routes and HTTP status mapping. |
| `src/attention/schemas.py` | Create | Pydantic request/response contracts. |
| `src/attention/models.py` | Create | SQLAlchemy tables and constraints. |
| `src/attention/database.py` | Create | Engine, sessions, migration bootstrap. |
| `src/attention/resolver.py` | Create | PMID/DOI normalization, identity lookup, conflict detection, canonical work upsert. |
| `src/attention/providers/pubmed.py` | Create | PMID metadata lookup adapter. |
| `src/attention/providers/europe_pmc.py` | Create | Europe PMC enrichment adapter. |
| `src/attention/providers/crossref.py` | Create | DOI metadata adapter. |
| `src/attention/providers/openalex.py` | Create | Work metadata/alternate-ID adapter. |
| `src/attention/connectors/base.py` | Create | Connector contract, source states, shared HTTP/retry policy. |
| `src/attention/connectors/wikimedia.py` | Create | First exact-identifier evidence connector. |
| `src/attention/connectors/registry.py` | Create | Configuration-aware enabled-connector registry. |
| `src/attention/services.py` | Create | Lookup orchestration, aggregation, queueing, and response assembly. |
| `src/attention/worker.py` | Create | Durable job claim/refresh loop. |
| `src/dashboard/research_attention.html` | Create | Semantic dashboard shell, filter controls, accessible evidence table, and D3 mount points. |
| `src/static/vendor/d3.v7.min.js` | Create | Pinned local distribution of the free D3.js v7 browser bundle, with license notice. |
| `src/static/research_attention_dashboard.js` | Create | D3 chart rendering, filters, keyboard tooltips, and API requests. |
| `src/static/research_attention_dashboard.css` | Create | Responsive layout, high-contrast tokens, chart legend and reduced-motion styles. |
| `alembic.ini`, `migrations/` | Create | Versioned PostgreSQL schema migrations. |
| `requirements.txt` | Modify | SQLAlchemy, Alembic, PostgreSQL driver, and HTTP client dependencies. |
| `tests/attention/` | Create | Unit, API, migration, and provider/connector contract tests. |

## Implementation Tasks

### Task 1: Establish the module boundary and database foundation

**Files:**
- Modify: `requirements.txt`, `src/api.py`, `src/config.py`
- Create: `src/attention/__init__.py`, `src/attention/database.py`, `src/attention/models.py`, `alembic.ini`, `migrations/`
- Test: `tests/attention/test_models.py`, `tests/attention/test_api_isolation.py`

- [ ] Add SQLAlchemy 2, Alembic, `psycopg[binary]`, and `httpx` with minimum versions compatible with Python 3.10.
- [ ] Add `RESEARCH_ATTENTION_DATABASE_URL`, `RESEARCH_ATTENTION_INTERNAL_API_KEY`, and source configuration values to `src/config.py`; fail startup only when the attention router is enabled but its database configuration is absent.
- [ ] Define the five tables in the data model and generate an initial Alembic migration.
- [ ] Register an `APIRouter(prefix="/api/v1/research-attention", tags=["research-attention"])` in `src/api.py` without changing `/api/analyze`.
- [ ] Write the failing API-isolation test asserting `/api/analyze` remains registered and imports neither attention resolver nor connector modules on request.
- [ ] Apply the migration to an ephemeral PostgreSQL test database and test identifier/evidence uniqueness constraints.

### Task 2: Implement deterministic PMID/DOI resolution

**Files:**
- Create: `src/attention/schemas.py`, `src/attention/resolver.py`, `src/attention/providers/base.py`, `src/attention/providers/pubmed.py`, `src/attention/providers/europe_pmc.py`, `src/attention/providers/crossref.py`, `src/attention/providers/openalex.py`
- Test: `tests/attention/test_identifier_normalization.py`, `tests/attention/test_resolver.py`, `tests/attention/test_provider_contracts.py`

- [ ] Define `normalize_pmid(value: str) -> str` to accept only digits and `normalize_doi(value: str) -> str` to remove resolver URLs/prefixes, lowercase the result, and reject invalid DOI syntax.
- [ ] Define an `IdentityProvider` protocol with `resolve_pmid(pmid)` and `resolve_doi(doi)` returning a common `ResolvedWork` value object.
- [ ] Write failing tests for `10.1000/ABC.1`, `doi:10.1000/ABC.1`, and `https://doi.org/10.1000/ABC.1` resolving to the same normalized DOI; include invalid values and conflicting PMID/DOI records.
- [ ] Reuse the existing PubMed and Europe PMC HTTP endpoint knowledge, but create focused attention adapters so document-keyword methods are not reused.
- [ ] Reconcile provider results with priority PMID authority → exact DOI → PMCID → normalized title/first author/year. Persist an audit record of provider values and return `409` for unresolved conflict.
- [ ] Test mocked provider responses, provider timeout fallback, and idempotent upsert of a canonical work.

### Task 3: Add evidence ingestion, state, and deduplication

**Files:**
- Create: `src/attention/connectors/base.py`, `src/attention/connectors/registry.py`, `src/attention/services.py`
- Test: `tests/attention/test_evidence_deduplication.py`, `tests/attention/test_connector_registry.py`, `tests/attention/test_refresh_state.py`

- [ ] Define `AttentionConnector.collect(work: ResearchWork) -> ConnectorResult` and require each result to include source state, collection scope, evidence candidates, and safe operational errors.
- [ ] Canonicalize evidence URLs by removing fragment identifiers and configured tracking query parameters before calculating `url_hash`.
- [ ] Write failing tests that ingest the same external source using DOI and PMID and assert a single evidence row is retained.
- [ ] Persist only `exact_identifier` and `canonical_url` candidates as public evidence. Persist `probable` candidates with `active=False` for audit/review.
- [ ] Calculate summary counts from active `attention_evidence` rows grouped by source; do not write a score column or a precomputed total.
- [ ] Test `ready`, `queued`, `running`, `not_configured`, `rate_limited`, and `failed` source refresh states.

### Task 4: Deliver the first connector and connector controls

**Files:**
- Create: `src/attention/connectors/wikimedia.py`
- Modify: `src/attention/connectors/registry.py`, `src/config.py`
- Test: `tests/attention/test_wikimedia_connector.py`

- [ ] Implement a Wikimedia connector that searches/inspects configured Wikimedia endpoints for literal canonical DOI, PMID, and PMCID references only.
- [ ] Capture stable page title, page URL, revision/permalink when available, discovery time, matched identifier, and exact-match confidence.
- [ ] Deduplicate at source-page level so repeated citations within one page are one evidence item unless product requirements later explicitly introduce reference-level counts.
- [ ] Gate the connector behind `RESEARCH_ATTENTION_ENABLE_WIKIMEDIA=true`; when false, expose `not_configured` rather than silently returning zero.
- [ ] Write fixture-based tests for DOI/PMID hit, no hit, malformed provider payload, rate-limit response, and a repeated page reference.

### Task 5: Expose lookup and refresh routes

**Files:**
- Create: `src/attention/router.py`
- Modify: `src/attention/services.py`, `src/api.py`
- Test: `tests/attention/test_router.py`, `tests/attention/test_openapi.py`

- [ ] Implement PMID and DOI routes with strict validation before external calls.
- [ ] Return cached `ready` data with canonical metadata, identifiers, source summaries, evidence, per-source status, and `last_refreshed_at`.
- [ ] On an unknown work, resolve identity then create an idempotent collection job and return `202`; do not hold the client connection while slow connectors run.
- [ ] Protect the refresh route with the internal API-key dependency; test missing, invalid, and valid key behavior.
- [ ] Ensure generated OpenAPI documentation describes `200`, `202`, `400`, `404`, `409`, `429`, and `502` response examples.
- [ ] Add API tests with FastAPI `TestClient` and a mock provider registry; no test may make a real external HTTP call.

### Task 6: Add durable refresh processing and operations safeguards

**Files:**
- Create: `src/attention/worker.py`
- Modify: `src/attention/services.py`, `src/attention/models.py`, deployment documentation
- Test: `tests/attention/test_worker.py`, `tests/attention/test_retry_policy.py`

- [ ] Implement a separate worker process that claims `attention_jobs` using a transaction-safe PostgreSQL lock, marks it running, executes configured connectors, and records completion/failure per source.
- [ ] Retry transient network and provider `429/5xx` failures with bounded exponential backoff and provider `Retry-After` support. Do not retry invalid identifiers or terms/credential failures.
- [ ] Schedule refreshes by source type: weekly for static references/policy/patent sources and daily for enabled news/social sources, with values configurable by environment.
- [ ] Record structured metrics/log fields: work ID, source, job ID, state, duration, HTTP status class, evidence candidates, accepted evidence, and error category. Never log request secrets.
- [ ] Test that duplicate refresh requests coalesce, failed connectors do not erase previously retained evidence, and a job lease can be recovered after worker interruption.

### Task 7: Build the D3.js article analytics dashboard

**Files:**
- Create: `src/dashboard/research_attention.html`, `src/static/vendor/d3.v7.min.js`, `src/static/research_attention_dashboard.js`, `src/static/research_attention_dashboard.css`
- Modify: `src/attention/router.py`, `src/attention/schemas.py`, `src/attention/services.py`, `src/api.py`
- Test: `tests/attention/test_analytics_api.py`, `tests/dashboard/test_research_attention_dashboard.py`

- [ ] Define a `WorkAnalyticsResponse` with `source_breakdown`, `timeline`, `evidence`, `coverage`, and `updated_at`. Build every chart dataset solely from active, source-level evidence retained by the service.
- [ ] Implement `GET /api/v1/research-attention/works/{work_id}/analytics` with `from`, `to`, `bucket=day|week|month`, and repeated `source` query parameters. Validate date ranges, use UTC buckets, and include zero-count periods between the requested start and end dates.
- [ ] Add a semantic dashboard page that loads D3.js v7 from `/static/vendor/d3.v7.min.js`, shows the canonical work summary, and contains a visible data-table alternative for each chart.
- [ ] Render a source-breakdown horizontal bar chart, an attention-over-time line/stacked-area chart, and a source legend with D3. Every mark must carry a text label or have an equivalent value in the adjacent accessible table.
- [ ] Render the evidence feed as ordinary HTML with source and date filters, direct source links, match confidence, and coverage badges. D3 is not required for the evidence list.
- [ ] Use a deterministic, color-blind-safe source palette; never communicate category only through color. Honor `prefers-reduced-motion` and provide keyboard/focus handling for filters and tooltips.
- [ ] Render “No evidence in this range” and source-unavailable states intentionally; do not render a misleading empty chart or zero total for a disabled/failed connector.
- [ ] Write API tests for bucket aggregation, empty-series generation, date/source filters, and evidence/source-summary consistency. Write browser-level tests that assert D3 mounts the three visualizations and the table alternatives remain populated.

### Task 8: Create provider-adapter extension points and release controls

**Files:**
- Create: `docs/research-attention-source-onboarding.md`, `docs/research-attention-runbook.md`
- Modify: `README.md`
- Test: `tests/attention/test_disabled_connectors.py`

- [ ] Document the connector onboarding checklist: legal/ToS review, credential storage, rate limit, retention, match rule, scope statement, error semantics, fixture capture, and kill switch.
- [ ] Add provider adapters for news, policies, patents, blogs, social, and reader counts only after their individual checklist is approved. Each adapter starts disabled and must return an explicit coverage state.
- [ ] Document operational runbooks for provider outage, terms change, corrupted evidence, re-resolution conflict, and customer correction request.
- [ ] Update README with the new endpoint, the fact that it sends only public identifiers/metadata (never uploaded document text), and the source-coverage limitation.
- [ ] Run migration tests, unit tests, API tests, and a manual OpenAPI smoke test before release.

## Acceptance Criteria

- `GET /api/v1/research-attention/works/pmid/12345678` and an equivalent DOI lookup return the same `work_id` when the identifiers represent the same publication.
- A new lookup resolves canonical metadata, queues collection, and returns `202` without delaying on all connectors.
- A refreshed lookup returns evidence links, counts grouped by source, and source coverage/refresh state; it returns no score.
- The article dashboard uses local D3.js v7 to render source breakdown and timeline charts from the analytics endpoint, while retaining equivalent readable tables and filters.
- Disabled or failed connector states remain visible in the dashboard and are never displayed as zero attention.
- Identical DOI/PMID evidence discovered through different paths becomes one active evidence record.
- A disabled, rate-limited, or failed source is distinguishable from a source that found no evidence.
- `/api/analyze` continues to process uploaded documents in memory and the attention modules never receive document text or derived plagiarism data.
- All provider and connector tests use mocked HTTP responses; CI makes no unapproved external calls.

## Explicitly Deferred From v1

- Composite attention score, percentile, colors, badge, or ranking algorithm.
- Broad/general web crawling and any source collection that violates terms or lacks a reliable API/feed.
- Portfolio-wide analytics across many publications, subscriptions, billing, tenant management, and customer API keys. The v1 dashboard is a single-work/article details dashboard.
- Human review console for probable title matches; retain candidates now and add the console when volumes justify it.
- Backfilling every PMID/DOI. Ingest on lookup/refresh first, then plan controlled bulk backfills.

## Verification Commands

```bash
python -m pytest tests/attention -q
python -m pytest tests -q
alembic upgrade head
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Manual smoke checks after the worker is running:

```bash
curl -i http://127.0.0.1:8000/api/v1/research-attention/works/pmid/12345678
curl -i 'http://127.0.0.1:8000/api/v1/research-attention/works/doi/10.1000%2Fexample'
curl -i -X POST http://127.0.0.1:8000/api/v1/research-attention/works/wrk_example/refresh \
  -H 'X-Research-Attention-Key: replace-with-configured-key'
```
