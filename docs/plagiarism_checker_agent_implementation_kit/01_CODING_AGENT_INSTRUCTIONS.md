# Coding Agent Instructions

## Role

Act as the senior implementation engineer for the Python Plagiarism Checker Agent.

Do not redesign outside this specification unless a concrete technical blocker is found. If a deviation is necessary:

1. document the issue;
2. propose the smallest compatible change;
3. add or update an ADR;
4. preserve current externally visible behavior unless the specification explicitly changes it.

## Required workflow

For every implementation phase:

1. inspect the existing repository before changing code;
2. identify current public APIs and internal dependencies;
3. write or update tests first where practical;
4. implement the smallest coherent slice;
5. run unit tests;
6. run integration tests;
7. run benchmark/evaluation tests when similarity behavior changes;
8. review performance and memory characteristics;
9. update documentation;
10. do not declare completion with failing tests or unmeasured behavior.

## Architectural rules

- Python is the implementation language for the core engine.
- Use async I/O for external scholarly-provider calls.
- Separate source acquisition from plagiarism detection.
- Do not call PubMed or Europe PMC directly from similarity-scoring code.
- Do not rebuild corpus indexes for every query.
- Index normalized passages, not only full documents.
- Preserve provenance for every indexed passage.
- Preserve licensing/rights metadata for every acquired document.
- Use lexical and semantic retrieval in parallel.
- Treat semantic similarity as evidence, not a plagiarism verdict.
- Do not classify bibliography/reference entries as plagiarized body text.
- Down-weight or suppress highly common scientific boilerplate.
- Any threshold must come from evaluation data or be explicitly marked provisional.
- No claim of "commercial-grade", "iThenticate-equivalent", or similar may appear in code/docs unless supported by benchmark evidence.

## Dependency preferences

Recommended libraries, subject to repository compatibility:

- HTTP: `httpx`
- Models/config validation: `pydantic`, `pydantic-settings`
- NLP segmentation: `spaCy`
- sentence embeddings: `sentence-transformers`
- lexical similarity: `datasketch`
- exact/fuzzy matching: Python stdlib + purpose-built lightweight utilities
- local dense ANN: `faiss-cpu` or `faiss-gpu`
- service/vector DB option: `qdrant-client`
- structured storage: current project DB if suitable; otherwise PostgreSQL
- testing: `pytest`, `pytest-asyncio`
- metrics: Prometheus client if service deployment already supports Prometheus

Do not add a heavyweight dependency unless its benefit is clear.

## Implementation style

- Type hints on all public functions.
- Dataclasses or Pydantic models for structured domain data.
- No global mutable provider clients.
- Dependency injection through constructors/factories.
- Explicit timeouts for all HTTP calls.
- Retries only for transient failures.
- Respect provider rate limits.
- Structured logging with correlation IDs.
- No raw secret values in logs.
- No raw copyrighted full text in debug logs.

## Test discipline

Similarity changes are high-risk. A unit test proving arithmetic correctness is insufficient.

Every change to:
- normalization,
- shingling,
- embedding,
- retrieval,
- reranking,
- scoring,
- thresholding,
- boilerplate suppression,
- citation handling

must run against a stable labeled benchmark.

## Definition of done

A task is complete only when:
- implementation is present;
- tests pass;
- benchmark regressions are checked;
- configuration is documented;
- observability is present;
- failure behavior is defined;
- no architecture rule above is violated.
