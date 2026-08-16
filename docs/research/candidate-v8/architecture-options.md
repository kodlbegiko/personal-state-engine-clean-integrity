# Candidate-v8 Architecture Options

## Decision objective

Candidate-v2 remains the retriever/ranker. Candidate-v8 is an evidence-certification layer. The goal is to preserve Candidate-v2 ordering for answerable evidence while sharply reducing unsafe retrievals, without relying on a closed keyword ontology.

## Architecture A — Clause-Level Evidence Certification

**Algorithm.** Segment each memory into conservative clauses; derive an `EvidenceClause` with subject anchors, predicate/relation signals, candidate value span, polarity, epistemic status, temporal scope, speech-act role, and source/speaker role when available. Evaluate clauses independently against the query; a memory is certifiable if at least one clause satisfies the required query fields without a clause-local blocker.

**Advantages.** Prevents a question/meta/uncertain clause from poisoning a separate factual clause; supports mixed memories and explainable evidence spans.

**Failure modes.** Rule-based segmentation can split coordinations incorrectly or fail on ellipsis; extracting implicit predicates remains difficult.

**False-abstention risk:** medium-low if fallback lexical semantics exists. **False-retrieval risk:** low-medium because scope errors are localized.

**Cost/determinism/explainability.** O(total tokens), deterministic, high explainability, zero model cost.

**Open vocabulary.** Better than v7 if relation matching uses requirement tokens and lexical evidence rather than only fixed families.

**Temporal/negation/multi-clause.** Strongest deterministic option because scope is clause-local.

**Implementation/testability.** Moderate complexity; easy unit-test surface with explicit evidence objects.

**Relationship to Candidate-v2.** Per-memory filtering of Candidate-v2 IDs; stable order retained among passing IDs.

## Architecture B — Multi-Signal Evidence Scoring

**Algorithm.** Compute hard blockers separately from positive evidence. Blockers include clause-local no-value, contradiction, unresolved epistemic state, question/agenda/meta-only, stale-only for current query, explicit queried-value negation, and wrong-subject evidence. Positive signals include subject binding, predicate compatibility, value bearing, lexical entailment/paraphrase overlap, temporal compatibility, direct assertion, and clause specificity. Certify only if no hard blocker applies and a minimum support quorum is satisfied.

**Advantages.** Avoids the v7 pattern where one weak lexical cue can dominate; makes uncertainty explicit and tunable before protected validation.

**Failure modes.** Poorly calibrated weights can become benchmark chasing; multiple weak correlated signals may create false confidence.

**False-abstention risk:** low-medium. **False-retrieval risk:** medium unless blockers and quorum are conservative.

**Cost/determinism/explainability.** Linear, deterministic, high explainability. Thresholds must be frozen at preregistration/freeze.

**Open vocabulary.** High if positive signals rely on query-derived predicate/content tokens and structural templates rather than fixed keyword families.

**Temporal/negation/multi-clause.** Good when applied per clause.

**Implementation/testability.** Moderate; every score component can be audited.

**Relationship to Candidate-v2.** Score is used only as evidence certification, never to rerank passing memories.

## Architecture C — Query Requirement Graph

**Algorithm.** Parse a query into required nodes: subject/entity, requested relation/property, temporal constraint, answer/value type, and optional qualifiers. Build edges describing mandatory co-satisfaction. Map evidence clauses to requirement nodes. A memory or evidence subset is certified only when all mandatory nodes are covered by compatible, non-contradicted evidence. Corrections/supersession can deactivate older edges.

**Advantages.** Directly addresses wrong-relation/right-subject and right-relation/wrong-subject errors; naturally handles distributed evidence and multiple requested attributes.

**Failure modes.** Deterministic query parsing may miss implicit subjects or conversational anaphora; graph complexity can be unnecessary for simple queries.

**False-abstention risk:** medium from under-parsing. **False-retrieval risk:** low if mandatory coverage is enforced.

**Cost/determinism/explainability.** O(query + evidence), deterministic, very explainable.

**Open vocabulary.** Medium-high when relation requirement is represented by query-derived lexical heads/content anchors plus optional typed hints.

**Temporal/negation/multi-clause.** Strong; requirements carry temporal scope and polarity constraints.

**Implementation/testability.** Highest complexity of the deterministic options but decomposes cleanly into unit tests.

**Relationship to Candidate-v2.** Candidate-v2 remains rank authority; graph only certifies which ranked items/evidence subsets are legally returnable.

## Architecture D — Hybrid Deterministic Verifier

**Algorithm.** Combine A+B+C in a deliberately small pipeline: (1) query-requirement decomposition, (2) conservative clause segmentation, (3) clause-local hard blockers, (4) multi-signal positive support, (5) per-memory certification, (6) optional multi-evidence requirement coverage, (7) preserve Candidate-v2 order among certified memories.

**Advantages.** Uses strict typed checks where precision is known to be high while retaining an open-vocabulary path. Structural requirements prevent a generic family/token match from being sufficient by itself.

**Failure modes.** Interaction complexity and duplicated heuristics; must keep the implementation auditable and prevent ad-hoc case patches.

**False-abstention risk:** low-medium. **False-retrieval risk:** low-medium, expected best Pareto balance among zero-cost deterministic options.

**Cost/determinism/explainability.** Linear to low-quadratic in number of clauses, deterministic, high explainability, zero monetary cost.

**Open vocabulary.** High relative to v7 because the typed family map is advisory rather than dispositive.

**Temporal/negation/multi-clause.** Explicitly first-class.

**Implementation/testability.** Moderate-high; requires comprehensive property tests and adversarial paired cases.

**Relationship to Candidate-v2.** Candidate-v2 ranking is never numerically modified. Candidate-v8 returns an order-preserving subsequence.

## Optional Architecture E — Local small-model/NLI hybrid

A frozen local CPU classifier or cross-encoder could score entailment after deterministic blockers. It is **not selected initially**. Reasons: reproducibility/dependency burden, model-download fragility, harder epistemic-role control, and the requirement to demonstrate material superiority over a deterministic baseline. If later tested, model identity, revision hash, dependency hashes, fixed seed, CPU path and deterministic decoding must be frozen; no paid API is permitted.

## Selected development architecture

**Architecture D** is selected for development, with Architecture C providing the central abstraction. Candidate-v8 will not use `return candidate_v2_ranking if any_support else []`. It will return an order-preserving subset of Candidate-v2 ranking whose memories are individually certified, and may require a certified multi-memory subset when query requirements are distributed.
