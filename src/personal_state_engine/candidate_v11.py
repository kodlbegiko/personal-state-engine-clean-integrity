from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .candidate_v2 import pse_candidate_v2_rank
from .candidate_v10 import (
    FrameRequirements,
    _primary_relations,
    certify_memory_v10,
    semantic_requirements_v10,
)
from .zero_cost_baselines import _stem, tokens

VERDICT_SUPPORTED = "SUPPORTED"
VERDICT_INSUFFICIENT = "INSUFFICIENT"

PRONOUN = re.compile(r"\b(?:he|she|they|his|her|their)\b", re.I)
FIRST_PERSON = re.compile(r"\b(?:i|me|my|mine|user)\b", re.I)

# General assertion forms. These are linguistic proof features, not benchmark
# templates or answer lexicons. Hard uncertainty/negation/hypothetical blockers
# remain entirely in Candidate-v10 eligibility and cannot be compensated here.
RECORD_ASSERTION = re.compile(
    r"\b(?:recorded\s+as|listed\s+as|registered\s+as|documented\s+as|"
    r"states?\s+(?:that\s+)?|shows?\s+(?:that\s+)?|contains?\s+|"
    r"gives?\s+.+?\s+as|identif(?:y|ies|ied)\s+.+?\s+as)\b",
    re.I,
)
DIRECT_PROPERTY_ASSERTION = re.compile(
    r"\b(?:is|are|has|have|uses?|owns?|keeps?|takes?|speaks?|attends?|"
    r"works?\s+as|serves?\s+as|belongs?\s+to|joined?|prefers?|"
    r"subscribed|resides?|lives?)\b",
    re.I,
)
WEAK_NARRATIVE = re.compile(
    r"\b(?:mentioned|mentions|discussion|discussed|discuss|agenda|topic|"
    r"note\s+about|reference\s+to|described\s+around)\b",
    re.I,
)
HISTORICAL_FRAME = re.compile(
    r"\b(?:formerly|previously|historically|earlier|before|last\s+(?:year|month|week)|"
    r"old\s+(?:entry|record|profile|snapshot|note)|prior\s+(?:entry|record|profile|snapshot|note)|"
    r"used\s+to|no\s+longer|superseded|obsolete)\b",
    re.I,
)
CURRENT_FRAME = re.compile(
    r"\b(?:current|currently|now|today|latest|these\s+days|still|presently)\b",
    re.I,
)

GENERIC_OBJECT_TERMS = {
    _stem(x)
    for x in {
        "field", "profile", "record", "entry", "value", "detail", "information",
        "current", "currently", "latest", "next", "professional", "personal",
    }
}


@dataclass(frozen=True)
class EvidencePriorityProofV11:
    memory_id: str
    subject_binding_quality: int
    relation_specificity: int
    object_slot_matches: int
    object_slot_total: int
    assertion_directness: int
    temporal_specificity: int
    semantic_completeness: int
    ambiguity_penalty: int
    candidate_v2_original_rank: int
    supported_clause: str
    priority_tuple: tuple[int, ...]


def _safe_case(case: dict[str, Any]) -> dict[str, Any]:
    """Metadata firewall: only production-style runtime fields enter inference."""
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


def _contains_anchor(text: str, anchor: str) -> bool:
    return bool(
        re.search(
            rf"(?<![a-z0-9_-]){re.escape(anchor.casefold())}(?![a-z0-9_-])",
            text.casefold(),
        )
    )


def _subject_binding_quality(clause: str, memory_text: str, req: FrameRequirements) -> int:
    anchors = tuple(req.base.subject_anchors)
    if anchors:
        if all(_contains_anchor(clause, anchor) for anchor in anchors):
            return 3
        if all(_contains_anchor(memory_text, anchor) for anchor in anchors) and PRONOUN.search(clause):
            return 2
        return 0
    if req.base.first_person:
        return 3 if FIRST_PERSON.search(clause) else 0
    return 1


