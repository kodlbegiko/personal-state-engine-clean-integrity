# Candidate-v12 Preregistration

Status: FROZEN BEFORE ANY NEW INDIVIDUAL CANDIDATE-V11 PROTECTED-CASE INSPECTION

Created (UTC): `2026-08-15T13:46:51Z`

Repository: `kodlbegiko/personal-state-engine-clean-integrity`  
Parent terminal commit: `8faf4965fdf99eae0c154de012939eb33295cbab`  
Candidate-v12 branch: `research/candidate-v12-fresh-lineage`  
Historical terminal state preserved: `CANDIDATE_V11_PROTECTED_FAIL`

## 1. Research question

Can a deterministic, discourse-robust semantic-frame extraction architecture separate discourse framing from the semantic proposition, bind subject/relation/object/temporal slots under unseen natural-language wrappers, and thereby preserve evidence eligibility without weakening Candidate-v11's evidence-safety, abstention, metadata-firewall, determinism, and Candidate-v2 candidate-source contracts?

The target failure class is upstream eligibility collapse under discourse-framing distribution shift. Candidate-v11's accepted post-eligibility rank-refinement result remains valid historical evidence and is not discarded.

## 2. Architecture hypotheses

At least four architectures are frozen for comparison.

### A — Frozen Candidate-v11 baseline

Use the immutable Candidate-v11 semantic extraction / eligibility logic followed by its Layer-2 rank refinement. No Candidate-v11 source modification is permitted.

Hypothesis: A will preserve known safety but remain vulnerable to discourse-frame contamination of mandatory semantic anchors.

### B — Bounded discourse-wrapper stripping baseline

Apply a bounded normalization layer intended to remove likely non-semantic discourse wrappers, then invoke Candidate-v11 parsing/ranking.

This is a diagnostic baseline, not the preferred production architecture. It must not be implemented as a list of historical Protected prefixes/tokens. It is expected to expose brittleness to unseen wrappers and semantic-deletion risk.

### C — Structured query semantic-frame parser

Parse the runtime query into an explicit structure:

- `discourse_intent`
- `semantic_proposition_spans`
- `subject_entities`
- `subject_coreference`
- `relation_frame`
- `predicate_constraints`
- `object_constraints`
- `temporal_scope`
- `modality`
- `answer_type`

Evidence eligibility is certified against semantic slots rather than generic capitalized/query-adjacent tokens. Candidate-v11 Layer-2 ranking is retained after eligibility.

Primary hypothesis: explicit proposition/slot separation will improve answerable recall and reduce false abstention under unseen discourse wrappers while preserving false-retrieval safety.

### D — Clause-first proposition graph with conservative slot binding

Segment the query into clauses, classify each clause/span as discourse scaffold versus proposition-bearing content using deterministic structural cues, then construct a proposition graph with entity/relation/object/temporal bindings. Eligibility requires agreement on safety-critical slots; unresolved ambiguity causes abstention rather than permissive matching. Candidate-v11 Layer-2 ranking remains downstream.

Hypothesis: clause-first binding will be more robust than surface wrapper stripping and may outperform C on multi-clause, appositive, passive, nominalized, possessive, and prepositional paraphrases, at the cost of greater abstention when structure is genuinely ambiguous.

No architecture may use benchmark labels, case IDs, stage names, grammar/discourse-family IDs, relevant-memory IDs, gold answers, generator provenance, or historical Protected wording at inference time.

## 3. Immutable metric definitions

Ranking metrics on answerable cases:

- MRR
- R@1
- R@3
- R@5
- Eligible Rank-1 Accuracy

Eligibility / safety metrics:

- answerable recall
- false abstention rate
- false retrieval rate
- abstention accuracy
- eligible answerable count / rate
- hard-blocker violation count
- candidate-source invariant violation count
- metadata-firewall violation count
- determinism violation count

Frame-extraction diagnostics, measured only on synthetic Development data with generator-known semantic annotations:

- subject exact-span accuracy
- subject mandatory-anchor precision
- subject mandatory-anchor recall
- relation-frame accuracy
- object-constraint accuracy
- temporal-scope accuracy
- proposition-span accuracy
- discourse-token contamination rate
- extra-anchor rate
- missing-anchor rate
- incorrect mandatory-anchor rate

