from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .candidate_v2 import pse_candidate_v2_rank
from .candidate_v8 import (
    QueryRequirements,
    _blocker,
    _segment_clauses,
    _temporal_ok,
    _value_bearing,
    query_requirements,
)
from .zero_cost_baselines import _stem, tokens

VERDICT_SUPPORTED = "SUPPORTED"
VERDICT_INSUFFICIENT = "INSUFFICIENT"

# Candidate-v10 moves relation reasoning from closed value lexicons to bounded
# predicate/slot frames. Relation cues describe semantic slots; answer values
# remain open-class. No benchmark IDs, answers, split names, or generator-only
# metadata are visible to inference.
RELATION_PATTERNS: dict[str, tuple[str, ...]] = {
    "preference": (
        r"\bprefer(?:s|red|ring)?\b", r"\bfavou?r(?:s|ed|ing|ite)?\b", r"\bgo-?to\b",
        r"\b(?:choice|pick|selection)\b", r"\bpartial\s+to\b",
        r"\b(?:regular|usual|default|typical)\b[^.;!?]{0,35}\b(?:breakfast|meal|drink|beverage|pick|choice|selection|music|genre|activity|option)\b",
        r"\b(?:breakfast|meal|drink|beverage|pick|choice|selection|music|genre|activity|option)\b[^.;!?]{0,25}\b(?:regular|usual|default|typical)\b",
    ),
    "education_institution": (
        r"\b(?:university|college|school|campus|institution|academy|polytechnic)\b",
        r"\b(?:attend|attends|attended|stud(?:y|ies|ied|ying)\s+at|enrolled\s+at)\b",
    ),
    "education_course": (r"\b(?:course|class|module|subject|seminar)\b", r"\benrolled\s+in\b"),
    "location": (r"\b(?:where|city|home|address|location|live|lives|living|reside|resides|based|located)\b",),
    "work_role": (r"\b(?:job|role|profession|occupation|career|position|works?\s+as|serves?\s+as)\b",),
    "device_use": (r"\b(?:device|computer|laptop|tablet|phone|workstation|machine|primary\s+computer)\b",),
    "transport": (r"\b(?:transport|transit|commute|commuting|route|bus|tram|metro|subway|train)\b",),
    "language": (r"\b(?:language|speak|speaks|speaking|fluent|fluently)\b",),
    "activity": (r"\b(?:hobby|pastime|activity|for\s+fun|practice|practices|enjoys?)\b",),
    "goal": (r"\b(?:goal|target|aim|objective|training\s+for|preparing\s+for|working\s+toward)\b",),
    "relationship": (r"\b(?:spouse|partner|married|husband|wife)\b",),
    "membership": (r"\b(?:member|membership|society|association|belongs?\s+to|joined?)\b",),
    "status": (r"\b(?:status|state)\b",),
    "schedule": (r"\b(?:schedule|weekday|day|time|when|check-?in|meeting\s+time|recurring\s+meeting)\b",),
    "possession_pet": (r"\b(?:pet|animal|owns?\s+(?:a|an)|keeps?\s+(?:a|an))\b",),
    "media": (r"\b(?:music|genre|song|album|film|movie|book|listen|listens|watch|watches|read|reads)\b",),
    "health_medication": (r"\b(?:medication|medicine|drug|prescription)\b",),
    "attribute_color": (r"\b(?:color|colour|shade|hue)\b",),
    "certification": (r"\b(?:certification|certificate|credential|licen[cs]e|qualification)\b",),
    "subscription": (r"\b(?:subscription|subscribed|service\s+plan|plan\s+tier|membership\s+tier)\b",),
    "travel_plan": (r"\b(?:travel\s+plan|trip|itinerary|destination|travelling|traveling|flying\s+to|visiting)\b",),
    "dietary_restriction": (r"\b(?:dietary|diet|food\s+restriction|allerg(?:y|ic)|intoleran(?:ce|t)|vegan|vegetarian|gluten[- ]free)\b",),
    "sports_team": (r"\b(?:sports?\s+team|football\s+club|baseball\s+team|basketball\s+team|team\s+(?:supports?|follows?))\b",),
    "volunteering": (r"\b(?:volunteer|volunteering|community\s+service|service\s+shift)\b",),
    "software_tool": (r"\b(?:software|software\s+tool|app|editor|ide|code\s+editor|design\s+tool)\b",),
    "communication_channel": (r"\b(?:communication\s+channel|contact\s+channel|contact\s+method|reach\s+.+\s+via|contact\s+.+\s+by)\b",),
    "routine": (r"\b(?:routine|habit|ritual|recurring\s+routine|daily\s+practice)\b",),
    "project_ownership": (r"\b(?:project\s+ownership|project\s+owner|owns?\s+the\s+project|leads?\s+the\s+project|responsible\s+for\s+the\s+project)\b",),
    "appointment": (r"\b(?:appointment|booking|reservation|scheduled\s+visit)\b",),
    "accommodation": (r"\b(?:accommodation|lodging|hotel|hostel|guesthouse|place\s+to\s+stay)\b",),
}

