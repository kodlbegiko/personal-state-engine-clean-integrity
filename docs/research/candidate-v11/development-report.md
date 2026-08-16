# Candidate-v11 Development Report

## Scope

This report records all Candidate-v11 Development iterations before freeze. No Protected, Confirmatory, or Final payload had been generated or inspected during these iterations.

## Iteration 1 — FAIL: negative-surface construction defect

Surface: `candidate-v11-development-v1`

Candidate-v11 ranking metrics were perfect on answerable cases, but safety failed:

- MRR = 1.0
- R@1 = 1.0
- answerable recall = 1.0
- false abstention = 0.0
- false retrieval = 0.0875
- abstention accuracy = 0.9125

Structured taxonomy found 21 / 240 supposed no-evidence cases returned evidence. The root cause was not Candidate-v11 ranking: the Development generator's wrong-relation offset could wrap around the domain list and accidentally select the original semantic domain. Those 21 cases therefore contained an actually valid direct subject/relation/value assertion despite being labelled no-evidence.

Action: preserve all iteration-1 artifacts; do not change thresholds; correct only the Development generator's negative-domain construction.

## Iteration 2 — PASS but methodologically under-discriminative

Surface: `candidate-v11-development-v2`

The corrected negative generator eliminated the data-quality defect:

- Candidate-v11 MRR = 1.0
- Candidate-v11 R@1 = 1.0
- answerable recall = 1.0
- false abstention = 0.0
- false retrieval = 0.0
- abstention accuracy = 1.0
- Eligible Rank-1 Accuracy = 1.0
- metadata firewall = PASS
- determinism = PASS
- Candidate-v2 source invariant violations = 0

However frozen Candidate-v10 also achieved R@1 = 1.0. The paired R@1 delta was 0 with CI [0, 0]. Thus the surface verified safety but could not meaningfully test the Candidate-v11 research hypothesis.

Action: preserve iteration 2; perform a Development-only methodological stress revision before freeze.

## Iteration 3 — numerical PASS, stress adequacy FAIL

Surface: `candidate-v11-development-v3`

An eligible-looking competitor was added, but Candidate-v10 remained R@1 = 1.0 and Candidate-v11 remained R@1 = 1.0. The proposed competitor did not create sufficient Candidate-v2 ordering pressure.

Action: preserve iteration 3; strengthen only the fresh Development stress construction.

## Iteration 4 — numerical PASS, stressor eligibility design FAIL

Surface: `candidate-v11-development-v4`

Candidate-v2 R@1 dropped to 0.25, showing strong lexical/recency pressure, but Candidate-v10 remained R@1 = 1.0. Diagnosis showed the competitor used a semicolon that split subject binding and the relation/value assignment into separate certification clauses. Candidate-v10 therefore filtered the competitor at Layer 1 rather than exposing its lack of Layer-2 priority.

Action: preserve iteration 4; add an explicit stressor-validity audit and construct the competitor in one bounded clause.

## Iteration 5 — PASS and accepted Development freeze surface

Surface: `candidate-v11-development-v5`

The Development stressor was independently checked before the final gate assertion:

- answerable cases = 360
- eligible competitor count = 360 / 360
- eligible competitor rate = 1.0
- Candidate-v2 competitor rank-1 count = 270 / 360
- Candidate-v2 competitor rank-1 pressure rate = 0.75
- stressor validity = PASS

### Candidate-v11

- MRR = 1.0
- R@1 = 1.0
- R@3 = 1.0
- R@5 = 1.0
- answerable recall = 1.0
- false abstention = 0.0
- false retrieval = 0.0
- abstention accuracy = 1.0
- Eligible Rank-1 Accuracy = 1.0
- Candidate-v2 source invariant violations = 0
- metadata firewall = PASS
- determinism (100 repeated executions) = PASS

### Frozen Candidate-v10 on the same fresh surface

- MRR = 0.625
- R@1 = 0.25
- R@3 = 1.0
- R@5 = 1.0
- answerable recall = 1.0
- false abstention = 0.0
- false retrieval = 0.0
- abstention accuracy = 1.0

### Paired statistical comparison

Candidate-v11 minus Candidate-v10 R@1:

- delta = +0.75
- bootstrap iterations = 10,000
- bootstrap seed = 55109
- 95% CI = [0.7055555555555556, 0.7944444444444444]
- preregistered noninferiority = PASS
- strict improvement observed = true

Iteration 5 passes every preregistered Development threshold and supplies an actual test of the post-eligibility ranking hypothesis. It is therefore selected as the Development freeze evidence surface.

## Architecture comparison on Development-v5

Four architectures were compared while preserving the same Layer-1 evidence safety surface:

| Architecture | MRR | R@1 | R@3 | Recall | False retrieval |
|---|---:|---:|---:|---:|---:|
| A — Candidate-v10 binary certification + Candidate-v2 order | 0.625 | 0.25 | 1.0 | 1.0 | 0.0 |
| B — structured weighted quality ranking | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 |
| C — lexicographic semantic proof ordering | 1.0 | 1.0 | 1.0 | 1.0 | 0.0 |
| D — Pareto dominance + Candidate-v2 fallback | 0.625 | 0.25 | 1.0 | 1.0 | 0.0 |

### Selection

Architecture C remains selected.

Architecture B demonstrates that structured semantic quality is sufficient to repair the rank-1 pathology, but its weighted score is compensatory and exposes unnecessary tuning degrees of freedom. Architecture D is too conservative: when candidates are incomparable it falls back to Candidate-v2 ordering and recreates the failure. Architecture C matches B's Development ranking performance while remaining deterministic, non-compensatory, explainable, and lower-dimensional.

## Freeze readiness

Candidate-v11 is ready for Development freeze provided the freeze process:

1. reruns the Candidate-v11 unit/invariant suite;
2. verifies Development-v5, stressor-validity, freshness, and architecture-comparison artifacts;
3. hashes all implementation, generator dependencies, evaluator, audit, formal runner, config, tests, preregistration, architecture decision, and formal workflow components;
4. initializes formal execution counts to 0 / 0 / 0;
5. confirms no formal-stage benchmark payload exists before the one-shot formal mission begins.

No threshold, seed, historical Final benchmark, or Candidate-v10 implementation has been changed.
