from __future__ import annotations

"""Candidate-v12 discourse-robust semantic-frame extraction.

Fresh-lineage constraints:
- Candidate-v2 remains the exclusive candidate source.
- Candidate-v10 evidence certification and Candidate-v11 Layer-2 proof ordering
  remain downstream safety/ranking mechanisms.
- Candidate-v12 changes the upstream query frame only: discourse scaffold is
  separated from proposition-bearing content, then subject and relation slots
  are conservatively bound.
- No historical Protected prefix/token blacklist, benchmark ID, split label,
  gold answer, relevant-memory ID, or generator metadata is visible here.
"""

import re
from dataclasses import asdict, dataclass, replace
from typing import Any, Iterable

from .candidate_v2 import pse_candidate_v2_rank
from .candidate_v8 import QueryRequirements
from .candidate_v10 import (
    FrameRequirements,
    _primary_relations,
    _raw_relation_signals,
    semantic_requirements_v10,
)
from .candidate_v11 import EvidencePriorityProofV11, evidence_priority_proof_v11

VERDICT_SUPPORTED = "SUPPORTED"
VERDICT_INSUFFICIENT = "INSUFFICIENT"

_CAPITALIZED_SPAN = re.compile(
    r"(?<![A-Za-z0-9_-])"
    r"([A-Z][A-Za-z0-9_-]*(?:['’]s)?(?:\s+[A-Z][A-Za-z0-9_-]*(?:['’]s)?){0,4})"
)
_FIRST_PERSON = re.compile(r"\b(?:i|me|my|mine)\b", re.I)
_PRONOUN = re.compile(r"\b(?:he|she|they|his|her|their|them)\b", re.I)
_QUESTION_CUE = re.compile(r"\b(?:what|which|who|where|when|how)\b", re.I)
_MODAL = re.compile(r"\b(?:may|might|could|would|should|possibly|perhaps|maybe)\b", re.I)
_HYPOTHETICAL = re.compile(r"\b(?:if|hypothetical|suppose|assuming)\b", re.I)


@dataclass(frozen=True)
class EntityCandidateV12:
    text: str
    anchors: tuple[str, ...]
    start: int
    token_count: int
    memory_document_frequency: int
    memory_occurrences: int
    relation_clause_overlap: int
    score: tuple[int, int, int, int]


@dataclass(frozen=True)
class StructuredQueryFrameV12:
    discourse_intent: str
    semantic_proposition_spans: tuple[str, ...]
    subject_entities: tuple[str, ...]
    subject_coreference: tuple[str, ...]
    relation_candidates: tuple[str, ...]
    relation_support: tuple[tuple[str, int], ...]
    relation_frame: tuple[str, ...]
    predicate_constraints: tuple[str, ...]
    object_constraints: tuple[str, ...]
    temporal_scope: str
    modality: str
    answer_type: str
    subject_ambiguous: bool
    relation_ambiguous: bool
    parse_valid: bool


def _safe_case(case: dict[str, Any]) -> dict[str, Any]:
    """Strict metadata firewall: only production-style runtime fields survive."""
    return {
        "query": str(case["query"]),
        "memories": [
            {
                "id": str(memory["id"]),
                "text": str(memory["text"]),
                "timestamp": memory.get("timestamp"),
            }
            for memory in case["memories"]
        ],
    }


def _contains_phrase(text: str, phrase: str) -> bool:
    return bool(
        re.search(
            rf"(?<![a-z0-9_-]){re.escape(phrase.casefold())}(?![a-z0-9_-])",
            text.casefold(),
        )
    )


def _entity_anchors(span: str) -> tuple[str, ...]:
    cleaned = span.replace("’", "'")
    parts = []
    for token in cleaned.split():
        token = re.sub(r"'s$", "", token, flags=re.I)
        if token:
            parts.append(token.casefold())
    return tuple(parts)


def _clause_spans(query: str) -> tuple[str, ...]:
    parts = [
        p.strip(" \t\n,:—-")
        for p in re.split(r"(?<=[.!?;])\s+|;\s+|\s+[—–]\s+", query)
        if p.strip(" \t\n,:—-")
    ]
    return tuple(parts) if parts else (query.strip(),)


