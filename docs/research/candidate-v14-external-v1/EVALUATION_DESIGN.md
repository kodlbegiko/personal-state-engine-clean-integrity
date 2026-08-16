# Evaluation Design

## Objective

Test frozen Candidate-v14 on a fresh heterogeneous personal-memory retrieval distribution that is independent of Candidate-v14 development, internal holdout, and historical EV-v4 case payloads.

## Scale

Target corpus: 1,600 cases.

- Answerable: 1,120 (70%)
- No-evidence / abstention: 480 (30%)
- Counterfactual: 120 pairs / 240 members
- Metamorphic: 100 groups / 400 members, including 300 derived cases
- Domains: 10, at least 160 cases per domain by round-robin allocation
- Naturalistic/conversational generation: at least 60%

## Required dimensions

Natural linguistic variation; lexical divergence; strong lexical lures; temporal conflict; negation/polarity; compositional retrieval; no-evidence; answerable-but-difficult weak-lexical support; distractor density; domain transfer; entity ambiguity; discourse contamination; counterfactual pairs; metamorphic invariance.

## Distractor density

- low: 4–8 memories
- medium: 9–20
- high: 21–50
- extreme: 51–70 on a small stress subset

## Domains

education, health-routines, travel, shopping, technology, work-projects, food, social-context, finance, household.

## Scoring contract

Answerable cases are correct when Candidate-v14 returns `SUPPORTED` and the top-ranked memory is relevant. For compositional cases marked `requires_all`, all required evidence IDs must appear in the returned top-k for family correctness. No-evidence cases are correct only when Candidate-v14 returns `INSUFFICIENT` with no ranking.

MRR/R@k are computed against frozen relevant IDs. Abstention metrics are computed only from frozen answerability labels. Counterfactual exact-pair consistency requires both members correct and the prediction to change when the frozen semantic truth changes. Metamorphic invariance requires equivalent transformed cases to keep the same verdict and top-ranked memory ID when semantics are unchanged.

No case-level error review is permitted before terminal decision.
