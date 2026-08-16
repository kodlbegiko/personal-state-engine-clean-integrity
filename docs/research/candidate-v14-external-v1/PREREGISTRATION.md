# Preregistration

All thresholds below are frozen before protected inference.

## Primary gates

- MRR >= 0.82
- R@1 >= 0.76
- R@3 >= 0.88
- R@5 >= 0.92
- Answerable Recall >= 0.90
- Eligible Rank-1 Accuracy >= 0.78
- Abstention Accuracy >= 0.88
- False Abstention Rate <= 0.10
- False Retrieval Rate <= 0.10

## Critical family gate

Every critical family accuracy >= 0.70:

weak lexical / correct semantic; strong lexical / wrong semantic; temporal supersession; negation; subject ambiguity; relation ambiguity; no evidence; discourse contamination; compositional; counterfactual.

## Domain gate

For every domain: R@1 >= 0.60; Answerable Recall >= 0.78; False Retrieval <= 0.20.

## Counterfactual / metamorphic

- counterfactual exact-pair consistency >= 0.85
- metamorphic invariance consistency >= 0.95

## Anti-collapse

Formal audit must reject always-abstain, always-retrieve, single-memory-position, single-domain, single-relation, or single-class collapse. Corpus retrieve rate must satisfy 0.10 < retrieve_rate < 0.90 and be materially consistent with frozen answerable prevalence.

## Uncertainty

Bootstrap 95% confidence intervals use 2,000 resamples with fixed scorer seed 20260816 for R@1, Answerable Recall, False Abstention Rate, and False Retrieval Rate.

## One-shot

`maximum_invocations = 1`, `reruns_permitted = 0`. A performance failure is a FAIL, never an infrastructure INVALID.
