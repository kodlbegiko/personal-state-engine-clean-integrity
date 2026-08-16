# Candidate-v11 Architecture Decision Record

## Decision

Candidate-v11 selects **Architecture C with a dominance guard**:

> Candidate-v10-compatible binary safety certification as Layer 1, followed by deterministic lexicographic semantic proof ordering among eligible Candidate-v2 candidates only.

Candidate-v2 original rank is the final tie-breaker. Ranking cannot rescue an ineligible memory and cannot inject a memory outside Candidate-v2's returned set.

## Evidence motivating the decision

The post-preregistration Candidate-v10 Final diagnostic found 15/15 rank-1 failures had multiple certification-compatible candidates, and 15/15 showed stronger assertion/directness in the relevant evidence than in the rank-1 distractor. The relevant evidence remained at rank 2 in all 15 cases. This isolates the missing mechanism as post-eligibility semantic preference rather than recall or blocker coverage.

## Alternatives considered

### Architecture A — Binary certification + Candidate-v2 order

**Mechanism:** preserve Candidate-v10 behavior.

**Strengths:** simplest; maximum continuity; safety behavior already demonstrated.

**Failure:** it cannot solve the diagnosed problem by construction. If two candidates pass certification, Candidate-v2 lexical/recency order remains authoritative even when one candidate contains a more direct and specific proof.

**Decision:** retained as the frozen baseline only.

### Architecture B — Structured weighted evidence-quality score

**Mechanism:** assign numeric weights to subject match, relation match, predicate specificity, object match, value-bearing strength, temporal fit, assertion strength, directness, and ambiguity.

**Strengths:** expressive and easy to optimize on Development.

**Risks:** compensatory scoring is undesirable in a safety-sensitive evidence verifier. A large gain on one soft feature can offset weakness on another, making promotion harder to reason about and easier to overfit. Weight tuning also creates a larger post-hoc search space.

**Decision:** rejected as the primary architecture. Structured features are retained as proof components, but not combined through an arbitrary weighted sum.

### Architecture C — Lexicographic semantic proof ordering

**Mechanism:** compare explicit proof dimensions in a fixed priority order and use Candidate-v2 rank only after semantic ties.

**Strengths:** deterministic, explainable, low tuning surface, non-compensatory, directly addresses the observed post-eligibility tie pathology.

**Risk:** a strict early dimension can over-dominate later evidence if the feature is noisy.

**Decision:** selected, with a dominance guard and conservative fallbacks.

### Architecture D — Pure Pareto/dominance partial ordering

**Mechanism:** reorder only when one candidate is no worse on all declared semantic dimensions and strictly better on at least one.

**Strengths:** highly conservative; minimizes unjustified reorderings.

**Risk:** too many incomparable pairs collapse back to Candidate-v2 order, potentially reproducing the exact Candidate-v10 failure mode.

**Decision:** use the dominance principle as a guard, not as the sole ordering rule.

## Two-layer architecture

### Layer 1 — Evidence eligibility

Candidate-v11 reuses the frozen Candidate-v10 certification philosophy and hard blockers. Eligibility checks include subject, relation, value type, open value-bearing assertion, temporal compatibility, assertion, and blocker status.

A memory failing Layer 1 is permanently excluded from ranking. Layer 2 has no code path that can change this result.

### Layer 2 — Evidence priority

For every eligible memory, Candidate-v11 derives a semantic proof from the best supported clause. The proof contains:

- `subject_binding_quality`
- `relation_specificity`
- `object_slot_coverage`
- `assertion_directness`
- `temporal_specificity`
- `semantic_completeness`
- `ambiguity_penalty`
- `candidate_v2_original_rank`

The first seven dimensions are computed only from runtime query/memory text and Candidate-v10 legitimate requirements/certification. Benchmark metadata is not passed to the function.

## Lexicographic priority order

The ordering is frozen conceptually as:

1. exact/direct subject binding;
2. relation specificity without competing relation frames;
3. object/slot compatibility when the query exposes object terms;
4. direct predicate-value assertion strength;
5. temporal specificity compatible with the query;
6. semantic proof completeness;
7. lower ambiguity;
8. Candidate-v2 original rank.

