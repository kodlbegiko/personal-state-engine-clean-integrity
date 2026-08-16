# Candidate-v12 Architecture Decision — Development

Status: `DEVELOPMENT_PASS`

Formal execution counts remain:

- Protected: `0`
- Confirmatory: `0`
- Final: `0`

This document records a Development decision only. It is not a Protected, Confirmatory, Final, or Gate-F result.

## 1. Historical failure class

The preregistered diagnostic of the already-existing Candidate-v11 Protected payload found that all 260 answerable failures had the same first blocking reason: `subject`. All 260 showed subject/entity over-expansion with preceding discourse material mixed into mandatory subject anchors. Candidate-v11 formal evaluation was not rerun, Candidate-v11 source was not modified, and no historical Protected text/entity/value/case ID was emitted into Candidate-v12 Development fixtures.

Therefore the dominant historical failure was upstream semantic-frame extraction / eligibility, not Candidate-v11 Layer-2 Rank-1 ordering.

## 2. Architecture comparison

Fresh Development surface:

- cases: 720
- answerable: 432
- no-evidence: 288
- seed: 12031
- grammar families: DA–DF
- discourse families: D0–D5
- historical Protected payload read by Development generator: no

Compared architectures:

1. **A — Frozen Candidate-v11**: historical semantic extraction / eligibility + Candidate-v11 Layer-2 proof ordering.
2. **B — Bounded discourse stripping**: strips only material before the strongest runtime-grounded entity span, then calls frozen Candidate-v11.
3. **C — Structured semantic frame**: conservatively binds subject spans, resolves competing relation lexemes with bound-subject runtime evidence, constructs a structured semantic frame, then preserves Candidate-v10 evidence certification and Candidate-v11 Layer-2 ordering.
4. **D — Clause-first proposition graph**: uses the same conservative semantic-frame binding but additionally requires the resolved relation to be present in a proposition-bearing clause before downstream certification.

Final Development metrics:

| Architecture | MRR | R@1 | Recall | False abstention | False retrieval | Abstention accuracy |
|---|---:|---:|---:|---:|---:|---:|
| A — frozen v11 | 0.3333 | 0.3333 | 0.3333 | 0.6667 | 0.0000 | 1.0000 |
| B — bounded stripping | 0.6667 | 0.6667 | 0.6667 | 0.3333 | 0.0000 | 1.0000 |
| C — structured frame | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 1.0000 |
| D — clause-first graph | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 1.0000 |

Candidate-v12 frame metrics under Architecture C:

- subject exact-span accuracy: 1.0000
- subject mandatory-anchor precision: 1.0000
- subject mandatory-anchor recall: 1.0000
- relation-frame accuracy: 1.0000
- temporal-scope accuracy: 1.0000
- discourse-token contamination rate: 0.0000
- metadata firewall: PASS
- Candidate-v2 candidate-source invariant: PASS
- determinism: PASS

## 3. Development iteration record

The first Architecture-C Development run was not accepted:

- relation-frame accuracy: 0.8333
- false retrieval rate: 0.0500
- false retrieval cases: 36

Failure decomposition showed a general second-order discourse contamination mechanism: lexemes used as discourse/request scaffolding can also be legitimate semantic-relation lexemes in other contexts. This caused relation-frame over-expansion. The 36 false retrievals were answerable `work_role` cases in which a wrong-relation memory became additionally eligible.

The remediation did **not** add token blacklists or Development-template exceptions. Instead Candidate-v12 now:

1. extracts all relation candidates from the query;
2. binds the subject first;
3. for a singleton relation candidate, retains it directly;
4. for competing relation candidates, measures support only in memories grounded to the bound subject;
5. selects a unique highest-support relation;
6. fails closed on a support tie or zero-support contest;
7. identifies proposition-bearing clauses only after the relation is resolved.

Abstracted regression tests use different wording and structure from the Development templates and historical Protected examples.

The next Development execution met every preregistered threshold without lowering any threshold.

## 4. Decision

**Select Architecture C — Structured Query Semantic Frame Parser as the Candidate-v12 Development winner.**

Architecture D ties C on the current Development surface but adds a clause-presence gate that produced no measured safety or ranking improvement. Because additional clause gating creates another possible false-abstention surface under unseen syntax, C is the lower-complexity choice with the same observed safety.

Architecture B is rejected as a final candidate because it improves over frozen v11 but still leaves one-third of answerable Development cases in false abstention and remains structurally brittle to discourse wrappers.

Architecture A remains the immutable historical baseline.

## 5. Preserved safety boundaries

Candidate-v12 does not:

- modify Candidate-v7 through Candidate-v11;
- rerun Candidate-v11 Protected;
- use Protected case IDs, labels, gold answers, relevant-memory IDs, grammar/discourse family IDs, or generator metadata at inference time;
- inject memories outside Candidate-v2 output;
- use a permissive fallback when frame parsing is ambiguous;
- lower evidence-safety thresholds to recover recall.

## 6. Evidence paths

- `docs/research/candidate-v12/preregistration.md`
- `docs/research/candidate-v12/preregistration-provenance.json`
- `scripts/diagnose_candidate_v11_protected_frame_failures.py`
- `results/candidate-v12/candidate-v11-protected-frame-failure-taxonomy.json`
- `src/personal_state_engine/candidate_v12.py`
- `tests/test_candidate_v12.py`
- `scripts/generate_candidate_v12_development.py`
- `scripts/evaluate_candidate_v12_development.py`
- `scripts/diagnose_candidate_v12_development.py`
- `experiments/benchmarks/candidate-v12-development-v1.json`
- `results/candidate-v12/architecture-comparison-development-v1.json`
- `results/candidate-v12/development-failure-taxonomy-v1.json`
- `results/candidate-v12/development-summary-v1.json`