PRIMARY_PRIORITY = (
    "subscription", "sports_team", "volunteering", "software_tool", "communication_channel",
    "routine", "project_ownership", "appointment", "accommodation", "travel_plan",
    "dietary_restriction", "certification", "preference", "education_institution",
    "education_course", "work_role", "device_use", "transport", "language", "goal",
    "relationship", "membership", "status", "schedule", "possession_pet", "media",
    "health_medication", "attribute_color", "activity", "location",
)

ASSIGNMENT = re.compile(
    r"(?:\b(?:is|are|has|have|uses?|owns?|keeps?|takes?|speaks?|attends?|works?|serves?|belongs?|joined?|lists?|records?|contains?|shows?)\b|[:—-])",
    re.I,
)
PRONOUN = re.compile(r"\b(?:he|she|they|his|her|their)\b", re.I)

GENERIC_OBJECT_STOP = {
    _stem(x) for x in {
        "current", "currently", "now", "today", "latest", "state", "status", "color", "colour",
        "job", "role", "profession", "occupation", "career", "device", "computer", "laptop",
        "course", "class", "school", "university", "college", "city", "home", "language",
        "pet", "animal", "music", "genre", "medication", "medicine", "schedule", "time", "day",
        "subscription", "certification", "certificate", "routine", "habit", "appointment",
        "accommodation", "hotel", "project", "team", "software", "tool", "channel", "diet",
        "travel", "trip", "goal", "hobby", "activity", "membership", "member",
    }
}


@dataclass(frozen=True)
class FrameRequirements:
    base: QueryRequirements
    relations: tuple[str, ...]
    object_terms: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceClauseV10:
    text: str
    subject_ok: bool
    relation_ok: bool
    value_type_ok: bool
    value_bearing: bool
    assertion_ok: bool
    temporal_ok: bool
    blocker: str | None
    relation_signals: tuple[str, ...]
    proof: tuple[str, ...]
    supported: bool


