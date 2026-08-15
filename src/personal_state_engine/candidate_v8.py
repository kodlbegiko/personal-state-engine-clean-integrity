from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any

from .candidate_v2 import content_tokens, pse_candidate_v2_rank
from .zero_cost_baselines import _stem, tokens

VERDICT_SUPPORTED = "SUPPORTED"
VERDICT_INSUFFICIENT = "INSUFFICIENT"

# Candidate-v8 treats these as semantic hints, never sufficient proof by themselves.
RELATION_PATTERNS: dict[str, tuple[str, ...]] = {
    "preference_choice": (
        r"\bprefer(?:s|red|ring)?\b", r"\bfavou?rite\b", r"\breach(?:es|ed|ing)?\s+for\b",
        r"\bchoose(?:s|n)?\b", r"\bchose\b", r"\border(?:s|ed|ing)?\b", r"\bgo-?to\b",
        r"\busually\b", r"\bmost often\b",
    ),
    "food_drink": (
        r"\bdrink\b", r"\bbeverage\b", r"\bfood\b", r"\bmeal\b", r"\beat(?:s|ing)?\b",
        r"\bcoffee\b", r"\btea\b", r"\bbreakfast\b", r"\blunch\b", r"\bdinner\b",
    ),
    "location": (
        r"\bwhere\b", r"\bliv(?:e|es|ed|ing)\b", r"\bresid(?:e|es|ed|ing)\b",
        r"\blocat(?:e|ed|ion)\b", r"\baddress\b", r"\brelocat(?:e|ed|ing)\b",
    ),
    "work_role": (
        r"\bwork\b", r"\bjob\b", r"\brole\b", r"\boccupation\b", r"\bcareer\b",
        r"\bemploy(?:er|ed|ment)?\b", r"\bworks?\s+as\b",
    ),
    "possession": (
        r"\bown(?:s|ed|ing)?\b", r"\bhas\b", r"\bhave\b", r"\bpet\b", r"\bcarry\b",
        r"\buses?\b", r"\bdevice\b",
    ),
    "activity": (
        r"\bhobby\b", r"\bactivity\b", r"\bpracti[cs](?:e|es|ed|ing)\b", r"\bplay(?:s|ed|ing)?\b",
        r"\benjoy(?:s|ed|ing)?\b", r"\bperform(?:s|ed|ing)?\b",
    ),
    "language": (
        r"\blanguage\b", r"\bspeak(?:s|ing)?\b", r"\bfluent\b", r"\blearn(?:s|ed|ing)?\b",
    ),
    "education_institution": (
        r"\buniversity\b", r"\bcollege\b", r"\bschool\b", r"\bcampus\b",
        r"\battend(?:s|ed|ing)?\b", r"\bstudies?\s+at\b",
    ),
    "education_course": (
        r"\bclass\b", r"\bcourse\b", r"\bmodule\b", r"\benroll(?:s|ed|ment)?\b",
        r"\bstud(?:y|ies|ied|ying)\b",
    ),
    "media": (
        r"\bmusic\b", r"\bsong\b", r"\balbum\b", r"\bmovie\b", r"\bfilm\b",
        r"\blisten(?:s|ed|ing)?\b", r"\bwatch(?:es|ed|ing)?\b", r"\bread(?:s|ing)?\b",
    ),
    "device": (
        r"\bcomputer\b", r"\blaptop\b", r"\btablet\b", r"\bphone\b", r"\bdevice\b",
        r"\bmacbook\b", r"\bthinkpad\b", r"\bsurface\b", r"\buses?\b",
    ),
    "goal": (
        r"\bgoal\b", r"\btarget\b", r"\baim\b", r"\bprepar(?:e|es|ed|ing)\b",
        r"\btrain(?:s|ed|ing)?\b", r"\bworking\s+toward\b",
    ),
    "transport": (
        r"\btransport\b", r"\btransit\b", r"\bbus\b", r"\btram\b", r"\bmetro\b",
        r"\broute\b", r"\bcommut(?:e|es|ed|ing)\b", r"\brid(?:e|es|ing)\b", r"\btake(?:s|n)?\b",
    ),
    "relationship": (
        r"\bmarri(?:ed|age)\b", r"\bspouse\b", r"\bpartner\b", r"\brelationship\b",
        r"\bmother\b", r"\bfather\b", r"\bsister\b", r"\bbrother\b", r"\bchild\b",
    ),
    "identity_attribute": (
        r"\bname\b", r"\bcalled\b", r"\bcolor\b", r"\bcolour\b", r"\bsize\b",
        r"\btype\b", r"\bkind\b", r"\bversion\b",
    ),
    "status": (
        r"\bstatus\b", r"\bstate\b", r"\bactive\b", r"\bpaused\b", r"\bclosed\b",
        r"\bapproved\b", r"\bconfirmed\b", r"\bcompleted\b", r"\bready\b",
    ),
    "schedule": (
        r"\bwhen\b", r"\btime\b", r"\bdate\b", r"\bschedule\b", r"\bcheck-?in\b",
        r"\bmeet(?:s|ing)?\b", r"\bappointment\b", r"\bmorning\b", r"\bafternoon\b",
    ),
    "health": (
        r"\bmedication\b", r"\bmedicine\b", r"\ballerg(?:y|ic)\b", r"\bhealth\b",
        r"\bdoctor\b", r"\bcondition\b", r"\btake(?:s|n)?\b",
    ),
    "membership": (
        r"\bclub\b", r"\bmember\b", r"\bmembership\b", r"\bjoin(?:s|ed|ing)?\b",
        r"\bteam\b", r"\bsociety\b",
    ),
}

