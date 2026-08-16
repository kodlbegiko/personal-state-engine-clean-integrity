# Candidate-v13 Preregistration

Status: `PREREGISTRATION_LOCK_PENDING_COMMIT`

Repository: `kodlbegiko/personal-state-engine-clean-integrity`  
Branch: `research/candidate-v13-fresh-lineage`  
Historical parent anchor: `16dfcbfeb47cf8ad9bf78c639150d17404f4a685`  
Historical parent terminal state: `CANDIDATE_V12_RESEARCH_INTEGRITY_FAILURE`

This Candidate-v13 lineage is historically informed but independently preregistered. Candidate-v7 through Candidate-v12 history is immutable. No historical formal payload may be copied into Candidate-v13 Development or any formal dataset.

## 1. Research question

Can a fully preregistered structured-semantic-frame retrieval architecture, developed without formal-payload exposure and frozen before formal evaluation, generalize across fresh heterogeneous natural-language surfaces while preserving evidence eligibility, semantic proof ordering, abstention safety, source invariants, metadata isolation, temporal validity, contradiction handling, and deterministic behavior?

Candidate-v13 starts from the historical architectural hypothesis that proposition/discourse separation plus structured semantic binding is useful, but Candidate-v13 must create its own source, Development evidence, freeze manifest, formal runner, formal surfaces, execution ledger, and terminal decision.

## 2. Immutable lifecycle ordering

The only valid lifecycle is:

`Preregistration -> Development -> Freeze -> Protected -> Confirmatory -> Final`

Preregistration must be committed before any Candidate-v13 benchmark case is materialized.

Before the preregistration commit, it is permitted to author only schemas, generator/evaluator code, metric code, runner logic, validation tests, and other non-materialized infrastructure. It is forbidden to materialize Development, Protected, Confirmatory, or Final cases.

After Development PASS and formal freeze, Candidate-v13 algorithm source is immutable.

Protected is exactly one execution. Confirmatory and Final are at most one execution each and are authorized only by the immediately preceding PASS.

## 3. Exclusive candidate-source contract

Candidate-v2 is the exclusive candidate retrieval source.

Candidate-v13 may:
- parse the query into a structured semantic frame;
- certify or reject eligibility among Candidate-v2-returned records;
- compute proof-quality attributes for eligible Candidate-v2 records;
- reorder eligible Candidate-v2 records using non-compensatory semantic proof ordering;
- abstain when no evidence is eligible or the query frame is unresolved.

Candidate-v13 may not:
- inject a memory absent from Candidate-v2 output;
- call another retrieval universe;
- mutate Candidate-v2;
- rescue a hard-ineligible candidate by lexical score;
- use evaluation metadata to alter candidate membership or order.

Every returned evidence ID must be present in the original Candidate-v2 candidate set.

## 4. Candidate-v13 architectural hypothesis

Primary architecture:

`Structured Semantic Frame + Hard Evidence Eligibility + Non-Compensatory Semantic Proof Ordering`

The runtime frame must explicitly represent:

- target subject/entity;
- subject aliases and coreference state;
- target relation;
- relation aliases;
- requested answer type;
- predicate constraints;
- object constraints;
- temporal scope;
- modality/status constraints;
- negation state;
- discourse framing separated from semantic proposition;
- evidence support state;
- evidence contradiction state;
- evidence ambiguity state.

Required flow:

```text
Raw Query
  -> Discourse / Proposition Separation
  -> Structured Semantic Frame
  -> Candidate-v2 Candidate Retrieval
  -> Hard Evidence Eligibility
  -> Semantic Proof Quality Ordering
  -> Answer OR Abstain
```

Pure lexical overlap is never sufficient for final semantic correctness.

Hard eligibility is non-compensatory: a failure of a mandatory subject, relation, contradiction, temporal, or status constraint cannot be compensated by a higher lexical/proximity score.

## 5. Metadata firewall

Inference may consume only:
- runtime query text;
- Candidate-v2 returned candidate records and production-style fields required by the existing retrieval interface.

Inference must not read, branch on, score with, or otherwise use:
- gold answer;
- gold memory ID;
- `relevant_memory_ids`;
- benchmark stage;
- grammar family ID;
- discourse family ID;
- structural family ID;
- case ID;
- answerability label;
- expected relation;
- expected subject;
- expected output;
- distractor label;
- protected/confirmatory/final indicator;
- evaluator-only annotations;
- generator-private labels;
- template provenance.

Required firewall test: mutate all forbidden metadata while legitimate runtime input is byte-for-byte unchanged; Candidate-v13 output must remain byte-for-byte identical.