def _matches(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def _raw_relation_signals(text: str) -> set[str]:
    return {name for name, patterns in RELATION_PATTERNS.items() if _matches(patterns, text)}


def _primary_relations(text: str) -> set[str]:
    raw = _raw_relation_signals(text)
    if not raw:
        return set()
    for rel in PRIMARY_PRIORITY:
        if rel in raw:
            if rel == "preference":
                return {"preference"}
            if rel in {
                "subscription", "sports_team", "volunteering", "software_tool",
                "communication_channel", "routine", "project_ownership", "appointment",
                "accommodation", "travel_plan", "dietary_restriction", "certification",
            }:
                return {rel}
            break
    return raw


def _object_terms(query: str) -> set[str]:
    q = query.replace("’s", "'s")
    if "'s" not in q:
        return set()
    tail = q.split("'s", 1)[1]
    # Temporal adjectives such as "current" are filtered as stop terms rather
    # than cutting the possessed object phrase. This preserves open objects
    # such as "permit" in "current permit status".
    tail = re.split(r"\b(?:in|on|at|for|with|now|today|these\s+days)\b", tail, maxsplit=1, flags=re.I)[0]
    out = set()
    for tok in tokens(tail):
        s = _stem(tok)
        if len(s) <= 1 or s in GENERIC_OBJECT_STOP:
            continue
        out.add(s)
    return out


def semantic_requirements_v10(query: str) -> FrameRequirements:
    base = query_requirements(query)
    rels = _primary_relations(query)
    q = query.casefold()
    if not rels and re.search(r"\bwhere\b", q):
        rels.add("location")
    if not rels and re.search(r"\bwho\b", q) and re.search(r"\b(?:partner|spouse|married)\b", q):
        rels.add("relationship")
    return FrameRequirements(base=base, relations=tuple(sorted(rels)), object_terms=tuple(sorted(_object_terms(query))))


def _subject_ok(clause: str, memory_text: str, req: FrameRequirements) -> bool:
    lowered = clause.casefold()
    memory_lower = memory_text.casefold()
    if req.base.subject_anchors:
        direct = all(
            re.search(rf"(?<![a-z0-9_-]){re.escape(anchor)}(?![a-z0-9_-])", lowered)
            for anchor in req.base.subject_anchors
        )
        if direct:
            return True
        in_memory = all(
            re.search(rf"(?<![a-z0-9_-]){re.escape(anchor)}(?![a-z0-9_-])", memory_lower)
            for anchor in req.base.subject_anchors
        )
        return bool(in_memory and PRONOUN.search(lowered))
    if req.base.first_person:
        return bool(re.search(r"\b(?:i|me|my|mine|user)\b", lowered))
    return True


def _relation_ok(clause: str, req: FrameRequirements) -> tuple[bool, set[str], set[str]]:
    qrels = set(req.relations)
    crels = _primary_relations(clause)
    shared = qrels & crels
    if shared:
        return True, crels, {f"relation:{x}" for x in sorted(shared)}
    if qrels in ({"status"}, {"attribute_color"}) and req.object_terms and ASSIGNMENT.search(clause):
        cstems = {_stem(t) for t in tokens(clause)}
        overlap = set(req.object_terms) & cstems
        conflicting = crels - qrels
        if overlap and not conflicting:
            return True, crels, {f"object-slot:{x}" for x in sorted(overlap)}
    return False, crels, set()


def _value_type_ok(req: FrameRequirements, relation_ok: bool, evidence_relations: set[str]) -> tuple[bool, set[str]]:
    if not req.relations:
        return False, set()
    if relation_ok:
        return True, {f"range:{x}" for x in req.relations}
    if set(req.relations) & evidence_relations:
        return True, {f"range:{x}" for x in set(req.relations) & evidence_relations}
    return False, set()


def certify_clause_v10(query: str, clause: str, memory_text: str, req: FrameRequirements | None = None) -> EvidenceClauseV10:
    req = req or semantic_requirements_v10(query)
    blocker = _blocker(clause, req.base)
    subject_ok = _subject_ok(clause, memory_text, req)
    relation_ok, crels, relation_proof = _relation_ok(clause, req)
    value_type_ok, type_proof = _value_type_ok(req, relation_ok, crels)
    value_bearing = _value_bearing(query, clause, req.base)
    assertion_ok = bool(ASSIGNMENT.search(clause))
    temporal_ok = _temporal_ok(clause, req.base)
    proof = set(relation_proof) | set(type_proof)
    if subject_ok:
        proof.add("subject")
    if value_bearing:
        proof.add("open-value")
    if assertion_ok:
        proof.add("assertion")
    if temporal_ok:
        proof.add("temporal")
    supported = (
        blocker is None
        and subject_ok
        and relation_ok
        and value_type_ok
        and value_bearing
        and assertion_ok
        and temporal_ok
    )
    return EvidenceClauseV10(
        text=clause,
        subject_ok=subject_ok,
        relation_ok=relation_ok,
        value_type_ok=value_type_ok,
        value_bearing=value_bearing,
        assertion_ok=assertion_ok,
        temporal_ok=temporal_ok,
        blocker=blocker,
        relation_signals=tuple(sorted(crels)),
        proof=tuple(sorted(proof)),
        supported=supported,
    )


def certify_memory_v10(query: str, memory: dict[str, Any], req: FrameRequirements | None = None) -> dict[str, Any]:
    req = req or semantic_requirements_v10(query)
    text = str(memory["text"])
    clauses = [certify_clause_v10(query, c, text, req) for c in _segment_clauses(text)]
    return {"memory_id": str(memory["id"]), "supported": any(c.supported for c in clauses), "clauses": clauses}


def evidence_support_signature_v10(case: dict[str, Any], ranking: list[str] | None = None) -> dict[str, Any]:
    safe_case = {
        "query": str(case["query"]),
        "memories": [
            {"id": str(m["id"]), "text": str(m["text"]), "timestamp": m.get("timestamp")}
            for m in case["memories"]
        ],
    }
    req = semantic_requirements_v10(safe_case["query"])
    ranking = ranking if ranking is not None else pse_candidate_v2_rank(safe_case, max(5, len(safe_case["memories"])))
    by_id = {m["id"]: m for m in safe_case["memories"]}
    certifications = [certify_memory_v10(safe_case["query"], by_id[mid], req) for mid in ranking if mid in by_id]
    supported_ids = [row["memory_id"] for row in certifications if row["supported"]]
    return {
        "verdict": VERDICT_SUPPORTED if supported_ids else VERDICT_INSUFFICIENT,
        "requirements": {"base": asdict(req.base), "relations": list(req.relations), "object_terms": list(req.object_terms)},
        "supporting_memory_ids": supported_ids,
        "certifications": certifications,
    }


def pse_candidate_v10_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Frame/constraint verifier over Candidate-v2's order-preserving ranking."""
    safe_case = {
        "query": str(case["query"]),
        "memories": [
            {"id": str(m["id"]), "text": str(m["text"]), "timestamp": m.get("timestamp")}
            for m in case["memories"]
        ],
    }
    full_ranking = pse_candidate_v2_rank(safe_case, max(k, len(safe_case["memories"])))
    signature = evidence_support_signature_v10(safe_case, full_ranking)
    allowed = set(signature["supporting_memory_ids"])
    return [mid for mid in full_ranking if mid in allowed][:k]
