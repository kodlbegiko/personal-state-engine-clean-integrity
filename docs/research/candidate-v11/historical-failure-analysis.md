# Candidate-v11 Historical Failure Analysis

## Scope and integrity boundary

This document is diagnostic evidence only. Candidate-v10 remains permanently terminal at `CANDIDATE_V10_FINAL_GATE_F_FAIL`; its Final benchmark is not rerun and its implementation is not modified.

Candidate-v11 preregistration was independently committed at `bf6c0d2b1435a9af868f1c6c3faf8f2853a5078b` before any individual Candidate-v10 Final query, memory, ID, grammar-family error table, or rank-1 distractor was inspected.

The diagnostic script intentionally emits hashes and structural features rather than raw historical query/memory text. Historical Final strings, entities, answer values, and case-specific exceptions are prohibited from Candidate-v11 tests and development surfaces.

## Observed failure set

Candidate-v10 Final contained 280 answerable cases. Its aggregate R@1 was 265/280 = 0.9464285714285714 while R@3 and answerable recall were both 1.0.

The post-preregistration diagnostic reproduced exactly 15 answerable cases in which:

- relevant evidence was retained by Candidate-v10;
- relevant evidence was in top-3;
- relevant evidence was not rank-1;
- in every one of the 15 cases the relevant evidence was rank-2.

This confirms that the terminal failure is a ranking-priority problem, not an evidence-recall problem.

## Root-cause taxonomy

Aggregate structured diagnostic counts:

| Root cause | Count | Interpretation |
|---|---:|---|
| multiple certification-compatible relation candidates | 15 / 15 | Binary eligibility cannot distinguish two plausible memories after both pass safety certification. |
| assertion/directness underweighted after eligibility | 15 / 15 | The relevant evidence supplies a stronger direct predicate/value assertion, but Candidate-v10 has no mechanism to prefer it after certification. |
| lexical overlap priority over semantic proof quality | 2 / 15 | Candidate-v2 lexical ranking can further favor a distractor even where its proof is semantically weaker. |

The diagnostic also showed the 15 failures were concentrated in one held-out structural family. This fact is used only as evidence of distribution-shift sensitivity; Candidate-v11 inference and development code may not inspect, branch on, or hardcode that historical family identifier.

## Dimension-by-dimension diagnosis

### 1. Relation ambiguity

The central ambiguity is not that Candidate-v10 fails to detect the requested relation. Instead, multiple memories can independently satisfy the same broad relation certification. Once this happens Candidate-v10 treats them as equivalent for ranking purposes.

### 2. Subject specificity

Subject certification is necessary and was generally successful in the rank-1 failure set. Subject matching therefore acts primarily as an eligibility/safety constraint. Candidate-v11 should nevertheless retain a finer subject-binding proof because exact in-clause binding is stronger than memory-level/pronominal fallback when both are eligible.

### 3. Predicate alignment

Candidate-v10's supported/not-supported result does not encode how specifically the evidence predicate answers the requested slot. A memory can pass the relation test while expressing a weaker or less direct predicate frame than another eligible memory.

This is the principal missing rank signal after certification.

### 4. Object/value alignment

Open-class values are correctly allowed; Candidate-v11 must not reintroduce closed answer-value lexicons. The useful distinction is whether the candidate directly fills the requested semantic slot and bears an asserted value, versus merely mentioning a compatible relation.

Object-slot compatibility should therefore be a proof feature, not an unrestricted relevance score.

### 5. Temporal specificity

Candidate-v10 correctly blocks temporally incompatible evidence when the query imposes an explicit temporal constraint. Under temporally unspecified profile-style queries, however, an older/historical compatible assertion can remain eligible and inherit Candidate-v2 priority.

Candidate-v11 may use temporal specificity only after eligibility. It must never use ranking to rescue evidence that Candidate-v10's hard temporal verifier rejects.

### 6. Assertion strength

This is the strongest observed failure dimension. All 15 rank-1 failures involved a relevant memory with a stronger direct assertion than the rank-1 eligible distractor, while Candidate-v10 gave no second-stage preference to that difference.

Candidate-v11 should explicitly distinguish direct predicate/value assertions from weaker assignment-like, narrative, descriptive, or ambiguous mentions, but only among already eligible candidates.

### 7. Evidence completeness

Candidate-v10's six binary checks can all be true for both the relevant evidence and its distractor. A simple count of binary checks is therefore insufficient. Candidate-v11 needs finer-grained proof quality inside the already-passing dimensions: direct subject binding, relation specificity, slot/object compatibility, directness, temporal specificity, and ambiguity.

### 8. Ranking-score pathology

Candidate-v10 implements:

1. Candidate-v2 produces an ordered candidate list.
2. Candidate-v10 certifies each candidate as supported or unsupported.
3. Unsupported candidates are removed.
4. Supported candidates retain Candidate-v2 order.

Therefore Candidate-v10 has no semantic quality ordering among supported candidates. The rank-1 distractor wins not because Candidate-v10 proves it is better evidence, but because Candidate-v2 placed it earlier and certification does not disturb that order.

This is the precise `retrieval eligibility` / `rank-1 preference` conflation Candidate-v11 must resolve.

## Research consequence

Candidate-v11 will keep Candidate-v10-style hard eligibility as Layer 1 and add an explainable deterministic Layer 2 that ranks only the eligible Candidate-v2 candidates.

The Layer-2 mechanism must satisfy four constraints:

1. no ineligible candidate can be promoted;
2. no candidate outside Candidate-v2's returned set can be injected;
3. semantic proof dimensions must be explicit and testable;
4. Candidate-v2 original order remains the final tie-breaker when semantic proof does not justify a reorder.

This motivates a lexicographic proof-ordering architecture rather than a free-form continuous relevance score.
