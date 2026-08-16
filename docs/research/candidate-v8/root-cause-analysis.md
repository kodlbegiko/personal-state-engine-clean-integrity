# Candidate-v8 Independent Root-Cause Analysis

## Evidence discipline

Candidate-v8 root-cause hypotheses, architecture alternatives, the development protocol, and the fresh-generator design were preregistered in commit `182eb1da70bf33952e2cdf3091f2c4e73fef05f3` **before** opening the Candidate-v7 140-case confirmatory semantic payload. Candidate-v7 confirmatory was then explicitly reclassified as `HISTORICAL_DIAGNOSTIC_ONLY` in `results/candidate-v8/historical-diagnostic-access-v1.json` before semantic access.

That historical surface is permanently excluded from Candidate-v8 development gates, threshold tuning, protected validation, confirmatory evaluation, and final Gate F. The retired historical Gate F 99-case semantic payload was never opened; only its manifest hashes/provenance may be used.

## Frozen observed failure counts

Candidate-v7 confirmatory had 85 answerable and 55 no-evidence cases. Candidate-v7 produced 7/85 false abstentions and 10/55 false retrievals. Candidate-v2 retained perfect ranking quality on that surface but retrieved on all no-evidence cases. Candidate-v7 therefore traded away answerability while still allowing unsafe retrievals and failed its frozen non-inferiority rule.

## A. Candidate-v7 false abstention: 7/85 fully classified

### A1 — relation realization mismatch: 3 cases

Historical diagnostic IDs: `CV7CONF-A-000`, `CV7CONF-A-022`, `CV7CONF-A-044`.

The query asks for a drink using forms such as `reach for most often`; the factual evidence uses `usually chooses <beverage>`. Candidate-v7 primarily types the query as `food_drink`, while the evidence is realized through preference/choice language. Unless the open-vocabulary beverage itself accidentally contains a listed cue such as `tea`, the relation-family compatibility test can fail despite correct subject and direct factual value.

Supported hypotheses: relation-family missing, lexical mismatch, low-overlap evidence, natural-language variation, and over-reliance on finite compatibility families.

### A2 — public-transport paraphrase plus lexical threshold: 4 cases

Historical diagnostic IDs: `CV7CONF-A-011`, `CV7CONF-A-033`, `CV7CONF-A-055`, `CV7CONF-A-077`.

The query is `Which public transport does <subject> take?`; evidence is `<subject> rides <route> ...`. The strict direct path does not robustly connect the query wording to `rides`, and the generic path falls back to lexical anchor coverage. Coverage remains about one-third, narrowly below Candidate-v7's `0.34` fallback threshold.

This is a structural interaction between finite relation coverage and a brittle lexical threshold. Lowering `0.34` would be benchmark chasing; Candidate-v8 instead requires explicit evidence requirements and multiple support signals.

### False-abstention conclusion

All 7 failures are explained by heterogeneous natural-language relation realization rather than missing evidence or Candidate-v2 retrieval failure. No evidence from these seven cases requires a case-ID patch.

## B. Candidate-v7 false retrieval: 10/55 fully classified

### B1 — meta-discussion paraphrase escape: 5 cases

Historical diagnostic IDs: `CV7CONF-N-004`, `CV7CONF-N-015`, `CV7CONF-N-026`, `CV7CONF-N-037`, `CV7CONF-N-048`.

Pattern: `The notes only discuss the question about <subject>'s music taste.` Candidate-v7's finite `META_ONLY` regex misses this paraphrase. Because subject, coarse relation and novel lexical material are present, the generic positive path incorrectly treats discussion *about the question* as evidence answering the question.

Classification: meta-discussion + semantically-nearby-but-unsupported + generic relation-family collision.

### B2 — no-value paraphrase escape: 5 cases

Historical diagnostic IDs: `CV7CONF-N-005`, `CV7CONF-N-016`, `CV7CONF-N-027`, `CV7CONF-N-038`, `CV7CONF-N-049`.

Pattern: `No verified information about <subject>'s medication is available.` This natural no-value construction escapes Candidate-v7's finite absence grammar. The sentence still contains subject and medication/health cues, and `is available` looks assertion-like to the positive path, so an explicit absence-of-evidence statement is accepted as evidence.

Classification: explicit unknown/no-value + natural-language variation + finite-blocker coverage failure.

### False-retrieval conclusion

All 10 failures are explained by open-ended paraphrases of non-evidence speech acts escaping whole-memory regex blockers. Growing a blacklist is not a sufficient abstraction.

## C. Structural architecture flaw

Candidate-v7 does:

1. Candidate-v2 creates top-k ranking.
2. Candidate-v7 scans ranked memories for any accepted support.
3. If one support exists, Candidate-v7 returns the **entire** Candidate-v2 ranking; otherwise it returns `[]`.

This means one false-positive evidence decision can unlock multiple unsupported memories, and a correct support decision cannot filter same-subject/wrong-relation distractors in the rest of top-k. Support is not bound to the requirements of each returned memory.

Candidate-v8 therefore changes the abstraction to:

`query requirements -> clause segmentation -> clause-local hard blockers + positive evidence signals -> per-memory certification -> order-preserving Candidate-v2 subsequence`

Candidate-v2 remains rank authority; Candidate-v8 never numerically reranks certified memories.

## D. Fresh-development evidence and retained negative iteration

Candidate-v8 development iteration 0 failed the fresh 240-case development surface and was retained. It exposed three defects independently of the historical confirmatory pass gate:

- `RELATION_INFLECTION_STUDIES_GAP`: course/taking queries versus factual `studies` form;
- `FIRST_PERSON_I_MISBOUND_AS_ENTITY_ANCHOR`: capitalized `I` was treated as a named entity;
- `SAME_SUBJECT_DIFFERENT_OBJECT_ATTRIBUTE_COLLISION`: an attribute query about one object could certify a fact about another object belonging to the same subject.

The iteration-0 source is reproducible from the retained `iter0-to-iter1.patch` plus the frozen iteration-1 source, and its SHA-256 is recorded in the development ledger. Fixes were general: inflection handling, explicit first-person binding, and object anchors for attribute/state requirements.

Iteration 1 then passed development with Candidate-v8 MRR=1.0, answerable recall=1.0, false abstention=0, false retrieval=0, and zero Candidate-v2 order-preservation violations. This is only a development result; protected and confirmatory evaluations remain mandatory.

## E. Integrity deviation identified before freeze

Provisional local surfaces originally associated with dataset seeds `2026081501` and `2026081502` were generated/inspected during pre-freeze implementation work. They were never committed or formal executions. They are permanently retired as local diagnostics. Formal protected and confirmatory datasets use fresh seeds `2026081511` and `2026081522`; the original numbers remain only as bootstrap RNG seeds. See `results/candidate-v8/pre-freeze-local-smoke-contamination-v1.json`.