def _relation_specificity(clause: str, req: FrameRequirements) -> int:
    requested = set(req.relations)
    observed = _primary_relations(clause)
    if not requested:
        return 0
    shared = requested & observed
    if shared and observed <= requested:
        return 3
    if shared:
        return 2
    # Candidate-v10 may establish a status/attribute relation through its
    # object-slot fallback. This remains weaker than an explicit relation cue.
    if requested in ({"status"}, {"attribute_color"}) and req.object_terms:
        return 1
    return 0


def _object_slot_coverage(clause: str, req: FrameRequirements) -> tuple[int, int]:
    meaningful = {
        term for term in req.object_terms
        if _stem(term) not in GENERIC_OBJECT_TERMS and len(_stem(term)) > 1
    }
    if not meaningful:
        return (0, 0)
    clause_stems = {_stem(tok) for tok in tokens(clause)}
    matches = sum(_stem(term) in clause_stems for term in meaningful)
    return (matches, len(meaningful))


def _assertion_directness(clause: str) -> int:
    if WEAK_NARRATIVE.search(clause):
        return 1
    if RECORD_ASSERTION.search(clause):
        return 4
    if DIRECT_PROPERTY_ASSERTION.search(clause):
        return 3
    # Candidate-v10 eligibility already requires an assignment-like assertion;
    # punctuation/other bounded assignment forms therefore receive the lowest
    # admissible directness rather than being rejected here.
    return 2


def _temporal_specificity(clause: str, req: FrameRequirements) -> int:
    historical = bool(HISTORICAL_FRAME.search(clause))
    current = bool(CURRENT_FRAME.search(clause))
    scope = req.base.temporal_scope
    if scope == "HISTORICAL":
        if historical:
            return 3
        if current:
            return 0
        return 1
    if scope == "CURRENT":
        if current:
            return 3
        if historical:
            return 0
        return 2
    # For profile/state questions without an explicit temporal operator, an
    # unmarked direct assertion is stronger than an explicitly historical one.
    if current:
        return 3
    if historical:
        return 0
    return 2


def _semantic_completeness(clause_cert: Any) -> int:
    return sum(
        bool(value)
        for value in (
            clause_cert.subject_ok,
            clause_cert.relation_ok,
            clause_cert.value_type_ok,
            clause_cert.value_bearing,
            clause_cert.assertion_ok,
            clause_cert.temporal_ok,
        )
    )


def _ambiguity_penalty(clause: str, supported_clause_count: int, req: FrameRequirements) -> int:
    observed = _primary_relations(clause)
    requested = set(req.relations)
    competing_relations = len(observed - requested)
    competing_supported_clauses = max(0, supported_clause_count - 1)
    return competing_relations + competing_supported_clauses