QUESTION_START = re.compile(r"^\s*(?:what|which|who|where|when|how|does|do|did|is|are|can|could|would|should|will)\b", re.I)
NO_VALUE = re.compile(
    r"(?:\bno\b[^.;!?]{0,50}\b(?:information|answer|value|fact|record|result|detail)\b[^.;!?]{0,40}\b(?:available|known|recorded|confirmed|entered|found|provided)\b"
    r"|\b(?:information|answer|value|fact|record|result|detail|route)\b[^.;!?]{0,30}\b(?:is|are|remains?)\b[^.;!?]{0,15}\b(?:missing|absent|unknown|unavailable|unspecified|unclear)\b"
    r"|\b(?:do|does|did)\s+not\s+know\b|\bnot\s+(?:known|decided|recorded|confirmed)\b|\bcannot\s+(?:determine|verify|confirm)\b)",
    re.I,
)
AGENDA = re.compile(r"\b(?:agenda|action item|to discuss|discussion topic|review topic|pencilled|penciled)\b", re.I)
META = re.compile(
    r"\b(?:prompt|instruction|query|keyword|question wording|discussion about|topic only|mentioned only|"
    r"notes?\s+(?:only\s+)?(?:discuss|describe|mention)|discuss(?:es|ed|ing)?\s+(?:only\s+)?the\s+question|"
    r"question\s+about\s+.+(?:taste|status|value|answer))\b",
    re.I,
)
UNCERTAIN = re.compile(r"\b(?:uncertain|unresolved|tentative|maybe|perhaps|probably|likely|guess|assume|might|possibly|unclear)\b", re.I)
CONFLICT = re.compile(r"\b(?:contradictory|conflicting|records?\s+conflict|values?\s+conflict|cannot\s+be\s+reconciled|cannot\s+reconcile|disagree\s+on)\b", re.I)
DECOY = re.compile(r"\b(?:wrong|incorrect|fake|fabricated|decoy|unrelated)\b[^.;!?]{0,30}\b(?:answer|value|fact|record|memory|claim|detail)\b|\bdo\s+not\s+use\b|\bignore\s+(?:this|that|the)\b", re.I)
HYPOTHETICAL = re.compile(r"\b(?:would|could|may|might|if|hypothetical|considering|plans?\s+to|intends?\s+to|hopes?\s+to|future\s+idea)\b", re.I)
ASSISTANT_SUGGESTION = re.compile(r"\b(?:assistant|system|bot)\b[^.;!?]{0,40}\b(?:suggest(?:ed|s)?|recommend(?:ed|s)?|proposed?)\b", re.I)
ATTRIBUTED_UNVERIFIED = re.compile(r"\b(?:rumou?r|alleged(?:ly)?|unverified\s+claim|someone\s+claimed|quoted\s+claim)\b", re.I)
STALE = re.compile(r"\b(?:formerly|previously|used\s+to|no\s+longer|obsolete|superseded|old\s+value|prior\s+value)\b", re.I)
CURRENT = re.compile(r"\b(?:current|currently|now|latest|these\s+days|still)\b", re.I)
UPDATE = re.compile(r"\b(?:changed|updated|corrected|correction|replaced|relocated|rescheduled|now)\b", re.I)
DIRECT_ASSERTION = re.compile(
    r"\b(?:is|are|was|were|has|have|works?|lives?|resides?|speaks?|studies?|enrolled|listens?|uses?|"
    r"trains?|training|rides?|takes?|owns?|plays?|practices?|performs?|prefers?|chooses?|orders?|"
    r"enjoys?|joined|married|meets?|runs?|carries?|wears?|drives?)\b",
    re.I,
)

