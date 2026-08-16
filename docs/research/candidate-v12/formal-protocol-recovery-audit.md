# Candidate-v12 Formal Protocol Recovery Audit

## Audit status

`FORMAL_PROTOCOL_RECOVERY_INVALID — PREREGISTRATION_CONFLICT`

This audit was performed before any Candidate-v12 Protected dataset materialization or Protected inference execution.

## Repository provenance

- Repository: `kodlbegiko/personal-state-engine-clean-integrity`
- Branch: `research/candidate-v12-fresh-lineage`
- Pre-formal boundary HEAD verified at audit start: `963bdcc9ad23a60c5e6d594fb9b48217ab3577a4`
- Candidate-v11 terminal provenance anchor: `8faf4965fdf99eae0c154de012939eb33295cbab`
- Candidate-v11 historical terminal state preserved: `CANDIDATE_V11_PROTECTED_FAIL`
- Candidate-v12 preregistration commit: `afe9d358a337c2dd1a47710aa2212ed5ae672288`
- Candidate-v12 preregistration SHA256 from frozen provenance: `f1aed776117058ff212346225654cc6dcf81fb45265bf0571cbbd00cc56384c6`
- Candidate-v12 preregistration frozen UTC: `2026-08-15T13:46:51Z`
- Candidate-v12 implementation Git blob SHA at audit: `87f1664d415113354d9e80cc051447137ad0a7de`
- Candidate-v12 Development benchmark Git blob SHA: `0f5fb778c98ade322463421fd1e6081624a464af`
- Candidate-v12 Development result Git blob SHA: `94e9580052eaa5a8ad80a0407220505162988559`

The GitHub connector exposes the repository Git-object SHA for the large Development benchmark/result objects. Their SHA256 values were not recomputed in this audit because the fatal protocol conflict below occurs before formal freeze and before any Protected materialization; no missing SHA256 was substituted or invented. The preregistration SHA256 is taken from the already-frozen provenance record.

## Development evidence and formal ledger

The existing Candidate-v12 Development result records:

- architecture selected: `C_structured_semantic_frame`
- Development acceptance: `PASS`
- case count: `720`
- answerable: `432`
- no-evidence: `288`
- MRR / R@1 / R@3 / R@5: `1.0 / 1.0 / 1.0 / 1.0`
- false abstention: `0.0`
- false retrieval: `0.0`
- metadata firewall: `PASS`
- Candidate-v2 source invariant: `PASS`
- determinism: `PASS`

Formal execution ledger at audit start:

- Protected: `0`
- Confirmatory: `0`
- Final: `0`

No Candidate-v12 formal execution has occurred.

## Historical governance precedent checked

Candidate-v11 terminal provenance demonstrates the applicable governance pattern:

1. preregistration preceded freeze;
2. freeze preceded formal execution;
3. formal Protected was executed exactly once;
4. a formal failure terminated the lineage;
5. no post-formal tuning or rerun was allowed;
6. formal execution counts were persisted.

This precedent supports preserving the earlier Candidate-v12 preregistration rather than replacing its formal design after Development results are known.

## Frozen Candidate-v12 preregistration requirements

The Candidate-v12 preregistration was frozen before Candidate-v12 Development materialization and explicitly states that thresholds may be tightened only before Development materialization by a new preregistration lineage and may never be changed outcome-dependently within Candidate-v12.

It freezes the following formal design:

### Protected size and seed

- Protected total: `480`
- answerable: `300`
- no-evidence: `180`
- Protected seed: `24043`

### Protected acceptance thresholds

- MRR >= `0.97`
- R@1 >= `0.96`
- R@3 >= `0.99`
- R@5 >= `0.995`
- answerable recall >= `0.99`
- false abstention <= `0.01`
- false retrieval <= `0.03`
- abstention accuracy >= `0.97`
- safety invariants = `PASS`
- metadata firewall = `PASS`
- determinism = `PASS`
- Candidate-v12 R@1 noninferiority against frozen Candidate-v11 under the frozen paired-bootstrap rule is mandatory.

The preregistration additionally freezes Confirmatory/Final sizes, formal seeds, stage-disjoint grammar/discourse families, paired-bootstrap seed `59117`, `10000` iterations, and noninferiority margin `-0.01`.

## Conflict introduced by the recovered mission

The newly supplied Formal Protocol Recovery mission simultaneously requires preserving the existing preregistration and imposes new post-Development formal specifications, including:

- Protected dataset size `>= 600`, rather than the frozen `480`;
- Protected MRR >= `0.98`, rather than the frozen `0.97`;
- Protected R@1 >= `0.97`, rather than the frozen `0.96`;
- eligible Rank-1 accuracy >= `0.97` as a Protected requirement not frozen in the original Protected threshold block;
- additional structural floor rules not preregistered before Development.

Those new requirements were supplied only after the Development benchmark had been materialized, Candidate-v12 had been modified during Development, Architecture C had been selected, and Development had passed.

Therefore no formal protocol can now satisfy both governing constraints:

1. preserve the immutable pre-Development preregistration; and
2. replace its Protected size/acceptance rules with the newly supplied post-Development values.

Silently choosing either set would be a post-hoc protocol mutation or would disobey the new mission. Re-preregistering Candidate-v12 now would also violate the frozen preregistration's timing rule.

## Integrity ruling

This is not an implementation defect and cannot be repaired inside Candidate-v12 without changing formal rules after Development outcomes are known.

Accordingly the workflow stops before:

- formal-protocol replacement;
- formal runner creation under conflicting rules;
- Candidate-v12 immutable formal freeze;
- Candidate-v12 Protected dataset materialization;
- any inspection of Candidate-v12 Protected individual cases;
- Candidate-v12 Protected inference;
- execution-ledger increment.

No Protected payload has been generated, read, scored, or used for tuning during this recovery mission.

## Decision

Operational mission classification:

`CANDIDATE_V12_PROTECTED_INVALID — EVALUATION_INTEGRITY_FAILURE`

Because the frozen preregistration's valid Candidate-v12 terminal-state vocabulary predates that label, the corresponding preregistered lineage classification is:

`CANDIDATE_V12_RESEARCH_INTEGRITY_FAILURE`

The Protected execution count remains `0`; this is an integrity-invalid pre-execution termination, not an algorithmic Protected FAIL.

A valid continuation that adopts the newly supplied >=600-case Protected design and stricter thresholds requires a fresh lineage with those rules frozen before any new Development outcome is observed (for example Candidate-v13). Candidate-v12 must not be retrofitted to those rules.
