# Candidate-v11 Development Methodology Review

## Status

Development iteration 2 passed every preregistered numerical and safety threshold. It is **not yet designated the final Development freeze surface** because the paired baseline saturated at Candidate-v10 R@1 = 1.0.

This review occurs before any Protected, Confirmatory, or Final payload has been generated or inspected.

## Why another Development-only iteration is justified

Candidate-v11's research question is specifically whether post-eligibility semantic priority improves rank-1 robustness when multiple memories are certification-compatible.

Iteration 2 established important safety facts:

- Candidate-v11 R@1 = 1.0;
- answerable recall = 1.0;
- false abstention = 0;
- false retrieval = 0;
- abstention accuracy = 1.0;
- metadata firewall = PASS;
- determinism = PASS;
- Candidate-v2 candidate-source invariant = PASS.

However, frozen Candidate-v10 also achieved R@1 = 1.0 on the same surface. Therefore the answerable competition did not sufficiently pressure the exact architectural difference under study. Candidate-v2 itself had materially lower R@1, showing the surface contained lexical distractors, but Candidate-v10's binary filtering removed the decisive distractors before ranking among eligible memories.

A surface on which both Candidate-v10 and Candidate-v11 saturate cannot meaningfully falsify or support the Layer-2 rank-refinement hypothesis.

## Development iteration 3 design change

Iteration 3 changes **only the fresh Development generator**, which remains mutable before freeze.

The answerable cases will include a deliberately certification-compatible competing memory with:

- the same subject;
- the same requested relation;
- an open value;
- no hard blocker;
- a terse assignment form with high lexical alignment;
- a newer timestamp than the relevant evidence;
- weaker semantic directness / slot proof than the relevant evidence.

This is not a historical-case reproduction. Entities, values, wording, and grammar mechanisms remain newly synthesized. The stress pattern is an abstract architectural probe: two eligible candidates, one lexically/recency-favored and one semantically stronger.

No threshold is changed. No Candidate-v10 historical Final case is copied. No formal surface is generated. Iterations 1 and 2 remain immutable evidence.

## Acceptance criterion

Iteration 3 must still satisfy all preregistered Development thresholds and safety invariants. In addition, for methodological adequacy the paired fresh-surface comparison should show a positive Candidate-v11 minus Candidate-v10 R@1 delta. This additional observation is not used to weaken or replace any preregistered gate; it is a reason to prefer iteration 3 as the freeze surface if the original gates also pass.
