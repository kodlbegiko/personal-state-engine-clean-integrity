# Candidate-v10 Terminal Report

Terminal state: `CANDIDATE_V10_FINAL_GATE_F_FAIL`

## Formal execution counts

- Protected: 1
- Confirmatory: 1
- Final Gate F: 1

## Stage results

- development: PASS | MRR=0.9982142857142857 | R@1=0.9964285714285714 | R@3=1.0 | R@5=1.0 | recall=1.0 | false_abstention=0.0 | false_retrieval=0.0 | abstention_accuracy=1.0 | order_violations=0
- protected: PASS | MRR=1.0 | R@1=1.0 | R@3=1.0 | R@5=1.0 | recall=1.0 | false_abstention=0.0 | false_retrieval=0.0 | abstention_accuracy=1.0 | order_violations=0
- confirmatory: PASS | MRR=1.0 | R@1=1.0 | R@3=1.0 | R@5=1.0 | recall=1.0 | false_abstention=0.0 | false_retrieval=0.0058823529411764705 | abstention_accuracy=0.9941176470588236 | order_violations=0
- final: FAIL | MRR=0.9732142857142857 | R@1=0.9464285714285714 | R@3=1.0 | R@5=1.0 | recall=1.0 | false_abstention=0.0 | false_retrieval=0.05 | abstention_accuracy=0.95 | order_violations=0

## Integrity

- Frozen implementation hashes verified: True
- Cross-stage freshness integrity: True
- Candidate-v2 remained the sole ranker.
- Inference did not receive labels, relevant IDs, answers, split names, provenance, or generator-only metadata.
- Paid external inference/API cost: USD 0.
- Candidate-v9 protected/confirmatory/final execution counts remain historical 1/1/0; no Candidate-v9 formal rerun occurred.

## Notes

- Development was frozen before any Candidate-v10 formal protected payload was generated.
- final formal gate failed; subsequent formal stages were not generated or executed.
