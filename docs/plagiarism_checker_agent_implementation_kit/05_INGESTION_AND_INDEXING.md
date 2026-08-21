# Ingestion and Indexing

## Goal

Convert source documents into persistent, searchable passage indexes.

## Ingestion flow

```text
provider
  ↓
metadata
  ↓
rights evaluation
  ↓
content retrieval
  ↓
normalization
  ↓
structure parsing
  ↓
passage segmentation
  ↓
lexical feature generation
  ↓
embedding generation
  ↓
persist metadata + indexes
```

## Normalization

Perform:
- Unicode normalization;
- whitespace normalization;
- case-folded representation for lexical matching;
- punctuation normalization where safe;
- optional lemmatized representation;
- preserve original text and offset mapping.

Do not destructively normalize the only stored representation.

## Segmentation

Use scientific-document-aware passages.

Recommended initial strategy:
- paragraph-based segmentation where source structure exists;
- otherwise sentence-pack windows;
- target 80–200 tokens;
- overlap 20–30 tokens;
- avoid cutting inside sentences.

Do not use fixed 50,000-character chunks as the semantic comparison unit.

Large chunks may still be used internally for safe parser batching.

## Shingling

Recommended baseline:
- word shingles: configurable `k`, start with 5;
- retain unique set for MinHash;
- retain ordered positions separately for detailed alignment.

Example:

`the treatment reduced mortality significantly`

5-gram:
`the treatment reduced mortality significantly`

For longer text, use overlapping k-grams.

## MinHash

Use MinHash only as an approximation mechanism for lexical set similarity.

Persist:
- signature;
- source passage ID;
- number of unique shingles;
- source metadata reference.

For very different set sizes, use containment-aware logic.

## Dense embeddings

Generate one embedding per indexed passage.

Batch embedding inference.

Persist:
- passage ID;
- model/version;
- vector;
- created timestamp.

Any embedding-model upgrade must create a new index version rather than silently mixing dimensions/models.

## Index versioning

Every index should include:

```text
index_version
normalization_version
shingle_version
embedding_model
embedding_model_revision
segmentation_version
created_at
```

This is mandatory for reproducibility.

## Incremental updates

When source content changes:
1. hash normalized source;
2. compare content hash;
3. skip unchanged documents;
4. remove old passage/index records when changed;
5. re-segment and re-index transactionally.

## Deletion

Support deletion by:
- provider;
- document ID;
- rights/license ID;
- index version.

This is required for licensing and reprocessing.
