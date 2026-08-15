from __future__ import annotations

"""Candidate-v13 fresh-lineage structured semantic retrieval.

Candidate-v13 is historically informed but independently preregistered. It
uses Candidate-v2 as the exclusive candidate source and reuses frozen semantic
certification/proof primitives from v10/v11, while owning the v13 runtime
frame, explicit evidence-state layer, hard eligibility policy, metadata
firewall, and deterministic non-compensatory ordering.

No benchmark stage/family/case/gold metadata is visible to inference.
"""

import re
from dataclasses import asdict, dataclass, replace
from typing import Any

from .candidate_v2 import pse_candidate_v2_rank
from .candidate_v10 import FrameRequirements, semantic_requirements_v10
from .candidate_v11 import EvidencePriorityProofV11, evidence_priority_proof_v11
from .candidate_v12 import StructuredQueryFrameV12, parse_query_frame_v12

VERDICT_SUPPORTED = "SUPPORTED"
VERDICT_INSUFFICIENT = "INSUFFICIENT"

_NEGATION = re.compile(
    r"\b(?:not|never|no\s+verified|incorrect|false|contradict(?:s|ed|ory)?|"
    r"does\s+not|did\s+not|is\s+not|are\s+not|was\s+not|were\s+not)\b",
    re.I,
)
_UNCERTAINTY = re.compile(
    r"\b(?:perhaps|maybe|possibly|uncertain|unverified|rumou?r|might|could)\b",
    re.I,
)
_ALIAS_CUE = re.compile(r"\b(?:also\s+known\s+as|aka|alias(?:ed)?\s+as)\b", re.I)
_FIRST_PERSON = re.compile(r"\b(?:i|me|my|mine)\b", re.I)


@dataclass(frozen=True)
class StructuredSemanticFrameV13:
    target_subject: tuple[str, ...]
    subject_aliases: tuple[str, ...]
    subject_coreference: tuple[str, ...]
    target_relation: tuple[str, ...]
    relation_aliases: tuple[str, ...]
    requested_answer_type: str
    predicate_constraints: tuple[str, ...]
    object_constraints: tuple[str, ...]
    temporal_scope: str
    modality_status: str
    negated_query: bool
    discourse_intent: str
    semantic_proposition_spans: tuple[str, ...]
    evidence_support_state: str
    evidence_contradiction_state: str
    evidence_ambiguity_state: str
    subject_ambiguous: bool
    relation_ambiguous: bool
    parse_valid: bool


@dataclass(frozen=True)
class EvidenceProofV13:
    memory_id: str
    support_state: str
    contradiction_state: str
    ambiguity_state: str
    semantic_proof: EvidencePriorityProofV11
    priority_tuple: tuple[int, ...]


def _safe_case(case: dict[str, Any]) -> dict[str, Any]:
    """Strict firewall: inference sees only production-style runtime fields."""
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


def _entity_anchors(span: str) -> tuple[str, ...]:
    cleaned = span.replace("’", "'")
    out: list[str] = []
    for token in cleaned.split():
        token = re.sub(r"'s$", "", token, flags=re.I)
        if token:
            out.append(token.casefold())
    return tuple(out)


def _aliases_for_subject(
    subject: tuple[str, ...], memories: list[dict[str, Any]]
) -> tuple[str, ...]:
    """Extract only explicit runtime alias assertions tied to the bound subject."""
    if not subject:
        return tuple()
    name = subject[0]
    aliases: set[str] = set()
    name_pat = re.escape(name)
    for memory in memories:
        text = str(memory["text"])
        if not re.search(rf"(?<!\w){name_pat}(?!\w)", text, re.I):
            continue
        if not _ALIAS_CUE.search(text):
            continue
        match = re.search(
            rf"(?<!\w){name_pat}(?!\w).*?"
            r"(?:also\s+known\s+as|aka|alias(?:ed)?\s+as)\s+"
            r"([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,3})",
            text,
            re.I,
        )
        if match:
            alias = match.group(1).strip(" .,;:")
            if alias.casefold() != name.casefold():
                aliases.add(alias)
    return tuple(sorted(aliases, key=str.casefold))


def parse_query_frame_v13(
    query: str, memories: list[dict[str, Any]]
) -> StructuredSemanticFrameV13:
    """Build the Candidate-v13 runtime frame from legitimate runtime input."""
    base: StructuredQueryFrameV12 = parse_query_frame_v12(query, memories)
    aliases = _aliases_for_subject(base.subject_entities, memories)

    relation_aliases: set[str] = set(base.relation_candidates)
    relation_aliases.update(base.relation_frame)

    if base.subject_ambiguous:
        ambiguity = "SUBJECT_AMBIGUOUS"
    elif base.relation_ambiguous:
        ambiguity = "RELATION_AMBIGUOUS"
    else:
        ambiguity = "RESOLVED"

    return StructuredSemanticFrameV13(
        target_subject=base.subject_entities,
        subject_aliases=aliases,
        subject_coreference=base.subject_coreference,
        target_relation=base.relation_frame,
        relation_aliases=tuple(sorted(relation_aliases)),
        requested_answer_type=base.answer_type,
        predicate_constraints=base.predicate_constraints,
        object_constraints=base.object_constraints,
        temporal_scope=base.temporal_scope,
        modality_status=base.modality,
        negated_query=any(bool(_NEGATION.search(span)) for span in base.semantic_proposition_spans),
        discourse_intent=base.discourse_intent,
        semantic_proposition_spans=base.semantic_proposition_spans,
        evidence_support_state="UNASSESSED",
        evidence_contradiction_state="UNASSESSED",
        evidence_ambiguity_state=ambiguity,
        subject_ambiguous=base.subject_ambiguous,
        relation_ambiguous=base.relation_ambiguous,
        parse_valid=base.parse_valid,
    )


