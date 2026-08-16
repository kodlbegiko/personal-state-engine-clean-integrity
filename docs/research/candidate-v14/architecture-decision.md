# Candidate-v14 Architecture Decision

## Decision

Select **Architecture B — Two-Stage Retrieve → Verify** as Candidate-v14.

## Rationale

1. Stage 1 scores and ranks all available memories, preserving retrieval opportunity.
2. Stage 2 verifies evidence sufficiency after ranking, so low parsing confidence alone cannot cause abstention.
3. Verification uses proposition binding, evidence completeness, contradiction/uncertainty penalties, and top-candidate competition instead of one absolute relevance threshold.
4. Development-safe evaluation reaches all aggregate, family, domain, and anti-collapse gates while A/C/D each violate at least one gate.
5. The implementation remains deterministic, offline, standard-library-only, explainable, and low-latency.

## Rejected alternatives

- **A:** high recall but false retrieval 0.1528 and abstention accuracy 0.8472 violate gates.
- **C:** relative-margin emphasis reintroduces abstention collapse; answerable recall 0.9167 and family floor 0.25 fail.
- **D:** sufficiency aggregate retrieves too aggressively; false retrieval 0.4167.

## Known risk

The fixed concept inventory and synthetic corpus may underrepresent truly heterogeneous language. Internal qualification, if achieved, therefore authorizes only a later independent fresh external-validity evaluation. It does not prove generalization.