A returned evidence item is a false retrieval if it is not gold-relevant on the evaluation surface. An answerable case is a false abstention if the system returns no eligible evidence while gold-relevant evidence is present in the Candidate-v2 candidate set.

## 4. Immutable thresholds

Thresholds may be tightened before Development materialization only by a new preregistration lineage; they may never be lowered within Candidate-v12.

### Development acceptance

- MRR >= 0.98
- R@1 >= 0.97
- R@3 >= 0.99
- R@5 >= 0.995
- answerable recall >= 0.99
- false abstention <= 0.01
- false retrieval <= 0.03
- abstention accuracy >= 0.97
- Eligible Rank-1 Accuracy >= 0.97
- subject mandatory-anchor precision >= 0.99
- subject mandatory-anchor recall >= 0.99
- relation-frame accuracy >= 0.98
- temporal-scope accuracy >= 0.98
- discourse-token contamination rate <= 0.01
- safety invariants = PASS
- metadata firewall = PASS
- determinism = PASS

### Protected acceptance

- MRR >= 0.97
- R@1 >= 0.96
- R@3 >= 0.99
- R@5 >= 0.995
- answerable recall >= 0.99
- false abstention <= 0.01
- false retrieval <= 0.03
- abstention accuracy >= 0.97
- safety invariants = PASS
- metadata firewall = PASS
- determinism = PASS
- Candidate-v12 R@1 must not be statistically materially inferior to frozen Candidate-v11 on the same fresh Candidate-v12 Protected surface under the noninferiority rule in Section 9

### Confirmatory acceptance

Same absolute ranking/safety thresholds as Protected, plus integrity = PASS and no post-freeze code/config/generator mutation.

### Final acceptance

Same absolute ranking/safety thresholds as Protected, plus integrity = PASS and every prerequisite formal gate must have passed exactly once.

## 5. Benchmark sizes

- Development: 720 total = 432 answerable + 288 no-evidence
- Protected: 480 total = 300 answerable + 180 no-evidence
- Confirmatory: 540 total = 336 answerable + 204 no-evidence
- Final: 660 total = 408 answerable + 252 no-evidence

Development may be regenerated only before Development freeze and only with the frozen Development seed and generator logic. Protected/Confirmatory/Final are one-shot formal surfaces after materialization.

## 6. Benchmark seeds

Frozen seeds:

- Development generation: `12031`
- Protected generation: `24043`
- Confirmatory generation: `36061`
- Final generation: `48073`
- paired bootstrap: `59117`
- bootstrap iterations: `10000`

No formal-stage seed replacement is permitted.

## 7. Grammar-family separation

Grammar families must be structurally disjoint across stages, not synonym swaps.

- Development: `DA`, `DB`, `DC`, `DD`, `DE`, `DF`
- Protected: `PA`, `PB`, `PC`, `PD`
- Confirmatory: `CA`, `CB`, `CC`, `CD`, `CE`
- Final: `FA`, `FB`, `FC`, `FD`, `FE`, `FF`

Mechanism families may include active declaratives, wh-fronting, possessive nominalization, passives, appositives, relative clauses, elliptical questions, indirect relational statements, prepositional paraphrases, slot/value forms, multi-clause competition, and coreferential forms. Each stage receives a disjoint structural allocation.

Required across every stage pair:

- exact query overlap = 0
- normalized query overlap = 0
- exact memory-text overlap = 0
- entity/value overlap by generated identity = 0
- grammar-family overlap = 0
- template-provenance overlap = 0

Skeleton overlap is measured and reported; high overlap blocks freeze pending methodology review.

## 8. Discourse-family separation

Discourse framing is independently varied from grammar.

