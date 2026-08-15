from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .candidate_v2 import pse_candidate_v2_rank
from .candidate_v8 import (
    DIRECT_ASSERTION,
    QueryRequirements,
    _blocker,
    _segment_clauses,
    _temporal_ok,
    _value_bearing,
    query_requirements,
)

VERDICT_SUPPORTED = "SUPPORTED"
VERDICT_INSUFFICIENT = "INSUFFICIENT"

# Candidate-v9 canonicalizes semantic relation intent instead of requiring
# Candidate-v8 lexical-family overlap. Patterns are generic language rules;
# no benchmark case IDs, answers, subject names, or protected-case strings
# are consulted by inference.
CANONICAL_RELATIONS: dict[str, tuple[str, ...]] = {
    "preference": (
        r"\bprefer(?:s|red|ring)?\b", r"\bfavou?r(?:s|ed|ing)?\b", r"\bfavou?rite\b",
        r"\bpartial\s+to\b", r"\bgo-?to\b", r"\busual\s+choice\b", r"\bregular\s+pick\b",
        r"\b(?:normally|usually|routinely|regularly|often)\b[^.;!?]{0,45}\b(?:choose|chooses|chose|pick|picks|picked|select|selects|selected|order|orders|ordered|have|has)\b",
        r"\btends?\s+to\s+(?:choose|pick|select|order|have)\b",
    ),
    "education_institution": (
        r"\b(?:university|college|school|campus|institution|polytechnic|academy)\b",
        r"\battend(?:s|ed|ing)?\b", r"\benroll(?:s|ed|ment)?\s+at\b",
        r"\bstud(?:y|ies|ied|ying)\s+at\b", r"\bpursu(?:e|es|ed|ing)\s+stud(?:y|ies)\b",
        r"\bstudent\s+at\b",
    ),
    "education_course": (
        r"\b(?:course|class|module|subject|seminar)\b", r"\benroll(?:s|ed|ment)?\s+in\b",
        r"\btak(?:e|es|ing)\s+(?:a\s+)?(?:course|class|module|subject|seminar)?\b",
        r"\bstud(?:y|ies|ied|ying)\b",
    ),
    "location": (
        r"\b(?:live|lives|lived|living|reside|resides|resided|residing|home|based|located|settled|city)\b",
        r"\bcall(?:s|ed|ing)?\b[^.;!?]{0,30}\bhome\b",
    ),
    "work_role": (
        r"\b(?:job|role|profession|occupation|career|professional)\b", r"\bworks?\s+as\b",
        r"\bserves?\s+as\b", r"\bemployed\s+as\b",
    ),
    "device_use": (
        r"\b(?:device|computer|laptop|tablet|phone|workstation|machine|macbook|thinkpad|surface|framework|zenbook)\b",
        r"\bworks?\s+(?:from|on)\b[^.;!?]{0,35}\b(?:computer|laptop|device|workstation|machine)\b",
    ),
    "transport": (
        r"\b(?:transport|transit|commute|commutes|commuting|bus|tram|metro|subway|train|route|line)\b",
        r"\baboard\b", r"\bgets?\s+to\s+work\b",
    ),
    "language": (
        r"\b(?:language|speak|speaks|speaking|fluent|fluently|communicate|communicates|communicating)\b",
    ),
    "activity": (
        r"\b(?:hobby|pastime|activity|practice|practices|practicing|enjoy|enjoys|weekends?)\b",
    ),
    "goal": (
        r"\b(?:goal|target|aim|training|train|trains|preparing|prepare|working\s+toward|working\s+towards)\b",
    ),
    "relationship": (
        r"\b(?:spouse|partner|married|marriage|husband|wife)\b",
    ),
    "membership": (
        r"\b(?:member|membership|club|society|association|organization|organisation|group|belongs?\s+to|joined?)\b",
    ),
    "status": (
        r"\b(?:status|state|approved|active|paused|ready|closed|scheduled|confirmed|archived|open|completed|pending)\b",
    ),
    "schedule": (
        r"\b(?:when|weekday|day|time|date|schedule|check-?in|appointment|meeting|recurring|standing)\b",
    ),
    "possession_pet": (
        r"\b(?:pet|animal|owns?|owned|keeps?|kept)\b",
    ),
    "media": (
        r"\b(?:music|genre|song|album|film|movie|listen|listens|listening|watch|watches|watching|read|reads|reading)\b",
    ),
    "health_medication": (
        r"\b(?:medication|medicine|drug|takes?|taking|prescribed)\b",
    ),
    "attribute_color": (
        r"\b(?:color|colour|colored|coloured|backpack|bag|shirt|jacket)\b",
    ),
}