def evidence_priority_proof_v11(
    query: str,
    memory: dict[str, Any],
    candidate_v2_original_rank: int,
    req: FrameRequirements | None = None,
) -> EvidencePriorityProofV11 | None:
    """Build a rank proof only for Candidate-v10-eligible evidence."""
    req = req or semantic_requirements_v10(query)
    certification = certify_memory_v10(query, memory, req)
    supported = [clause for clause in certification["clauses"] if clause.supported]
    if not supported:
        return None

    def clause_key(clause: Any) -> tuple[int, ...]:
        object_matches, object_total = _object_slot_coverage(clause.text, req)
        object_quality = object_matches if object_total else 0
        return (
            _subject_binding_quality(clause.text, str(memory["text"]), req),
            _relation_specificity(clause.text, req),
            object_quality,
            _assertion_directness(clause.text),
            _temporal_specificity(clause.text, req),
            _semantic_completeness(clause),
            -_ambiguity_penalty(clause.text, len(supported), req),
        )

    best = max(supported, key=clause_key)
    object_matches, object_total = _object_slot_coverage(best.text, req)
    subject_quality = _subject_binding_quality(best.text, str(memory["text"]), req)
    relation_specificity = _relation_specificity(best.text, req)
    assertion_directness = _assertion_directness(best.text)
    temporal_specificity = _temporal_specificity(best.text, req)
    completeness = _semantic_completeness(best)
    ambiguity = _ambiguity_penalty(best.text, len(supported), req)

    # Lexicographic proof ordering is deliberately non-compensatory. Candidate-v2
    # order is only the last tie-breaker and no lexical score is reintroduced.
    priority_tuple = (
        subject_quality,
        relation_specificity,
        object_matches if object_total else 0,
        assertion_directness,
        temporal_specificity,
        completeness,
        -ambiguity,
        -candidate_v2_original_rank,
    )

    return EvidencePriorityProofV11(
        memory_id=str(memory["id"]),
        subject_binding_quality=subject_quality,
        relation_specificity=relation_specificity,
        object_slot_matches=object_matches,
        object_slot_total=object_total,
        assertion_directness=assertion_directness,
        temporal_specificity=temporal_specificity,
        semantic_completeness=completeness,
        ambiguity_penalty=ambiguity,
        candidate_v2_original_rank=candidate_v2_original_rank,
        supported_clause=best.text,
        priority_tuple=priority_tuple,
    )


def evidence_support_signature_v11(case: dict[str, Any]) -> dict[str, Any]:
    safe_case = _safe_case(case)
    query = safe_case["query"]
    req = semantic_requirements_v10(query)
    full_ranking = pse_candidate_v2_rank(
        safe_case, max(5, len(safe_case["memories"]))
    )
    by_id = {str(memory["id"]): memory for memory in safe_case["memories"]}

    proofs: list[EvidencePriorityProofV11] = []
    for original_rank, memory_id in enumerate(full_ranking, start=1):
        memory = by_id.get(memory_id)
        if memory is None:
            continue
        proof = evidence_priority_proof_v11(
            query, memory, original_rank, req
        )
        if proof is not None:
            proofs.append(proof)

    proofs.sort(key=lambda proof: proof.priority_tuple, reverse=True)
    supporting_ids = [proof.memory_id for proof in proofs]
    return {
        "verdict": VERDICT_SUPPORTED if supporting_ids else VERDICT_INSUFFICIENT,
        "requirements": {
            "base": asdict(req.base),
            "relations": list(req.relations),
            "object_terms": list(req.object_terms),
        },
        "candidate_v2_ranking": full_ranking,
        "supporting_memory_ids": supporting_ids,
        "proofs": [asdict(proof) for proof in proofs],
    }


def pse_candidate_v11_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Safety-preserving semantic rank refinement over Candidate-v2 candidates."""
    signature = evidence_support_signature_v11(case)
    return signature["supporting_memory_ids"][:k]


def candidate_source_invariant_v11(case: dict[str, Any], k: int = 5) -> dict[str, Any]:
    """Evidence that v11 is a permutation/subsequence of eligible v2 candidates."""
    safe_case = _safe_case(case)
    full_v2 = pse_candidate_v2_rank(
        safe_case, max(k, len(safe_case["memories"]))
    )
    v11 = pse_candidate_v11_rank(safe_case, k)
    v2_set = set(full_v2)
    no_injection = all(memory_id in v2_set for memory_id in v11)

    req = semantic_requirements_v10(safe_case["query"])
    by_id = {str(memory["id"]): memory for memory in safe_case["memories"]}
    eligible = {
        memory_id
        for memory_id in full_v2
        if memory_id in by_id
        and certify_memory_v10(safe_case["query"], by_id[memory_id], req)["supported"]
    }
    only_eligible = all(memory_id in eligible for memory_id in v11)
    unique = len(v11) == len(set(v11))
    return {
        "candidate_v2_count": len(full_v2),
        "candidate_v11_count": len(v11),
        "no_injection": no_injection,
        "only_eligible": only_eligible,
        "unique": unique,
        "pass": no_injection and only_eligible and unique,
    }
