# Candidate-v9 Evaluation Protocol

## Identity boundary

Every evaluation records SHA-256 for Candidate-v9 source, config, generator, evaluator, and materialized dataset. Any mismatch fails closed. Candidate-v8 terminal HEAD must remain `86c440fc487c46a1e603144177e666d32a52e725` and its frozen evidence must be unchanged.

## Inference boundary

Candidate-v9 receives only the user query and Candidate-v2-ranked memory contents/identifiers required to return the order-preserving filtered result. It may not receive gold labels, relevant IDs, expected answers, split/stage labels, benchmark filename, or case ID as semantic features.

## Metrics

Primary metrics: MRR, R@1, R@3, R@5, answerable recall, false-abstention rate, abstention accuracy, false-retrieval rate, and Candidate-v2 order-preservation violations. Paired bootstrap compares per-answerable-case reciprocal rank between Candidate-v9 and Candidate-v2 using 10,000 iterations and a non-inferiority margin of -0.03.

## Development

360 cases: 210 answerable, 150 no-evidence; seed 2026081509. Iteration is legal only here. All iterations remain in an append-only ledger. Development must meet the gates in `preregistration.md` before freeze.

## Protected

300 cases: 190 answerable, 110 no-evidence; dataset seed 2026081511; bootstrap seed 2026081512. Execution order is lock, materialize, commit, authorize, execute once, persist result. A semantic FAIL terminates the lineage.

## Confirmatory

360 independent cases: 220 answerable, 140 no-evidence; dataset seed 2026081513; bootstrap seed 2026081514. May execute only if protected passes. One-shot.

## Fresh Final Gate F

480 independent cases: 300 answerable, 180 no-evidence; dataset seed 2026081515; bootstrap seed 2026081516. May execute only if confirmatory passes. The old 99-case semantic payload is permanently excluded.

## One-shot counters

Before a formal stage materializes: execution_count=0, rerun=false, payload_manually_inspected=false. After the sole semantic execution: execution_count=1. A failed run may not be repeated. Infrastructure/identity failure before payload execution must record whether semantic payload was accessed and does not silently consume or reset a formal execution.

## Formal gates

Protected and confirmatory: MRR >=0.96; R@1 >=0.95; R@3/R@5 >=0.97; answerable recall >=0.97; false abstention <=0.03; false retrieval <=0.05; abstention accuracy >=0.95; zero order violations; paired-bootstrap lower 95% bound >=-0.03; absolute false-retrieval reduction vs Candidate-v2 >=0.80.

Final: MRR >=0.96; answerable recall >=0.97; false abstention <=0.03; false retrieval <=0.05; abstention accuracy >=0.95; zero order violations; paired-bootstrap lower bound >=-0.03; false-retrieval reduction >=0.80.

## Defect handling

If a materialized formal benchmark is later shown to contain a real defect, invalidate the whole formal execution, document it, make no PASS claim, and move to a new versioned lineage/protocol. Never delete or edit individual cases after seeing outcomes.
