# Candidate-v13 Naturalistic External Validity v4 — Terminal Report

## Terminal State

`EXTERNAL_VALIDITY_V4_CANDIDATE_FAIL`

## Candidate Integrity

- expected SHA: `b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838`
- observed SHA: `b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838`
- modified: `false`
- preauthorization imported: `false`
- preauthorization invoked: `false`

## Infrastructure Qualification

- source qualification: `True`
- gold cardinality: `True`
- capacity: `True`
- contamination: `True`
- dedup: `True`
- determinism: `True`
- full materialization: `PASS`
- evaluator QA: `True`
- runner QA: `True`
- Candidate firewall: `True`
- launch-path QA: `True`
- preregistration completeness: `PASS`
- freeze: `FROZEN`

## Formal Evaluation

- ev_a_v4: executed=true, invocation_count=1, result=FAIL
- ev_b_v4: executed=false, invocation_count=0, result=NOT_EXECUTED
- ev_c_v4: executed=false, invocation_count=0, result=NOT_EXECUTED

## Formal Integrity

- formal reruns: `0`
- illegal reruns: `False`
- performance-driven protocol changes: `0`
- post-freeze modifications: `0`
- research integrity status: `PASS`

## External-Validity Metrics

See the complete stage summaries embedded in `results/candidate-v13-external-validity-v4/terminal-summary.json`. No failed preregistered metric is omitted.

## Scientific Conclusion

`external validity rejected`

## Git Evidence

- branch: `research/candidate-v13-external-validity-infra-v4`
- v3 terminal ancestor: `21d1bb3a645c9c38000294694a78be3fcedbea16`
- freeze commit: `385962f438b8d7d5a7c0814c7468b984b27c994d`
- terminal commit: populated by the final evidence commit in Git history
- Draft PR: maintained separately against `main`
