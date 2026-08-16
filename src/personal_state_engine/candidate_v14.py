from __future__ import annotations

"""Candidate-v14: deterministic two-stage retrieve -> verify architecture.

The architecture deliberately decouples high-recall ranking from abstention.
Inference is restricted to production-style runtime fields: query and memories
(id/text/timestamp). No benchmark labels or case metadata are consumed.
"""

import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

VERDICT_SUPPORTED = "SUPPORTED"
VERDICT_INSUFFICIENT = "INSUFFICIENT"

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?")
_NEG_RE = re.compile(r"\b(?:not|never|no longer|isn't|aren't|wasn't|weren't|doesn't|didn't|incorrect|false|contradict(?:s|ed|ory)?)\b", re.I)
_UNCERTAIN_RE = re.compile(r"\b(?:perhaps|maybe|possibly|uncertain|unverified|rumou?r(?:ed)?|might|could|guess|apparently)\b", re.I)
_FIRST_PERSON_RE = re.compile(r"\b(?:i|me|my|mine)\b", re.I)
_META_DISAVOWAL_RE = re.compile(r"\b(?:only\s+copied|only\s+a\s+tag|unrelated|refers?\s+to\s+another|phrase.+appears|mentioned\s+without|discussed\s+without)\b", re.I)
_ASSERTION_RE = re.compile(r"\b(?:is|are|was|were|has|have|uses?|prefers?|likes?|lives?|resides?|speaks?|studies?)\b(?!\s+(?:discussed|mentioned|referenced|copied))", re.I)

_STOP = {
    "a","an","the","is","are","was","were","be","been","being","do","does","did",
    "of","for","to","from","in","on","at","with","about","which","what","when","where",
    "who","whom","whose","how","stated","state","states","tell","show","recorded","record",
    "currently","current","according","memory","memories","please","can","could","would","should",
}

_CONCEPT_GROUPS = [
    {"language","tongue","speaks","speak","linguistic"},
    {"city","town","location","located","lives","live","resides","reside","based"},
    {"color","colour","hue"},
    {"food","meal","cuisine","dish","eat","eats"},
    {"device","computer","laptop","phone","model","machine"},
    {"course","class","subject","study","studies","major"},
    {"meeting","appointment","session","schedule","scheduled","day","time"},
    {"hobby","activity","pastime","enjoys","enjoy","likes","like","prefers","prefer","preference","favorite","favourite"},
    {"work","job","role","occupation","profession"},
    {"pet","animal","dog","cat"},
    {"music","genre","song","artist"},
    {"transport","commute","travel","train","bus","bike","car"},
]
_CONCEPT: dict[str, str] = {}
for i, group in enumerate(_CONCEPT_GROUPS):
    label = f"c{i}"
    for token in group:
        _CONCEPT[token] = label


@dataclass(frozen=True)
class MemoryScoreV14:
    memory_id: str
    lexical: float
    semantic: float
    entity: float
    relation: float
    char_similarity: float
    temporal: float
    proposition_binding: float
    evidence_completeness: float
    contradiction_penalty: float
    uncertainty_penalty: float
    total: float
    direct_support: bool


@dataclass(frozen=True)
class DecisionV14:
    verdict: str
    ranking: tuple[str, ...]
    confidence: float
    abstention_reason: str | None
    top_margin: float
    scores: tuple[MemoryScoreV14, ...]


def _safe_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "query": str(case["query"]),
        "memories": [
            {"id": str(m["id"]), "text": str(m["text"]), "timestamp": m.get("timestamp")}
            for m in case["memories"]
        ],
    }


def _tokens(text: str) -> list[str]:
    return [t.casefold() for t in _TOKEN_RE.findall(text)]