- Development discourse families: `D0` direct/no-wrapper, `D1` neutral informational lead-in, `D2` conversational context, `D3` document-oriented framing, `D4` contrastive setup, `D5` multi-sentence setup
- Protected discourse families: `P0` direct/no-wrapper, `P1` indirect referential framing, `P2` contextualized request, `P3` parenthetical framing
- Confirmatory discourse families: `C0` direct/no-wrapper, `C1` embedded-question framing, `C2` discourse-anaphoric framing, `C3` concessive framing, `C4` coordination-heavy setup
- Final discourse families: `F0` direct/no-wrapper, `F1` narrative lead-in, `F2` cross-clause referential framing, `F3` mixed nominal/verbal framing, `F4` sparse/elliptical framing

Family identifiers and exact templates are generator metadata and are forbidden at inference time.

## 9. Statistical test

Primary paired comparison on each fresh formal surface:

- frozen Candidate-v11 versus frozen Candidate-v12
- exact same candidate surface per case
- primary statistic: paired answerable-case R@1 difference
- nonparametric paired bootstrap
- 10,000 iterations
- seed `59117`
- 95% percentile confidence interval

Noninferiority margin for Candidate-v12 minus Candidate-v11 R@1 is frozen at `-0.01`. Protected noninferiority passes only if the lower endpoint of the 95% bootstrap CI is >= -0.01.

The absolute acceptance thresholds remain independently mandatory; noninferiority cannot rescue an absolute-threshold failure.

## 10. Freeze policy

Development may iterate only on Candidate-v12 code, Candidate-v12 tests, Candidate-v12 Development generator/evaluator, Development-only diagnostics, and architecture records.

Protected, Confirmatory, and Final payloads must remain unread and unmaterialized during Development.

After Development PASS, create a freeze manifest hashing at minimum:

- Candidate-v12 implementation
- Candidate-v12 benchmark generator
- Candidate-v12 evaluator
- freshness audit
- formal runner
- config
- Candidate-v12 tests
- this preregistration
- architecture decision record

After freeze, these components are immutable. No code, config, prompt, parser rule, benchmark generator, evaluator, or threshold change is allowed between Protected, Confirmatory, and Final.

## 11. Stopping rules

Formal execution maxima:

- Protected: exactly one execution
- Confirmatory: at most one execution and only after Protected PASS
- Final: at most one execution and only after Confirmatory PASS

Initial counts:

```json
{"protected": 0, "confirmatory": 0, "final": 0}
```

Stop immediately on:

1. Protected algorithmic/threshold FAIL
2. Confirmatory algorithmic/threshold FAIL
3. Final algorithmic/threshold FAIL
4. any integrity violation
5. objectively verified infrastructure blocker that prevents a valid result
6. Final PASS

No rerun, relabeling, threshold lowering, or post-hoc algorithmic repair is permitted after a formal-stage algorithmic result.

## 12. Terminal states

Only these Candidate-v12 terminal states are valid:

- `CANDIDATE_V12_FINAL_GATE_F_PASS`
- `CANDIDATE_V12_PROTECTED_FAIL`
- `CANDIDATE_V12_CONFIRMATORY_FAIL`
- `CANDIDATE_V12_FINAL_GATE_F_FAIL`
- `CANDIDATE_V12_RESEARCH_INTEGRITY_FAILURE`
- `CANDIDATE_V12_INFRASTRUCTURE_BLOCKED`

A formal algorithmic failure terminates Candidate-v12.

## 13. Candidate-v11 historical-data usage policy

Before this preregistration commit, only mission-supplied aggregate Candidate-v11 metrics, formal counts, terminal state/provenance, frozen-source hash, and existing non-case-level historical research records may be used.

After this preregistration commit, Candidate-v11 Protected may be inspected only for the mandatory diagnostic taxonomy described by the mission.

Candidate-v11 Protected may never be rerun. Candidate-v11 source may never be modified. Historical individual cases may not be copied into Candidate-v12 Development, Protected, Confirmatory, Final, unit tests, or regression fixtures.

The frozen Candidate-v11 algorithm may be executed on fresh Candidate-v12 surfaces for paired comparison.

## 14. Protected-data prohibition

Forbidden during Candidate-v12 Development and implementation:

- exact Candidate-v11 Protected query strings
- exact Candidate-v11 Protected memory strings
- exact entity names/values/case IDs
- relevant-memory IDs
- Protected grammar/discourse labels
- benchmark labels or gold answers
- regexes, token lists, prefixes, suffixes, or exceptions derived from individual Protected wording

