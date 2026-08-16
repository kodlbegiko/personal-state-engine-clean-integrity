# Candidate-v8 Fresh Generator Design

The generator is synthetic but template-diverse and deterministic. It separates semantic specifications from rendered linguistic forms so evidence certification can be evaluated on held-out render families.

## Semantic record

Each generated case contains an internal specification with `subject`, `relation`, `value`, `temporal_scope`, `polarity`, `epistemic_status`, `speech_act`, and `speaker_role`. The inference function never receives the specification fields; only the evaluator does.

## Positive construction

For answerable cases, one or more memories assert the required fact using a render family. Distractors may match subject, relation, or vocabulary independently. Current-query cases can include stale superseded values so the evaluator requires the current evidence ID.

## Negative construction

No-evidence cases use paired controls: wrong relation, wrong subject, unknown/no-value, contradiction without resolution, stale-only, hypothetical, future intent, question-only, agenda, meta-only, quoted false claim, assistant suggestion, entity collision, and mixed-clause distractors.

## Split discipline

Development, protected validation, and confirmatory use disjoint seed ranges and disjoint render-family assignments. Protected/confirmatory generation is performed only after the previous freeze. The generator source can be shared, but each evaluation manifest freezes seed, case count, render-family allowlist/denylist, and output SHA-256 before execution.

## Overlap control

Every case obtains a canonical semantic-surface hash over normalized query and memories. Comparison to historical surfaces may use only case IDs/hashes/provenance/manifest metadata. The retired 99-case semantic payload is never opened.
