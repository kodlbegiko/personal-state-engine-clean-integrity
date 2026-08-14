from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .candidate_v2 import content_tokens, pse_candidate_v2_rank
from .zero_cost_baselines import _stem, parse_timestamp, tokens

VERDICT_SUPPORTED = "SUPPORTED"
VERDICT_INSUFFICIENT = "INSUFFICIENT"
VERDICT_CONTRADICTED = "CONTRADICTED"

CURRENT_CUES = {_stem(x) for x in {"current", "latest", "now", "currently", "still"}}
STALE_CUES = {_stem(x) for x in {"old", "previous", "prior", "formerly", "used", "before", "stale", "superseded", "obsolete"}}
UPDATE_CUES = {_stem(x) for x in {"updated", "changed", "corrected", "replaced", "moved", "switched", "rescheduled", "became", "now", "currently"}}

QUESTION_START = re.compile(r"^\s*(?:what|which|who|where|when|how|does|do|did|is|are|can|could|would|should)\b", re.I)
NO_VALUE = re.compile(
    r"\b(?:no\s+(?:recorded|known|confirmed|available|explicit|direct)?\s*(?:answer|value|fact|result|record|information)|"
    r"(?:answer|value|fact|result|record|information)\s+(?:is\s+)?(?:missing|absent|unknown|unavailable|not\s+recorded)|"
    r"(?:do|does|did)\s+not\s+know|not\s+known|hasn['’]?t\s+been\s+decided|not\s+decided|cannot\s+determine)\b",
    re.I,
)
AGENDA = re.compile(r"\b(?:agenda|action item|to discuss|discussion topic|review topic|review of)\b", re.I)
META_ONLY = re.compile(r"\b(?:prompt|instruction|query|keyword|question wording|we discussed|discussion about|mentioned only|topic only)\b", re.I)
UNRESOLVED = re.compile(r"\b(?:unresolved|uncertain|pending|maybe|perhaps|probably|likely|guess|assume|might|possibly|tentative)\b", re.I)
EXPLICIT_CONFLICT = re.compile(r"\b(?:contradictory|conflicting|records conflict|values conflict|cannot reconcile|disagree on)\b", re.I)
NEGATIVE_DECOY = re.compile(
    r"\b(?:wrong|incorrect|fake|fabricated|decoy|unrelated)\s+(?:answer|value|fact|record|memory|claim|detail)\b|"
    r"\bdo\s+not\s+use\b|\bignore\s+(?:this|that|the)\b",
    re.I,
)

CUE_FAMILIES: dict[str, set[str]] = {
    "preference": {"prefer", "preference", "favorite", "favourite", "like", "love", "enjoy", "obsess", "choose", "pick", "go-to", "usually", "always"},
    "location": {"where", "live", "reside", "home", "location", "located", "move", "moved", "based", "city", "town", "address", "room", "site"},
    "work_role": {"work", "job", "role", "employer", "company", "occupation", "career", "teach", "teacher", "engineer", "designer", "manager"},
    "schedule_time": {"when", "time", "date", "schedule", "scheduled", "appointment", "meeting", "morning", "afternoon", "evening", "weekday", "weekend", "day"},
    "contact": {"phone", "telephone", "mobile", "email", "e-mail", "contact", "address"},
    "possession": {"have", "has", "own", "owns", "adopt", "adopted", "pet", "car", "device", "carry", "uses", "use"},
    "activity_hobby": {"hobby", "activity", "play", "plays", "practice", "practices", "train", "training", "read", "run", "hike", "climb", "swim", "paint", "cook"},
    "travel": {"travel", "trip", "visit", "visited", "fly", "flight", "hotel", "destination", "vacation", "holiday"},
    "food_drink": {"food", "drink", "eat", "eats", "order", "orders", "tea", "coffee", "snack", "meal", "restaurant", "breakfast", "lunch", "dinner"},
    "relationship": {"mother", "father", "sister", "brother", "partner", "spouse", "friend", "colleague", "child", "children", "family"},
    "quantity_numeric": {"how many", "count", "quantity", "number", "amount", "budget", "price", "cost", "balance", "salary", "age"},
    "status_state": {"status", "state", "current", "latest", "now", "became", "changed", "updated", "completed", "active", "inactive"},
}
CUE_STEMS = {
    family: {_stem(token) for cue in cues for token in re.findall(r"[A-Za-z0-9_-]+", cue.casefold())}
    for family, cues in CUE_FAMILIES.items()
}

