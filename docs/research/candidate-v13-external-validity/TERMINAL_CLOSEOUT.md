# Candidate-v13 Naturalistic External Validity — Terminal Closeout

## Terminal decision

`NATURALISTIC_EXTERNAL_VALIDITY_INFRASTRUCTURE_BLOCKED`

The external-validity lineage did not reach a legal formal Candidate-v13 invocation. EV-B and EV-C remain unconsumed. This closeout does **not** claim that Candidate-v13 passed or failed naturalistic external validity; it records that the preregistered/frozen infrastructure could not legally establish the formal evaluation without changes forbidden by the closeout protocol.

## 1. Candidate-v13 到底通過還是失敗？

Neither PASS nor FAIL was established for naturalistic external validity.

The terminal state is `NATURALISTIC_EXTERNAL_VALIDITY_INFRASTRUCTURE_BLOCKED`. No EV-B or EV-C performance result exists, so a performance PASS/FAIL claim would be unsupported.

## 2. EV-B 真實狀態？

- Ledger: `EV-B = 0` (reconstructed from the preregistered initial ledger plus no later consumption evidence).
- Run: no external EV-B formal Candidate-v13 invocation found.
- Decision: `NOT_EXECUTED`.
- Metrics: none.
- Integrity result: not applicable because formal execution never began.
- Rerun: no.

The target-branch history contains no committed `results/candidate-v13-external-validity/formal-ledger.json`, no historical `ev-b-summary.json`, and no GitHub Actions run showing an EV-B formal Candidate-v13 invocation.

## 3. EV-C 真實狀態？

- Ledger: `EV-C = 0`.
- Run: none.
- Decision: `NOT_EXECUTED`.
- Metrics: none.
- Integrity result: not applicable because EV-C was never authorized or invoked.
- Rerun: no.

The target-branch history contains no historical `ev-c-summary.json` and no EV-C formal Candidate-v13 invocation.

## 4. 是否有 formal rerun？

`NO`

No EV-A, EV-B, or EV-C formal rerun was performed during reconciliation. The EverMemBench-Dynamic run `31924604151` was a pre-formal forensic evidence-persistence probe of the already locked gap source; its guard confirmed `candidate_v13_invoked=false` and `formal_case_materialized=false`, so it consumed no formal bullet.

## 5. Candidate-v13 是否在 external result 後被修改？

`NO`

Candidate-v13 was not modified after the external preregistration lock and no external performance result was observed. The last `src/personal_state_engine/candidate_v13.py` modification is commit `8dd34a8d414e122ca5c2d4ebb665c901e58c35e7`, which predates external preregistration provenance commit `7c429cdf1236ff1ae16f5d2cac3a28e6168ab0f2`.

The current Candidate-v13 Git blob remains `6c8ae4bce6ba8def0dd32fc3106c65639d521ef3`, matching the Candidate-v13 freeze manifest. The freeze manifest records Candidate-v13 SHA256 `b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838`.

## 6. Research integrity 是否成立？

`PASS`

Reason:

- no external Candidate-v13 formal invocation occurred;
- EV-B and EV-C bullets remain at zero;
- no formal rerun occurred;
- no candidate tuning occurred after external preregistration;
- no performance-driven threshold, gold, seed, domain, family, or source replacement was performed;
- the lineage stops at infrastructure block rather than repairing the parser/adapter/source contract to force a runnable evaluation.

This is an integrity PASS, **not** an external-validity performance PASS.

## Reconciliation evidence

### External preregistration and ledger

The external preregistration lock records initial formal ledger `EV-B=0`, `EV-C=0` and requires post-lock protocol changes to invalidate rather than silently amend the formal evaluation. Commit history shows no later external formal-ledger artifact and no EV-B/EV-C summary history.

### Frozen Candidate-v13 provenance

The Candidate-v13 freeze manifest records:

- Candidate-v13 SHA256: `b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838`
- Candidate-v13 Git blob: `6c8ae4bce6ba8def0dd32fc3106c65639d521ef3`
- formal runner SHA256: `8cf552ad6dc5aeba0f7054c90d71d73453f3e239b47862a118eb1c63e0802b83`
- evaluator SHA256: `5d849e9d3f13dc1067619984d883055fee52d6da59ae45c62043e15ce9096838`

The external lineage did not reach a separate full formal hash-manifest materialization step for every external adapter/allocation component. Where a separate SHA256 was not committed, this closeout preserves the Git blob SHA and explicitly leaves SHA256 unavailable rather than inventing it.

### Capacity block before any formal invocation

Two independent pre-formal capacity audits produced the same shortage:

- D6: `212 / 468`
- D7: `243 / 468`
- result: `CAPACITY_SHORTFALL`

Both audits were pre-performance and did not invoke Candidate-v13 or materialize formal cases.

### Final locked gap source

`source-activation-v3.json` locked `EverMind-AI/EverMemBench-Dynamic` as the gap-filling source for D6/D7 and prohibited ad hoc source substitution after failure.

The forensic persistence run `31924604151` used the already committed probe code and did not modify Candidate-v13, the evaluator, parser, adapter policy, allocation policy, thresholds, or source selection. The probe downloaded and pinned revision `a6b210a32248e841967b7b64a64281d2ff3f669d` and committed aggregate evidence at `2821dc6c0f5855186fd8e85f137d2ea35fb01272`.

Committed probe evidence shows:

- `candidate_v13_invoked=false`
- `formal_case_materialized=false`
- `dialogue_row_count=0`
- `qar_topic_counts={}`
- `aggregate_counts={}`

The subsequent workflow boundary assertion failed, but the aggregate evidence had already been committed. The failure occurred before any formal Candidate-v13 execution.

## Why the lineage must stop here

The preregistered source pool still lacks enough D6/D7 capacity, while the final locked gap source cannot yield usable formal cases under the frozen pre-formal probe contract. Continuing would require at least one prohibited action: changing the parser/adapter/source contract, replacing or adding a source, altering materialization logic, or otherwise revising the frozen infrastructure after observing the failure.

Because EV-B and EV-C were never consumed, the correct conservative terminal classification is:

`NATURALISTIC_EXTERNAL_VALIDITY_INFRASTRUCTURE_BLOCKED`

No Candidate-v14 is created by this closeout, and Candidate-v13 development remains closed.
