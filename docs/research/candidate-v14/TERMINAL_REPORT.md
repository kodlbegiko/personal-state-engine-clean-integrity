# Candidate-v14 Terminal Report

## Terminal state

`CANDIDATE_V14_INTERNAL_QUALIFIED`

## Historical integrity

- Candidate-v13 remained unchanged from the v4 terminal lineage; its expected SHA-256 remains `b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838`.
- External Validity v4 terminal commit remains `df5986f4a45adadfc04055b3b8c6f38b2704d134`.
- The base-to-freeze Git comparison contains only Candidate-v14 additions; no v13 or v4 historical file is modified.
- Candidate-v14 protected-data firewall: PASS.
- v4 protected case-level payload used: NO.
- v4 protected assignment reconstruction: NO.

## Candidate-v14 architecture

Selected architecture: **B — Two-Stage Retrieve → Verify**.

Candidate SHA-256: `f2e28fd11edb65fb1bca94a919b3c0b479221d010bd1a1d33dae40004e564e44`.

Major changes relative to the v13 failure model:

1. ranking occurs before abstention, preserving retrieval opportunity;
2. evidence verification is a second stage rather than a pre-ranking hard gate;
3. scoring combines lexical, deterministic semantic concepts, entity/relation signals, proposition binding, temporal recency, contradiction/uncertainty penalties, and top-candidate competition;
4. no external model dependency is added; execution remains deterministic and offline.

## Development comparison

The frozen Candidate-v13 historical development-safe benchmark had already scored 1.00 on MRR, R@1/R@3/R@5, answerable recall, eligible rank-1 accuracy, and abstention accuracy, with zero false abstention/retrieval. This is explicitly not external evidence.

Candidate-v14 Architecture B likewise achieved 1.00 on all principal development-safe ranking/retrieval metrics, 1.00 abstention accuracy, and zero false abstention/retrieval across 1,152 architecture-development/internal-validation/adversarial-validation cases. Architectures A, C, and D each failed at least one preregistered development/anti-collapse gate.

## Freeze and one-shot internal holdout

Freeze commit: `232030e67022e492991edb3e2c89ed96eef0c20a`.

The freeze commit changed only `results/candidate-v14/candidate-v14-freeze.json` relative to its parent. The one-shot workflow verified frozen Candidate/evaluator/policy/preregistration hashes and the preregistered holdout digest before execution.

Internal holdout run: `31932765495`.

- case count: 384
- MRR: 1.00
- R@1: 1.00
- R@3: 1.00
- R@5: 1.00
- answerable recall: 1.00
- eligible rank-1 accuracy: 1.00
- abstention accuracy: 1.00
- false abstention: 0.00
- false retrieval: 0.00
- family gates: PASS
- domain gates: PASS
- anti-collapse: PASS
- invocation count: 1
- rerun count: 0

## Integrity decision

Research integrity: **PASS**.

The internal-holdout workflow has exactly one run and one attempt. No Candidate-v14 source, evaluator, threshold policy, benchmark generator, or holdout selection was changed after freeze/holdout. Post-holdout repository changes in the terminal evidence commit are restricted to evidence/report artifacts.

## Scientific conclusion

Candidate-v14 passed internal qualification and is authorized for a future independent fresh external-validity evaluation. External validity has NOT yet been established.
