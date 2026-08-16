# Candidate-v9 Fresh Benchmark Design

## Purpose

Generate independent natural-language surfaces that stress answerability preservation and unsupported-retrieval safety without copying or paraphrasing Candidate-v8 protected cases or the retired 99-case Gate F payload.

## Generation principles

- Deterministic local generator with pinned seed and no paid API.
- New namespaces, subjects, values, templates, distractors, and case IDs for each stage.
- No Candidate-v8 protected case IDs, texts, answers, or templates are inputs.
- Stage generators share abstract linguistic phenomena but not instantiated cases.
- Each case records provenance fields needed for evaluation; inference code is not given benchmark-only metadata.

## Answerable families

Direct assertion; verb paraphrase; nominal paraphrase; relation paraphrase; object/value alias; first-person; third-person; pronoun/coreference; temporal qualifier; multi-clause evidence; distractor memories; multiple same-subject facts; same relation with different object; same object with different relation.

## No-evidence/adversarial families

Question-only; no-value; meta-discussion; agenda; assistant suggestion; negative decoy; contradiction; hypothetical; future intent; uncertain claim; unverified attribution; stale state; same subject/wrong relation; same relation/wrong object; semantically nearby but unsupported.

## Frozen sizes and seeds

- Development: 360 = 210 answerable + 150 no-evidence, seed 2026081509.
- Protected: 300 = 190 answerable + 110 no-evidence, seed 2026081511.
- Confirmatory: 360 = 220 answerable + 140 no-evidence, seed 2026081513.
- Fresh Final Gate F: 480 = 300 answerable + 180 no-evidence, seed 2026081515.

No post-result sample-size increase is permitted.

## Distribution design

Within each stage, answerable families and adversarial families are deterministically balanced as evenly as integer counts permit, then shuffled by the stage seed. Surface vocabularies are stage-specific. Relation families must include preference, transport/use, consumption, work/study, residence/ownership, need/like/dislike/avoid, and at least three additional non-overlapping relation families selected by the generator before materialization.

## Distractors

Each answerable case includes at least two distractor memories where possible. Distractors vary subject, relation, object, polarity, certainty, or temporal status. No-evidence cases contain plausible lexical overlap to prevent trivial abstention by word absence.

## Gold construction

The generator emits the relevant memory ID(s) and expected evidence status from construction logic. Candidate-v2 ranking is evaluated separately. Candidate-v9 inference cannot read gold fields.

## Freshness audit

Before each formal materialization, compare generated IDs and normalized semantic signatures against all earlier Candidate-v9 surfaces and available historical metadata. Exact duplicates are forbidden. Candidate-v8 protected semantics are not used for overlap testing before the historical diagnostic is authorized; after authorization they remain diagnostic-only and may not be used as templates.

## Failure taxonomy

Evaluation classifies false abstentions and false retrievals by generic mechanism: subject resolution, relation normalization, value typing/alias, temporal compatibility, polarity/certainty, segmentation, blocker scope, or other. Taxonomy is diagnostic only and does not alter formal decisions.