A firewall failure blocks formal evaluation.

## 6. Fixed stages, sizes, composition, and seeds

The four stages are mutually exclusive.

### Development
- total: `900`
- answerable: `540`
- no-evidence: `360`
- generation seed: `13013`
- execution count: unrestricted before freeze, but each result and meaningful change must be logged.

### Protected
- total: `720`
- answerable: `450`
- no-evidence: `270`
- generation seed: `26039`
- maximum legal execution count: `1`
- execution rule: exactly once after freeze prerequisites pass.

### Confirmatory
- total: `720`
- answerable: `450`
- no-evidence: `270`
- generation seed: `39019`
- maximum legal execution count: `1`
- only after Protected PASS.

### Final
- total: `900`
- answerable: `558`
- no-evidence: `342`
- generation seed: `52027`
- maximum legal execution count: `1`
- only after Confirmatory PASS.

Paired bootstrap:
- seed: `73129`
- iterations: `10000`
- interval: `95% percentile`
- noninferiority margin: `-0.01`
- primary statistic: paired answerable-case `R@1` difference.

## 7. Stage-disjoint grammar families

Grammar family membership logic is frozen here. A family is a structural generator mechanism, not a synonym list.

### Development grammar families
- `V13-DG1`: canonical wh/declarative relation query with a single explicit subject;
- `V13-DG2`: possessive or nominalized relation query;
- `V13-DG3`: two-clause query with proposition in the second clause;
- `V13-DG4`: parenthetical/appositive target-subject query;
- `V13-DG5`: explicit temporal qualifier plus relation query;
- `V13-DG6`: contrastive multi-entity query with one semantically targeted subject.

### Protected grammar families
- `V13-PG1`: passive/agentive relation realization;
- `V13-PG2`: relative-clause target embedding;
- `V13-PG3`: fronted temporal/prepositional relation realization;
- `V13-PG4`: indirect question with relation paraphrase;
- `V13-PG5`: coordinated propositions with one target relation and one nearby wrong relation.

### Confirmatory grammar families
- `V13-CG1`: cleft/pseudo-cleft target construction;
- `V13-CG2`: subject introduced after a discourse anaphor;
- `V13-CG3`: elliptical follow-up whose local clause still contains resolvable subject/relation evidence;
- `V13-CG4`: negated distractor clause plus affirmative target clause;
- `V13-CG5`: modality/status contrast with requested answer-type paraphrase.

### Final grammar families
- `V13-FG1`: narrative lead-in with embedded target proposition;
- `V13-FG2`: cross-clause coreference with explicit antecedent and target relation;
- `V13-FG3`: mixed nominal/verbal relation paraphrase across clauses;
- `V13-FG4`: sparse slot/value surface with temporal restriction;
- `V13-FG5`: distractor-heavy three-entity comparison;
- `V13-FG6`: contradiction-bearing evidence surface requiring hard eligibility and proof ordering.

After this preregistration commit, family membership logic may not be changed within Candidate-v13.

## 8. Stage-disjoint discourse families

Discourse family namespace is disjoint across stages. Exact surface templates are generator-private metadata and are forbidden at inference time.

### Development discourse families
- `V13-DD1`: direct factual request;
- `V13-DD2`: neutral informational lead-in;
- `V13-DD3`: instruction-before-proposition;
- `V13-DD4`: instruction-after-proposition;
- `V13-DD5`: contrastive setup;
- `V13-DD6`: two-sentence contextual setup.

### Protected discourse families
- `V13-PD1`: indirect referential framing;
- `V13-PD2`: parenthetical framing;
- `V13-PD3`: document/record-oriented framing;
- `V13-PD4`: multiple-named-entity framing;
- `V13-PD5`: answer-format instruction surrounding the proposition.

### Confirmatory discourse families
- `V13-CD1`: embedded-question framing;
- `V13-CD2`: concessive framing;
- `V13-CD3`: discourse-anaphoric framing;
- `V13-CD4`: coordination-heavy setup;
- `V13-CD5`: misleading lexical-overlap framing.

### Final discourse families
- `V13-FD1`: narrative context;
- `V13-FD2`: cross-clause referential framing;
- `V13-FD3`: sparse/elliptical framing;
- `V13-FD4`: mixed instruction/proposition order;
- `V13-FD5`: distractor-heavy natural-language framing;
- `V13-FD6`: contradiction/no-evidence framing.

## 9. Cross-stage freshness and disjointness

The generator must enforce and the audit must verify across every pair of stages:

