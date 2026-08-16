# Candidate-v13 External Validity v3 — Terminal Report

## Terminal decision

`EXTERNAL_VALIDITY_V3_INFRASTRUCTURE_BLOCKED`

## Evidence state

- Pre-freeze infrastructure qualification: PASS
- Gold-cardinality qualification: PASS
- Full production materialization: PASS — 3,744/3,744
- Gold truncation: 0
- Runtime gold loss: 0
- Materialization exceptions: 0
- Candidate-v13 SHA256: `b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838`
- Candidate-v13 modified: NO
- Candidate-v13 formal invocation: NO
- EV-A-v3: NOT_EXECUTED
- EV-B-v3: NOT_EXECUTED
- EV-C-v3: NOT_EXECUTED
- Formal ledger: 0 / 0 / 0
- Formal reruns: 0
- Illegal formal reruns: NO
- Performance-driven protocol changes: 0
- Research integrity: PASS

## Post-freeze infrastructure blocker

Infrastructure freeze and authorization completed at commit `6ac49d8e069d25f2497195fa7010a72e940dfaf1`. The frozen infrastructure workflow wrote and pushed `formal-authorization-lock-v3.json` using the GitHub Actions `GITHUB_TOKEN`.

GitHub suppresses recursive workflow triggering for pushes made by `GITHUB_TOKEN`. Consequently, the frozen path-filtered `Candidate v13 External Validity v3 — Formal Sequence` push workflow did not start from the authorization commit. Direct verification of the freeze commit showed zero Actions runs. The formal ledger therefore remained unconsumed and Candidate-v13 was never imported or invoked by the formal sequence.

This is a frozen infrastructure orchestration defect, not Candidate-v13 performance evidence. The preregistered v3 rule forbids patching frozen infrastructure and rerunning the formal sequence. Repair therefore requires a new v4 infrastructure lineage; v3 terminates here.

## Key pre-freeze materialization metrics

- EV-A-v3: 384/384; maximum runtime memories 70
- EV-B-v3: 1,440/1,440; maximum runtime memories 83
- EV-C-v3: 1,920/1,920; maximum runtime memories 100
- All stage selection/materialization/runtime-payload reconstruction digests were stable before freeze.

No external performance conclusion about Candidate-v13 is scientifically permitted from this lineage.
