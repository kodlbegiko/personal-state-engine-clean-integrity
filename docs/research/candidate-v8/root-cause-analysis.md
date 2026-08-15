# Candidate-v8 Independent Root-Cause Analysis

## Evidence boundary at design time

This document is intentionally started **before opening the Candidate-v7 140-case confirmatory semantic payload**. At this stage, allowed evidence is limited to frozen Candidate-v2/Candidate-v7 source, Candidate-v7 terminal snapshot, aggregate confirmatory statistics, historical failure taxonomy, and the retained Candidate-v7 development ledger.

The frozen facts are: Candidate-v7 protected validation passed perfectly, but confirmatory produced 7/85 false abstentions and 10/55 false retrievals. Candidate-v7 implements a binary case gate: Candidate-v2 produces the ranking; Candidate-v7 scans ranked memories for any support; if at least one support object exists it returns the entire Candidate-v2 ranking, otherwise it returns an empty list.

## A. False-abstention hypotheses (7/85)

The observed false-abstention rate is compatible with several non-exclusive causes. No cause is treated as proven until historical diagnostic access is logged and per-failure evidence is classified.

1. **Relation-family coverage gap.** Candidate-v7 uses finite `CUE_FAMILIES`; unseen relations can cause `_relation_compatible` to fail even when the clause is factual.
2. **Lexical mismatch / paraphrase gap.** `_families` and `_anchor_coverage` depend on shallow stems and hand-written cues. Low-overlap paraphrases can be rejected.
3. **Implicit predicate / copular fact gap.** A narrow exception exists only for `identity_attribute`; other implicit relations can fail.
4. **Subject binding failure.** Capitalization/entity-anchor heuristics can over-constrain evidence, while first-person matching is surface-form based.
5. **Temporal false stale.** A whole memory is assigned one temporal class; a stale cue in one clause can invalidate a current fact in another.
6. **Multi-clause contamination.** Hard rejection is memory-level rather than clause-level. A question, agenda, uncertainty cue, or meta phrase in one clause can reject a separate factual clause.
7. **Value novelty heuristic failure.** `specific_novel_tokens` treats novel lexical material as a proxy for value bearing; valid values that overlap the query or are short/numeric can fail.
8. **Natural-language variation / direct-verb gap.** `_strict_direct_support` has a finite verb regex; unseen factual verbs depend on the weaker generic path.
9. **Query decomposition failure.** Candidate-v7 does not represent independent subject/relation/time/property requirements; a valid evidence subset may not line up with the single compatibility decision.

## B. False-retrieval hypotheses (10/55)

1. **Same subject / wrong relation.** Broad family overlap can accept a memory about the right entity but a different property.
2. **Same relation / wrong subject.** Anchor extraction can be empty for common names or pronouns, making subject compatibility vacuously true.
3. **Lexical-overlap distractor.** Novel token + low anchor coverage can pass generic support even when it does not entail the requested value.
4. **Semantically nearby but unsupported.** Relation families are coarse (for example possession/device, education/course, status/state), permitting family collision.
5. **Explicit unknown/no-value variants outside regex.** Candidate-v7 learned several regex forms in development but remains open to unseen linguistic variants.
6. **Contradiction/negation scope.** Memory-level regex detects some conflicts but does not bind negation to the queried predicate/value.
7. **Stale evidence mixed with current evidence.** Whole-memory temporal labeling may miss clause-specific stale/current distinctions.
8. **Hypothetical / future intent / agenda / question / meta.** Surface blockers are finite and can miss paraphrases.
9. **Quoted or attributed incorrect statements.** Candidate-v7 has no speech-source or quotation-role model.
10. **Assistant suggestion mistaken as user fact.** No explicit speaker/epistemic role is represented.
11. **Entity collision.** Generic/no-anchor queries can allow relation-compatible facts about another entity.
12. **Multi-clause contamination.** One apparently factual clause can unlock an unrelated ranked list.

## C. Structural flaw

The architecture contains the exact structural risk under investigation: **one accepted memory can unlock the full Candidate-v2 top-k list**. This is not equivalent to certifying each returned memory as evidence. It creates two failure channels:

- a false-positive support decision on any one memory turns into potentially multiple returned unsupported memories;
- a correct support decision cannot filter wrong-relation or wrong-subject distractors within the Candidate-v2 ranking.

Candidate-v8 therefore treats evidence certification as a **per-memory and per-query-requirement problem**, not a single case-level binary gate. Candidate-v2 rank order is preserved only among individually certified memories.

## Pre-diagnostic research hypotheses

- **H8-1:** Clause-level segmentation will reduce both benign-cue false abstention and multi-clause false support.
- **H8-2:** Explicit query requirements (subject, predicate/property, temporal scope, requested value type) will reduce relation-family collisions.
- **H8-3:** Separating hard blockers from positive support signals will avoid treating absence of a cue as evidence.
- **H8-4:** Filtering Candidate-v2 ranking per memory will reduce false retrieval without altering ranking quality among certified memories.
- **H8-5:** Multi-evidence aggregation is necessary for corrections/supersession and queries whose requirements are distributed across memories.

A later section will append evidence-backed classifications after the confirmatory surface is formally reclassified as `HISTORICAL_DIAGNOSTIC_ONLY`.
