# Configuration

## Principles

- environment-specific;
- validated at startup;
- secret references, not secret values in source-controlled config;
- thresholds versioned;
- model/index versions explicit.

## Example

```yaml
engine:
  segmentation:
    target_tokens: 150
    overlap_tokens: 25
    min_passage_tokens: 20

  lexical:
    shingle_size: 5
    minhash_num_perm: 128
    lsh_threshold: 0.5
    top_k: 30

  semantic:
    model: sentence-transformers/all-mpnet-base-v2
    batch_size: 32
    top_k: 30
    index_backend: faiss

  reranker:
    enabled: false
    model: null
    top_k: 15

  scoring:
    threshold_version: v1
    min_suspicious_tokens: 12

providers:
  pubmed:
    enabled: true
  europe_pmc:
    enabled: true
  pmc_oa:
    enabled: false
  crossref:
    enabled: false

rights:
  fail_closed: true

observability:
  metrics_enabled: true
```

## Environment variables

Use environment variables/secret manager for:
- provider API keys;
- database credentials;
- vector DB credentials;
- proxy credentials.

## Model changes

Changing embedding model requires:
1. new model version;
2. new vector index;
3. benchmark run;
4. cutover plan;
5. no mixed-model vectors in one index.
