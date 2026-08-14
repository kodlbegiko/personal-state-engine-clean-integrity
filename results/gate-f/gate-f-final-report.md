# Candidate-v6 Gate F Sealed-Final Evaluation — Final Report

## Executive verdict

- Candidate: `candidate-v6` / Assertion-Structure Evidence Objects
- Clean-lineage Gate E: **COMPLETE**
- Formal Gate F: **NOT COMPLETE**
- Gate F selection verdict: **FAIL**
- Gate F integrity verdict: **PASS**
- Terminal state: `GATE_F_SELECTION_FAIL`
- Algorithm parity: **NO**
- Gate G: **NOT STARTED**
- New monetary cost: **USD 0**

The result is accepted fail-closed. Candidate-v6 must not be modified and rerun against this same sealed-final benchmark.

## Authorization and preregistration

Human authorization was recorded before Gate F execution at clean-lineage commit:

`cb23d831e1019e21e681b59afb8c29a7fe9cfc8d`

The Gate F protocol was preregistered before sealed-final path resolution/payload access at commit:

`20bbadface7268d2e2c3279c0774fb61502c6b0e`

The protocol froze the metrics, guardrails, 10,000 paired-bootstrap procedure, seed `20260814`, noninferiority margin `0.03`, single-execution rule, and claim boundaries.

## Sealed-final identity

- Benchmark: archived LongMemEval-S cleaned sealed-final split
- Dataset SHA-256: `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`
- Split-file SHA-256: `1f5cb377ce971931dffc0be97550240181ea9062d4ae1dd1251af432ca8f015f`
- Case-ID set SHA-256: `1ca053112b634871d24addbb3982d4e417dc8f4acce10609554cc41b6ed8e987`
- Total cases: 99
- Answerable: 93
- Official no-evidence/abstention: 6
- Missing: 0
- Duplicate: 0
- Invalid: 0

No raw semantic sealed-final payload was copied into the clean public repository.

## Candidate identity

Candidate-v6 remained byte-identical to its Gate E frozen identity:

- Source SHA-256: `c540056c6f30f0145ab8ef8c10be3abcae2ed24e6a087a2d9a3531bc5e545325`
- Config SHA-256: `067bfa64d97bf2eb1f7208082c36d202118a0e50a2414fc345bf328f83cab5b1`
- Candidate modified after sealed exposure: **false**

## Schema adapter

The official LongMemEval schema was mapped mechanically into the frozen PSE retrieval-case schema before formal selection execution:

- each history turn became one immutable memory;
- the original turn text was used unchanged;
- the official session timestamp was preserved;
- `has_answer=true` turns defined relevant evidence for non-abstention cases;
- official `_abs` cases defined no-evidence cases;
- no answer text, benchmark-specific lexicon, or result-specific rule was used by the adapter.

Synthetic adapter tests passed in the CI Test step on Python 3.11, 3.12 and 3.13 before the formal selection-bearing run. The broader historical CI subsequently failed only at benchmark-lock freshness because the new Python evaluator changed the repository's broad benchmark-affecting input set; this failure was preserved and was not used to alter the Gate F adapter, candidate, sealed benchmark, or Gate F thresholds.

## Formal execution provenance

- Workflow: `Gate F Sealed-Final Single Execution`
- Run ID: `31801039217`
- Attempt: `1`
- Job ID: `94768816797`
- Trigger commit: `8da87b2f8d1d3dbbfcc168a8f7c700e6f3bec4f8`
- Selection execution count: `1`
- Workflow conclusion: `success`
- Result-bearing rerun: **false**
- Artifact ID: `9219287805`
- Artifact digest: `sha256:43690c59bc90a151dd170e580590b8601f24bf9e73225f3226642133d2861137`
- `formal-result.json` SHA-256: `566284023e198539f5560b3ce8da8e97ded64555b78895c178d36fdcab0a039f`
- Evaluator exit code: `2`, meaning the preregistered selection guardrails failed while evidence generation/upload completed successfully.

## Metrics

### Candidate-v2

- MRR: `0.19480286738351246`
- R@1: `0.06989247311827956`
- R@3: `0.1810035842293907`
- R@5: `0.27240143369175623`
- Answerable recall: `1.0`
- False abstention: `0.0`
- No-evidence false retrieval: `6/6 = 1.0`
- Abstention accuracy: `0.0`

