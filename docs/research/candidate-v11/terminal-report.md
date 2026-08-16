# Candidate-v11 Terminal Report

## Provenance

- Candidate-v10 terminal commit: `f909c0da144ada1268145b2f42cf26571231818e`
- Candidate-v11 branch root / parent terminal commit: `f909c0da144ada1268145b2f42cf26571231818e`
- Candidate-v11 preregistration commit: `bf6c0d2b1435a9af868f1c6c3faf8f2853a5078b`
- Candidate-v11 freeze commit: `f75c2b249d74a5b63734a71bad9a1ca43a499b37`
- Candidate-v11 terminal evidence commit: `343586a5841b48733874a88043dc559244c82643`

## Historical diagnosis

Candidate-v10 Final rank-1 failure cases diagnosed: **15**.

Root-cause counts:

- `assertion_directness_underweighted_after_eligibility`: 15
- `lexical_overlap_priority_over_semantic_proof_quality`: 2
- `multiple_certification_compatible_relation_candidates`: 15

The central pathology was post-eligibility ordering: multiple memories could pass binary evidence certification while Candidate-v10 preserved Candidate-v2 order rather than preferring the more direct and complete semantic proof.

## Architecture

Alternatives evaluated on the accepted fresh Development-v5 surface:

- `A_binary_certification_plus_candidate_v2_order` — MRR=0.625000, R@1=0.250000, R@3=1.000000, false retrieval=0.000000.
- `B_structured_weighted_quality_ranking` — MRR=1.000000, R@1=1.000000, R@3=1.000000, false retrieval=0.000000.
- `C_lexicographic_semantic_proof_ordering` — MRR=1.000000, R@1=1.000000, R@3=1.000000, false retrieval=0.000000.
- `D_pareto_dominance_plus_candidate_v2_tiebreak` — MRR=0.625000, R@1=0.250000, R@3=1.000000, false retrieval=0.000000.

Selected design: **Architecture C — lexicographic semantic proof ordering after hard evidence eligibility**. It matched the weighted alternative's Development rank performance without a compensatory score or weight-tuning surface, while the pure dominance alternative remained too conservative and fell back to Candidate-v2 ordering.

Safety invariants: blocked evidence never enters Layer 2; Candidate-v11 may reorder only eligible Candidate-v2-returned candidates; no outside memory may be injected; metadata-only evaluation fields are removed at the inference boundary.

## Development

### Iteration 1 — FAIL — generator negative-surface defect; evidence preserved

Candidate-v11: MRR=1.000000, R@1=1.000000, R@3=1.000000, R@5=1.000000, recall=1.000000, false_abstention=0.000000, false_retrieval=0.087500, abstention_accuracy=0.912500.
Frozen Candidate-v10 on same surface: MRR=1.000000, R@1=1.000000, R@3=1.000000, R@5=1.000000, recall=1.000000, false_abstention=0.000000, false_retrieval=0.087500, abstention_accuracy=0.912500.
Benchmark SHA256: `2ad455c343d2df8cd741e30784f92d853aec9a6e42244899cf6315e0704e74a2`.

### Iteration 2 — PASS — safety-valid but under-discriminative

Candidate-v11: MRR=1.000000, R@1=1.000000, R@3=1.000000, R@5=1.000000, recall=1.000000, false_abstention=0.000000, false_retrieval=0.000000, abstention_accuracy=1.000000.
Frozen Candidate-v10 on same surface: MRR=1.000000, R@1=1.000000, R@3=1.000000, R@5=1.000000, recall=1.000000, false_abstention=0.000000, false_retrieval=0.000000, abstention_accuracy=1.000000.
Benchmark SHA256: `97aa090ab58be9d5122579b9a4d2c9ab86f3c443cdba51606c5b614506ad615d`.

### Iteration 3 — PASS metrics — stress adequacy failed

