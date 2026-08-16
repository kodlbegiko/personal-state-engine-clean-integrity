# Candidate-v9 Preregistration

## Status

Preregistered before any Candidate-v8 protected semantic failure payload is opened. Candidate-v8 protected aggregate metrics, hashes, provenance, execution metadata, terminal report, architecture source, and evaluation methodology may be read; protected case semantics may not.

## Research question

Can a per-memory evidence-certification layer preserve Candidate-v2 answerable ranking quality while materially reducing unsupported retrieval, using fresh development, protected, confirmatory, and final surfaces with one-shot formal execution?

## Frozen invariants

1. Candidate-v2 is the sole ranker. Candidate-v9 may only certify/filter memories.
2. Every memory is certified independently; one valid memory cannot unlock another.
3. Candidate-v9 output must be an order-preserving subsequence of Candidate-v2 ranking.
4. No inference access to case IDs, gold labels, relevant IDs, answers, split names, benchmark filenames, or stage indicators.
5. Hard negative blockers remain fail-closed unless replaced by a stricter typed interpretation with equal or stronger safety.
6. Paid API cost is zero. No paid remote model may be used.
7. Candidate-v8 and retired 99-case Gate F semantic payloads remain immutable historical evidence.

## Candidate architecture family

Candidate-v9 development may compare only the preregistered architecture families in `architecture-options.md`: typed requirement graph, relation canonicalization, weighted evidence score with hard blockers, normalized claim extraction/query entailment, and hybrid dual-channel certification. Thresholds may be selected only on fresh development data and become frozen before protected materialization.

## Development protocol

Fresh development surface: exactly 360 cases, fixed before protected work: 210 answerable and 150 no-evidence/adversarial. Generator seed: `2026081509`. Bootstrap seed: `2026081510`. All development iterations are retained in `results/candidate-v9/development-ledger.jsonl` with source/config/generator/evaluator hashes, metrics, failure taxonomy, reason, and patch summary.

Development gates:

- MRR >= 0.985
- R@1 >= 0.975
- R@3 >= 0.990
- R@5 >= 0.990
- answerable recall >= 0.985
- false abstention <= 0.015
- false retrieval <= 0.025
- abstention accuracy >= 0.975
- Candidate-v2 order-preservation violations = 0
- paired bootstrap MRR non-inferiority vs Candidate-v2: 10,000 iterations, margin -0.03, 95% CI lower bound >= -0.03

## Architecture selection rule

Only development evidence plus the post-preregistration Candidate-v8 historical diagnostic may be used. A candidate architecture is eligible only if all development gates pass. Among eligible variants, minimize false retrieval first, then false abstention, then maximize MRR, then prefer lower implementation complexity. Historical failure cases may classify failure modes but may not supply case-specific phrases, names, answers, IDs, or whitelists.

## Fresh protected validation

Exactly 300 fresh cases: 190 answerable, 110 no-evidence. Dataset seed `2026081511`; paired-bootstrap seed `2026081512`. The sample size may not be increased after results are known.

Protected gates:

- MRR >= 0.96
- R@1 >= 0.95
- R@3 >= 0.97
- R@5 >= 0.97
- answerable recall >= 0.97
- false abstention <= 0.03
- false retrieval <= 0.05
- abstention accuracy >= 0.95
- order-preservation violations = 0
- paired-bootstrap MRR non-inferiority lower 95% bound >= -0.03, 10,000 iterations
- absolute false-retrieval reduction vs Candidate-v2 >= 0.80

Protected execution is one-shot after lock, materialization, commit, and explicit authorization. Any semantic FAIL terminates Candidate-v9 at `CANDIDATE_V9_PROTECTED_VALIDATION_FAIL`.

## Fresh confirmatory

Exactly 360 fresh independent cases: 220 answerable, 140 no-evidence. Dataset seed `2026081513`; paired-bootstrap seed `2026081514`. Same gates as protected. One-shot only. Any failure terminates at `CANDIDATE_V9_CONFIRMATORY_FAIL`.

## Fresh Final Gate F

Exactly 480 fresh cases: 300 answerable, 180 no-evidence. Dataset seed `2026081515`; paired-bootstrap seed `2026081516`. Candidate-v2, frozen Candidate-v8 historical baseline, and Candidate-v9 are evaluated. Primary Candidate-v9 gates: MRR >= 0.96, answerable recall >= 0.97, false abstention <= 0.03, false retrieval <= 0.05, abstention accuracy >= 0.95, zero order violations, paired-bootstrap non-inferiority lower 95% bound >= -0.03, and absolute false-retrieval reduction vs Candidate-v2 >= 0.80.

## Formal execution rule

For protected, confirmatory, and final: lock -> materialize -> commit manifest/dataset -> authorize -> execute exactly once -> commit result. No rerun to improve results. A benchmark defect invalidates the whole formal execution and requires a new explicitly versioned lineage/protocol; it does not permit editing the executed surface.

## Statistical reporting

Always report MRR, R@1/R@3/R@5, answerable recall, false abstention, abstention accuracy, false retrieval, order violations, paired bootstrap delta and 95% CI. Wilson intervals and category-level diagnostics are secondary only and cannot change the primary decision rule.

## Leakage and integrity audit

Before freeze and at every formal boundary, verify source/config/generator/evaluator identity hashes; inspect inference signatures and source for forbidden benchmark metadata access; verify Candidate-v8 terminal commit and frozen artifact hashes. Any identity mismatch fails closed before semantic execution when possible.

## Terminal states

Only: `CANDIDATE_V9_DEVELOPMENT_BLOCKED`, `CANDIDATE_V9_PROTECTED_VALIDATION_FAIL`, `CANDIDATE_V9_CONFIRMATORY_FAIL`, `CANDIDATE_V9_FINAL_GATE_F_FAIL`, or `CANDIDATE_V9_FINAL_GATE_F_PASS`.