GENERIC_STOP = {
    _stem(x) for x in {
        "what","which","who","where","when","how","does","do","did","is","are","was","were","can",
        "could","would","should","will","the","a","an","of","for","to","at","on","in","and","or","with",
        "tell","me","please","current","currently","latest","now","still","this","that","these","those",
        "their","his","her","my","your","user","person","kind","most","often","tend","public",
    }
}
DISCOURSE_STOP = {
    _stem(x) for x in {
        "during","after","before","without","hesitation","comfortably","everyday","conversation","regional",
        "office","home","named","most","saturdays","semester","year","academic","daily","tasks","each",
        "weekday","earlier","recently","really","time","week","busy","filed","since","changing","apartments",
    }
}
RELATION_STEMS = {
    _stem(t)
    for patterns in RELATION_PATTERNS.values()
    for p in patterns
    for t in re.findall(r"[A-Za-z][A-Za-z-]*", re.sub(r"\\[bBsSwWdD\?\:\|\(\)\[\]\{\}\+\*\.\^$]", " ", p))
    if len(t) > 1
}

@dataclass(frozen=True)
class QueryRequirements:
    subject_anchors: tuple[str, ...]
    first_person: bool
    relation_signals: tuple[str, ...]
    predicate_terms: tuple[str, ...]
    object_anchors: tuple[str, ...]
    temporal_scope: str

@dataclass(frozen=True)
class EvidenceClause:
    text: str
    subject_ok: bool
    relation_ok: bool
    value_bearing: bool
    direct_assertion: bool
    temporal_ok: bool
    blocker: str | None
    support_signals: tuple[str, ...]
    score: int
    supported: bool

def _stems(text: str) -> set[str]:
    return {_stem(t) for t in tokens(text)}

def _relation_signals(text: str) -> set[str]:
    return {name for name, patterns in RELATION_PATTERNS.items() if any(re.search(p, text, re.I) for p in patterns)}

def _first_person(text: str) -> bool:
    return bool(set(tokens(text)) & {"i","me","my","mine"})

def _subject_anchors(query: str) -> set[str]:
    raw = re.findall(r"\b[A-Z][A-Za-z0-9_-]*\b", query)
    blocked = {"What","Which","Who","Where","When","How","Does","Do","Did","Is","Are","Can","Could","Would","Should","Will","I"}
    return {x.casefold() for x in raw if x not in blocked}

def _predicate_terms(query: str, anchors: set[str]) -> set[str]:
    out = set()
    anchor_stems = {_stem(a) for a in anchors}
    for t in content_tokens(query):
        s = _stem(t)
        if s in GENERIC_STOP or s in anchor_stems or len(s) <= 1:
            continue
        out.add(s)
    return out

def query_requirements(query: str) -> QueryRequirements:
    anchors = _subject_anchors(query)
    relation_signals = _relation_signals(query)
    temporal = "HISTORICAL" if STALE.search(query) else ("CURRENT" if CURRENT.search(query) or re.search(r"\b(?:does|is|are|has|have)\b", query, re.I) else "UNSPECIFIED")
    # Object anchors are mandatory only for attribute/state queries where the same
    # subject may own several objects (tablet vs phone, bag vs coat, application vs account).
    object_vocab = {"tablet","bag","application","account","passport","car","bike","bicycle","watch","shirt","jacket"}
    object_anchors = {_stem(t) for t in tokens(query) if _stem(t) in object_vocab} if relation_signals & {"identity_attribute","status"} else set()
    return QueryRequirements(
        subject_anchors=tuple(sorted(anchors)),
        first_person=_first_person(query),
        relation_signals=tuple(sorted(relation_signals)),
        predicate_terms=tuple(sorted(_predicate_terms(query, anchors))),
        object_anchors=tuple(sorted(object_anchors)),
        temporal_scope=temporal,
    )

