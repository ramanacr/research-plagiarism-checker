# Security and Content Rights

## Rights are part of architecture

API access does not imply permission to:
- store full text;
- create persistent derived indexes;
- use content commercially;
- show matching snippets.

Every provider/document must resolve through a rights policy before persistence.

## Fail-closed behavior

If rights are unknown:
- metadata may be retained if permitted;
- full text must not be persistently stored/indexed until policy allows it.

## Secrets

Store in:
- environment secret store;
- AWS Secrets Manager;
- Vault;
- equivalent deployment secret manager.

Never commit secrets.

## Transport

Require HTTPS/TLS for remote providers.

## User document handling

Define:
- retention;
- encryption;
- deletion;
- whether user documents join the comparison corpus.

Default recommendation:
user submissions do **not** automatically enter the reusable corpus unless product terms explicitly permit it.

## Multi-tenant future readiness

If product becomes multi-tenant:
- corpus ownership must be explicit;
- private tenant corpora must be isolated;
- report access must be tenant scoped;
- index metadata must include tenant scope where applicable.

## Snippet display

Even where matching is allowed, output snippets must follow source-license/contract constraints.

## Audit

Record:
- rights decision;
- provider;
- license record;
- indexing decision;
- deletion decision.
