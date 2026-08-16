# Candidate-v14 Failure Model

## Scope and evidence boundary

Candidate-v13 ended with the valid external terminal state `EXTERNAL_VALIDITY_V4_CANDIDATE_FAIL`. The v4 infrastructure and research-integrity gates passed, so the performance failure is treated as a Candidate failure, not an evaluator/infrastructure excuse. This document uses only frozen aggregate v4 diagnostics plus Candidate-v13 source code. No v4 protected case-level query, memory, case ID, assignment, or seed is used.

## Observed aggregate failure signature

The allowed terminal aggregate evidence shows EV-A-v4 MRR ≈ 0.0833, R@1 ≈ 0.0792, R@3/R@5 = 0.0875, answerable recall = 0.0875, eligible rank-1 accuracy ≈ 0.3654, abstention accuracy ≈ 0.9028, false-abstention ≈ 0.7833, false-retrieval ≈ 0.1224, abstain rate ≈ 0.8281, anti-collapse FAIL, 11/12 primary families below the accuracy floor, and all 8 domains failing answerable-recall/R@1 requirements.

## H1 — Abstention gate miscalibration

The v13 verifier contains hard failure paths before useful evidence can be returned. A weak or incomplete parse can become an empty ranking rather than merely lower confidence. This can amplify uncertainty into systematic false abstention.

**v14 response:** never abstain before Stage-1 retrieval has produced a ranked evidence competition. Verification controls the final retrieve/abstain decision.

## H2 — Exact / lexical evidence dependence

Heterogeneous paraphrases can weaken rigid token, entity, or relation matching. Exact development fixtures can therefore overstate robustness.

**v14 response:** combine lexical overlap, lightweight semantic concept equivalence, character similarity, entity matching, relation matching, and proposition binding. No single lexical threshold decides retrieval.

## H3 — Ranking and abstention coupling

In v13, a verifier failure or empty supporting-memory set yields an empty rank output. Ranking quality and evidence sufficiency are therefore tightly coupled.

**v14 response:** split high-recall ranking from verification. Every memory receives a rank score first; only then does the verifier decide whether the top evidence is sufficient.

## H4 — Poor relative evidence reasoning

Absolute relevance thresholds can abstain even when one candidate is clearly superior to distractors.

**v14 response:** use top-1/top-2 margin and evidence competition in addition to absolute component scores. Relative superiority is evidence, but cannot override contradiction/uncertainty checks.

## H5 — Missing query–memory semantic representation

Pure lexical overlap is brittle under synonymy and paraphrase, but a large opaque neural dependency would reduce determinism/offline reproducibility.

**v14 response:** use a deterministic hybrid symbolic-semantic representation: fixed broad concept groups + proposition binding + character similarity. This is intentionally lightweight and auditable.

## H6 — Domain/family routing failure

Failure across 11/12 families and all 8 domains is more consistent with a global architecture bottleneck than a single benchmark-specific defect.

**v14 response:** avoid domain-specific routers. Use one evidence architecture across domains, with family/domain qualification floors and anti-collapse gates.

## Falsifiable prediction

If the diagnosis is directionally correct, Candidate-v14 should reduce false abstention without degenerating into always-retrieve, preserve rank quality under paraphrase and distractors, and pass counterfactual evidence-removal tests. Internal success is not external-validity evidence; a later fresh protected evaluation is still required.