VALUE_TYPE_PATTERNS: dict[str, tuple[str, ...]] = {
    "beverage": (r"\b(?:beverage|drink|coffee|tea|latte|espresso|cocoa|juice|water|soda|smoothie|kombucha)\b",),
    "food": (r"\b(?:food|meal|breakfast|lunch|dinner|toast|oatmeal|yogurt|sandwich|noodles|rice|salad)\b",),
    "institution": (r"\b(?:university|college|school|campus|institution|polytechnic|academy)\b",),
    "course": (r"\b(?:course|class|module|subject|seminar|calculus|ecology|robotics|linguistics|ceramics|statistics|geology)\b",),
    "location": (r"\b(?:city|home|based|located|reside|live|lives|taipei|kyoto|utrecht|oslo|adelaide|valencia|helsinki|nagoya|zurich|bologna)\b",),
    "role": (r"\b(?:job|role|profession|occupation|engineer|analyst|designer|technician|curator|planner|therapist|coordinator|researcher|architect)\b",),
    "device": (r"\b(?:device|computer|laptop|tablet|phone|workstation|machine|macbook|thinkpad|surface|framework|zenbook|elitebook|latitude)\b",),
    "transport": (r"\b(?:transport|transit|commute|bus|tram|metro|subway|train|route|line)\b",),
    "language": (r"\b(?:language|english|japanese|spanish|french|mandarin|italian|german|korean|portuguese|dutch|swedish)\b",),
    "activity": (r"\b(?:hobby|pastime|activity|climbing|cycling|painting|pottery|rowing|chess|gardening|photography|dancing|woodworking)\b",),
    "goal": (r"\b(?:goal|target|exam|marathon|triathlon|certificate|certification|portfolio|exhibition|audition|conference)\b",),
    "person": (r"\b(?:spouse|partner|married|husband|wife)\b",),
    "organization": (r"\b(?:club|society|association|organization|organisation|group|collective|orchestra|league|guild)\b",),
    "status": (r"\b(?:status|state|approved|active|paused|ready|closed|scheduled|confirmed|archived|open|completed|pending)\b",),
    "schedule": (r"\b(?:weekday|monday|tuesday|wednesday|thursday|friday|morning|afternoon|evening|time|date|schedule|check-?in|appointment)\b",),
    "pet": (r"\b(?:pet|animal|cat|dog|rabbit|parrot|gecko|hamster|fish|terrier|spaniel)\b",),
    "media": (r"\b(?:music|genre|jazz|folk|rock|pop|classical|ambient|soul|flamenco|film|movie|book)\b",),
    "medication": (r"\b(?:medication|medicine|ibuprofen|cetirizine|paracetamol|acetaminophen|naproxen)\b",),
    "color": (r"\b(?:color|colour|navy|teal|amber|violet|maroon|silver|olive|coral|charcoal|cream)\b",),
}

QUERY_VALUE_TYPES: dict[str, tuple[str, ...]] = {
    "beverage": (r"\b(?:beverage|drink)\b",),
    "food": (r"\b(?:food|meal|breakfast|lunch|dinner)\b",),
    "institution": (r"\b(?:where.*stud|institution|university|college|school|campus)\b",),
    "course": (r"\b(?:course|class|module|subject|seminar)\b",),
    "location": (r"\b(?:where.*(?:live|reside|based)|city|home)\b",),
    "role": (r"\b(?:job|role|profession|occupation|career)\b",),
    "device": (r"\b(?:device|computer|laptop|tablet|phone|workstation|machine)\b",),
    "transport": (r"\b(?:transport|transit|commute|bus|tram|metro|subway|train|route|line)\b",),
    "language": (r"\blanguage\b",),
    "activity": (r"\b(?:hobby|pastime|activity|for fun)\b",),
    "goal": (r"\b(?:goal|target|aim|prepar|training|working toward)\b",),
    "person": (r"\b(?:who|spouse|partner)\b",),
    "organization": (r"\b(?:club|society|association|organization|organisation|group|member)\b",),
    "status": (r"\b(?:status|state)\b",),
    "schedule": (r"\b(?:when|weekday|day|time|date|schedule|check-?in|appointment)\b",),
    "pet": (r"\b(?:pet|animal)\b",),
    "media": (r"\b(?:music|genre|song|album|film|movie|book|listen|watch|read)\b",),
    "medication": (r"\b(?:medication|medicine|drug)\b",),
    "color": (r"\b(?:color|colour)\b",),
}

RELATION_TO_VALUE_TYPES: dict[str, set[str]] = {
    "preference": {"beverage", "food", "media", "activity"},
    "education_institution": {"institution"},
    "education_course": {"course"},
    "location": {"location"},
    "work_role": {"role"},
    "device_use": {"device"},
    "transport": {"transport"},
    "language": {"language"},
    "activity": {"activity"},
    "goal": {"goal"},
    "relationship": {"person"},
    "membership": {"organization"},
    "status": {"status"},
    "schedule": {"schedule"},
    "possession_pet": {"pet"},
    "media": {"media"},
    "health_medication": {"medication"},
    "attribute_color": {"color"},
}

