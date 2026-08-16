# Candidate-v13 External Validity v3 — V2 Forensic Audit

## Immutable historical anchor

- v2 terminal commit: `53d028455292094fcde66ec3b001179bb959a6fe`
- v2 terminal state: `EXTERNAL_VALIDITY_V2_INFRASTRUCTURE_BLOCKED`
- Candidate-v13 expected SHA256: `b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838`
- Candidate-v13 modified in v2: NO
- Candidate-v13 formal external invocation in v2: NO
- EV-A-v2 ledger: 0
- EV-B-v2 ledger: 0
- EV-C-v2 ledger: 0
- formal reruns: 0
- research integrity: PASS

## Exact v2 failure

`RuntimeError: selected base gold exceeds runtime maximum: evermembench-dynamic:evermem:1:F_MH_Top01_033`

The failure occurred after infrastructure freeze and before EV-A ledger consumption. Therefore it provides no Candidate-v13 performance evidence.

## Structural root cause to be measured

The frozen v2 materializer hard-coded `MAX_MEMORIES = 80`, while pre-freeze allocation feasibility did not qualify selected-case gold cardinality and the pre-freeze materialization QA was synthetic rather than a production-faithful 100% materialization of future formal selections.

v3 treats the following as a mandatory hard gate before preregistration/freeze:

`selected_case_count == successfully_materialized_case_count && gold_truncation_count == 0 && runtime_gold_loss_count == 0 && materialization_exception_count == 0`

Individual future formal IDs and natural-language payloads must not be persisted. Only aggregate evidence and cryptographic digests may be committed.

## Scientific interpretation

An infrastructure failure is not evidence of Candidate failure. Candidate-v14 development is out of scope unless a legally executed external evaluation later produces Candidate-v13 performance failure evidence.