def _provisional_semantic_clauses(query: str) -> tuple[str, ...]:
    """Broad proposition candidates used only before relation disambiguation."""
    clauses = _clause_spans(query)
    selected = [
        clause
        for clause in clauses
        if _QUESTION_CUE.search(clause) or _raw_relation_signals(clause)
    ]
    return tuple(selected) if selected else (min(clauses, key=len),)


def _candidate_entity_spans(query: str, memories: Iterable[dict[str, Any]]) -> list[EntityCandidateV12]:
    memory_list = list(memories)
    semantic_clauses = _provisional_semantic_clauses(query)
    out: list[EntityCandidateV12] = []
    seen: set[tuple[str, int]] = set()

    for match in _CAPITALIZED_SPAN.finditer(query):
        raw = match.group(1).strip()
        anchors = _entity_anchors(raw)
        if not anchors:
            continue
        key = (raw.casefold(), match.start(1))
        if key in seen:
            continue
        seen.add(key)

        doc_frequency = 0
        occurrences = 0
        for memory in memory_list:
            text = str(memory["text"])
            count = len(
                re.findall(
                    rf"(?<![a-z0-9_-]){re.escape(raw.casefold())}(?![a-z0-9_-])",
                    text.casefold(),
                )
            )
            if count:
                doc_frequency += 1
                occurrences += count

        relation_clause_overlap = sum(
            1 for clause in semantic_clauses if _contains_phrase(clause, raw)
        )
        token_count = len(anchors)
        score = (
            doc_frequency,
            occurrences,
            token_count,
            relation_clause_overlap,
        )
        out.append(
            EntityCandidateV12(
                text=raw,
                anchors=anchors,
                start=match.start(1),
                token_count=token_count,
                memory_document_frequency=doc_frequency,
                memory_occurrences=occurrences,
                relation_clause_overlap=relation_clause_overlap,
                score=score,
            )
        )
    return out


def _resolve_subject(query: str, memories: Iterable[dict[str, Any]]) -> tuple[tuple[str, ...], bool]:
    candidates = [
        c for c in _candidate_entity_spans(query, memories)
        if c.memory_document_frequency > 0
    ]
    if not candidates:
        return tuple(), False

    candidates.sort(key=lambda c: (c.score, -c.start), reverse=True)
    best = candidates[0]
    tied = [
        c
        for c in candidates
        if c.score == best.score and c.text.casefold() != best.text.casefold()
    ]
    if tied:
        return tuple(), True
    return (best.text,), False


