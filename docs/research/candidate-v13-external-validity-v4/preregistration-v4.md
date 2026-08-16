# Candidate-v13 External Validity v4 — Preregistration

Candidate-v13 remains immutable, unimported, and uninvoked. All source, allocation, materialization, evaluator, runner, and policy decisions below are candidate-blind and become immutable at freeze.

## Formal sequence

EV-A-v4 (384) → PASS required → EV-B-v4 (1,440) → PASS required → EV-C-v4 (1,920). No stage reruns, no threshold changes, no benchmark replacement, no post-freeze infrastructure patch.

## Allocation

Fresh v3 seeds and fresh deterministic max-flow assignments. Exact source×domain, family, domain, and answerability quotas are locked in `preregistration-lock-v4.json`. Cross-stage base reuse must equal zero. Individual protected assignments are process-memory only.

## Runtime memory policy

Policy C: `max(5, gold_count + 4)`, global safety ceiling 100. All source-native gold must be retained for answerable cases; all target gold is withheld for no-evidence cases. Case dropping after allocation is forbidden.

## Full materialization gate

Before freeze, all 3,744 future formal cases must materialize production-faithfully with zero gold truncation, zero runtime gold loss, zero exceptions, stable selection/materialization/runtime-payload digests, and no Candidate import.

## Evaluation and anti-collapse

Metrics, thresholds, anti-collapse rules, stop conditions, evaluator behavior, and reserve-source policy are frozen by the machine-readable preregistration lock and referenced policy files. Candidate performance cannot alter them.
