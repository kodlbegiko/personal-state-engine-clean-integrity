# Candidate-v11 Preregistration

Status: FROZEN BEFORE CANDIDATE-V10 INDIVIDUAL FINAL FAILURE INSPECTION

Created: 2026-08-15T19:59:00+08:00
Repository: `kodlbegiko/personal-state-engine-clean-integrity`
Parent lineage: `research/candidate-v10-fresh-lineage`
Parent terminal commit: `f909c0da144ada1268145b2f42cf26571231818e`
Candidate-v11 branch: `research/candidate-v11-fresh-lineage`

## 1. Research question

Can a semantics-first rank-refinement architecture improve Rank-1 robustness under unseen natural-language grammar-family distribution shift while preserving Candidate-v10's answerability, abstention, evidence-verification, and Candidate-v2 candidate-source safety contracts?

The target is not to repair one historical Candidate-v10 Final miss. The target is a general mechanism that distinguishes evidence eligibility from rank-1 preference when multiple Candidate-v2-returned memories are plausible.

## 2. Candidate architecture hypotheses

### A — Binary evidence certification + Candidate-v2 order

Frozen baseline representing Candidate-v10's current concept. Candidates that pass certification remain in Candidate-v2 order.

### B — Structured evidence quality ranking

After hard eligibility certification, compute a deterministic structured proof for each eligible candidate with at least:

- subject_match
- relation_match
- predicate_specificity
- object_match
- value_bearing
- temporal_match
- assertion_strength
- blocker_status
- directness
- ambiguity

Only eligible Candidate-v2-returned candidates may be reordered. Ineligible memories can never be rescued by ranking.

### C — Lexicographic semantic proof ordering

After eligibility, rank by a deterministic lexicographic proof tuple prioritizing:

1. blocker_free
2. exact subject binding
3. relation specificity
4. object compatibility
5. direct value-bearing assertion
6. temporal compatibility
7. semantic completeness
8. Candidate-v2 original rank

This hypothesis is preferred over an unconstrained continuous relevance score when equivalent performance is achievable because it exposes decision rules and reduces compensatory scoring risk.

### D — Dominance-constrained proof ranking

Use a partial-order / dominance rule among eligible candidates: a candidate may outrank another only if it is no worse on safety-critical semantic slots and strictly better on at least one predeclared preference slot. Remaining ties fall back to Candidate-v2 order. This architecture is considered only if A/B/C diagnostics show weighted or strict lexicographic ordering creates systematic false promotions.

No architecture may use historical Final case IDs, exact wording, benchmark labels, answer text, relevant IDs, stage names, grammar-family metadata, semantic-domain metadata, or generator provenance at inference time.

## 3. Immutable metrics

Primary ranking metrics:

- MRR
- R@1
- R@3
- R@5
- Eligible Rank-1 Accuracy

Safety / answerability metrics:

- answerable recall
- false abstention
- false retrieval
- abstention accuracy
- order/candidate-source invariant violations
- hard-blocker violations
- metadata-firewall violations
- determinism violations

Comparison metrics:

- paired Candidate-v11 minus frozen Candidate-v10 R@1 on the same fresh Candidate-v11 evaluation surface
- paired Candidate-v11 minus Candidate-v2 R@1 on the same fresh surface where methodologically valid

## 4. Immutable evaluation thresholds

### Development

- MRR >= 0.98
- R@1 >= 0.97
- R@3 >= 0.99
- R@5 >= 0.995
- answerable recall >= 0.99
- false abstention <= 0.01
- false retrieval <= 0.05
- abstention accuracy >= 0.95
- Eligible Rank-1 Accuracy >= 0.97
- safety invariants = PASS
- metadata firewall = PASS
- determinism = PASS

### Protected

- MRR >= 0.97
- R@1 >= 0.96
- R@3 >= 0.99
- R@5 >= 0.995
- answerable recall >= 0.99
- false abstention <= 0.01
- false retrieval <= 0.05
- abstention accuracy >= 0.95
- safety invariants = PASS
- Candidate-v11 R@1 must not be statistically materially inferior to frozen Candidate-v10 on the same fresh surface

### Confirmatory

- MRR >= 0.97
- R@1 >= 0.96
- R@3 >= 0.99
- R@5 >= 0.995
- answerable recall >= 0.99
- false abstention <= 0.01
- false retrieval <= 0.05
- abstention accuracy >= 0.95
- integrity = PASS