def _requirements_from_frame(
    query: str, frame: StructuredSemanticFrameV13
) -> FrameRequirements | None:
    if not frame.parse_valid or frame.negated_query:
        return None

    original = semantic_requirements_v10(query)
    subject_anchors: tuple[str, ...] = tuple()
    if frame.target_subject:
        subject_anchors = _entity_anchors(frame.target_subject[0])

    base = replace(
        original.base,
        subject_anchors=subject_anchors,
        first_person=(not subject_anchors and bool(_FIRST_PERSON.search(query))),
        temporal_scope=frame.temporal_scope,
    )
    return FrameRequirements(
        base=base,
        relations=frame.target_relation,
        object_terms=frame.object_constraints,
    )


def _evidence_states(
    memory: dict[str, Any], proof: EvidencePriorityProofV11
) -> tuple[str, str, str]:
    text = str(memory["text"])
    contradiction = "CONTRADICTED" if _NEGATION.search(text) else "NOT_CONTRADICTED"
    uncertain = bool(_UNCERTAINTY.search(text))
    ambiguity = (
        "AMBIGUOUS"
        if uncertain or proof.ambiguity_penalty > 0
        else "UNAMBIGUOUS"
    )
    support = (
        "DIRECT_SUPPORTED"
        if contradiction == "NOT_CONTRADICTED" and not uncertain
        else "NOT_ELIGIBLE"
    )
    return support, contradiction, ambiguity


def evidence_support_signature_v13(case: dict[str, Any]) -> dict[str, Any]:
    safe_case = _safe_case(case)
    query = safe_case["query"]
    memories = safe_case["memories"]
    frame = parse_query_frame_v13(query, memories)
    req = _requirements_from_frame(query, frame)

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
    proofs: list[EvidenceProofV13] = []
    for original_rank, memory_id in enumerate(full_ranking, start=1):
        memory = by_id.get(memory_id)
        if memory is None:
            continue
        semantic = evidence_priority_proof_v11(
            query=query,
            memory=memory,
            candidate_v2_original_rank=original_rank,
            req=req,
        )
        if semantic is None:
            continue

        support, contradiction, ambiguity = _evidence_states(memory, semantic)

        # Hard eligibility is non-compensatory: a contradiction or uncertainty
        # cannot be rescued by a strong lexical or proof score.
        if support != "DIRECT_SUPPORTED" or contradiction != "NOT_CONTRADICTED":
            continue

        priority = (
            1,
            1 if ambiguity == "UNAMBIGUOUS" else 0,
            *semantic.priority_tuple,
        )
        proofs.append(
            EvidenceProofV13(
                memory_id=str(memory_id),
                support_state=support,
                contradiction_state=contradiction,
                ambiguity_state=ambiguity,
                semantic_proof=semantic,
                priority_tuple=priority,
            )
        )

    proofs.sort(key=lambda p: p.priority_tuple, reverse=True)
    supporting = [proof.memory_id for proof in proofs]
    return {
        "verdict": VERDICT_SUPPORTED if supporting else VERDICT_INSUFFICIENT,
        "frame": asdict(frame),
        "candidate_v2_ranking": full_ranking,
        "supporting_memory_ids": supporting,
        "proofs": [
            {
                "memory_id": proof.memory_id,
                "support_state": proof.support_state,
                "contradiction_state": proof.contradiction_state,
                "ambiguity_state": proof.ambiguity_state,
                "semantic_proof": asdict(proof.semantic_proof),
                "priority_tuple": list(proof.priority_tuple),
            }
            for proof in proofs
        ],
    }


def pse_candidate_v13_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    return evidence_support_signature_v13(case)["supporting_memory_ids"][:k]


def candidate_source_invariant_v13(case: dict[str, Any], k: int = 5) -> dict[str, Any]:
    safe_case = _safe_case(case)
    full_v2 = pse_candidate_v2_rank(
        safe_case, max(k, len(safe_case["memories"]))
    )
    v13 = pse_candidate_v13_rank(safe_case, k)
    v2_set = set(full_v2)
    no_injection = all(memory_id in v2_set for memory_id in v13)
    unique = len(v13) == len(set(v13))
    return {
        "candidate_v2_count": len(full_v2),
        "candidate_v13_count": len(v13),
        "no_injection": no_injection,
        "unique": unique,
        "pass": no_injection and unique,
    }