Candidate-v11: MRR=1.000000, R@1=1.000000, R@3=1.000000, R@5=1.000000, recall=1.000000, false_abstention=0.000000, false_retrieval=0.000000, abstention_accuracy=1.000000.
Frozen Candidate-v10 on same surface: MRR=1.000000, R@1=1.000000, R@3=1.000000, R@5=1.000000, recall=1.000000, false_abstention=0.000000, false_retrieval=0.000000, abstention_accuracy=1.000000.
Benchmark SHA256: `1ea4e47d415585eed27d768b003f9efb062cc45a013de07751b957b503726c31`.

### Iteration 4 — PASS metrics — stressor was not Layer-1 eligible

Candidate-v11: MRR=1.000000, R@1=1.000000, R@3=1.000000, R@5=1.000000, recall=1.000000, false_abstention=0.000000, false_retrieval=0.000000, abstention_accuracy=1.000000.
Frozen Candidate-v10 on same surface: MRR=1.000000, R@1=1.000000, R@3=1.000000, R@5=1.000000, recall=1.000000, false_abstention=0.000000, false_retrieval=0.000000, abstention_accuracy=1.000000.
Benchmark SHA256: `1a4d13320e789af482502f6b76153e04464349d352a63e99d5412840782dcfea`.

### Iteration 5 — PASS — accepted Development freeze surface

Candidate-v11: MRR=1.000000, R@1=1.000000, R@3=1.000000, R@5=1.000000, recall=1.000000, false_abstention=0.000000, false_retrieval=0.000000, abstention_accuracy=1.000000.
Frozen Candidate-v10 on same surface: MRR=0.625000, R@1=0.250000, R@3=1.000000, R@5=1.000000, recall=1.000000, false_abstention=0.000000, false_retrieval=0.000000, abstention_accuracy=1.000000.
Benchmark SHA256: `441f202807bb80d6606f81278e0908ac7c064e502794d06ea8387d8690902435`.

## Formal

### Protected — FAIL

- Execution count: 1
- Benchmark SHA256: `f3b2b5cfbfe855b878960cd1c2f556d5868c175b93e9aed0d02ba02d7eb68434`
- Candidate-v11: MRR=0.000000, R@1=0.000000, R@3=0.000000, R@5=0.000000, recall=0.000000, false_abstention=1.000000, false_retrieval=0.000000, abstention_accuracy=1.000000
- Candidate-v10: MRR=0.000000, R@1=0.000000, R@3=0.000000, R@5=0.000000, recall=0.000000, false_abstention=1.000000, false_retrieval=0.000000, abstention_accuracy=1.000000
- Paired R@1 delta v11-v10: 0.000000; 95% CI [0.000000, 0.000000]; 10,000 bootstrap iterations; seed 55109
- Metadata firewall: PASS
- Determinism: PASS
- Candidate-v2 source invariant violations: 0

### Confirmatory — NOT EXECUTED

### Final — NOT EXECUTED

## Integrity

- Frozen-hash verification: PASS — freeze verifier completed before formal runner
- Formal execution counts: Protected=1, Confirmatory=0, Final=0
- Cross-stage freshness: required before every formal execution; hard overlap violations terminate as research-integrity failure.
- Metadata firewall: evaluated on every executed stage.
- Historical candidates: no write path in Candidate-v11 workflows targets v7/v8/v9/v10 branches or historical result files.
- Candidate-v10 Final: not rerun.
- Paid APIs: none; monetary cost recorded as USD 0.
- Formal reruns: prohibited; execution ledger records at most one STARTED/COMPLETED pair per stage.

## Verdict

`CANDIDATE_V11_PROTECTED_FAIL`

This report declares only the terminal state produced by the one-shot frozen formal mission. No post-formal tuning is permitted for Candidate-v11.

## Infrastructure recovery

The freeze boundary itself completed successfully, but its GITHUB_TOKEN-authenticated push did not recursively trigger the frozen push-triggered formal workflow. A post-freeze infrastructure-only launcher was therefore used. It changed no frozen component, threshold, seed, benchmark generator, evaluator, test, or algorithm; it first re-verified the freeze hashes and zero formal counts, then invoked the already frozen `scripts/run_candidate_v11_formal.py` exactly once.