### Final Gate F

- MRR >= 0.97
- R@1 >= 0.96
- R@3 >= 0.99
- R@5 >= 0.995
- answerable recall >= 0.99
- false abstention <= 0.01
- false retrieval <= 0.05
- abstention accuracy >= 0.95
- integrity = PASS

Thresholds may not be lowered after this preregistration.

## 5. Formal execution counts

Candidate-v11 formal execution maxima:

- Protected: exactly one execution
- Confirmatory: at most one execution, only after Protected PASS
- Final: at most one execution, only after Confirmatory PASS

Initial Candidate-v11 counts are:

```json
{"protected": 0, "confirmatory": 0, "final": 0}
```

Any algorithmic formal-stage failure is terminal for Candidate-v11. No rerun is permitted.

## 6. Benchmark sizes

- Development: 600 total = 360 answerable + 240 no-evidence
- Protected: 420 total = 260 answerable + 160 no-evidence
- Confirmatory: 480 total = 300 answerable + 180 no-evidence
- Final: 600 total = 360 answerable + 240 no-evidence

## 7. Benchmark and bootstrap seeds

Seeds are frozen before any individual Candidate-v10 Final failure payload is inspected:

- Development generation seed: `11021`
- Protected generation seed: `22027`
- Confirmatory generation seed: `33037`
- Final generation seed: `44041`
- Paired bootstrap seed: `55109`
- Bootstrap iterations: `10000`

No formal-stage seed replacement is permitted after a stage is materialized or executed.

## 8. Stage grammar-family separation policy

Family names are identifiers only; construction mechanisms must be structurally disjoint.

- Development: L, M, N, O
- Protected: P, Q
- Confirmatory: R, S, T
- Final: U, V, W, X

The generator must implement materially different syntax/discourse mechanisms across stages, not synonym substitution. Mechanisms may include wh-fronting, possessive nominalization, clefts, passive constructions, appositives, record-oriented phrasing, elliptical questions, prepositional framing, descriptive predicates, relative clauses, indirect relational statements, discourse-context forms, and multi-clause competition.

Hard freshness requirements across every stage pair:

- exact case overlap = 0
- normalized case overlap = 0
- grammar-family overlap = 0
- template provenance overlap = 0

Skeleton overlap must be measured and reported. High structural overlap requires a documented pre-freeze methodology review.

## 9. Statistical testing method

All formal summaries must use deterministic metric computation.

Primary paired comparison:

- frozen Candidate-v10 algorithm versus frozen Candidate-v11 algorithm
- both evaluated on the exact same fresh Candidate-v11 stage surface
- primary statistic: paired difference in answerable-case R@1
- nonparametric paired bootstrap with 10,000 iterations
- bootstrap seed 55109
- 95% percentile confidence interval

Safety metrics are evaluated against the immutable absolute thresholds above. Where a noninferiority statement is reported, its margin must be declared in the evaluator/config before Development freeze and may not be changed during formal evaluation.

Historical Candidate-v10 Final is not a comparison surface for Candidate-v11 tuning or formal testing.

## 10. Freeze rules

Development may iterate on:

- Candidate-v11 implementation
- Candidate-v11 tests
- Candidate-v11 development generator
- Candidate-v11 architecture
- development-only diagnostics

Protected, Confirmatory, and Final payloads must remain unread/unmaterialized during Development.

After Development PASS, a freeze manifest must hash at minimum:

- `src/personal_state_engine/candidate_v11.py`
- Candidate-v11 benchmark generator
- Candidate-v11 evaluator
- freshness audit
- formal runner
- config
- Candidate-v11 tests
- this preregistration
- architecture decision record

After freeze, none of those components may change. Protected -> Confirmatory -> Final must run without human or code modification between gates.

## 11. Formal stopping rules

Stop Candidate-v11 immediately on:

1. Protected algorithmic FAIL -> `CANDIDATE_V11_PROTECTED_FAIL`
2. Confirmatory algorithmic FAIL -> `CANDIDATE_V11_CONFIRMATORY_FAIL`
3. Final algorithmic FAIL -> `CANDIDATE_V11_FINAL_GATE_F_FAIL`
4. Any integrity violation -> `CANDIDATE_V11_RESEARCH_INTEGRITY_FAILURE`
5. Objectively verified non-algorithmic infrastructure blocker -> `CANDIDATE_V11_INFRASTRUCTURE_BLOCKED`
6. Final PASS -> `CANDIDATE_V11_FINAL_GATE_F_PASS`

