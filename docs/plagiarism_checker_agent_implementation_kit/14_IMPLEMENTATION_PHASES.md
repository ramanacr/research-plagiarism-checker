# Implementation Phases

## Phase 0 — Baseline capture

Before refactor:
- snapshot current tests;
- benchmark current PubMed/Europe PMC behavior;
- record latency/memory;
- freeze representative test corpus.

Deliverable:
`baseline-results.json`

## Phase 1 — Provider abstraction

- create provider interface;
- wrap current PubMed implementation;
- wrap current Europe PMC implementation;
- remove direct provider calls from similarity engine.

Exit criteria:
existing functionality unchanged.

## Phase 2 — Document domain + segmentation

- normalized document model;
- section-aware parsing;
- references/quotes marking;
- token-aware passage segmentation.

Exit criteria:
stable passage IDs and offsets.

## Phase 3 — Persistent lexical index

- passage shingles;
- MinHash signatures;
- persistent index;
- containment-aware retrieval;
- corpus update/delete.

Exit criteria:
no query-time corpus rebuild.

## Phase 4 — Persistent dense ANN

- embedding service;
- FAISS/Qdrant adapter;
- persistent vectors;
- semantic top-K retrieval.

Exit criteria:
versioned index and deterministic integration tests.

## Phase 5 — Hybrid retrieval

- lexical + semantic + exact candidate union;
- deduplication;
- candidate fusion;
- retrieval metrics.

Exit criteria:
benchmark Recall@K target agreed and met.

## Phase 6 — Detailed matching

- exact spans;
- token overlap;
- containment;
- edit similarity;
- semantic score;
- passage aggregation.

## Phase 7 — Citation/reference/boilerplate handling

- reference exclusion;
- quote detection;
- citation context;
- phrase/document-frequency index;
- down-weight common phrases.

## Phase 8 — Classification/scoring

- MatchEvidence model;
- deterministic initial classifier;
- separate suspicious vs cited/quoted coverage.

## Phase 9 — Benchmark calibration

- human-reviewed benchmark;
- threshold tuning;
- regression gates.

This phase is mandatory before production claims.

## Phase 10 — Optional cross-encoder

Add only if benchmark shows meaningful improvement.

## Phase 11 — Additional free sources

Recommended:
- PMC OA
- Crossref
- OpenAlex
- Unpaywall
- arXiv
- CORE
- DOAJ

## Phase 12 — Scale/operations

- background ingestion scheduler;
- checkpoints;
- monitoring;
- index compaction/rebuild strategy;
- load testing.

## Phase 13 — Paid source readiness

- rights registry;
- provider contract templates;
- paid provider adapters only after license approval.
