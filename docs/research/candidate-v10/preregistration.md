# Candidate-v10 Preregistration

Status: **FROZEN BEFORE Candidate-v9 confirmatory failure semantic payload access**

Repository: `kodlbegiko/personal-state-engine-clean-integrity`  
Branch: `research/candidate-v10-fresh-lineage`  
Base: Candidate-v9 terminal commit `a5f627248064ab98fed9e23a1f5eb24707a74c22`

## 1. Integrity boundary

Candidate-v7, Candidate-v8, and Candidate-v9 are immutable historical evidence. Candidate-v9 protected and confirmatory formal executions remain exactly 1 and 1; Candidate-v9 final remains 0. Candidate-v9 confirmatory semantic failure payload MUST NOT be opened before this preregistration commit exists.

After this commit, the ten Candidate-v9 confirmatory false-abstention cases may be opened only as `HISTORICAL_DIAGNOSTIC_ONLY`. They may support taxonomy, generalizable hypotheses, and architecture selection, but may not be copied into Candidate-v10 protected, confirmatory, or final surfaces and may not cause case-specific lexical or ID hardcoding.

## 2. Research question

Why did Candidate-v9 preserve answerability perfectly on development/protected while producing 10/220 false abstentions on a fresh confirmatory semantic surface despite retaining false retrieval = 0? Candidate-v10 must recover semantic generalization without coupling novelty to unsafe retrieval.

## 3. Preregistered hypotheses

- **H1 — Semantic relation abstraction failure.** Candidate-v9 relation canonicalization remains dependent on surface lexical families and fails on genuinely novel relation realizations.
- **H2 — Argument/value binding failure.** Relation identity is recovered but the certifier binds the wrong object/value span or fails to identify the value-bearing proposition.
- **H3 — Typed value inference brittleness.** Relation-range/value-type reasoning is domain-dependent and fails on unseen ontologies or open-class values.
- **H4 — Query decomposition failure.** Single-layer requirements do not robustly decompose target entity, predicate, temporal scope, modality, and argument type.
- **H5 — Evidence entailment representation failure.** Lexical/regex proxies are insufficient; an explicit predicate–argument compatibility representation is needed.
- **H6 — Negative-safety/answerability coupling.** Uncertainty is collapsed into abstention, preserving false-retrieval safety at the expense of recall under semantic novelty.
- **H7 — Generator-family overfitting.** Candidate-v9 development/protected may have had latent grammar-family overlap despite zero exact overlap, overstating generalization.

## 4. Architecture search space

Candidate-v10 is not required to preserve Candidate-v9 internals. The following designs are admissible:

A. improved canonical relation system;  
B. predicate–argument semantic frames;  
C. typed entailment graph;  
D. constraint-based semantic verifier;  
E. deterministic local semantic parser + hard safety blockers;  
F. a derived hybrid if justified by the historical taxonomy.

The selected architecture must preserve:

1. Candidate-v2 as the sole ranker;
2. order-preserving output (supported memories are a subsequence of Candidate-v2 rank order);
3. explicit no-evidence/adversarial safety;
4. no hidden benchmark metadata at inference time;
5. no paid external inference/API.

### Architecture selection rule

After historical diagnosis, select the simplest architecture that directly addresses the dominant root-cause classes and can express subject, predicate, argument/value, temporal scope, and epistemic/blocker status independently. Preference is given to a bounded deterministic proof system over expanding lexical exception lists.

## 5. Frozen semantic representation target

The primary design target is a bounded frame/constraint representation:

`subject + predicate/relation + value/arguments + temporal scope + modality/epistemic status + blockers`

Support is permitted only when:

- subject compatibility passes;
- predicate compatibility passes;
- value/argument binding is compatible;
- temporal scope is compatible;
- hard contradiction/negation/uncertainty blockers do not fire.

Semantic novelty alone is not a blocker.

## 6. Formal metrics

All stages track:

- MRR
- R@1
- R@3
- R@5
- answerable recall
- false abstention
- false retrieval
- abstention accuracy
- order-preservation violations
- paired bootstrap non-inferiority versus Candidate-v2
- absolute false-retrieval reduction versus Candidate-v2

Paired bootstrap iterations: **10,000**.  
Non-inferiority margin: **-0.03**.  
No formal threshold may be changed after this commit.

## 7. Frozen gates

### Development

- MRR >= 0.98
- R@1 >= 0.98
- R@3 >= 0.99
- R@5 >= 0.99
- answerable recall >= 0.98
- false abstention <= 0.02
- false retrieval <= 0.05
- abstention accuracy >= 0.95
- order-preservation violations = 0
- paired-bootstrap lower 95% CI >= -0.03

Freeze target (desirable, not an additional formal gate): false retrieval = 0 and answerable recall >= 0.99.

### Protected

