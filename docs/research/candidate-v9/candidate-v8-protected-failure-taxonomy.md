# Candidate-v8 Protected Failure Taxonomy (Historical Diagnostic Only)

This surface is excluded from Candidate-v9 development, protected, confirmatory, and final evaluation. It was opened only after Candidate-v9 preregistration and diagnostic-access authorization.

## Failure 1: `CV8-PROTECTED-A-021`

- Query: `What drink is Vera's usual choice?`
- Candidate-v2 ranking: `['CV8-PROTECTED-A-021-rel', 'CV8-PROTECTED-A-021-n4', 'CV8-PROTECTED-A-021-n2', 'CV8-PROTECTED-A-021-n5', 'CV8-PROTECTED-A-021-n1', 'CV8-PROTECTED-A-021-n3']`
- Candidate-v8 ranking: `[]`
- Root cause: **RELATION_REALIZATION**
- Predicted by preregistered hypothesis: `True`

Relevant memory `CV8-PROTECTED-A-021-rel`: `Vera tends to order espresso when taking a break.`

- Clause: `Vera tends to order espresso when taking a break.`
  - subject_ok=True; relation_ok=False; value_bearing=True; direct_assertion=True; temporal_ok=True; blocker=None; score=4; supported=False

Generalization constraint: fix only the typed mechanism; do not whitelist this case ID, subject, value, answer, or exact phrase.

## Failure 2: `CV8-PROTECTED-A-027`

- Query: `Where does Benoit study?`
- Candidate-v2 ranking: `['CV8-PROTECTED-A-027-n4', 'CV8-PROTECTED-A-027-rel', 'CV8-PROTECTED-A-027-n1', 'CV8-PROTECTED-A-027-n2', 'CV8-PROTECTED-A-027-n5', 'CV8-PROTECTED-A-027-n3']`
- Candidate-v8 ranking: `[]`
- Root cause: **RELATION_REALIZATION**
- Predicted by preregistered hypothesis: `True`

Relevant memory `CV8-PROTECTED-A-027-rel`: `Someone asked a separate planning question earlier; Benoit attends Maple Coast University this year.`

- Clause: `Someone asked a separate planning question earlier`
  - subject_ok=False; relation_ok=False; value_bearing=True; direct_assertion=False; temporal_ok=True; blocker=None; score=2; supported=False
- Clause: `Benoit attends Maple Coast University this year.`
  - subject_ok=True; relation_ok=False; value_bearing=True; direct_assertion=False; temporal_ok=True; blocker=None; score=3; supported=False

Generalization constraint: fix only the typed mechanism; do not whitelist this case ID, subject, value, answer, or exact phrase.

## Failure 3: `CV8-PROTECTED-A-063`

- Query: `What drink is Lena's usual choice?`
- Candidate-v2 ranking: `['CV8-PROTECTED-A-063-n4', 'CV8-PROTECTED-A-063-rel', 'CV8-PROTECTED-A-063-n2', 'CV8-PROTECTED-A-063-n5', 'CV8-PROTECTED-A-063-n1', 'CV8-PROTECTED-A-063-n3']`
- Candidate-v8 ranking: `[]`
- Root cause: **RELATION_REALIZATION**
- Predicted by preregistered hypothesis: `True`

Relevant memory `CV8-PROTECTED-A-063-rel`: `Someone asked a separate planning question earlier; Lena tends to order flat white when taking a break.`

- Clause: `Someone asked a separate planning question earlier`
  - subject_ok=False; relation_ok=False; value_bearing=True; direct_assertion=False; temporal_ok=True; blocker=None; score=2; supported=False
- Clause: `Lena tends to order flat white when taking a break.`
  - subject_ok=True; relation_ok=False; value_bearing=True; direct_assertion=True; temporal_ok=True; blocker=None; score=4; supported=False

Generalization constraint: fix only the typed mechanism; do not whitelist this case ID, subject, value, answer, or exact phrase.

## Failure 4: `CV8-PROTECTED-A-069`

- Query: `Where does Rhea study?`
- Candidate-v2 ranking: `['CV8-PROTECTED-A-069-rel', 'CV8-PROTECTED-A-069-n4', 'CV8-PROTECTED-A-069-n1', 'CV8-PROTECTED-A-069-n5', 'CV8-PROTECTED-A-069-n2', 'CV8-PROTECTED-A-069-n3']`
- Candidate-v8 ranking: `[]`
- Root cause: **RELATION_REALIZATION**
- Predicted by preregistered hypothesis: `True`

Relevant memory `CV8-PROTECTED-A-069-rel`: `Rhea attends Silver Hill College this year.`

- Clause: `Rhea attends Silver Hill College this year.`
  - subject_ok=True; relation_ok=False; value_bearing=True; direct_assertion=False; temporal_ok=True; blocker=None; score=3; supported=False

Generalization constraint: fix only the typed mechanism; do not whitelist this case ID, subject, value, answer, or exact phrase.

