# Candidate-v8 Terminal Report

## Terminal state
`CANDIDATE_V8_PROTECTED_VALIDATION_FAIL`

## Last formal stage
`protected` — `FAIL`

Candidate-v7 remained immutable. The retired 99-case semantic payload was never opened. Candidate-v7 confirmatory is historical-diagnostic-only. Formal protected/confirmatory executions were one-shot and cost USD 0.

```json
{
  "schema_version": "candidate-v8-evaluation-v1",
  "stage": "protected",
  "benchmark_name": "candidate-v8-protected-v1",
  "benchmark_sha256": "087352b8ccc3a66790cd29953f41418e9fb296df60d10245b576bf41c49d55f8",
  "candidate_v8_source_sha256": "09d58cfb5c4b8ecfe8fcdb8cbc96b5fc85363ea155d8901ab54b42b92cd1322a",
  "candidate_v2": {
    "MRR": 0.9789473684210527,
    "R@1": 0.9578947368421052,
    "R@3": 1.0,
    "R@5": 1.0,
    "answerable_recall": 1.0,
    "false_abstention": 0.0,
    "abstention_accuracy": 0.0,
    "false_retrieval": 1.0,
    "order_preservation_violations": 0,
    "answerable_count": 95,
    "no_evidence_count": 65
  },
  "candidate_v8": {
    "MRR": 0.9578947368421052,
    "R@1": 0.9578947368421052,
    "R@3": 0.9578947368421052,
    "R@5": 0.9578947368421052,
    "answerable_recall": 0.9578947368421052,
    "false_abstention": 0.042105263157894736,
    "abstention_accuracy": 1.0,
    "false_retrieval": 0.0,
    "order_preservation_violations": 0,
    "answerable_count": 95,
    "no_evidence_count": 65
  },
  "candidate_v8_absolute_false_retrieval_reduction_vs_candidate_v2": 1.0,
  "paired_bootstrap": {
    "iterations": 10000,
    "seed": 2026081501,
    "delta": -0.021052631578947368,
    "ci95": [
      -0.05789473684210526,
      0.010526315789473684
    ],
    "margin": -0.03,
    "noninferiority": false
  },
  "checks": {
    "mrr": true,
    "answerable_recall": true,
    "false_retrieval": true,
    "false_abstention": true,
    "order_preservation": true,
    "paired_bootstrap_noninferiority": false
  },
  "verdict": "FAIL",
  "monetary_cost_usd": 0
}
```
