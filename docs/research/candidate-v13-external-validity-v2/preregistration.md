# Candidate-v13 Naturalistic External Validity v2 — Preregistration

## Status

`PREREGISTERED_BEFORE_ANY_CANDIDATE_V13_EXTERNAL_PERFORMANCE_OBSERVATION`

Candidate-v13 has not been imported or invoked by this v2 lineage before this preregistration. No formal case payload has been persisted or exposed to Candidate-v13.

## 1. Frozen candidate

- Candidate: `Candidate-v13`
- Path: `src/personal_state_engine/candidate_v13.py`
- Git blob: `6c8ae4bce6ba8def0dd32fc3106c65639d521ef3`
- SHA256: `b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838`
- Candidate modification after this preregistration: **FORBIDDEN**.

## 2. Qualified source pool

Primary sources are pinned to immutable revisions recorded in `source-manifest-v2.json`:

- PersonaMem-v2: `b7b42b78917157afed063527a1c959e98f6109f2`
- LongMemEval-cleaned: `98d7416c24c778c2fee6e6f3006e7a073259d48f`
- LoCoMo: `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`
- SGD carryover: `e852981ae34990f4358979625854259302feaa78`
- EverMemBench-Dynamic: `a6b210a32248e841967b7b64a64281d2ff3f669d`

Preregistered reserve:

- RHELM: `4799f7b5757c6d9a945770fe8660c7ccfafca4c5`

RHELM is inactive for the frozen allocation. It may not be activated after this preregistration. Any need to change source membership after this point invalidates the v2 formal lineage rather than authorizing source shopping.

## 3. Source qualification and capacity

The qualified deduplicated base pool contains `96,092` cases. Hard capacity and all N1–N12 family requirements pass. D2 has a recorded safety-margin warning (`568/468`, 1.214x) but exceeds the preregistered hard requirement; this warning is retained and may not be used to replace D2 cases after performance observation.

Strict contamination audit passed with zero material overlap under:

1. exact normalized overlap;
2. token 5-gram Jaccard >= 0.85;
3. project synthetic-namespace overlap;
4. normalized skeleton similarity >= 0.92.

## 4. Adapter and gold construction

The frozen adapter is `adapter-policy-v2.json`.

Gold hierarchy is source-native and candidate-blind. Candidate predictions, LLM relabeling, fuzzy answer matching, post-result gold repair, and performance-driven exclusion are forbidden.

Each transformed case preserves source dataset, revision, source record ID, source message IDs, adapter version, domain, gold IDs, and deterministic transformation hash.

## 5. Runtime materialization

The frozen materializer contract is `materializer-contract-v2.json`.

Candidate runtime input contains only:

- `query`
- `memories[]` with `id`, `text`, `timestamp`

Evaluator/source/domain/family metadata is never passed to Candidate-v13.

Runtime context rules:

- minimum memories: 5
- minimum non-gold distractors: 4
- maximum memories: 80
- answerable cases retain target gold and add deterministic source-native distractors;
- no-evidence cases withhold every target gold unit before distractor construction;
- distractors are same-source qualified source-native units, prioritized by same subject+relation, then same subject, then same domain;
- Candidate-dependent hard-negative mining is forbidden.

### Timestamp policy

The qualified v2 base representation does not mechanically retain source timestamps. Therefore runtime `timestamp` is `null`. No timestamp may be invented, inferred, enriched, repaired, or added after performance observation. This is a known preregistered limitation and may make temporal cases harder; it is not grounds for post-result adapter modification.

## 6. Stage allocation

Allocation policy: `allocation-policy-v2.json`.

Stages and seeds:

- EV-A-v2: 384 cases, seed `42018`
- EV-B-v2: 1,440 cases, seed `42019`
- EV-C-v2: 1,920 cases, seed `42020`

Every stage has exact D1–D8 quotas, exact N1–N12 primary-family quotas, fixed answerable/no-evidence quotas, fixed source×domain cells, and source share <= 45%.

No base ID or normalized query may be reused across stages.

Pre-freeze deterministic selection digests are locked as:

- EV-A-v2: `09531ebaa5558a4e424c0f99d6173e5dde7f2a766e461f0eeb9650253d8ac4bc`
- EV-B-v2: `0fab0710a020cdeb53b58bc1f0de0b0adb2c09acf6276228d4f839d7763c90ab`
- EV-C-v2: `c7a32b83c2ba79241513b3a442ff242f68b4035c52265531324b6d155d75f50d`

Formal runtime must reconstruct these exact digests before Candidate-v13 is imported. Any mismatch is `FREEZE_MISMATCH` and no formal evaluation may proceed.

