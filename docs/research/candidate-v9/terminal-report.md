# Candidate-v9 Terminal Report

## 1. Terminal State

`CANDIDATE_V9_CONFIRMATORY_FAIL`

## 2. Branch / HEAD

- Branch: `research/candidate-v9-fresh-lineage`
- HEAD at terminal snapshot generation: `705cc07155ccf77b513fa0317179586cfc4f1a05`
- Terminal evidence commit follows this recorded semantic HEAD.

## 3. Candidate-v8 Integrity

Verified. Candidate-v8 terminal branch remains `86c440fc487c46a1e603144177e666d32a52e725` and frozen Candidate-v8 research/result/source/config paths were unchanged throughout Candidate-v9 execution.

## 4. Candidate-v9 Architecture

Typed Query Intent + Relation Canonicalization + Relation-Range Value Binding + inherited hard safety blockers. Candidate-v2 is the sole ranker; Candidate-v9 performs independent per-memory certification and returns an order-preserving subsequence.

## 5. Candidate-v8 Failure Diagnosis

All four historical Candidate-v8 protected false abstentions were relation-realization failures. Subject, value-bearing, temporal compatibility, and blocker checks were not the limiting mechanism. The historical protected surface was opened only after Candidate-v9 preregistration and was excluded from all Candidate-v9 formal evaluation.

## 6. Development

cases=360; MRR=1.0; R@1=1.0; R@3=1.0; R@5=1.0; recall=1.0; false_abstention=0.0; false_retrieval=0.0; abstention_accuracy=1.0; order_violations=0; bootstrap={'iterations': 10000, 'seed': 2026081510, 'delta': 0.0, 'ci95': [0.0, 0.0], 'margin': -0.03, 'noninferiority': True}; verdict=PASS; tests=`........................................................................ [ 26%]
........................................................................ [ 52%]
........................................................................ [ 78%]
............................................................             [100%]
276 passed in 0.58s`.

## 7. Protected Validation

cases=300; MRR=1.0; R@1=1.0; R@3=1.0; R@5=1.0; recall=1.0; false_abstention=0.0; false_retrieval=0.0; abstention_accuracy=1.0; order_violations=0; bootstrap_delta=0.0; ci95=[0.0, 0.0]; noninferiority=True; verdict=PASS

## 8. Confirmatory

cases=360; MRR=0.9545454545454546; R@1=0.9545454545454546; R@3=0.9545454545454546; R@5=0.9545454545454546; recall=0.9545454545454546; false_abstention=0.045454545454545456; false_retrieval=0.0; abstention_accuracy=1.0; order_violations=0; bootstrap_delta=-0.045454545454545456; ci95=[-0.07272727272727272, -0.01818181818181818]; noninferiority=False; verdict=FAIL

## 9. Fresh Final Gate F

NOT EXECUTED

## 10. Formal Execution Counts

- protected: 1
- confirmatory: 1
- final: 0

All recorded rerun flags are false.

## 11. Integrity Deviations

- {"benchmark_written": false, "cause": "finite subject/value cycle produced exact duplicate normalized surfaces before file write", "failure": "duplicate semantic signatures within development generator output", "formal_execution_count": {"confirmatory": 0, "final": 0, "protected": 0}, "monetary_cost_usd": 0, "remediation": "expand deterministic subject namespace with surnames; preserve frozen case count, seed, categories, gates, and templates", "semantic_formal_payload_accessed": false, "stage": "PRE_DEVELOPMENT_MATERIALIZATION", "workflow_run_id": "31881331110"}
- {"benchmark_written": false, "cause": "first-person answerable family omits subject, while value index repeated on the same 24-case mode period", "failure": "duplicate semantic signatures remained after subject-namespace expansion", "formal_execution_count": {"confirmatory": 0, "final": 0, "protected": 0}, "monetary_cost_usd": 0, "remediation": "include deterministic mode-cycle index in value selection; preserve counts, seed, categories, templates, and gates", "semantic_formal_payload_accessed": false, "stage": "PRE_DEVELOPMENT_MATERIALIZATION", "workflow_run_id": "31881376267"}

No deviation changed a formal benchmark after materialization or caused a formal semantic evaluation rerun. The retired 99-case Gate F semantic payload was not opened.

## 12. Research Conclusion

The only valid research conclusion is the terminal state above. Candidate-v9 success is claimed only if development, fresh protected, fresh confirmatory, and Fresh Final Gate F all pass their preregistered gates. Paid API cost was USD 0.

## 13. Next Legal Action

STOP; Candidate-v10 fresh lineage required for further semantic research
