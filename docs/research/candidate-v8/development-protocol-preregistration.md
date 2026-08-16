# Candidate-v8 Development Protocol Preregistration

## Frozen historical boundaries

- Candidate-v7 source/config/results remain immutable historical evidence.
- Old Gate F 99-case semantic payload remains permanently retired and must not be opened.
- Candidate-v7 confirmatory 140-case payload is unavailable to development at preregistration time. If later opened, it becomes `HISTORICAL_DIAGNOSTIC_ONLY` and can be used only for taxonomy/qualitative diagnosis, never as a Candidate-v8 pass gate, threshold-tuning set, protected validation, confirmatory, or final surface.

## Development objective

Develop a zero-cost deterministic evidence certifier that returns an order-preserving subsequence of Candidate-v2 ranking. The certifier must improve no-evidence safety without materially degrading answerable MRR/recall.

## Fresh development surface

A new deterministic generator will create **240 development cases** with a fixed seed and unique `v8-dev-*` provenance:

- 140 answerable
- 100 no-evidence/adversarial

Coverage strata include preference, location, work role, schedule/time, contact, possession/device, activity/hobby, travel, food/drink, relationship, numeric/quantity, status, media, health, goal, transport, education, language, identity attributes, membership, free-form properties, correction/supersession, and multi-evidence requirements.

Linguistic strata include first person, named third person, pronoun variants, copular, verb predicate, apposition, low-overlap paraphrase, implicit predicate, coordination, multi-clause mixed speech acts, negation, uncertainty, quotation/attribution, hypothetical, future intent, agenda, meta-discussion, no-value variants, stale/current contrasts, and entity collisions.

The generator must emit case IDs, provenance, surface hashes, answerability labels and relevant-memory IDs. No case may derive from Candidate-v7 confirmatory payload or the retired 99-case semantic payload.

## Development gates

A development iteration passes only if all hold:

1. Candidate-v8 answerable MRR >= 0.97.
2. Candidate-v8 answerable recall >= 0.97.
3. Candidate-v8 false retrieval <= 0.05.
4. Candidate-v8 false abstention <= 0.03.
5. Candidate-v8 preserves Candidate-v2 relative order among all returned IDs.
6. No ground-truth leakage: inference reads only query, memory ID/text/timestamp/speaker metadata if present.
7. Unit/property tests all pass.
8. Retired-surface overlap check by IDs/hashes/provenance is zero.

Thresholds/weights may be changed only during development and every failed iteration must be retained in `results/candidate-v8/development-ledger.jsonl`.

## Protected validation

After a development freeze commit, generate a **fresh 160-case protected surface** using a separately frozen seed/template split:

- 95 answerable
- 65 no-evidence

The protected payload must not be opened for manual case tuning after materialization. Formal execution count = 1. Pass gates:

- MRR >= 0.95
- answerable recall >= 0.95
- false retrieval <= 0.08
- false abstention <= 0.05
- paired bootstrap non-inferiority versus Candidate-v2 on answerable reciprocal rank with margin -0.03, 10,000 iterations, frozen seed 2026081501

If protected validation fails, Candidate-v8 may return to development only under a new development iteration and must materialize a **new** protected surface/seed after the next freeze; the failed protected surface becomes historical diagnostic only.

## Confirmatory evaluation

After protected PASS and a second freeze, generate a **fresh 200-case confirmatory surface** from templates/seeds not used in development/protected validation:

- 120 answerable
- 80 no-evidence

Execution count = 1. No post-result editing. Confirmatory pass gates:

- MRR >= 0.95
- answerable recall >= 0.95
- false retrieval <= 0.08
- false abstention <= 0.05
- absolute false-retrieval reduction vs Candidate-v2 >= 0.70
- paired bootstrap non-inferiority vs Candidate-v2 with margin -0.03, 10,000 iterations, seed 2026081502

Only if all confirmatory gates pass may the mission reach `READY_FOR_FRESH_FINAL_GATE_F_AUTHORIZATION`. This state authorizes preparation for a separate fresh final Gate F; it does **not** execute final Gate F automatically.

## Prohibited behavior

No paid API, no direct case-ID branches in inference, no answer-string lookup, no confirmatory-to-development promotion, no semantic reuse of retired Gate F, no deletion of failed iterations, and no claim that development/protected performance proves generalization.