def _segment_clauses(text: str) -> list[str]:
    # Clause-local blockers are the central Candidate-v8 change.
    pieces = re.split(r"(?<=[.!?;])\s+|;\s+|\s+(?:however|but)\s+", text, flags=re.I)
    return [p.strip(" \t,;") for p in pieces if p.strip(" \t,;")]

def _blocker(clause: str, req: QueryRequirements) -> str | None:
    s = clause.strip()
    if not s:
        return "EMPTY"
    if s.endswith("?") and QUESTION_START.search(s):
        return "QUESTION_ONLY"
    if NO_VALUE.search(s):
        return "NO_VALUE"
    if AGENDA.search(s):
        return "AGENDA"
    if META.search(s):
        return "META_ONLY"
    if CONFLICT.search(s):
        return "CONTRADICTION"
    if DECOY.search(s):
        return "NEGATIVE_DECOY"
    if ASSISTANT_SUGGESTION.search(s):
        return "ASSISTANT_SUGGESTION"
    if ATTRIBUTED_UNVERIFIED.search(s):
        return "UNVERIFIED_ATTRIBUTION"
    if UNCERTAIN.search(s) and not re.search(r"\b(?:confirmed|resolved|now known|now confirmed)\b", s, re.I):
        return "UNRESOLVED"
    if HYPOTHETICAL.search(s) and not re.search(r"\b(?:is|are|has|have|currently|now|confirmed)\b", s, re.I):
        return "HYPOTHETICAL_OR_INTENT"
    if req.temporal_scope == "CURRENT" and STALE.search(s) and not (CURRENT.search(s) or UPDATE.search(s)):
        return "STALE_ONLY"
    return None

def _subject_ok(clause: str, req: QueryRequirements) -> bool:
    lowered = clause.casefold()
    if req.subject_anchors and not all(re.search(rf"(?<![a-z0-9_-]){re.escape(anchor)}(?![a-z0-9_-])", lowered) for anchor in req.subject_anchors):
        return False
    if req.first_person and not (_first_person(clause) or bool(re.search(r"\buser\b", lowered))):
        return False
    if req.object_anchors:
        cstems = _stems(clause)
        if not set(req.object_anchors).issubset(cstems):
            return False
    return True

def _temporal_ok(clause: str, req: QueryRequirements) -> bool:
    if req.temporal_scope != "CURRENT":
        return True
    if STALE.search(clause) and not (CURRENT.search(clause) or UPDATE.search(clause)):
        return False
    return True

def _relation_ok(clause: str, req: QueryRequirements) -> tuple[bool, set[str]]:
    qsig = set(req.relation_signals)
    msig = _relation_signals(clause)
    shared = qsig & msig
    if shared:
        return True, shared

    qpred = set(req.predicate_terms)
    cstems = _stems(clause)
    lexical = qpred & cstems
    if lexical:
        return True, {f"lexical:{x}" for x in lexical}

    # Copular/possessive open-attribute fallback: relation word can be absent in evidence
    # if a query-derived property noun is repeated and the clause is directly assertive.
    if DIRECT_ASSERTION.search(clause):
        property_terms = {p for p in qpred if p not in GENERIC_STOP}
        if property_terms & cstems:
            return True, {f"property:{x}" for x in property_terms & cstems}
    return False, set()