Historical Protected data is diagnostic-only after preregistration and must never enter a Candidate-v12 test fixture or generator.

## 15. Anti-overfitting rules

Every Development change must be justified by a failure class and accompanied by:

- stated root cause
- architecture/rule-level change
- abstracted regression fixture that is lexically and structurally distinct from historical Protected examples
- retained previous Development evidence
- new Development result

Forbidden:

- case-specific exception tables
- deleting failing cases
- editing gold labels to fit output
- lowering thresholds
- replacing difficult Development cases with easier ones
- using formal-stage payloads for tuning
- hardcoding historical discourse-introducer tokens solely because they appeared in Candidate-v11 Protected

## 16. Metadata firewall

Candidate-v12 inference may consume only:

- runtime query text
- Candidate-v2 returned candidate records/fields that are part of the production-style retrieval interface

It must not read, branch on, score with, or otherwise use:

- `relevant_memory_ids`
- gold labels/answers
- split/stage name
- grammar-family ID
- discourse-family ID
- semantic-domain metadata
- template/generator provenance
- designation
- case ID
- hidden evaluation metadata

Firewall tests must mutate forbidden metadata while legitimate runtime input remains fixed; output must remain byte-for-byte identical.

## 17. Candidate-source invariants

Candidate-v2 remains the exclusive candidate source.

Candidate-v12 may:

- certify/invalidate eligibility among Candidate-v2-returned memories
- reorder eligible Candidate-v2-returned memories

Candidate-v12 may not:

- inject a memory absent from Candidate-v2 output
- mutate Candidate-v2
- rescue hard-ineligible candidates
- use external retrieval to alter the candidate set

Required invariant: every returned evidence item is a member of the original Candidate-v2 candidate set; returned evidence is a subsequence/permutation of eligible Candidate-v2 candidates only.

## 18. Subject/entity extraction invariants

- discourse scaffold tokens are never mandatory subject entities merely because of capitalization, sentence position, punctuation adjacency, or wrapper position
- subject entities must derive from proposition-bearing spans or resolved coreference
- entity spans may not include generic discourse labels unless they are semantically part of the queried entity
- multiple genuine subject entities must remain distinct
- unresolved entity ambiguity must fail closed rather than broaden eligibility
- no historical Protected token blacklist is allowed

## 19. Relation-frame invariants

- relation extraction must operate on semantic proposition content, not on generic request verbs alone
- verbal, nominalized, passive, possessive, prepositional, slot/value, and indirect paraphrases must map to a normalized relation frame through general rules
- relation matching must not depend on benchmark family IDs or exact template strings
- weakening relation constraints to improve recall is forbidden if it increases false retrieval beyond threshold
- unresolved relation ambiguity must remain explicit and cannot be silently coerced into a convenient relation

## 20. Abstention-safety requirements

Candidate-v12 must reduce false abstention by fixing semantic-frame extraction, not by weakening evidence certification globally.

Required:

- no blanket permissive fallback
- no “return top Candidate-v2 result when parsing fails”
- no eligibility rescue based solely on lexical overlap
- parsing uncertainty must be represented and may trigger abstention
- no-evidence cases must remain protected by hard blockers and semantic constraints
- false retrieval threshold is safety-critical and cannot be traded away for recall

## 21. Historical-failure firewall

Any regression inspired by Candidate-v11 Protected must be labeled `abstracted historical regression` and must differ in query wording, discourse construction, entity identity, value, memory wording, and case identifier. Exact Protected strings or named prefixes are prohibited.

## 22. Cost and determinism policy

Target monetary cost: `0 USD`.

No paid API, remote LLM reranker, or stochastic external semantic service is authorized. Candidate-v12 must be deterministic under identical legitimate runtime inputs.

## 23. Preregistration provenance

This file's SHA256 is recorded externally after the commit is created, because embedding the Git commit SHA inside the committed bytes would be circular. The authoritative provenance record must include:

- this preregistration commit SHA
- SHA256 of this exact file content
- UTC timestamp

No new individual Candidate-v11 Protected-case inspection may occur before this preregistration commit exists.