### Candidate-v6

- MRR: `0.0`
- R@1: `0.0`
- R@3: `0.0`
- R@5: `0.0`
- Answerable recall: `0.0`
- False abstention: `1.0`
- No-evidence false retrieval: `0/6 = 0.0`
- Abstention accuracy: `1.0`

Candidate-v6 therefore preserved its conservative no-evidence behavior but rejected every one of the 93 answerable natural-language LongMemEval cases under the frozen assertion-structure verifier.

## Retrieval deficits vs Candidate-v2

- MRR deficit: `0.19480286738351246` > allowed `0.03` → **FAIL**
- R@1 deficit: `0.06989247311827956` > allowed `0.03` → **FAIL**
- R@3 deficit: `0.1810035842293907` > allowed `0.02` → **FAIL**
- R@5 deficit: `0.27240143369175623` > allowed `0.02` → **FAIL**
- Answerable recall `0.0` < required `0.95` → **FAIL**
- False abstention `1.0` > allowed `0.05` → **FAIL**
- Abstention accuracy `1.0` ≥ required `0.90` → **PASS**
- No-evidence false retrieval `0.0` ≤ allowed `0.10` → **PASS**
- Absolute false-retrieval reduction vs v2 `1.0` ≥ required `0.70` → **PASS**

## Paired bootstrap

Comparison: Candidate-v6 minus Candidate-v2 on the 93 answerable cases.

- Iterations: `10,000`
- Seed: `20260814`
- Noninferiority margin: `0.03`
- Point ΔMRR: `-0.19480286738351246`
- Bootstrap mean ΔMRR: `-0.1945758243727581`
- 95% CI: `[-0.2603942652329749, -0.13279569892473117]`
- Fraction with Δ ≥ `-0.03`: `0.0`
- Preregistered rule: lower 95% CI ≥ `-0.03`
- Noninferiority: **FAIL**

Win / tie / loss on answerable reciprocal rank:

- wins: `0`
- ties: `58`
- losses: `35`

## Integrity decision

Gate F integrity is **PASS**:

- explicit human authorization existed before execution;
- preregistration preceded sealed-final exposure;
- Candidate-v6 source/config identity matched exactly;
- the official dataset and split identities were recorded;
- all 99 cases were accounted for;
- no case was excluded;
- no benchmark edit/regeneration occurred;
- the selection-bearing execution ran exactly once;
- no result-bearing rerun occurred;
- no result-driven metric, threshold, bootstrap seed, margin, or evaluator change occurred;
- no paid API/GPU/inference was used;
- negative evidence is preserved.

The original repository's historical `SEALED-PATH-METADATA-001` incident remains a historical integrity deviation of that old lineage. This Gate F execution neither deletes nor retroactively cures it.

## Formal Gate F decision

Because multiple preregistered selection guardrails and paired-bootstrap noninferiority failed:

`GATE_F_FORMAL = NOT COMPLETE`

`TERMINAL_STATE = GATE_F_SELECTION_FAIL`

The same sealed-final benchmark is now permanently exposed for this candidate lineage and must not be used to tune Candidate-v6 or to certify a retuned candidate through a rerun.

## Research interpretation

The aggregate failure mechanism is sharply localized: Candidate-v6's assertion-structure verifier is sufficiently conservative to reject all six official no-evidence cases correctly, but its narrow deterministic assertion grammar fails to recognize supported evidence in the heterogeneous natural-language LongMemEval domain. This interpretation may guide hypothesis generation only at the aggregate architectural level; the 99 sealed-final cases themselves must remain quarantined from subsequent candidate development.

## Next legal boundary

Gate G is **NOT STARTED** and cannot proceed because Gate F did not pass.

The next legal mission is a **post-Gate-F failure recovery / Candidate-v7 development track** that:

1. permanently retires this 99-case sealed-final split from selection use;
2. develops only on non-sealed development surfaces;
3. preregisters a broader natural-language evidence-verification hypothesis before protected evaluation;
4. freezes a new candidate before generating a fresh protected benchmark;
5. obtains a genuinely fresh final evaluation surface before any future Gate F-style certification;
6. does not claim that Candidate-v6 passed Gate F, parity, or universal superiority.
