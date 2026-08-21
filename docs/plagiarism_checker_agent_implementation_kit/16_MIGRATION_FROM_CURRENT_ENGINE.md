# Migration from Current Engine

## Current implementation assumptions

Current roadmap indicates:
- `spacy-transformers` / `en_core_web_trf`;
- `all-mpnet-base-v2`;
- blank spaCy sentencizer for candidate abstracts;
- `datasketch`;
- `filter_candidates_via_lsh`;
- LSH enabled when candidate library exceeds 20 documents.

## Required corrections

### 1. Remove incorrect semantic responsibility from spaCy

If any code uses spaCy `.similarity()` as a core plagiarism signal:
- deprecate it;
- preserve spaCy only for NLP tasks actually needed.

If `en_core_web_trf` is loaded but NER/POS/dependencies are not used:
- remove it from the hot path.

### 2. Keep MPNet, but move it into an embedding service

Create:
`EmbeddingService`

Responsibilities:
- batch encode;
- normalize vectors if desired;
- expose model/version;
- no classification logic.

### 3. Replace request-time LSH construction

If `filter_candidates_via_lsh()` builds a new index per request:
- split into `CorpusIndexer` and `LexicalRetriever`;
- build persistent passage index during ingestion;
- query only during plagiarism request.

### 4. Remove `>20 documents` as architecture behavior

A 20-document threshold may remain only as a temporary micro-optimization for tiny in-memory tests.

Production behavior should use persistent retrieval consistently.

### 5. Move from document/abstract-only comparison to passage-level

Existing abstract sentence comparison may continue as fallback for sources without full text, but full-text sources should be segmented into passages.

### 6. Introduce version compatibility

During migration:
- support old and new engine behind a feature flag;
- run both on benchmark documents;
- compare outcomes;
- cut over after regression targets pass.

## Suggested feature flags

```yaml
features:
  persistent_lexical_index: true
  dense_ann_index: true
  hybrid_retrieval: true
  citation_aware_scoring: false
  boilerplate_suppression: false
  cross_encoder: false
```

Roll out incrementally rather than changing all scoring behavior at once.
