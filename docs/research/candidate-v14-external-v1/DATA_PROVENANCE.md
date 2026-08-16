# Data Provenance

The protected corpus is generated from a new deterministic generator defined only from the public task interface and the preregistered external-validity dimensions.

Forbidden inputs to corpus generation:

- Candidate-v14 source implementation details, thresholds, weights, tokenization tables, aliases, or internal keyword tables
- Candidate-v14 development examples or internal holdout examples
- Candidate-v13 EV-v4 case-level queries, memories, answer keys, assignments, seeds, templates, IDs, or protected payloads

Allowed inputs:

- task interface: query + memories -> retrieval/abstention
- high-level historical terminal decisions and aggregate failure categories
- generic retrieval/adversarial-testing principles
- this preregistered domain/family specification

The generator emits corpus shards and a separate answer key. The answer key is not consumed by Candidate-v14; only the scorer reads it after prediction artifact lock.