- MRR >= 0.97
- R@1 >= 0.96
- R@3 >= 0.98
- R@5 >= 0.98
- answerable recall >= 0.98
- false abstention <= 0.02
- false retrieval <= 0.05
- abstention accuracy >= 0.95
- order-preservation violations = 0
- paired-bootstrap lower 95% CI >= -0.03
- false-retrieval reduction versus Candidate-v2 >= 0.80

### Confirmatory

- MRR >= 0.96
- R@1 >= 0.95
- R@3 >= 0.97
- R@5 >= 0.97
- answerable recall >= 0.97
- false abstention <= 0.03
- false retrieval <= 0.05
- abstention accuracy >= 0.95
- order-preservation violations = 0
- paired-bootstrap lower 95% CI >= -0.03
- false-retrieval reduction versus Candidate-v2 >= 0.80

### Fresh Final Gate F

The uploaded mission source ends immediately after the recommended development case counts and therefore does not contain a separate Final Gate F numeric threshold block. To eliminate post-hoc degrees of freedom **before any historical failure payload is opened**, Candidate-v10 freezes Final Gate F to the same minimum numeric gates as Confirmatory, with a wholly fresh grammar-family partition and seed. Final may execute once only after Confirmatory PASS.

## 8. Fresh benchmark protocol

Freshness must vary semantic realization, not merely names/values/seeds.

### Query realization axes

Direct WH, indirect, elliptical, nominalized relation, paraphrase, passive, possessive, contrastive, embedded clause, first-person, third-person, pronoun/coreference.

### Evidence realization axes

Canonical assertion, paraphrase, nominal predicate, apposition, copular, verb, possessive, prepositional relation, multi-clause, explicit temporal qualifier.

### Semantic domains

Preferences, education, employment, location, device ownership/use, transportation, language, hobbies, goals, relationships, memberships, schedules, pets, media, medication, attributes/colors, plus certifications, subscriptions, travel plans, dietary restrictions, sports teams, volunteering, software/tools, communication channels, recurring routines, project ownership, appointments, and accommodations.

## 9. Latent template-family separation

Generator-only metadata SHALL include:

- semantic domain
- query grammar family
- evidence grammar family
- argument-structure family
- temporal family
- polarity/adversarial family

Inference code MUST NOT read these fields. Evaluator may use them only for stratification/audit.

Frozen family partitions:

- Development: `A/B/C`
- Protected: `D/E`
- Confirmatory: `F/G/H`
- Final: `I/J/K`

The generator must emit `freshness-audit.json` containing exact overlap, normalized overlap, question-skeleton overlap, evidence-skeleton overlap, grammar-family overlap, domain distributions, and template provenance.

## 10. Frozen case counts and seeds

The uploaded mission explicitly recommends Development = 480 / 280 answerable / 200 no-evidence-adversarial, and the source ends there. To avoid later researcher degrees of freedom, the remaining counts are fixed here before historical semantic diagnosis:

- **Development:** 480 = 280 answerable + 200 no-evidence/adversarial; seed `2026081515`.
- **Protected:** 360 = 220 answerable + 140 no-evidence/adversarial; seed `2026081516`.
- **Confirmatory:** 420 = 250 answerable + 170 no-evidence/adversarial; seed `2026081517`.
- **Final:** 480 = 280 answerable + 200 no-evidence/adversarial; seed `2026081518`.

Bootstrap seeds respectively: `2026081525`, `2026081526`, `2026081527`, `2026081528`.

## 11. Formal execution policy

- Development may iterate before freeze and every iteration must be retained in the ledger.
- Once Development is frozen, the implementation/config/evaluator/generator hashes are fixed for Protected.
- Protected formal execution count max = 1.
- Confirmatory formal execution count max = 1 and requires Protected PASS.
- Final formal execution count max = 1 and requires Confirmatory PASS.
- A failed formal stage terminates the lineage; no rerun, filtering, rescoring, seed change, or post-result patch is allowed.

## 12. Leakage prohibitions

Forbidden:

- case-ID logic;
- answer dictionaries;
- benchmark-specific regexes;
- copying historical failed queries or evidence into fresh surfaces;
- using generator metadata in inference;
- tuning after viewing protected/confirmatory/final payloads;
- relabeling a modified seed/surface as a rerun of the same formal stage.

## 13. Terminal states

- provenance/integrity mismatch -> `CANDIDATE_V10_INTEGRITY_BLOCKED`
- Development gate failure after research budget is exhausted/frozen -> `CANDIDATE_V10_DEVELOPMENT_FAIL`
- Protected failure -> `CANDIDATE_V10_PROTECTED_VALIDATION_FAIL`
- Confirmatory failure -> `CANDIDATE_V10_CONFIRMATORY_FAIL`
- Final failure -> `CANDIDATE_V10_FINAL_GATE_F_FAIL`
- all formal stages pass -> `CANDIDATE_V10_FINAL_GATE_F_PASS`

This preregistration is immutable after commit.