- exact case ID overlap = `0`;
- exact query overlap = `0`;
- normalized query overlap = `0`;
- exact memory-text overlap = `0`;
- grammar-family overlap = `0`;
- discourse-family overlap = `0`;
- template-provenance overlap = `0`;
- generated entity identity overlap = `0` where the generator controls identity;
- generated value identity overlap = `0` where the generator controls values.

Structural skeleton overlap must be measured and reported. A generator implementation that collapses multiple frozen families into the same normalized skeleton is invalid and must be fixed before any formal payload is materialized.

Formal-stage lexical surfaces must not be inspected during Development.

## 10. Structural evaluation families

Every case is assigned one primary structural family by the generator. These labels are evaluator-only and forbidden at inference time.

- `S1 Subject Binding`: target subject, aliases/coreference, embedded named entities, distractor subjects.
- `S2 Relation Binding`: relation paraphrase, nearby wrong relations, related predicates, relation collision.
- `S3 Temporal Scope`: current/historical, before/after, bounded time, obsolete evidence.
- `S4 Discourse Contamination Resistance`: meta-instructions, answer-format words, surrounding discourse, irrelevant imperative verbs.
- `S5 Evidence Eligibility`: direct support, partial support, contradiction, ambiguity, subject mismatch, relation mismatch.
- `S6 Abstention Safety`: no valid evidence, only contradiction, wrong subject, wrong relation, misleading lexical match.
- `S7 Proof Ordering`: direct over indirect, precise over underspecified, temporally valid over weaker temporal support, proposition-complete over partial proof.

Each formal stage must contain all seven structural families. The generator must distribute cases so that no family has fewer than 8% of the stage total.

## 11. Immutable metric definitions

Ranking metrics on answerable cases:
- MRR;
- R@1;
- R@3;
- R@5;
- eligible rank-1 accuracy.

Eligibility/safety metrics:
- answerable recall;
- false abstention rate;
- false retrieval rate;
- abstention accuracy.

Structural metrics:
- subject binding accuracy;
- relation binding accuracy;
- temporal scope accuracy;
- discourse contamination resistance accuracy/rate;
- evidence eligibility accuracy;
- abstention safety accuracy;
- proof ordering accuracy.

A false retrieval is any returned evidence item not gold-relevant for the generated case. A false abstention is an answerable case with gold-relevant evidence present in the Candidate-v2 candidate set but no eligible evidence returned.

Eligible rank-1 accuracy is the proportion of answerable cases whose top returned eligible evidence is gold-relevant.

MRR/R@k are computed on answerable cases against the ordered Candidate-v13 returned evidence IDs.

Determinism requires byte-identical output on repeated execution over identical legitimate runtime input.

## 12. Development acceptance criteria

Development PASS requires all conditions simultaneously:

Aggregate:
- MRR >= `0.985`
- R@1 >= `0.980`
- R@3 >= `0.995`
- R@5 >= `0.998`
- answerable recall >= `0.995`
- false abstention <= `0.005`
- false retrieval <= `0.020`
- abstention accuracy >= `0.980`
- eligible rank1 accuracy >= `0.980`

Structural:
- subject binding accuracy >= `0.990`
- relation binding accuracy >= `0.985`
- temporal accuracy >= `0.985`
- discourse contamination rate <= `0.010`

Safety:
- metadata firewall = PASS
- Candidate-v2 source invariant = PASS
- deterministic replay = PASS
- no formal-payload exposure = PASS

Development may iterate while not frozen. Thresholds, formal sizes/seeds, formal family membership, formal evaluator rules, formal execution maxima, and terminal-state rules may not be changed after Development has been materialized.

## 13. Protected acceptance criteria

Protected is a one-shot decision.

Aggregate:
- MRR >= `0.980`
- R@1 >= `0.970`
- R@3 >= `0.990`
- R@5 >= `0.995`
- answerable recall >= `0.990`
- false abstention <= `0.010`
- false retrieval <= `0.030`
- abstention accuracy >= `0.970`
- eligible rank1 accuracy >= `0.970`

Structural family floors:
- Subject Binding >= `0.970`
- Relation Binding >= `0.960`
- Temporal Scope >= `0.960`
- Discourse Resistance >= `0.960`
- Evidence Eligibility >= `0.970`
- Abstention Safety >= `0.970`
- Proof Ordering >= `0.960`

Mandatory safety:
- metadata firewall = PASS
- Candidate-v2 source invariant = PASS
- deterministic replay = PASS
- all anti-collapse gates = PASS
- noninferiority rule evaluated if and only if the frozen Candidate-v12 baseline can be provenance-verified.

