# Candidate-v9 Architecture Options

These alternatives are preregistered before Candidate-v8 protected failure semantics are inspected. Candidate-v9 may combine them only in the bounded forms described here; case-specific lexical whitelists are prohibited.

## A — Typed Semantic Requirement Graph

Normalize each query into typed requirements: `SUBJECT`, `RELATION`, `VALUE_TYPE`, `TEMPORAL_SCOPE`, `POLARITY`, and `EVIDENCE_STATUS`. Normalize each memory clause into typed claim features. Certification requires sufficient graph satisfaction while hard safety blockers remain fail-closed.

Strength: explicit semantics and auditable failure reasons. Risk: brittle parsers can move the mismatch rather than solve it.

## B — Relation Canonicalization Layer

Map bounded verb, nominal, inflectional, and common paraphrase forms into canonical relation families such as prefer, choose, use, take, ride, eat, drink, work, study, live, own, need, like, dislike, and avoid.

Strength: directly addresses predicate asymmetry. Risk: over-broad aliases can create unsafe false support.

## C — Weighted Evidence Score + Hard Safety Blockers

Retain mandatory negative blockers. If no hard blocker fires, combine positive evidence signals for subject, relation, value/object, assertion, temporal compatibility, and semantic compatibility. The threshold is selected only on fresh development and frozen before protected materialization.

Strength: reduces brittle conjunction behavior. Risk: weak signals could accumulate incorrectly if weights are not bounded.

## D — Normalized Claim Extraction + Query Entailment

Extract a deterministic claim tuple: subject, relation, value, polarity, certainty, and temporal state. Query support is tested against the normalized tuple. No remote model or stochastic paid service is permitted.

Strength: separates extraction from support decision. Risk: claim extraction errors can cascade.

## E — Hybrid Dual Channel

Channel 1 is strict exact/typed evidence certification. Channel 2 is bounded paraphrase/canonical-relation resolution. A memory is certified only if one complete channel satisfies the full support requirements; isolated weak signals cannot unlock retrieval.

Strength: preserves a conservative path while expanding paraphrase coverage. Risk: duplicated logic and maintenance complexity.

## Allowed composition

A final Candidate-v9 implementation may combine A+B+C, A+B+D, or A+B+E if development evidence supports it. Hard blockers, per-memory certification, Candidate-v2-only ranking, and order preservation are non-negotiable.

## Selection criteria

Eligibility requires all preregistered development gates. Rank eligible variants by: lowest false retrieval; lowest false abstention; highest MRR; lower complexity. The post-preregistration historical Candidate-v8 diagnostic may identify which general hypothesis is relevant but cannot introduce case-specific strings, identities, answers, IDs, or benchmark-dependent branches.