GENERIC_STOP = {
    _stem(x) for x in {
        "what", "which", "who", "where", "when", "how", "does", "do", "did", "is", "are",
        "was", "were", "the", "a", "an", "of", "for", "to", "at", "on", "in", "and", "or",
        "with", "user", "person", "tell", "me", "please", "current", "latest", "now", "still",
        "recorded", "known", "fact", "information", "about", "their", "his", "her", "my", "your",
    }
}
ALL_CUE_STEMS = set().union(*CUE_STEMS.values())


@dataclass(frozen=True)
class SupportEvidence:
    memory_id: str
    path: str
    families: tuple[str, ...]
    anchor_coverage: float
    temporal_scope: str


def _stems(text: str) -> set[str]:
    return {_stem(t) for t in tokens(text)}


def _families(text: str) -> set[str]:
    stems = _stems(text)
    return {family for family, cues in CUE_STEMS.items() if stems & cues}


def _entity_anchors(query: str) -> set[str]:
    raw = re.findall(r"\b[A-Za-z][A-Za-z0-9_-]*\b", query)
    anchors: set[str] = set()
    for i, atom in enumerate(raw):
        stem = _stem(atom)
        if stem in GENERIC_STOP or stem in ALL_CUE_STEMS:
            continue
        if atom.casefold() in {"i", "me", "my", "user"}:
            continue
        if any(c.isdigit() for c in atom) or "-" in atom or (atom[0].isupper() and i > 0):
            anchors.add(atom.casefold())
    return anchors


def _query_is_first_person(query: str) -> bool:
    q = set(tokens(query))
    return bool(q & {"i", "me", "my"})


def _memory_is_first_person(text: str) -> bool:
    t = set(tokens(text))
    return bool(t & {"i", "me", "my", "mine"})


def _temporal_scope(text: str) -> str:
    stems = _stems(text)
    if stems & UPDATE_CUES:
        return "CURRENT"
    if stems & STALE_CUES:
        return "STALE"
    return "UNSPECIFIED"


def _current_query(query: str) -> bool:
    return bool(_stems(query) & CURRENT_CUES)


def _hard_reject_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if NO_VALUE.search(text) or AGENDA.search(text) or EXPLICIT_CONFLICT.search(text) or NEGATIVE_DECOY.search(text):
        return True
    if stripped.endswith("?") and QUESTION_START.search(stripped):
        return True
    if META_ONLY.search(text):
        if not re.search(r"\b(?:but|however|actually|correction|updated|changed|now|currently)\b", text, re.I):
            return True
    if UNRESOLVED.search(text) and not re.search(r"\b(?:confirmed|resolved|now known|now confirmed|currently confirmed)\b", text, re.I):
        return True
    return False


def _relation_compatible(query: str, text: str) -> tuple[bool, set[str]]:
    qf = _families(query)
    mf = _families(text)
    if not qf:
        return True, set()
    shared = qf & mf
    return bool(shared), shared


def _subject_compatible(query: str, text: str) -> bool:
    anchors = _entity_anchors(query)
    lowered = text.casefold()
    if anchors:
        return all(re.search(rf"(?<![a-z0-9_-]){re.escape(anchor)}(?![a-z0-9_-])", lowered) for anchor in anchors)
    if _query_is_first_person(query):
        return _memory_is_first_person(text) or bool(re.search(r"\buser\b", lowered))
    return True


def _anchor_coverage(query: str, text: str) -> float:
    q_content = {
        _stem(t) for t in content_tokens(query)
        if _stem(t) not in GENERIC_STOP and _stem(t) not in ALL_CUE_STEMS
    }
    if not q_content:
        return 1.0
    m = {_stem(t) for t in content_tokens(text)}
    return len(q_content & m) / len(q_content)


