# Candidate-v14 Development Data Provenance

## Sources

Candidate-v14 architecture development uses a newly generated deterministic synthetic controlled corpus only. No external protected benchmark payload is imported.

The corpus covers 8 domains (`identity`, `preference`, `schedule`, `location`, `device`, `education`, `food`, `activity`) and 12 controlled families (`exact`, `paraphrase`, `synonym`, `entity_substitution`, `temporal_shift`, `negation`, `contradiction`, `irrelevant_distractor`, `ambiguous_evidence`, `multi_memory`, `weak_lexical_strong_semantic`, `strong_lexical_wrong_semantic`). Every family/domain cell contains answerable and no-evidence cases.

## Split construction

| Split | Seed | Cases | Use |
|---|---:|---:|---|
| architecture-development | 14001 | 384 | architecture iteration |
| internal-validation | 14002 | 384 | development validation/calibration |
| adversarial-validation | 14003 | 384 | lexical lure / contradiction / ambiguity stress |
| untouched-internal-holdout | 14999 | 384 | one-shot post-freeze qualification only |

The holdout payload is generated before qualification, hashed, and remains excluded from performance evaluation until after candidate/evaluator/policy freeze. The manifest records immutable SHA-256 digests.

## Historical v13 development-safe baseline

The frozen repository already contains `results/candidate-v13/development-summary-v1.json`, produced on `experiments/benchmarks/candidate-v13-development-v1.json` with 900 development cases. It is explicitly marked `stage=development`, `formal_execution=false`, `no_formal_payload_exposure=true`, and reports all principal retrieval/abstention metrics at 1.00. Candidate-v14 does not reinterpret that result as external evidence.

## Protected-data firewall

The v14 development executable/data tree is scanned mechanically. The scanner rejects protected v4 case/query/memory/assignment/seed references. Aggregate terminal metrics and historical anchor identifiers are allowed only as research-history context, not selectors or training data.

## Limitations

Synthetic controlled data can detect specified architectural pathologies but cannot establish natural-language external validity. The v13 history—perfect internal development metrics followed by external collapse—is direct evidence that a later independent fresh external-validity evaluation remains mandatory.
