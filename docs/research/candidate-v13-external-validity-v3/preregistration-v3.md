# Candidate-v13 External Validity v3 — Preregistration

Candidate-v13 remains immutable and uninvoked. All 3,744 future formal cases have passed production-faithful materialization before freeze.

## Locked sequence

EV-A-v3 (384) -> PASS required -> EV-B-v3 (1,440) -> PASS required -> EV-C-v3 (1,920). No reruns.

## Runtime memory policy

Policy C: `max(5, gold_count + 4)`, global infrastructure ceiling 100, zero gold truncation.

## Integrity

Pinned immutable source revisions; fresh v3 seeds; no v2 individual assignment reuse; aggregate-only persisted protected evidence; Candidate import only after per-stage ledger 0->1 is committed and pushed.
