# Candidate-v14 Architecture Comparison

All results below use the combined architecture-development, internal-validation, and adversarial-validation splits (1,152 cases). The untouched internal holdout is excluded.

| Architecture | MRR | R@1 | Answerable recall | Abstention acc. | False abstention | False retrieval | Min family acc. | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A — Calibrated Hybrid Retriever | 1.0000 | 1.0000 | 1.0000 | 0.8472 | 0.0000 | 0.1528 | 0.7500 | FAIL: false retrieval / abstention |
| B — Two-Stage Retrieve → Verify | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 1.0000 | PASS |
| C — Multi-Hypothesis Evidence Competition | 0.9167 | 0.9167 | 0.9167 | 0.8333 | 0.0833 | 0.1667 | 0.2500 | FAIL: recall, abstention, false retrieval, family |
| D — Evidence Sufficiency Classifier | 1.0000 | 1.0000 | 1.0000 | 0.5833 | 0.0000 | 0.4167 | 0.7500 | FAIL: false retrieval / abstention |

All four variants share the same deterministic evidence features so the architecture comparison isolates decision policy: A applies an absolute hybrid score threshold; B ranks first and verifies structural sufficiency; C emphasizes relative margin; D applies a separate sufficiency aggregate.

## Complexity

| Architecture | External model | Deterministic | Added runtime passes | Explainability | Main risk |
|---|---|---|---:|---|---|
| A | none | yes | 1 | high | absolute threshold permits no-evidence retrieval |
| B | none | yes | 2 logical stages over one scoring pass | high | handcrafted semantic vocabulary may not transfer |
| C | none | yes | 1 | high | margin gate increases false abstention |
| D | none | yes | 1 | high | sufficiency aggregate is poorly separated |

Architecture B is selected because it is the only candidate satisfying every development gate and directly addresses the v13 ranking/abstention coupling hypothesis. Its extra complexity is logical rather than dependency-heavy: no model, service, or package dependency is added.
