# Candidate-v9 Pre-diagnostic Root-Cause Hypotheses

This document is frozen before reading Candidate-v8 protected failure semantics. The hypotheses are general and may not be converted into case-ID or phrase-specific patches.

## H1 — Relation realization sparsity

The evidence certifier may depend on a finite lexical family and miss semantically equivalent verbs or nominal forms. Examples of a generic family include take/ride/commute/travel/use/go by/catch/board.

## H2 — Query/evidence predicate asymmetry

A query such as “what does X prefer?” may be supported by evidence phrased as “usually chooses”, “tends to order”, “reaches for”, or “go-to”. Literal overlap may therefore under-represent support.

## H3 — Over-constrained conjunction

Requiring all positive signals simultaneously can reject valid paraphrastic evidence. A weighted or quorum-based positive path may preserve safety if hard blockers remain mandatory.

## H4 — Object/value extraction mismatch

Typed objects can be surface-divergent but semantically compatible, such as device↔phone, transport↔subway, drink↔coffee, medication↔ibuprofen, or exercise↔swimming.

## H5 — Subject/coreference realization

Evidence can refer to the same subject by pronoun, first person, possessive, role label, or canonical name. Bounded deterministic coreference may be required.

## H6 — Temporal compatibility false negatives

Current-state evidence can include “usually”, “these days”, “currently”, “recently”, “often”, or “on weekdays” even when the query lacks an explicit temporal expression. Over-strict temporal matching can create false abstention.

## H7 — Clause segmentation artifact

Clause-local certification may split subject, relation, and value across coordinated or appositive structures, hiding a complete supported claim.

## H8 — Safety blocker leakage

Broad uncertainty, hypothetical, meta-only, no-value, future-intent, or stale-state blockers can accidentally capture asserted evidence if their scope is not typed precisely.

## H9 — Morphosyntactic normalization gap

Negation scope, tense/aspect, possessives, nominalizations, and phrasal verbs may be normalized inconsistently between query and evidence.

## H10 — Multi-signal calibration discontinuity

A binary requirement gate may produce brittle behavior near paraphrase boundaries. A bounded score with hard blockers can smooth positive evidence recognition without weakening negative safety.

## Falsification criteria

A hypothesis is supported only if independent fresh development examples or the later historical diagnostic expose the predicted mechanism. A hypothesis is rejected or deprioritized when the mechanism is absent, or when fixing it increases false retrieval beyond preregistered gates.