def _specific_novel_tokens(query: str, text: str) -> set[str]:
    q = {_stem(t) for t in content_tokens(query)} | GENERIC_STOP | ALL_CUE_STEMS
    result = {
        _stem(t) for t in content_tokens(text)
        if _stem(t) not in q and len(_stem(t)) > 1
    }
    return result


def _strict_direct_support(query: str, text: str) -> bool:
    if _hard_reject_text(text) or not _subject_compatible(query, text):
        return False
    compatible, _ = _relation_compatible(query, text)
    if not compatible:
        return False
    direct = bool(re.search(
        r"\b(?:is|are|was|were|has|have|uses|use|prefers?|likes?|loves?|works?|lives?|resides?|"
        r"moved|changed|updated|switched|became|plays?|practices?|orders?|adopted)\b",
        text, re.I
    ))
    return direct and bool(_specific_novel_tokens(query, text))


def _generic_support(query: str, text: str) -> tuple[bool, set[str], float]:
    if _hard_reject_text(text):
        return False, set(), 0.0
    if not _subject_compatible(query, text):
        return False, set(), 0.0
    compatible, shared = _relation_compatible(query, text)
    if not compatible:
        return False, shared, 0.0
    if _current_query(query) and _temporal_scope(text) == "STALE":
        return False, shared, 0.0

    coverage = _anchor_coverage(query, text)
    novel = _specific_novel_tokens(query, text)
    entity = bool(_entity_anchors(query)) or _query_is_first_person(query)
    family_signal = bool(shared)

    supported = bool(novel) and (
        coverage >= 0.20
        or (entity and family_signal)
        or (not _families(query) and coverage >= 0.34)
    )
    return supported, shared, coverage


def evidence_support_signature(case: dict[str, Any], ranking: list[str] | None = None) -> dict[str, Any]:
    query = str(case["query"])
    memories = [
        {"id": str(memory["id"]), "text": str(memory["text"]), "timestamp": memory.get("timestamp")}
        for memory in case["memories"]
    ]
    safe_case = {"query": query, "memories": memories}
    ranking = ranking if ranking is not None else pse_candidate_v2_rank(safe_case, 5)
    by_id = {memory["id"]: memory for memory in memories}

    evidence: list[SupportEvidence] = []
    for memory_id in ranking:
        memory = by_id.get(memory_id)
        if memory is None:
            continue
        text = memory["text"]
        if _current_query(query) and _temporal_scope(text) == "STALE":
            continue
        if _strict_direct_support(query, text):
            evidence.append(SupportEvidence(
                memory_id=memory_id,
                path="STRICT_DIRECT",
                families=tuple(sorted(_families(query) & _families(text))),
                anchor_coverage=_anchor_coverage(query, text),
                temporal_scope=_temporal_scope(text),
            ))
            continue
        supported, shared, coverage = _generic_support(query, text)
        if supported:
            evidence.append(SupportEvidence(
                memory_id=memory_id,
                path="GENERIC_COMPATIBILITY",
                families=tuple(sorted(shared)),
                anchor_coverage=coverage,
                temporal_scope=_temporal_scope(text),
            ))

    return {
        "verdict": VERDICT_SUPPORTED if evidence else VERDICT_INSUFFICIENT,
        "supporting_memory_ids": [e.memory_id for e in evidence],
        "evidence": evidence,
    }


def pse_candidate_v7_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Candidate-v7: frozen Candidate-v2 ranking gated by deterministic evidence support.

    Ground-truth fields, case IDs, question type labels, answer strings and `_abs`
    suffixes are deliberately not read. Only query, memory text, timestamp and memory
    identity are copied into the inference surface.
    """
    safe_case = {
        "query": str(case["query"]),
        "memories": [
            {"id": str(memory["id"]), "text": str(memory["text"]), "timestamp": memory.get("timestamp")}
            for memory in case["memories"]
        ],
    }
    ranking = pse_candidate_v2_rank(safe_case, k)
    signature = evidence_support_signature(safe_case, ranking)
    return ranking if signature["verdict"] == VERDICT_SUPPORTED else []
