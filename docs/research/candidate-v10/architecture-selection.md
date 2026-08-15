# Candidate-v10 Architecture Selection

## Historical diagnosis

Candidate-v9 confirmatory produced 10 false abstentions. Post-preregistration historical diagnosis classified all 10 as relation-abstraction failures; one also had typed-value brittleness. Nine failures were nominalized preference assertions in which the query expressed a regular-choice relation while evidence assigned a regular meal attribute without Candidate-v9's expected preference verb/lexical family. The remaining failure was an open-class permit state value whose evidence assigned the state through the permit object slot rather than a closed status word.

No historical failure was primarily caused by subject resolution, temporal compatibility, evidence value-bearing detection, or a safety blocker.

## Hypothesis assessment

- H1 semantic relation abstraction failure: **strongly supported** (10/10).
- H2 argument/value binding failure: **not supported as primary cause** in the ten historical failures.
- H3 typed value inference brittleness: **supported in a minority case** (1/10).
- H4 query decomposition failure: **partially implicated** because object/property slots were not represented independently enough to bridge nominal assertions.
- H5 evidence entailment representation failure: **supported**; lexical relation families were acting as the proof rather than one signal inside a predicate–argument proof.
- H6 safety/answerability coupling: **structurally plausible but not directly observed**; safety remained perfect while relation novelty converted to abstention.
- H7 generator-family overfitting: **supported as a research-risk explanation** because the failing nominal surface family appeared only at confirmatory despite perfect development/protected results.

## Selected architecture

**Hybrid B + D + E: Predicate–Argument Semantic Frames + Constraint-Based Verifier + Deterministic Parser/Hard Blockers.**

Candidate-v10 represents each query as:

`subject + semantic relation/slot + optional possessed object + temporal scope`

Each evidence clause is evaluated independently against:

1. subject compatibility, including bounded same-memory pronoun coreference;
2. semantic relation compatibility;
3. open-class value/range compatibility licensed by the proven relation/slot rather than a closed answer lexicon;
4. value-bearing evidence;
5. direct assignment/assertion structure;
6. temporal compatibility;
7. inherited hard epistemic/safety blockers.

Two proof paths are permitted:

- **canonical relation proof:** query and evidence resolve to the same semantic relation frame;
- **open object-slot proof:** for status/color-style attributes, a query-owned object (for example a permit or backpack) can prove the predicate when evidence directly assigns an open value to the same object and no conflicting relation is present.

The second path is intentionally narrow. It is not a generic lexical fallback.

## Why Candidate-v9-style patching was rejected

Adding the ten missing lexical forms would reproduce the exact failure mechanism: a growing list of surface phrases that appears safe until the next independent grammar family. Candidate-v10 instead makes nominal assignment and object-slot structure part of the proof representation.

## Ranker and safety invariants

- Candidate-v2 remains the sole ranker.
- Candidate-v10 only removes unsupported memories and therefore returns an order-preserving subsequence.
- Benchmark IDs, labels, answers, provenance, split names, and generator-only metadata are ignored by inference.
- No paid API or remote model inference is used.
- Historical Candidate-v9 failed strings are diagnostic evidence only and are excluded from fresh formal surface generation.
