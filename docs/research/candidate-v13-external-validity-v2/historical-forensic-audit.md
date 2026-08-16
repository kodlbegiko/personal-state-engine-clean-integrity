# Candidate-v13 External Validity v2 — Historical Forensic Audit

Status: `HISTORICAL_RECONCILIATION_COMPLETE`

This artifact is infrastructure-only. Candidate-v13 was not imported, called, or evaluated.

## Historical anchors

- Terminal commit: `bad307ac11e549437b4337f0459ccfd55625f826`
- Historical terminal state: `NATURALISTIC_EXTERNAL_VALIDITY_INFRASTRUCTURE_BLOCKED`
- Candidate-v13 frozen blob: `6c8ae4bce6ba8def0dd32fc3106c65639d521ef3`
- Candidate-v13 SHA256: `b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838`
- Historical EV-B ledger: `0`
- Historical EV-C ledger: `0`
- Historical formal Candidate-v13 external invocation: `NO`

## A1 — Failure layer

The historical failure is classified as a compound **source-contract / schema-parser / capacity / materialization infrastructure failure**, not a Candidate-v13 performance failure.

The pre-formal capacity audit had sufficient aggregate capacity for D1–D5 and D8 and for every N1–N12 family, but D6 and D7 were short: D6 `212/468`, D7 `243/468`. A final gap source, `EverMind-AI/EverMemBench-Dynamic`, was then activated candidate-blind, but its forensic probe produced zero usable dialogue/QAR rows before formal case materialization.

## A2 — Why `dialogue_row_count = 0`

The historical probe contains a silent-empty parser contract:

```python
dialogues = json.loads(d_raw)
dialogue_rows = dialogues if isinstance(dialogues, list) else []
```

Therefore any valid non-list top-level JSON is silently converted to an empty dataset. This is an evaluator/parser defect class. The v2 lineage does **not** infer the actual source schema from this failure; v2 must directly inspect and persist a schema manifest from the pinned source bytes and fail loudly on mismatch.

## A3 — QAR schema issue

The historical probe applies the same silent-list assumption to `EverMemBench_QAR.json` and expects row fields `topic_id`, `Q`, `A`, `R`. Public source inspection shows the legacy root QAR asset and the dataset-card/config representation are not safe to treat as the same schema by filename alone. v2 therefore treats raw-file layout and dataset-config layout as distinct contracts and will only activate a representation whose source-native references can be mechanically resolved.

## A4 — Parser assumption mismatch

Historical assumptions that are forbidden in v2:

1. top-level `list` inferred from filename/README;
2. non-list JSON treated as valid empty data;
3. missing required keys tolerated until downstream count becomes zero;
4. source qualification and formal capacity depending on an unverified representation.

v2 requires explicit `top_level_type`, `top_level_keys`, `record_type`, `record_keys`, container fields, ID/reference fields, and deterministic parse invariants before capacity is counted.

## A5 — Would a parser-only repair solve D6/D7?

`NOT_ESTABLISHED`.

A parser repair is necessary to determine the real EverMemBench capacity, but it is not sufficient evidence that D6/D7 requirements will be met. v2 additionally requires source-native gold resolution, deduplication, domain mapping, license/revision pinning, and a safety margin of at least `1.5×` required capacity before formal freeze. No Candidate-v13 output may be used to make that determination.

## v2 consequence

The old four-source pool will be freshly requalified under a v2 wrapper. EverMemBench-Dynamic and Microsoft RHELM are evaluated as candidate-blind supplemental/reserve sources. No supplemental source is activated merely because it would make Candidate-v13 perform better.