def _stem(token: str) -> str:
    for suffix in ("ing", "edly", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[:-len(suffix)]
    return token


def _content_tokens(text: str) -> list[str]:
    return [_stem(t) for t in _tokens(text) if t not in _STOP and len(t) > 1]


def _concepts(tokens: list[str]) -> set[str]:
    return {_CONCEPT[t] for t in tokens if t in _CONCEPT}


def _char_ngrams(text: str, n: int = 3) -> Counter[str]:
    normalized = " ".join(_tokens(text))
    if len(normalized) < n:
        return Counter({normalized: 1}) if normalized else Counter()
    return Counter(normalized[i:i+n] for i in range(len(normalized)-n+1))


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    if not dot:
        return 0.0
    na = math.sqrt(sum(v*v for v in a.values()))
    nb = math.sqrt(sum(v*v for v in b.values()))
    return dot / (na * nb)


def _entity_terms(query: str) -> set[str]:
    raw = _tokens(query)
    out: set[str] = set()
    for token in raw:
        if token in _STOP or len(token) <= 1 or token.isdigit():
            continue
        stem = _stem(token)
        if _CONCEPT.get(token) is not None or _CONCEPT.get(stem) is not None:
            continue
        out.add(stem)
    out -= {"favorite","favourite","prefer","preference","tell","know","value"}
    return out


def _proposition_binding(query: str, memory_text: str) -> float:
    entities = _entity_terms(query)
    q_concepts = _concepts(_tokens(query))
    raw_mtoks = _tokens(memory_text)
    mtoks = [_stem(t) for t in raw_mtoks]
    if not entities or not q_concepts:
        return 0.0
    entity_positions = [i for i,t in enumerate(mtoks) if t in entities]
    concept_positions = [i for i,t in enumerate(raw_mtoks) if (_CONCEPT.get(t) in q_concepts or _CONCEPT.get(_stem(t)) in q_concepts)]
    if not entity_positions or not concept_positions:
        return 0.0
    distance = min(abs(i-j) for i in entity_positions for j in concept_positions)
    if distance <= 4:
        return 1.0
    if distance <= 8:
        return 0.6
    if distance <= 12:
        return 0.25
    return 0.0


def _timestamp_value(value: Any) -> float:
    if not value:
        return 0.0
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return 0.0


def _score_memory(query: str, memory: dict[str, Any], recency_rank: float) -> MemoryScoreV14:
    q_tokens = _content_tokens(query)
    m_tokens = _content_tokens(str(memory["text"]))
    qset, mset = set(q_tokens), set(m_tokens)
    overlap = qset & mset
    lexical = len(overlap) / max(1, len(qset))
    qc, mc = _concepts(_tokens(query)), _concepts(_tokens(str(memory["text"])))
    semantic = len(qc & mc) / max(1, len(qc)) if qc else 0.0
    entities = _entity_terms(query)
    entity_overlap = entities & mset
    entity = len(entity_overlap) / max(1, len(entities)) if entities else (0.55 if _FIRST_PERSON_RE.search(query) else 0.0)
    relation = 1.0 if qc and (qc & mc) else (0.35 if not qc and lexical >= 0.45 else 0.0)
    binding = _proposition_binding(query, str(memory["text"]))
    char_similarity = _cosine(_char_ngrams(query), _char_ngrams(str(memory["text"])))
    text = str(memory["text"])
    contradicted = bool(_NEG_RE.search(text))
    uncertain = bool(_UNCERTAIN_RE.search(text))
    meta_disavowal = bool(_META_DISAVOWAL_RE.search(text))
    completeness = 1.0 if binding >= 0.60 and _ASSERTION_RE.search(text) and not meta_disavowal else 0.0
    contradiction_penalty = 0.55 if contradicted or meta_disavowal else 0.0
    uncertainty_penalty = 0.30 if uncertain else 0.0
    unbound_penalty = 0.28 if entities and qc and binding == 0.0 else 0.0
    total = (
        0.28 * lexical + 0.20 * semantic + 0.20 * entity + 0.10 * relation
        + 0.14 * binding + 0.12 * completeness + 0.06 * char_similarity
        + 0.04 * recency_rank - contradiction_penalty - uncertainty_penalty - unbound_penalty
    )
    direct_support = (
        not contradicted and not uncertain and (
            (completeness >= 1.0 and binding >= 0.60 and entity >= 0.50 and (relation >= 0.35 or semantic >= 0.5))
            or (completeness >= 1.0 and binding >= 0.60 and lexical >= 0.48 and char_similarity >= 0.40)
            or (completeness >= 1.0 and binding >= 0.60 and semantic >= 0.99 and lexical >= 0.25)
        )
    )
    return MemoryScoreV14(
        memory_id=str(memory["id"]), lexical=lexical, semantic=semantic, entity=entity,
        relation=relation, char_similarity=char_similarity, temporal=recency_rank,
        proposition_binding=binding, evidence_completeness=completeness,
        contradiction_penalty=contradiction_penalty, uncertainty_penalty=uncertainty_penalty,
        total=total, direct_support=direct_support,
    )


def _rank_scores(case: dict[str, Any]) -> list[MemoryScoreV14]:
    safe = _safe_case(case)
    memories = safe["memories"]
    timestamps = [_timestamp_value(m.get("timestamp")) for m in memories]
    ordered_ts = sorted(set(timestamps))
    denom = max(1, len(ordered_ts) - 1)
    scores: list[MemoryScoreV14] = []
    for memory, ts in zip(memories, timestamps):
        recency = ordered_ts.index(ts) / denom if ts in ordered_ts else 0.0
        scores.append(_score_memory(safe["query"], memory, recency))
    scores.sort(key=lambda s: (-s.total, -s.direct_support, s.memory_id))
    return scores


def decide_candidate_v14(case: dict[str, Any], k: int = 5) -> DecisionV14:
    scores = _rank_scores(case)
    if not scores:
        return DecisionV14(VERDICT_INSUFFICIENT, tuple(), 1.0, "NO_MEMORIES", 0.0, tuple())
    top = scores[0]
    second = scores[1] if len(scores) > 1 else None
    margin = top.total - (second.total if second else 0.0)
    structural_support = top.direct_support
    clean = top.contradiction_penalty == 0.0 and top.uncertainty_penalty == 0.0
    competitive_support = clean and top.evidence_completeness >= 1.0 and top.total >= 0.46 and margin >= 0.08 and top.lexical >= 0.30 and top.proposition_binding >= 0.60
    redundant_support = clean and top.evidence_completeness >= 1.0 and top.total >= 0.58 and top.proposition_binding >= 0.60 and (top.semantic >= 0.50 or top.entity >= 0.50)
    verified = clean and (structural_support or competitive_support or redundant_support) and top.total > 0.18
    if not verified:
        confidence = max(0.0, min(1.0, 1.0 - max(0.0, top.total)))
        return DecisionV14(VERDICT_INSUFFICIENT, tuple(), confidence, "EVIDENCE_INSUFFICIENT", margin, tuple(scores))
    eligible = [s for s in scores if s.total > 0.10 and s.contradiction_penalty == 0.0]
    ranking = tuple(s.memory_id for s in eligible[:k])
    if not ranking:
        return DecisionV14(VERDICT_INSUFFICIENT, tuple(), 1.0, "NO_ELIGIBLE_MEMORY", margin, tuple(scores))
    confidence = max(0.0, min(1.0, 0.55 * top.total + 0.45 * max(0.0, margin) + 0.25))
    return DecisionV14(VERDICT_SUPPORTED, ranking, confidence, None, margin, tuple(scores))


def pse_candidate_v14_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    return list(decide_candidate_v14(case, k).ranking)


def pse_candidate_v14_decide(case: dict[str, Any], k: int = 5) -> dict[str, Any]:
    decision = decide_candidate_v14(case, k)
    return {"verdict": decision.verdict, "ranking": list(decision.ranking), "confidence": decision.confidence, "abstention_reason": decision.abstention_reason, "top_margin": decision.top_margin}


def explain_candidate_v14(case: dict[str, Any], k: int = 5) -> dict[str, Any]:
    d = decide_candidate_v14(case, k)
    return {"decision": {"verdict": d.verdict, "ranking": list(d.ranking), "confidence": d.confidence, "abstention_reason": d.abstention_reason, "top_margin": d.top_margin}, "scores": [asdict(s) for s in d.scores]}
