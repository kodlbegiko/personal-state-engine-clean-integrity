# Candidate-v13 White-Box Audit

## Evidence boundary

Audit target: frozen `src/personal_state_engine/candidate_v13.py` at the v4 terminal lineage. Candidate source is development-safe evidence. No v4 protected case-level artifact is used.

## Pipeline audit

| Layer | v13 behavior / risk | v14 architectural response |
|---|---|---|
| preprocessing | Deterministic normalization is useful but upstream parse failures can become terminal | retain deterministic normalization; do not make parse success a precondition to rank |
| query normalization | query frame extraction is structurally important | use query tokens/concepts directly as parallel signals |
| memory representation | multiple component modules feed proof/ranking | make component scores explicit and inspectable |
| candidate generation | candidate/supporting IDs can be filtered before final ranking | rank all supplied memories first |
| lexical scoring | can be distribution-sensitive under paraphrase | lexical is one component, not the gate |
| semantic scoring | proof depends on fixed verifier conditions | lightweight concept semantics are continuous scoring evidence |
| temporal handling | prior candidate modules participate | explicit timestamp recency component; deterministic tie behavior |
| negation handling | semantic proof may reject negated/ambiguous inputs | contradiction penalty applied at verification/ranking level |
| contradiction handling | can zero support | retain strong penalty, but after candidate competition |
| entity handling | frame subject requirements can be brittle | entity overlap is graded; proposition binding checks local relation |
| relation matching | relation parse can be a hard prerequisite | relation concept matching is graded |
| rank aggregation | final ranking restricted to verifier-approved supporting IDs | Stage 1 always produces ranked scores |
| abstention decision | verifier verdict != SUPPORTED or no supporting IDs => `[]` | Stage 2 verifier only after ranking |
| evidence sufficiency | tightly coupled to semantic proof | explicit completeness + contradiction + relative margin |
| confidence | proof-oriented rather than independently calibrated | explicit confidence and calibration audit |

## Probable bottlenecks

1. **Pre-ranking rejection amplification.** Query-frame/proof failures can eliminate retrieval opportunity entirely.
2. **Ranking/abstention coupling.** Final rank output depends on a supporting-ID subset produced by the verifier.
3. **Distribution-sensitive hard gates.** Relation/subject completeness and ambiguity/uncertainty conditions can behave sharply outside development fixtures.
4. **Evidence competition is secondary.** The design is more proof-gated than relative-evidence-first.
5. **Development overfit risk.** v13 scored 1.00 across its own 900-case development benchmark yet failed v4 external validity, proving that internal pass alone was not a sufficient generalization signal.

## Failure amplification path

`surface variation / parse weakness → frame or semantic proof failure → supporting IDs empty → rank returns [] → false abstention`

This path is architecture-level and is sufficient to justify a new lineage without using protected v4 examples.
