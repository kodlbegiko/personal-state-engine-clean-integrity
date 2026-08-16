# Candidate-v12 Formal Integrity Terminal Decision

## Decision type

This document is intentionally named to satisfy the formal-mission terminal-decision artifact requirement, but **no Candidate-v12 Protected evaluation was executed**.

The invalidity arose during formal-protocol recovery, before Protected materialization and before formal freeze.

## Terminal status

Operational status required by the recovered mission:

`CANDIDATE_V12_PROTECTED_INVALID — EVALUATION_INTEGRITY_FAILURE`

Corresponding status in the already-frozen Candidate-v12 preregistration terminal vocabulary:

`CANDIDATE_V12_RESEARCH_INTEGRITY_FAILURE`

This is not:

- `CANDIDATE_V12_PROTECTED_FAIL`
- a Protected algorithmic result
- a near-pass or provisional result
- an authorization to rerun or rebuild Candidate-v12 formal evaluation

## Cause

The pre-Development Candidate-v12 preregistration commit `afe9d358a337c2dd1a47710aa2212ed5ae672288` froze:

- Protected size: `480 = 300 answerable + 180 no-evidence`
- Protected seed: `24043`
- Protected MRR threshold: `>= 0.97`
- Protected R@1 threshold: `>= 0.96`
- formal paired-bootstrap/noninferiority requirements
- formal-stage separation and one-shot rules

It also states that threshold tightening is permitted only before Development materialization via a new preregistration lineage.

After Candidate-v12 Development had already been materialized and passed, the recovered mission supplied incompatible formal requirements, including:

- Protected size `>= 600`
- MRR `>= 0.98`
- R@1 `>= 0.97`
- additional Protected structural-floor requirements

Applying those values to Candidate-v12 would be a post-Development formal-protocol mutation. Ignoring them would violate the recovered mission. The conflict cannot be repaired without invalidating preregistration integrity.

## Execution evidence

At termination:

```text
protected_execution_count = 0
confirmatory_execution_count = 0
final_execution_count = 0
```

Candidate-v12 Protected:

- dataset materialized: `NO`
- individual cases inspected: `NO`
- inference executed: `NO`
- metrics computed: `NO`
- execution ledger incremented: `NO`
- formal freeze completed: `NO`

Therefore there are deliberately no Protected MRR/R@k, answerability, frame, bootstrap, or safety-result values to report.

## Preserved evidence

- Candidate-v11 terminal state remains `CANDIDATE_V11_PROTECTED_FAIL`.
- Candidate-v12 Development remains a historical Development PASS; it is not reinterpreted as a formal PASS.
- Candidate-v12 Development results and architecture decision are not modified.
- Existing preregistration and provenance are not overwritten.
- No formal payload was used for tuning.

## Research-integrity consequence

Candidate-v12 must not proceed to Protected, Confirmatory, or Final under either an invented compromise protocol or the newly introduced post-Development formal rules.

If the stricter recovered mission design is desired, the legal research continuation is a fresh lineage whose complete formal protocol is preregistered before Development materialization. Candidate-v12 is not eligible for retrofit or formal rerun.