@dataclass(frozen=True)
class SemanticRequirements:
    base: QueryRequirements
    relations: tuple[str, ...]
    value_types: tuple[str, ...]

@dataclass(frozen=True)
class EvidenceClauseV9:
    text: str
    subject_ok: bool
    relation_ok: bool
    value_type_ok: bool
    value_bearing: bool
    direct_assertion: bool
    temporal_ok: bool
    blocker: str | None
    relation_signals: tuple[str, ...]
    value_type_signals: tuple[str, ...]
    score: int
    supported: bool


def _matches(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def _relation_signals(text: str) -> set[str]:
    return {name for name, patterns in CANONICAL_RELATIONS.items() if _matches(patterns, text)}


def _query_value_types(query: str) -> set[str]:
    return {name for name, patterns in QUERY_VALUE_TYPES.items() if _matches(patterns, query)}


def _evidence_value_types(text: str) -> set[str]:
    return {name for name, patterns in VALUE_TYPE_PATTERNS.items() if _matches(patterns, text)}


def semantic_requirements(query: str) -> SemanticRequirements:
    base = query_requirements(query)
    rels = _relation_signals(query)
    qlower = query.casefold()

    # Typed question-shape canonicalization. These rules bridge semantic forms
    # that Candidate-v8 split across lexical families.
    if re.search(r"\bwhere\b", qlower) and re.search(r"\bstud(?:y|ies|ied|ying)\b", qlower):
        rels.add("education_institution")
    if re.search(r"\b(?:beverage|drink|breakfast|meal|food)\b", qlower) and re.search(
        r"\b(?:prefer|favou?r|usual|normally|often|choice|pick)\b", qlower
    ):
        rels.add("preference")
    if re.search(r"\b(?:course|class|module|subject|seminar)\b", qlower):
        rels.add("education_course")
    if re.search(r"\b(?:where|city|home)\b", qlower) and not re.search(r"\bstud", qlower):
        rels.add("location")
    if re.search(r"\b(?:job|role|profession|occupation|career)\b", qlower):
        rels.add("work_role")
    if re.search(r"\b(?:device|computer|laptop|tablet|phone|workstation|machine)\b", qlower):
        rels.add("device_use")
    if re.search(r"\b(?:transport|transit|commute|bus|tram|metro|subway|train|route|line)\b", qlower):
        rels.add("transport")
    if re.search(r"\blanguage\b", qlower):
        rels.add("language")
    if re.search(r"\b(?:hobby|pastime|activity|for fun)\b", qlower):
        rels.add("activity")
    if re.search(r"\b(?:goal|target|aim|prepar|training|working toward)\b", qlower):
        rels.add("goal")
    if re.search(r"\b(?:spouse|partner|married)\b", qlower) or qlower.startswith("who "):
        rels.add("relationship")
    if re.search(r"\b(?:club|society|association|organization|organisation|group|member)\b", qlower):
        rels.add("membership")
    if re.search(r"\b(?:status|state)\b", qlower):
        rels.add("status")
    if re.search(r"\b(?:when|weekday|time|date|schedule|check-?in|appointment)\b", qlower):
        rels.add("schedule")
    if re.search(r"\b(?:pet|animal)\b", qlower):
        rels.add("possession_pet")
    if re.search(r"\b(?:music|genre|song|album|film|movie|book|listen|watch|read)\b", qlower):
        rels.add("media")
    if re.search(r"\b(?:medication|medicine|drug)\b", qlower):
        rels.add("health_medication")
    if re.search(r"\b(?:color|colour)\b", qlower):
        rels.add("attribute_color")

    value_types = _query_value_types(query)
    # If the query shape established exactly one relation and no explicit value
    # type, infer the bounded type(s) licensed by that relation.
    if not value_types and len(rels) == 1:
        value_types |= RELATION_TO_VALUE_TYPES.get(next(iter(rels)), set())
    return SemanticRequirements(base=base, relations=tuple(sorted(rels)), value_types=tuple(sorted(value_types)))


def _subject_ok_v9(clause: str, memory_text: str, req: SemanticRequirements) -> bool:
    base = req.base
    lowered = clause.casefold()
    memory_lower = memory_text.casefold()
    if base.subject_anchors:
        direct = all(
            re.search(rf"(?<![a-z0-9_-]){re.escape(anchor)}(?![a-z0-9_-])", lowered)
            for anchor in base.subject_anchors
        )
        if direct:
            return True
        # Bounded coreference: every canonical subject anchor must occur in the
        # same memory and the clause must carry an explicit third-person pronoun.
        in_memory = all(
            re.search(rf"(?<![a-z0-9_-]){re.escape(anchor)}(?![a-z0-9_-])", memory_lower)
            for anchor in base.subject_anchors
        )
        if in_memory and re.search(r"\b(?:he|she|they|his|her|their)\b", lowered):
            return True
        return False
    if base.first_person:
        return bool(re.search(r"\b(?:i|me|my|mine|user)\b", lowered))
    return True


def _relation_ok_v9(clause: str, req: SemanticRequirements) -> tuple[bool, set[str]]:
    qrels = set(req.relations)
    crels = _relation_signals(clause)
    shared = qrels & crels
    return bool(shared), shared


def _value_type_ok(clause: str, req: SemanticRequirements) -> tuple[bool, set[str]]:
    qtypes = set(req.value_types)
    ctypes = _evidence_value_types(clause)
    if not qtypes:
        return True, ctypes
    shared = qtypes & ctypes
    return bool(shared), shared


def certify_clause_v9(query: str, clause: str, memory_text: str, req: SemanticRequirements | None = None) -> EvidenceClauseV9:
    req = req or semantic_requirements(query)
    blocker = _blocker(clause, req.base)
    subject_ok = _subject_ok_v9(clause, memory_text, req)
    relation_ok, rel_evidence = _relation_ok_v9(clause, req)
    value_type_ok, type_evidence = _value_type_ok(clause, req)
    value_bearing = _value_bearing(query, clause, req.base)
    direct = bool(DIRECT_ASSERTION.search(clause)) or bool(
        re.search(r"\b(?:attends?|enrolled|serves?|belongs?|commutes?|speaks?|owns?|happens?|carries?|selects?|picks?|takes?)\b", clause, re.I)
    )
    temporal_ok = _temporal_ok(clause, req.base)
    score = sum((subject_ok, relation_ok, value_type_ok, value_bearing, direct, temporal_ok))
    supported = (
        blocker is None
        and subject_ok
        and relation_ok
        and value_type_ok
        and value_bearing
        and temporal_ok
        and score >= 5
    )
    return EvidenceClauseV9(
        text=clause,
        subject_ok=subject_ok,
        relation_ok=relation_ok,
        value_type_ok=value_type_ok,
        value_bearing=value_bearing,
        direct_assertion=direct,
        temporal_ok=temporal_ok,
        blocker=blocker,
        relation_signals=tuple(sorted(rel_evidence)),
        value_type_signals=tuple(sorted(type_evidence)),
        score=score,
        supported=supported,
    )


def certify_memory_v9(query: str, memory: dict[str, Any], req: SemanticRequirements | None = None) -> dict[str, Any]:
    req = req or semantic_requirements(query)
    text = str(memory["text"])
    clauses = [certify_clause_v9(query, clause, text, req) for clause in _segment_clauses(text)]
    return {
        "memory_id": str(memory["id"]),
        "supported": any(c.supported for c in clauses),
        "clauses": clauses,
    }


def evidence_support_signature_v9(case: dict[str, Any], ranking: list[str] | None = None) -> dict[str, Any]:
    safe_case = {
        "query": str(case["query"]),
        "memories": [
            {"id": str(m["id"]), "text": str(m["text"]), "timestamp": m.get("timestamp")}
            for m in case["memories"]
        ],
    }
    req = semantic_requirements(safe_case["query"])
    ranking = ranking if ranking is not None else pse_candidate_v2_rank(safe_case, max(5, len(safe_case["memories"])))
    by_id = {m["id"]: m for m in safe_case["memories"]}
    certifications = [certify_memory_v9(safe_case["query"], by_id[mid], req) for mid in ranking if mid in by_id]
    supported_ids = [row["memory_id"] for row in certifications if row["supported"]]
    return {
        "verdict": VERDICT_SUPPORTED if supported_ids else VERDICT_INSUFFICIENT,
        "requirements": {
            "base": asdict(req.base),
            "relations": list(req.relations),
            "value_types": list(req.value_types),
        },
        "supporting_memory_ids": supported_ids,
        "certifications": certifications,
    }


def pse_candidate_v9_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Candidate-v9: typed semantic relation certification over Candidate-v2.

    Candidate-v2 remains the sole ranker. Candidate-v9 receives only query and
    memory content/timestamps, certifies each ranked memory independently, and
    returns an order-preserving subsequence. Benchmark IDs, labels, answers,
    relevant IDs, split names, and provenance are intentionally ignored.
    """
    safe_case = {
        "query": str(case["query"]),
        "memories": [
            {"id": str(m["id"]), "text": str(m["text"]), "timestamp": m.get("timestamp")}
            for m in case["memories"]
        ],
    }
    full_ranking = pse_candidate_v2_rank(safe_case, max(k, len(safe_case["memories"])))
    signature = evidence_support_signature_v9(safe_case, full_ranking)
    allowed = set(signature["supporting_memory_ids"])
    return [mid for mid in full_ranking if mid in allowed][:k]
