# Data Model and Storage

## Core entities

### SourceDocument

```text
document_id
provider
provider_source_id
doi
pmid
pmcid
title
authors
journal
publication_date
language
content_hash
rights_id
ingestion_status
created_at
updated_at
```

### SourcePassage

```text
passage_id
document_id
section
paragraph_index
start_offset
end_offset
token_count
normalized_hash
text_storage_ref_or_nullable
segmentation_version
```

### RightsRecord

```text
rights_id
provider
license_uri
commercial_use_allowed
text_mining_allowed
raw_storage_allowed
derived_index_allowed
snippet_display_allowed
retention_days
effective_from
effective_to
```

### LexicalSignature

```text
passage_id
index_version
shingle_count
minhash_blob_or_external_ref
```

### EmbeddingRecord

```text
passage_id
index_version
model_name
model_revision
dimension
vector_external_ref
```

### CorpusPhraseFrequency

```text
phrase_hash
document_frequency
passage_frequency
index_version
```

### PlagiarismCheck

```text
check_id
document_hash
created_at
engine_version
threshold_version
status
```

### Match

```text
match_id
check_id
query_passage_id
source_passage_id
classification
confidence
matched_query_start
matched_query_end
feature_payload
```

## Storage separation

Recommended:
- relational DB: metadata, provenance, rights, jobs, reports;
- lexical index: dedicated serialized/index layer;
- vector index: FAISS/Qdrant;
- object store/file store: raw source content only if rights allow.

## Raw text policy

Where licensing does not require long-term raw storage:
- process source;
- generate legal derived index;
- retain only permitted snippets/metadata;
- purge raw source according to policy.

## Referential integrity

Every vector and lexical signature must resolve to a valid `passage_id`, and every passage must resolve to source provenance.