Individual protected case IDs and natural-language formal payloads are not persisted pre-freeze.

## 7. Evaluation metrics and thresholds

The complete fixed thresholds are in `evaluation-policy-v2.json` and are incorporated by reference into this preregistration.

Required reporting includes overall metrics, domain metrics, family metrics, rank metrics, coverage, invalid rate, bootstrap/Wilson 95% intervals, error counts, source distribution, and integrity status.

Primary metrics and thresholds may not be added, removed, weakened, strengthened, or reinterpreted after Candidate-v13 external output.

Family accuracy is evaluated under the frozen evaluator implementation; aggregate false-retrieval and abstention gates remain separate and may not be dropped.

## 8. EV-A-v2

EV-A-v2 is a small but fully formal one-shot external shakedown.

Before EV-A-v2:

- infrastructure qualification PASS;
- formal-infrastructure qualification PASS;
- preregistration locked;
- full SHA256 + git-blob freeze manifest PASS;
- formal ledger `ev_a_v2 = 0`.

The ledger must be irreversibly changed `0 -> 1` and successfully pushed before Candidate-v13 is imported/called.

After any EV-A-v2 performance observation, source, parser, adapter, materializer, allocation, seed, gold, evaluator, thresholds, and Candidate-v13 may not change within this lineage.

If EV-A-v2 fails a preregistered performance gate, terminal state is `EXTERNAL_VALIDITY_V2_PERFORMANCE_FAIL`; EV-B-v2 and EV-C-v2 remain unexecuted.

## 9. EV-B-v2

EV-B-v2 may execute only if EV-A-v2 legally PASSes.

It is one-shot. Ledger transition is `0 -> 1` only. `1 -> 2` is forbidden.

If EV-B-v2 fails a preregistered performance gate, terminal state is `EXTERNAL_VALIDITY_V2_PERFORMANCE_FAIL`; EV-C-v2 remains unexecuted.

## 10. EV-C-v2

EV-C-v2 may execute only if EV-B-v2 legally PASSes.

It is the final one-shot confirmatory stage. Ledger transition is `0 -> 1` only. `1 -> 2` is forbidden.

If EV-C-v2 PASSes, terminal state is `EXTERNAL_VALIDITY_V2_PASS` provided all integrity gates also PASS.

## 11. Determinism audit inside a formal stage

The frozen evaluator invokes the same Candidate-v13 ranker twice on the same runtime case solely to verify deterministic output. This duplicate call is part of the single preregistered stage execution and is **not** a second stage/rerun. It may not be used to select a better result; any disagreement is an integrity failure.

## 12. Invalidity and infrastructure rules

Before any formal stage ledger is consumed, an unrecoverable frozen infrastructure failure terminates as `EXTERNAL_VALIDITY_V2_INFRASTRUCTURE_BLOCKED`.

After any formal stage ledger is consumed, an unexpected execution/integrity failure that prevents a legal summary terminates the formal lineage as `EXTERNAL_VALIDITY_V2_INVALID`. The consumed stage may not be rerun.

Automatic invalidity includes:

- Candidate exposure before legal ledger consumption;
- protected rerun;
- protocol or threshold change after result;
- gold change after result;
- evaluator change after result;
- source replacement after preregistration;
- selection digest mismatch;
- frozen-file hash mismatch;
- ledger inconsistency;
- candidate-source invariant violation;
- nondeterministic formal output;
- contamination discovered after freeze.

## 13. Stopping rules

Formal progression stops immediately on any of:

`CANDIDATE_FIREWALL_FAIL`, `CONTAMINATION_FAIL`, `SOURCE_LICENSE_FAIL`, `SCHEMA_FAILURE`, `GOLD_RESOLUTION_FAIL`, `CAPACITY_FAIL`, `FREEZE_MISMATCH`, `PREREGISTRATION_VIOLATION`, `FORMAL_RERUN_DETECTED`, `LEDGER_INCONSISTENCY`.

No stop condition may be bypassed to obtain a PASS.

## 14. Terminal states

Only these terminal classifications are legal:

1. `EXTERNAL_VALIDITY_V2_PASS`
2. `EXTERNAL_VALIDITY_V2_PERFORMANCE_FAIL`
3. `EXTERNAL_VALIDITY_V2_INVALID`
4. `EXTERNAL_VALIDITY_V2_INFRASTRUCTURE_BLOCKED`

Candidate-v14 is not authorized by this mission under any terminal outcome.

## 15. Research-integrity declaration

The objective is a trustworthy answer, not a PASS. A legitimate performance failure is preserved as failure; an infrastructure block is preserved as block; an invalid protocol is preserved as invalid. No performance-driven change is permitted after formal observation.
