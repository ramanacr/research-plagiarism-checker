# Source Provider Strategy

## Current providers

### PubMed
Primary role:
- biomedical publication discovery;
- metadata;
- abstracts where available.

Do not treat PubMed as a universal full-text source.

### Europe PMC
Primary role:
- biomedical metadata;
- abstracts;
- accessible full text where available and permitted.

## Immediate next providers

Recommended order:

1. PMC Open Access corpus
2. Crossref
3. OpenAlex
4. Unpaywall
5. arXiv
6. CORE
7. DOAJ
8. bioRxiv
9. medRxiv
10. institutional OAI-PMH repositories

## Roles

### Discovery providers
Examples:
- PubMed
- Crossref
- OpenAlex

They answer:
"What scholarly works may be relevant?"

### Full-text resolvers/providers
Examples:
- Europe PMC
- PMC OA
- Unpaywall-resolved OA locations
- arXiv
- CORE
- institutional repositories

They answer:
"Where can legally usable full text be retrieved?"

### Paid providers
Future:
- ProQuest
- Elsevier
- Springer Nature
- Wiley
- IEEE
- ACM
- others

These require explicit licensing analysis.

## Provider registry

Each provider must register:
- name;
- capabilities;
- rate limit;
- authentication type;
- source ID type;
- metadata support;
- full-text support;
- license behavior;
- health state.

## Example capability model

```python
@dataclass(frozen=True)
class ProviderCapabilities:
    search: bool
    metadata: bool
    abstracts: bool
    full_text: bool
    bulk_ingest: bool
```

## Failure isolation

If one provider fails:
- continue with available providers;
- record provider warning;
- do not fail the entire plagiarism check unless required by caller policy.