Any required family-floor failure is Protected FAIL even if aggregate metrics pass.

## 14. Protected anti-collapse gates

Any of the following is Protected FAIL:
- single-class prediction collapse;
- near-universal abstention;
- near-universal retrieval;
- one structural family catastrophic collapse;
- systematic subject-binding collapse;
- systematic relation-binding collapse;
- discourse tokens becoming the dominant semantic subject;
- metadata leakage;
- nondeterministic formal outputs;
- formal payload tampering;
- Candidate-v2 source-invariant violation.

Operational definitions:
- near-universal abstention: >= `95%` of all Protected cases return no eligible evidence;
- near-universal retrieval: >= `95%` of all Protected cases return at least one eligible item AND false retrieval > `0.10`;
- catastrophic structural-family collapse: any required structural-family accuracy < `0.50`;
- single-class prediction collapse: >= `95%` of cases share the same binary retrieve/abstain outcome while both answerable and no-evidence classes each comprise >= `30%` of the stage.

## 15. Noninferiority analysis

Primary baseline:
- frozen Candidate-v12 architecture snapshot or historical implementation, only if repository provenance permits exact reconstruction without modifying Candidate-v12.

This is not a Candidate-v12 Protected rerun. It is a comparison of a frozen historical implementation on the fresh Candidate-v13 Protected surface.

If Candidate-v12 baseline provenance cannot be verified:
- comparison status = `NOT_EVALUABLE`;
- this alone does not fail Candidate-v13;
- no noninferiority claim may be made.

If baseline is provenance-verified:
- primary metric = paired answerable-case R@1;
- statistic = `Candidate-v13 R@1 - baseline R@1`;
- paired nonparametric bootstrap;
- seed = `73129`;
- iterations = `10000`;
- interval = `95% percentile`;
- margin = `-0.01`;
- PASS only if CI lower bound >= `-0.01`.

Absolute Protected thresholds remain independently mandatory.

## 16. Confirmatory acceptance criteria

Confirmatory may be materialized/executed only after Protected PASS.

Aggregate:
- MRR >= `0.975`
- R@1 >= `0.965`
- R@3 >= `0.990`
- R@5 >= `0.995`
- answerable recall >= `0.990`
- false abstention <= `0.010`
- false retrieval <= `0.030`
- abstention accuracy >= `0.970`
- eligible rank1 accuracy >= `0.965`

Structural floors:
- Subject >= `0.960`
- Relation >= `0.950`
- Temporal >= `0.950`
- Discourse >= `0.950`
- Eligibility >= `0.960`
- Abstention >= `0.960`
- Proof Ordering >= `0.950`

Mandatory:
- metadata firewall PASS;
- source invariant PASS;
- determinism PASS;
- no anti-collapse violation.

Maximum execution count: `1`. FAIL terminates Candidate-v13 and may not be rerun.

## 17. Final Gate F acceptance criteria

Final may be materialized/executed only after Confirmatory PASS and must be an unseen distribution.

Aggregate:
- MRR >= `0.975`
- R@1 >= `0.965`
- R@3 >= `0.990`
- R@5 >= `0.995`
- answerable recall >= `0.990`
- false abstention <= `0.010`
- false retrieval <= `0.030`
- abstention accuracy >= `0.970`
- eligible rank1 accuracy >= `0.965`

Structural floors:
- Subject >= `0.960`
- Relation >= `0.950`
- Temporal >= `0.950`
- Discourse >= `0.950`
- Eligibility >= `0.960`
- Abstention >= `0.960`
- Proof Ordering >= `0.950`

Mandatory:
- deterministic;
- metadata-safe;
- Candidate-v2 source-invariant;
- anti-collapse safe.

Maximum execution count: `1`.

## 18. Development-to-formal freeze

A freeze is authorized only after Development PASS.

The freeze manifest must hash and identify at minimum:
- Candidate-v13 implementation source;
- Candidate-v13 generator;
- Candidate-v13 evaluator;
- Candidate-v13 formal runner;
- Candidate-v13 tests;
- cross-stage freshness audit;
- this preregistration;
- Development benchmark;
- Development result;
- configuration, if any;
- Python/runtime/dependency versions;
- inference entrypoint;
- metadata firewall result;
- source-invariant result;
- determinism result;
- formal execution ledger.

Initial formal ledger at freeze:
```json
{"protected": 0, "confirmatory": 0, "final": 0}
```

After the freeze manifest is committed, Candidate-v13 algorithm/evaluator/formal-generator logic is immutable.

## 19. Formal runner requirements

