# Target Architecture

## Architectural objective

Build a layered plagiarism detection system that can scale from the existing PubMed + Europe PMC integration to multiple scholarly and web sources without coupling source-specific logic to similarity logic.

## High-level flow

```text
                    SOURCE INGESTION
────────────────────────────────────────────────────────────

 PubMed       Europe PMC      Future providers
    │              │               │
    └──────────────┴───────────────┘
                   ↓
             Provider Layer
                   ↓
        Metadata + Rights Resolver
                   ↓
          Full-text Acquisition
                   ↓
          Document Normalization
                   ↓
      Scientific Structure Processing
                   ↓
            Passage Segmentation
                   ↓
     ┌─────────────┼───────────────┐
     ↓             ↓               ↓
 lexical       embeddings       metadata
 features          │               │
     ↓             ↓               ↓
 lexical index  vector index   provenance DB


                     QUERY PIPELINE
────────────────────────────────────────────────────────────

 Uploaded manuscript
        ↓
 parse / normalize
        ↓
 identify sections
        ↓
 exclude or mark:
 references / quotes / boilerplate
        ↓
 passage segmentation
        ↓
 ┌────────────────────┬─────────────────────┐
 ↓                    ↓                     ↓
exact/phrase      lexical retrieval     dense ANN retrieval
 matching         MinHash/containment     embeddings
 └────────────────────┴─────────────────────┘
                     ↓
              Candidate Fusion
                     ↓
             Detailed Comparison
                     ↓
              Cross-Encoder
                (optional)
                     ↓
            Evidence Aggregation
                     ↓
         Context / Citation Adjustment
                     ↓
          Classification + Scoring
                     ↓
         Source-attributed Report
```

## Layers

### 1. Provider layer

Responsibilities:
- query external sources;
- retrieve metadata;
- retrieve content when legally permitted;
- expose normalized provider-independent contracts;
- enforce rate limits and provider authentication.

Must not:
- calculate plagiarism scores;
- generate embeddings;
- decide whether content is plagiarism.

### 2. Rights layer

Responsibilities:
- record content license;
- allow/deny raw storage;
- allow/deny persistent derived indexes;
- allow/deny snippet display;
- define retention.

### 3. Document processing layer

Responsibilities:
- normalize Unicode and whitespace;
- retain offsets back to original content;
- detect document structure;
- identify references and quoted material;
- segment content into passages.

### 4. Lexical index

Responsibilities:
- store passage shingles/fingerprints;
- support containment-oriented candidate retrieval;
- support exact and near-exact overlap detection.

### 5. Dense vector index

Responsibilities:
- persist embeddings for source passages;
- ANN retrieval by semantic similarity;
- filter by metadata where needed.

### 6. Match analysis

Responsibilities:
- exact overlap;
- n-gram containment;
- Jaccard/MinHash signal;
- edit/token similarity;
- semantic similarity;
- span length;
- source rarity/frequency;
- optional cross-encoder reranking.

### 7. Classification

Responsibilities:
- combine independent evidence;
- apply citation/quotation/boilerplate context;
- classify match type;
- calculate report contribution.

## Match classes

Recommended initial classes:

- `EXACT_COPY`
- `NEAR_EXACT_COPY`
- `LIKELY_PARAPHRASE`
- `POSSIBLE_PARAPHRASE`
- `COMMON_PHRASE`
- `PROPERLY_QUOTED`
- `CITED_OVERLAP`
- `REFERENCE_ONLY`
- `LOW_SIGNIFICANCE`
- `UNRELATED`

These are evidence classes, not legal/academic misconduct verdicts.

## Scalability principle

The corpus is prepared once and queried many times.

Never:

```text
request
  ↓
download candidate library
  ↓
build LSH/vector index
  ↓
search
```

Instead:

```text
background ingestion
  ↓
persistent indexes

request
  ↓
query persistent indexes
```