def _subject_scoped_memories(
    subjects: tuple[str, ...],
    first_person: bool,
    memories: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    memory_list = list(memories)
    if subjects:
        subject = subjects[0]
        return [m for m in memory_list if _contains_phrase(str(m["text"]), subject)]
    if first_person:
        return [m for m in memory_list if _FIRST_PERSON.search(str(m["text"]))]
    return []


def _relation_candidates(query: str) -> tuple[str, ...]:
    return tuple(sorted(_raw_relation_signals(query)))


def _resolve_relation(
    query: str,
    subjects: tuple[str, ...],
    first_person: bool,
    memories: Iterable[dict[str, Any]],
) -> tuple[tuple[str, ...], tuple[tuple[str, int], ...], bool]:
    """Resolve lexical relation ambiguity without discourse-token blacklists.

    A query can contain words that are valid relation lexemes in one semantic
    context but merely discourse/request scaffolding in another. When exactly
    one relation signal is present, it is used directly. When several relation
    signals compete, only memories tied to the already-bound subject are used
    as runtime evidence for disambiguation. A tie or zero-support contest fails
    closed instead of broadening eligibility.
    """
    candidates = _relation_candidates(query)
    if not candidates:
        return tuple(), tuple(), False
    if len(candidates) == 1:
        only = candidates[0]
        return (only,), ((only, 0),), False

    scoped = _subject_scoped_memories(subjects, first_person, memories)
    support: dict[str, int] = {relation: 0 for relation in candidates}
    for memory in scoped:
        signals = _raw_relation_signals(str(memory["text"]))
        for relation in candidates:
            if relation in signals:
                support[relation] += 1

    ordered_support = tuple(sorted(support.items(), key=lambda item: (-item[1], item[0])))
    top_relation, top_count = ordered_support[0]
    second_count = ordered_support[1][1]
    if top_count <= 0 or top_count == second_count:
        return tuple(), ordered_support, True
    return (top_relation,), ordered_support, False


def _semantic_clauses(query: str, relation_frame: tuple[str, ...]) -> tuple[str, ...]:
    clauses = _clause_spans(query)
    if relation_frame:
        target = relation_frame[0]
        selected = [
            clause for clause in clauses if target in _raw_relation_signals(clause)
        ]
        if selected:
            return tuple(selected)
    return _provisional_semantic_clauses(query)


def _discourse_intent(query: str, semantic_spans: tuple[str, ...]) -> str:
    clauses = _clause_spans(query)
    if len(clauses) == 1 and semantic_spans == clauses:
        return "DIRECT_PROPOSITION_QUERY"
    if len(clauses) > 1:
        return "CONTEXT_PLUS_PROPOSITION"
    if semantic_spans and semantic_spans[0] != query.strip():
        return "EMBEDDED_PROPOSITION_QUERY"
    return "MIXED_DISCOURSE_QUERY"


def parse_query_frame_v12(query: str, memories: Iterable[dict[str, Any]]) -> StructuredQueryFrameV12:
    memory_list = list(memories)
    subjects, subject_ambiguous = _resolve_subject(query, memory_list)
    first_person = bool(_FIRST_PERSON.search(query))
    relations, relation_support, relation_ambiguous = _resolve_relation(
        query, subjects, first_person, memory_list
    )
    semantic_spans = _semantic_clauses(query, relations)
    base = semantic_requirements_v10(query)

    coreference: list[str] = []
    if subjects and any(_PRONOUN.search(span) for span in semantic_spans):
        coreference.append("PRONOUN_TO_BOUND_SUBJECT")
    if first_person:
        coreference.append("FIRST_PERSON_SELF")

    if _HYPOTHETICAL.search(query):
        modality = "HYPOTHETICAL"
    elif _MODAL.search(query):
        modality = "MODAL_OR_UNCERTAIN"
    else:
        modality = "ASSERTED_QUERY"

    answer_type = "RELATION_VALUE" if relations else "UNKNOWN"
    has_subject = bool(subjects) or first_person
    parse_valid = (
        bool(relations)
        and has_subject
        and not subject_ambiguous
        and not relation_ambiguous
    )

    return StructuredQueryFrameV12(
        discourse_intent=_discourse_intent(query, semantic_spans),
        semantic_proposition_spans=semantic_spans,
        subject_entities=subjects,
        subject_coreference=tuple(coreference),
        relation_candidates=_relation_candidates(query),
        relation_support=relation_support,
        relation_frame=relations,
        predicate_constraints=relations,
        object_constraints=tuple(base.object_terms),
        temporal_scope=base.base.temporal_scope,
        modality=modality,
        answer_type=answer_type,
        subject_ambiguous=subject_ambiguous,
        relation_ambiguous=relation_ambiguous,
        parse_valid=parse_valid,
    )


def _requirements_from_frame(
    query: str,
    memories: Iterable[dict[str, Any]],
    frame: StructuredQueryFrameV12 | None = None,
) -> FrameRequirements | None:
    memory_list = list(memories)
    frame = frame or parse_query_frame_v12(query, memory_list)
    if not frame.parse_valid:
        return None

    original = semantic_requirements_v10(query)
    subject_anchors: tuple[str, ...] = tuple()
    if frame.subject_entities:
        subject_anchors = _entity_anchors(frame.subject_entities[0])

    base: QueryRequirements = replace(
        original.base,
        subject_anchors=subject_anchors,
        first_person=(not subject_anchors and bool(_FIRST_PERSON.search(query))),
    )
    return FrameRequirements(
        base=base,
        relations=frame.relation_frame,
        object_terms=frame.object_constraints,
    )


def evidence_support_signature_v12(case: dict[str, Any]) -> dict[str, Any]:
    safe_case = _safe_case(case)
    query = safe_case["query"]
    memories = safe_case["memories"]
    frame = parse_query_frame_v12(query, memories)
    req = _requirements_from_frame(query, memories, frame)

    full_ranking = pse_candidate_v2_rank(safe_case, max(5, len(memories)))
    if req is None:
        return {
            "verdict": VERDICT_INSUFFICIENT,
            "frame": asdict(frame),
            "candidate_v2_ranking": full_ranking,
            "supporting_memory_ids": [],
            "proofs": [],
        }

    by_id = {str(memory["id"]): memory for memory in memories}
    proofs: list[EvidencePriorityProofV11] = []
    for original_rank, memory_id in enumerate(full_ranking, start=1):
        memory = by_id.get(memory_id)
        if memory is None:
            continue
        proof = evidence_priority_proof_v11(
            query=query,
            memory=memory,
            candidate_v2_original_rank=original_rank,
            req=req,
        )
        if proof is not None:
            proofs.append(proof)

    proofs.sort(key=lambda proof: proof.priority_tuple, reverse=True)
    supporting_ids = [proof.memory_id for proof in proofs]
    return {
        "verdict": VERDICT_SUPPORTED if supporting_ids else VERDICT_INSUFFICIENT,
        "frame": asdict(frame),
        "candidate_v2_ranking": full_ranking,
        "supporting_memory_ids": supporting_ids,
        "proofs": [asdict(proof) for proof in proofs],
    }


def pse_candidate_v12_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    return evidence_support_signature_v12(case)["supporting_memory_ids"][:k]


def _bounded_strip_query(query: str, memories: Iterable[dict[str, Any]]) -> str | None:
    """Architecture B: bounded normalization baseline, not Candidate-v12 proper."""
    candidates = [
        c for c in _candidate_entity_spans(query, memories)
        if c.memory_document_frequency > 0
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda c: (c.score, -c.start), reverse=True)
    best = candidates[0]
    if (
        len(candidates) > 1
        and candidates[1].score == best.score
        and candidates[1].text.casefold() != best.text.casefold()
    ):
        return None
    return query[best.start:].strip()


def pse_candidate_v12_arch_b_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Architecture B baseline: bounded discourse-prefix stripping + v11."""
    from .candidate_v11 import pse_candidate_v11_rank

    safe_case = _safe_case(case)
    stripped = _bounded_strip_query(safe_case["query"], safe_case["memories"])
    if stripped is None:
        return []
    normalized = {"query": stripped, "memories": safe_case["memories"]}
    return pse_candidate_v11_rank(normalized, k)


def pse_candidate_v12_arch_d_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Architecture D: clause-first conservative proposition graph."""
    safe_case = _safe_case(case)
    query = safe_case["query"]
    memories = safe_case["memories"]
    frame = parse_query_frame_v12(query, memories)
    if not frame.parse_valid:
        return []
    target = frame.relation_frame[0]
    if not any(target in _raw_relation_signals(span) for span in frame.semantic_proposition_spans):
        return []
    return pse_candidate_v12_rank(safe_case, k)


def candidate_source_invariant_v12(case: dict[str, Any], k: int = 5) -> dict[str, Any]:
    safe_case = _safe_case(case)
    full_v2 = pse_candidate_v2_rank(
        safe_case, max(k, len(safe_case["memories"]))
    )
    v12 = pse_candidate_v12_rank(safe_case, k)
    v2_set = set(full_v2)
    no_injection = all(memory_id in v2_set for memory_id in v12)
    unique = len(v12) == len(set(v12))

    signature = evidence_support_signature_v12(safe_case)
    eligible = set(signature["supporting_memory_ids"])
    only_eligible = all(memory_id in eligible for memory_id in v12)
    return {
        "candidate_v2_count": len(full_v2),
        "candidate_v12_count": len(v12),
        "no_injection": no_injection,
        "only_eligible": only_eligible,
        "unique": unique,
        "pass": no_injection and only_eligible and unique,
    }