Infrastructure failure may not be used to relabel an algorithmic failure.

## 12. Terminal-state definitions

### `CANDIDATE_V11_FINAL_GATE_F_PASS`

All prerequisite gates passed, Final executed exactly once, all Final thresholds and integrity checks passed, and immutable evidence was recorded.

### `CANDIDATE_V11_PROTECTED_FAIL`

Protected executed exactly once and failed an algorithmic or threshold requirement.

### `CANDIDATE_V11_CONFIRMATORY_FAIL`

Protected passed; Confirmatory executed exactly once and failed an algorithmic or threshold requirement.

### `CANDIDATE_V11_FINAL_GATE_F_FAIL`

Protected and Confirmatory passed; Final executed exactly once and failed an algorithmic or threshold requirement.

### `CANDIDATE_V11_RESEARCH_INTEGRITY_FAILURE`

Any forbidden historical mutation, post-hoc formal tuning, hidden-label use, benchmark metadata leakage, forbidden rerun, formal seed replacement, exact historical-case copying, or equivalent integrity breach.

### `CANDIDATE_V11_INFRASTRUCTURE_BLOCKED`

Only an objectively documented external/tooling failure that prevents valid execution without revealing a formal-stage payload or producing an interpretable algorithmic result.

## 13. Candidate-v10 historical data usage policy

Before this preregistration commit, only the mission-supplied aggregate Candidate-v10 Final metrics, formal execution counts, terminal state, branch/commit provenance, file identities/hashes, and historical immutability status may be used.

After this preregistration is committed, Candidate-v10 individual Final failures may be inspected only for structured diagnostic taxonomy and architecture motivation.

Historical Final cases may never become Candidate-v11 training/development/evaluation cases.

The frozen Candidate-v10 algorithm may be evaluated on fresh Candidate-v11 surfaces for paired comparison. Candidate-v10 Final itself may never be rerun.

## 14. Prohibition against copying historical Final cases into tests

Forbidden:

- exact historical query strings
- exact historical memory text
- exact entity names
- exact answer values
- historical case IDs
- relevant-memory IDs
- regexes or exceptions targeting historical wording
- hardcoded I/J/K grammar-family identifiers

Regression fixtures motivated by historical failures must be newly synthesized, lexically and structurally different, and labeled `abstracted historical regression`.

## 15. Anti-overfitting policy

Development changes must target failure classes, not individual cases.

Every development iteration must preserve:

- prior failed-run evidence
- a structured failure taxonomy
- a stated root cause
- a general architecture or rule change
- an abstract regression test
- a new development result

Forbidden responses to Development failure:

- deleting hard cases
- editing benchmark answers
- lowering thresholds
- replacing failing development cases with easier cases
- case-specific exception tables
- hidden metadata usage

No Protected/Confirmatory/Final payload may be used to modify Candidate-v11. A formal algorithmic failure ends the lineage.

## 16. Inference metadata firewall

Candidate-v11 inference must not read, branch on, score, log-derived-rank with, or otherwise use:

- `relevant_memory_ids`
- gold labels
- answer text
- benchmark split/stage
- grammar-family tag
- semantic-domain metadata
- generator/template provenance
- designation
- case IDs
- hidden evaluation metadata

Candidate-v11 may consume only runtime query text and the Candidate-v2 returned candidate records/fields that are legitimately part of the production-style retrieval interface.

Firewall tests must mutate forbidden metadata while keeping legitimate runtime input constant; outputs must be byte-for-byte identical.

## Historical immutability and candidate-source contract

Candidate-v7/v8/v9/v10 implementations, benchmarks, formal results, terminal reports, ledgers, and terminal branches are immutable.

Candidate-v2 remains the candidate source. Candidate-v11 may reorder only eligible memories already returned by Candidate-v2. It may not inject a memory outside that candidate set or modify Candidate-v2.

A permutation/subsequence invariant must prove:

- Candidate-v11 output candidates are a subset of Candidate-v2 returned candidates
- hard-ineligible candidates never appear in returned evidence
- no external or benchmark-only memory is injected
- any reordering is confined to eligible Candidate-v2 candidates

## Cost policy

Target monetary cost: `monetary_cost_usd = 0`.

No paid model or commercial reranker API is authorized. The mission must use deterministic local code and GitHub Actions capabilities already available to the repository.
