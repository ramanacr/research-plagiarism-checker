# Observability and Operations

## Logging

Structured fields:
- request/check ID
- provider
- document ID
- pipeline stage
- duration
- candidate counts
- index version
- model version
- warning/error code

Never log:
- provider secrets;
- complete copyrighted documents;
- user manuscript text unless explicitly allowed by product policy.

## Metrics

Recommended:

```text
plagiarism_checks_total
plagiarism_check_duration_seconds
provider_requests_total
provider_errors_total
provider_latency_seconds
documents_ingested_total
passages_indexed_total
lexical_candidates_per_passage
semantic_candidates_per_passage
reranker_invocations_total
index_query_duration_seconds
embedding_duration_seconds
```

## Health

Expose:
- application health;
- DB;
- lexical index;
- vector index;
- each provider independently.

## Job monitoring

Ingestion jobs need:
- status;
- started/finished;
- provider;
- documents attempted;
- succeeded;
- failed;
- skipped;
- last cursor/checkpoint.

## Backpressure

Provider ingestion and query-time plagiarism checking must not compete uncontrollably for GPU/CPU.

Use separate worker pools/queues if required.

## Recovery

Ingestion must be checkpointed and idempotent.

A crash should not require complete corpus rebuild.
