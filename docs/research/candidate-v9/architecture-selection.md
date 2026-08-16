# Candidate-v9 Architecture Selection

## Decision

Candidate-v9 freezes the following architecture for formal evaluation:

`TYPED_QUERY_INTENT + RELATION_CANONICALIZATION + RELATION_RANGE_VALUE_BINDING + HARD_SAFETY_BLOCKERS`

Candidate-v2 remains the only ranker. Candidate-v9 independently certifies each ranked memory and returns only an order-preserving subsequence.

## Why this architecture was selected

Candidate-v8 historical protected diagnosis found all four false abstentions were relation-realization failures: the subject, value-bearing, temporal, and safety-blocker checks passed while the relation check failed. This supported the preregistered H1/H2 family and ruled out a broad relaxation of safety blockers.

Candidate-v9 development iteration 0 added typed query intent and canonical relation matching. It preserved safety (`false retrieval = 0/150`) but retained 22/210 false abstentions. The complete development failure taxonomy classified all 22 as value-type failures, showing that a finite closed entity lexicon was the next bottleneck.

Iteration 1 introduced open-class value compatibility. It reduced false abstention to 3/210 while maintaining zero false retrieval, but still missed the preregistered R@3/R@5 and paired-bootstrap non-inferiority gates.

The remaining three misses were all object/value-binding scope errors: incidental words in a clause were interpreted as the answer's value type. Examples included an activity word inside a goal value and a schedule adjunct inside a preference clause. Iteration 2 therefore made the semantic range of a monomorphic canonical relation authoritative over incidental clause-level type signals, while polymorphic preference remained fail-closed on explicit competing content types. The medication shortcut remains disabled because generic `take/taking` is semantically ambiguous.

Iteration 2 passed every preregistered development gate on the unchanged 360-case development surface. Iteration 3 changed only the descriptive configuration to match the already-passing implementation and reproduced the same development result.

## Rejected alternatives

### Pure typed requirement graph without relation canonicalization

Rejected because Candidate-v8 historical failures directly demonstrated that lexical relation realization was the limiting factor. A graph whose relation nodes still depended on the same sparse surface mapping would preserve the failure mode.

### Threshold-only weighted evidence scoring

Rejected as the primary fix. The failures were not low aggregate evidence scores caused by noisy positive signals; they were systematic semantic typing/normalization misses. Lowering a score threshold would increase the risk of unsupported retrieval without correcting the representation error.

### Full normalized claim extraction pipeline

Not selected for Candidate-v9 because it introduces additional deterministic extraction failure surfaces and complexity that development evidence did not require. Candidate-v9 achieves the needed structure with typed query intent, relation normalization, and bounded relation-range value binding.

### Dual-channel strict + paraphrase resolver

Not selected as a separate architecture because the selected implementation already preserves the strict hard-blocker path while adding bounded canonical relation resolution in a single per-memory certifier. A second independently maintained channel would duplicate logic without development evidence of added safety or recall.

## Frozen invariants

1. Candidate-v2 is the sole ranker.
2. Each memory is certified independently.
3. Output is an order-preserving subsequence of Candidate-v2 ranking.
4. Hard negative blockers inherited from Candidate-v8 remain mandatory.
5. Subject, temporal compatibility, and value-bearing checks remain mandatory.
6. Monomorphic canonical relations may type an open-class value by relation range.
7. Polymorphic preference may accept an unknown value only when no explicit competing content type is detected.
8. Generic medication `take/taking` does not receive a structural type shortcut.
9. Inference cannot use case ID, gold labels, relevant IDs, answer, benchmark split, filename, designation, or provenance.
10. No paid API or remote paid model is used.

## Known limitations

The relation ontology remains bounded and deterministic. Unknown relation families can still abstain. Polymorphic relations are intentionally conservative. Generic medication wording remains more conservative than other monomorphic relation families. Coreference is bounded to same-memory canonical subject anchoring plus explicit third-person pronouns rather than unrestricted discourse resolution.

## Expected formal failure modes

The principal remaining risks are unseen relation paraphrases, cross-clause value binding not represented by the bounded segmentation rules, ambiguous polymorphic relation values, and conservative medication/coreference handling. These risks must be measured only on the fresh protected, confirmatory, and final surfaces; they may not be patched inside Candidate-v9 after a formal failure.