### Conservative dominance guard

A candidate is not allowed to win solely by a soft later feature if it is strictly worse on a safety-adjacent earlier dimension. In particular:

- weaker subject binding cannot be compensated by directness;
- weaker relation specificity cannot be compensated by lexical overlap or recency;
- object mismatch, when a meaningful object constraint exists, cannot be compensated by directness;
- any hard blocker remains absolute because blocked candidates never reach Layer 2.

Within exact ties, original Candidate-v2 order is preserved.

## Feature definitions

### Subject binding quality

- 3: all query subject anchors occur directly in the supported clause, or direct first-person binding is present when required;
- 2: subject anchors are established at memory level and the supported clause uses an admissible pronoun binding;
- 1: no explicit subject is required by the query;
- 0: should be unreachable for eligible evidence; retained as a defensive value.

### Relation specificity

- 3: supported clause expresses the requested primary relation without competing primary relations;
- 2: requested relation is present with additional compatible/broad relation signals;
- 1: relation is established through the Candidate-v10 object-slot fallback;
- 0: unreachable after eligibility.

### Object-slot coverage

Only meaningful query object terms extracted by the runtime semantic requirements are used. Generic terms do not become answer labels. Coverage is represented as an integer ratio numerator/denominator for deterministic comparison; if no meaningful object terms exist, candidates tie on this dimension.

### Assertion directness

Preference order:

1. explicit record/assertion predicates that directly bind a slot to a value (`recorded as`, `listed as`, `states`, `shows`, direct copular/property assignment, equivalent runtime forms);
2. ordinary assignment assertions;
3. narrative/descriptive mentions.

Uncertainty, negation, unsupported hypothetical future, and no-value cases are Layer-1 blockers, not low directness scores.

### Temporal specificity

Layer 1 remains authoritative for temporal admissibility. Layer 2 distinguishes stronger query-compatible temporal evidence only after admissibility. For an explicitly current query, explicit current evidence outranks temporally vague evidence. For an unspecified profile/state query, clearly historical framing is weaker than an otherwise equivalent non-historical assertion, but this preference cannot overcome stronger subject/relation/object proof.

### Semantic completeness

Count of satisfied structured proof components in the supported clause. Because Candidate-v10 failures often tie at full binary completeness, this is deliberately later than the finer-grained dimensions.

### Ambiguity

Penalty for competing primary relation signals or multiple equally supported clauses that make the memory less specific. It is a tie-break dimension, never an eligibility override.

## Candidate-v2 contract

Candidate-v11 obtains its candidate universe by calling Candidate-v2. Let `V2` be the ordered Candidate-v2 output and `E` the subset certified eligible by Layer 1.

Candidate-v11 output `V11` must satisfy:

- `set(V11) ⊆ set(V2)`;
- `set(V11) ⊆ E`;
- no memory absent from `V2` is introduced;
- `V11` is a permutation/subsequence of eligible members of `V2` only;
- when all semantic proof tuples tie, `V11` preserves Candidate-v2 relative order.

The previous Candidate-v10 `order-preservation` metric is therefore replaced for Candidate-v11 by a **candidate-source/permutation invariant**. Reordering eligible candidates is the intended intervention, not a violation.

## Metadata firewall

The public ranker sanitizes its input to only:

- query text;
- memory ID;
- memory text;
- memory timestamp.

It must not read relevant IDs, answer text, labels, split/stage, grammar family, semantic domain, generator provenance, designation, case ID, or other benchmark-only metadata.

## Why this is not Candidate-v10 + regex

Candidate-v11 does not expand the evidence-eligibility surface to chase historical wording. The intervention is architectural: it introduces a second semantic ordering layer after the safety verifier. Any lexical patterns used to characterize direct assertion are general runtime linguistic features and are tested on newly synthesized, structurally different examples.

## Falsification criteria

The architecture is considered unsupported if fresh Development cannot meet preregistered ranking thresholds without degrading false retrieval, false abstention, candidate-source invariants, metadata firewall, or determinism. A formal-stage failure terminates Candidate-v11 and is not repaired in-place.
