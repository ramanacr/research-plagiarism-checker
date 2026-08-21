# Hybrid Retrieval and Matching

## Objective

Retrieve a small high-recall set of candidate source passages before expensive comparison.

## Retrieval channels

### A. Exact / rare phrase retrieval

Useful for:
- verbatim copying;
- unusually distinctive phrases.

Can use:
- normalized phrase hashes;
- inverted n-gram index;
- targeted SQL/search-engine index depending on scale.

### B. Lexical retrieval

Use:
- MinHash / LSH;
- containment-aware retrieval;
- shingle overlap.

Do not rely on document-level Jaccard alone.

### C. Dense semantic retrieval

Use Sentence Transformer embeddings + ANN.

Initial model:
`all-mpnet-base-v2`

Treat it as the baseline, not a permanent guaranteed best model.

## Candidate fusion

For each query passage:

1. retrieve top K lexical candidates;
2. retrieve top K dense candidates;
3. add exact-match candidates;
4. union candidates;
5. deduplicate by source passage;
6. retain retrieval-channel scores;
7. send top fused candidates to detailed matching.

Recommended initial values:
- lexical top K: 30
- semantic top K: 30
- detailed comparison max: 40

These are provisional and must be benchmarked.

## Detailed matching features

Calculate:
- exact matched token span;
- longest matching normalized sequence;
- n-gram containment;
- token Jaccard;
- edit similarity;
- semantic cosine;
- source/query length ratio;
- matched token count;
- phrase rarity;
- section/context features.

## Cross-encoder reranking

Optional but recommended after hybrid retrieval.

Use on only the final candidate set because cross-encoders are expensive.

The architecture must allow:
- disabled;
- enabled for suspicious candidates only;
- pluggable model.

## Passage aggregation

Adjacent source matches should be mergeable.

Example:

```text
Query passages 10,11,12
match
Source passages 44,45,46
```

should become one coherent evidence block rather than three independent report items.

## False-positive controls

Down-weight:
- very short matches;
- common technical phrases;
- references;
- citation boilerplate;
- legal/ethics boilerplate;
- standard method phrases.

## Semantic-only matches

A high semantic score with low lexical evidence should be classified conservatively unless reranking/context supports paraphrase.