Before Protected, a deterministic formal runner must exist and must:
- validate freeze manifest;
- validate source hashes;
- validate preregistration hash;
- validate execution ledger;
- reject a second execution;
- reject wrong stage ordering;
- reject source or frozen-evaluator mismatch;
- prevent metadata injection;
- produce append-only results;
- produce machine-readable summary;
- store environment provenance;
- record benchmark hash;
- record result hash;
- record UTC run timestamp.

The runner must not expose formal individual-case content to Development code paths.

## 20. Protected materialization boundary

Protected may be materialized only if:
- preregistration is locked;
- Development PASS;
- Candidate-v13 is frozen;
- freeze manifest validates;
- source hash validates;
- formal runner validates;
- ledger is exactly `0/0/0`;
- metadata firewall PASS;
- Candidate-v2 source invariant PASS;
- determinism PASS.

After Protected payload materialization, no algorithmic modification is legal.

## 21. Historical-use firewall

Candidate-v7 through Candidate-v12 are immutable.

Historical evidence may be used only at high level to motivate architecture or, for Candidate-v12, as a provenance-verified frozen baseline on fresh Candidate-v13 Protected data.

Forbidden in Candidate-v13 datasets/tests:
- exact historical formal query;
- exact historical formal memory text;
- exact historical formal entity/value identity;
- exact historical formal distractor;
- exact historical formal case ID/composition.

Candidate-v12 Development evidence may inform the architectural hypothesis, but Candidate-v13 must rebuild its own Development evidence.

## 22. Anti-overfitting rules

Every Development change must be tied to a general failure class and logged with:
- root cause;
- architecture/rule-level change;
- abstracted regression case that does not copy any historical formal case;
- retained prior Development evidence;
- new Development result.

Forbidden:
- case-specific exception tables;
- deleting failing cases;
- editing gold labels to fit output;
- lowering thresholds;
- replacing difficult cases with easier ones;
- using any formal-stage payload for tuning;
- hardcoding formal-stage template wording.

## 23. Formal failure and integrity rules

After freeze, any algorithmic/formal threshold failure terminates Candidate-v13.

Research-integrity failure is triggered by any of:
- post-Development formal-threshold modification;
- formal dataset exposure before freeze;
- formal payload used for tuning;
- formal rerun;
- execution-ledger inconsistency;
- hash mismatch;
- metadata leakage;
- formal result overwritten;
- historical Candidate modified;
- stage-order violation;
- formal seed changed after preregistration;
- benchmark payload regenerated after outcome inspection;
- formal case removed because it failed;
- evaluator changed after formal result to alter the decision.

Research-integrity terminal state:
`CANDIDATE_V13_RESEARCH_INTEGRITY_FAILURE`

Infrastructure-blocked state is legal only when an objectively verified infrastructure failure prevents valid formal inference from beginning. Once formal inference has begun, an unfavorable outcome may not be reclassified as infrastructure failure.

Infrastructure terminal state:
`CANDIDATE_V13_INFRASTRUCTURE_BLOCKED`

## 24. Exact terminal states

The only Candidate-v13 terminal states are:
1. `CANDIDATE_V13_FINAL_GATE_F_PASS`
2. `CANDIDATE_V13_PROTECTED_FAIL`
3. `CANDIDATE_V13_CONFIRMATORY_FAIL`
4. `CANDIDATE_V13_FINAL_GATE_F_FAIL`
5. `CANDIDATE_V13_RESEARCH_INTEGRITY_FAILURE`
6. `CANDIDATE_V13_INFRASTRUCTURE_BLOCKED`

Protected PASS and Confirmatory PASS are intermediate states only.

## 25. Cost and determinism policy

Target monetary cost: `0 USD`.

No paid API, remote LLM reranker, or stochastic external semantic service is authorized. Candidate-v13 must be deterministic under identical legitimate runtime inputs.

## 26. Preregistration provenance rule

Embedding this file's own Git commit SHA or Git blob SHA inside the committed bytes would be circular. Therefore the authoritative lock record is written only after this file is committed and must include:
- preregistration Git commit SHA;
- preregistration Git blob SHA;
- SHA256 of these exact bytes;
- commit UTC timestamp;
- branch;
- repository;
- historical parent anchor.

The lock record must itself be committed before any Candidate-v13 Development payload is materialized.

After the preregistration commit exists, this file is immutable. If a fatal protocol defect is discovered before Development materialization, the existing preregistration history must remain visible and a replacement preregistration lineage may be created. If Development has been materialized, formal acceptance protocol changes require terminating Candidate-v13 and moving to Candidate-v14.