def _value_bearing(query: str, clause: str, req: QueryRequirements) -> bool:
    q = {_stem(t) for t in content_tokens(query)} | GENERIC_STOP | DISCOURSE_STOP
    q |= set(req.subject_anchors)
    c = {_stem(t) for t in content_tokens(clause)}
    novel = {t for t in c if t not in q and t not in DISCOURSE_STOP and len(t) > 1}
    # Numeric/version/time values are valid even when short.
    if re.search(r"\b\d+(?:[.:]\d+)*\b", clause):
        return True
    # Do not allow pure discourse/meta novelty to count as a value.
    novelty_block = {_stem(x) for x in {"note","notes","question","discuss","taste","information","available","verified","record","field","topic","planning","item"}}
    return bool(novel - novelty_block)

def certify_clause(query: str, clause: str, req: QueryRequirements | None = None) -> EvidenceClause:
    req = req or query_requirements(query)
    blocker = _blocker(clause, req)
    subject_ok = _subject_ok(clause, req)
    relation_ok, relation_evidence = _relation_ok(clause, req)
    value_bearing = _value_bearing(query, clause, req)
    direct = bool(DIRECT_ASSERTION.search(clause))
    temporal_ok = _temporal_ok(clause, req)

    support_signals: set[str] = set(relation_evidence)
    if subject_ok: support_signals.add("subject")
    if value_bearing: support_signals.add("value")
    if direct: support_signals.add("assertion")
    if temporal_ok: support_signals.add("temporal")

    # Mandatory requirements: subject, relation, value, temporal compatibility, no blocker.
    # Score/quorum is secondary and prevents a single lexical family from deciding support.
    score = int(subject_ok) + int(relation_ok) + int(value_bearing) + int(direct) + int(temporal_ok)
    supported = blocker is None and subject_ok and relation_ok and value_bearing and temporal_ok and score >= 4
    return EvidenceClause(
        text=clause,
        subject_ok=subject_ok,
        relation_ok=relation_ok,
        value_bearing=value_bearing,
        direct_assertion=direct,
        temporal_ok=temporal_ok,
        blocker=blocker,
        support_signals=tuple(sorted(support_signals)),
        score=score,
        supported=supported,
    )

def certify_memory(query: str, memory: dict[str, Any], req: QueryRequirements | None = None) -> dict[str, Any]:
    req = req or query_requirements(query)
    clauses = [certify_clause(query, c, req) for c in _segment_clauses(str(memory["text"]))]
    supported = any(c.supported for c in clauses)
    return {
        "memory_id": str(memory["id"]),
        "supported": supported,
        "clauses": clauses,
    }

def evidence_support_signature(case: dict[str, Any], ranking: list[str] | None = None) -> dict[str, Any]:
    safe_case = {
        "query": str(case["query"]),
        "memories": [
            {
                "id": str(m["id"]),
                "text": str(m["text"]),
                "timestamp": m.get("timestamp"),
                **({"speaker": m.get("speaker")} if "speaker" in m else {}),
            }
            for m in case["memories"]
        ],
    }
    req = query_requirements(safe_case["query"])
    ranking = ranking if ranking is not None else pse_candidate_v2_rank(safe_case, max(5, len(safe_case["memories"])))
    by_id = {m["id"]: m for m in safe_case["memories"]}
    certifications = [certify_memory(safe_case["query"], by_id[mid], req) for mid in ranking if mid in by_id]
    supported_ids = [row["memory_id"] for row in certifications if row["supported"]]
    return {
        "verdict": VERDICT_SUPPORTED if supported_ids else VERDICT_INSUFFICIENT,
        "requirements": req,
        "supporting_memory_ids": supported_ids,
        "certifications": certifications,
    }

def pse_candidate_v8_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Candidate-v8: order-preserving per-memory evidence certification over Candidate-v2.

    Inference intentionally ignores case IDs, labels, relevant IDs, answer strings and benchmark
    provenance. Candidate-v2 remains the sole ranker; Candidate-v8 only removes memories that do
    not satisfy the query's evidence requirements.
    """
    safe_case = {
        "query": str(case["query"]),
        "memories": [
            {"id": str(m["id"]), "text": str(m["text"]), "timestamp": m.get("timestamp")}
            for m in case["memories"]
        ],
    }
    full_ranking = pse_candidate_v2_rank(safe_case, max(k, len(safe_case["memories"])))
    signature = evidence_support_signature(safe_case, full_ranking)
    allowed = set(signature["supporting_memory_ids"])
    return [mid for mid in full_ranking if mid in allowed][:k]
