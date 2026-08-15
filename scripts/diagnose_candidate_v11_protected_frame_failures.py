from __future__ import annotations

"""Diagnostic-only taxonomy for the already-executed Candidate-v11 Protected set.

This script MUST NOT call the Candidate-v11 formal runner or evaluator. It reads the
historical benchmark, inspects the frozen semantic-frame functions, and writes only
aggregate diagnostics plus hashed case references. Exact Protected query/memory text,
entity names, values, case IDs, and generator-family labels are deliberately excluded
from the output so the artifact cannot become a development fixture.
"""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from personal_state_engine.candidate_v8 import _subject_anchors
from personal_state_engine.candidate_v10 import (
    _primary_relations,
    certify_memory_v10,
    semantic_requirements_v10,
)
from personal_state_engine.zero_cost_baselines import _stem, tokens

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "experiments/benchmarks/candidate-v11-protected-v1.json"
OUT = ROOT / "results/candidate-v12/candidate-v11-protected-frame-failure-taxonomy.json"

WH = {"what", "which", "who", "where", "when", "how", "does", "do", "did", "is", "are"}
GENERIC_RECORD_NOUNS = {"profile", "record", "entry", "field", "value", "detail", "information"}
PREPOSITIONS = {
    "with", "for", "regarding", "concerning", "about", "respect", "to", "under", "within",
    "according", "from", "in", "on", "at", "of",
}
DISCOURSE_VERBS = {"lookup", "look", "give", "gives", "listed", "list", "show", "shows", "state", "states"}
CURRENT = re.compile(r"\b(?:current|currently|now|today|latest|still|presently)\b", re.I)
HISTORICAL = re.compile(r"\b(?:formerly|previously|historically|earlier|before|prior|old|used\s+to|no\s+longer)\b", re.I)
PLANNED = re.compile(r"\b(?:plan(?:s|ned)?|intend(?:s|ed)?|will|future|upcoming|scheduled\s+to)\b", re.I)
RECURRING = re.compile(r"\b(?:daily|weekly|monthly|every\s+\w+|recurring|usually|regularly)\b", re.I)
COMPLETED = re.compile(r"\b(?:completed|finished|ended|closed|done)\b", re.I)
PASSIVE = re.compile(r"\b(?:is|are|was|were|be|been)\s+(?:recorded|listed|assigned|documented|registered|shown)\b", re.I)
SLOT_VALUE = re.compile(r"\b(?:field|slot|value|entry|record|under|assigned)\b", re.I)
INDIRECT_LOOKUP = re.compile(r"\b(?:give|gives|listed|show|shows|state|states|recorded|assigned)\b", re.I)
POSSESSIVE = re.compile(r"(?:'s|’s)\b")


def _sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _case_ref(case_id: str) -> str:
    return hashlib.sha256(case_id.encode("utf-8")).hexdigest()[:16]


def _caps(text: str) -> list[str]:
    return re.findall(r"\b[A-Z][A-Za-z0-9_-]*\b", text)


def _contains(text: str, anchor: str) -> bool:
    return bool(re.search(rf"(?<![a-z0-9_-]){re.escape(anchor)}(?![a-z0-9_-])", text.casefold()))


def _gold_memory(case: dict[str, Any]) -> dict[str, Any] | None:
    relevant = {str(x) for x in case.get("relevant_memory_ids", [])}
    if not relevant:
        return None
    for memory in case.get("memories", []):
        if str(memory.get("id")) in relevant:
            return memory
    return None


def _semantic_subject_anchors(query: str, gold_text: str) -> set[str]:
    # Diagnostic gold proxy: capitalized query tokens that also occur in the
    # gold-relevant evidence. This avoids copying generator entity metadata and
    # is sufficient to expose mandatory-anchor contamination.
    return {tok.casefold() for tok in _caps(query) if _contains(gold_text, tok.casefold())}


def _positions(query: str, anchors: Iterable[str]) -> dict[str, int]:
    q = query.casefold()
    out: dict[str, int] = {}
    for a in anchors:
        m = re.search(rf"(?<![a-z0-9_-]){re.escape(a)}(?![a-z0-9_-])", q)
        out[a] = m.start() if m else 10**9
    return out


def _subject_categories(query: str, extracted: set[str], semantic: set[str]) -> Counter[str]:
    out: Counter[str] = Counter()
    extra = extracted - semantic
    if not extra:
        return out
    pos = _positions(query, extracted | semantic)
    first_semantic = min((pos[a] for a in semantic), default=10**9)
    colon = query.find(":")
    lowered_tokens = [t.casefold() for t in tokens(query)]

    for anchor in extra:
        stem = _stem(anchor)
        if pos.get(anchor, 10**9) < first_semantic:
            out["discourse-introducer-tokens"] += 1
            out["mixed-with-preceding-discourse-tokens"] += 1
        if colon >= 0 and pos.get(anchor, 10**9) < colon:
            out["section-label-or-lookup-framing"] += 1
        if stem in {_stem(x) for x in GENERIC_RECORD_NOUNS}:
            out["generic-record-nouns"] += 1
        if stem in {_stem(x) for x in WH}:
            out["interrogative-scaffolding"] += 1
        if stem in {_stem(x) for x in PREPOSITIONS}:
            out["prepositional-framing"] += 1
        if stem in {_stem(x) for x in DISCOURSE_VERBS}:
            out["lookup-framing"] += 1

    # Structural prepositional framing: a preposition occurs before the first
    # semantic subject, regardless of the specific historical prefix.
    if semantic and first_semantic < 10**9:
        prefix = query[:first_semantic].casefold()
        if any(re.search(rf"\b{re.escape(p)}\b", prefix) for p in PREPOSITIONS):
            out["prepositional-framing"] += 1
    if any(t in WH for t in lowered_tokens[:3]):
        out["interrogative-scaffolding"] += 1
    return out


def _best_clause(certification: dict[str, Any]) -> Any | None:
    clauses = certification.get("clauses", [])
    if not clauses:
        return None

    def score(c: Any) -> tuple[int, int]:
        positives = sum(
            bool(x)
            for x in (
                c.subject_ok,
                c.relation_ok,
                c.value_type_ok,
                c.value_bearing,
                c.assertion_ok,
                c.temporal_ok,
            )
        )
        return positives, 1 if c.blocker is None else 0

    return max(clauses, key=score)


def _first_blocking_reason(query: str, gold_memory: dict[str, Any]) -> tuple[str, dict[str, bool]]:
    req = semantic_requirements_v10(query)
    cert = certify_memory_v10(query, gold_memory, req)
    clause = _best_clause(cert)
    if clause is None:
        return "clause segmentation", {"no_clause": True}

    clause_stems = {_stem(t) for t in tokens(clause.text)}
    object_missing = bool(req.object_terms) and not bool(set(req.object_terms) & clause_stems)

    flags = {
        "subject_ok": bool(clause.subject_ok),
        "relation_ok": bool(clause.relation_ok),
        "value_type_ok": bool(clause.value_type_ok),
        "value_bearing": bool(clause.value_bearing),
        "assertion_ok": bool(clause.assertion_ok),
        "temporal_ok": bool(clause.temporal_ok),
        "safety_blocker": clause.blocker is not None,
        "object_missing": object_missing,
    }
    if clause.blocker is not None:
        return "safety blocker", flags
    if not clause.subject_ok:
        return "subject", flags
    if object_missing:
        return "object", flags
    if not req.relations:
        return "predicate", flags
    if not clause.relation_ok:
        return "relation", flags
    if not clause.value_type_ok or not clause.assertion_ok:
        return "predicate", flags
    if not clause.value_bearing:
        return "value-bearing", flags
    if not clause.temporal_ok:
        return "temporal", flags
    return "other", flags


def _temporal_label(query: str) -> str:
    if COMPLETED.search(query):
        return "completed"
    if PLANNED.search(query):
        return "planned"
    if RECURRING.search(query):
        return "recurring"
    if HISTORICAL.search(query):
        return "historical"
    if CURRENT.search(query):
        return "current"
    return "unspecified"


def _relation_form_labels(query: str) -> list[str]:
    labels: list[str] = []
    if re.search(r"\b(?:status|state|role|subscription|language|accommodation|volunteering|membership|appointment|routine|goal|tool|channel|team)\b", query, re.I):
        labels.append("nominalized-predicate-or-slot-noun")
    if INDIRECT_LOOKUP.search(query):
        labels.append("indirect-lookup-wording")
    if SLOT_VALUE.search(query):
        labels.append("slot-value-language")
    if re.search(r"\b(?:profile|record|entry)\b", query, re.I):
        labels.append("record-entry-construction")
    if PASSIVE.search(query):
        labels.append("passive-construction")
    if re.match(r"^\s*(?:with|for|regarding|concerning|about|according|in|under)\b", query, re.I):
        labels.append("prepositional-paraphrase")
    return labels


def main() -> None:
    raw = BENCHMARK.read_bytes()
    payload = json.loads(raw)
    cases = payload["cases"]

    answerable = [c for c in cases if c.get("relevant_memory_ids")]
    no_evidence = [c for c in cases if not c.get("relevant_memory_ids")]

    subject_counts = Counter()
    subject_category_counts: Counter[str] = Counter()
    entity_span_counts: Counter[str] = Counter()
    first_blockers: Counter[str] = Counter()
    relation_failure_forms: Counter[str] = Counter()
    relation_query_forms: Counter[str] = Counter()
    object_counts: Counter[str] = Counter()
    temporal_counts: Counter[str] = Counter()
    per_case: list[dict[str, Any]] = []

    for case in answerable:
        query = str(case["query"])
        gold = _gold_memory(case)
        if gold is None:
            first_blockers["other"] += 1
            per_case.append({"case_ref": _case_ref(str(case["id"])), "first_blocking_reason": "other"})
            continue

        gold_text = str(gold["text"])
        raw_anchors = {x.casefold() for x in _subject_anchors(query)}
        req = semantic_requirements_v10(query)
        extracted = set(req.base.subject_anchors)
        semantic = _semantic_subject_anchors(query, gold_text)
        extra = extracted - semantic
        missing = semantic - extracted

        subject_counts["answerable_cases"] += 1
        subject_counts["cases_with_extra_anchor"] += int(bool(extra))
        subject_counts["cases_with_missing_anchor"] += int(bool(missing))
        subject_counts["cases_with_incorrect_mandatory_anchor"] += int(bool(extra))
        subject_counts["raw_anchor_count"] += len(raw_anchors)
        subject_counts["semantic_anchor_count"] += len(semantic)
        subject_counts["extra_anchor_count"] += len(extra)
        subject_counts["missing_anchor_count"] += len(missing)

        subject_category_counts.update(_subject_categories(query, extracted, semantic))
        if missing:
            entity_span_counts["fragmented"] += 1
        if extra:
            entity_span_counts["over-expanded"] += 1
            pos = _positions(query, extra | semantic)
            first_sem = min((pos[x] for x in semantic), default=10**9)
            if any(pos[x] < first_sem for x in extra):
                entity_span_counts["mixed-with-preceding-discourse-tokens"] += 1
            if any(pos[x] > first_sem for x in extra):
                entity_span_counts["mixed-with-following-label-or-scaffold"] += 1
        if len(re.split(r"[.!?;]+", query)) > 2 and extra:
            entity_span_counts["incorrectly-bound-across-clauses"] += 1

        blocker, flags = _first_blocking_reason(query, gold)
        first_blockers[blocker] += 1

        forms = _relation_form_labels(query)
        relation_query_forms.update(forms)
        if blocker in {"relation", "predicate"}:
            relation_failure_forms.update(forms or ["other"])

        if req.object_terms:
            object_counts["cases_with_object_constraints"] += 1
            clause_stems = {_stem(t) for t in tokens(gold_text)}
            overlap = set(req.object_terms) & clause_stems
            if not overlap:
                object_counts["object-overconstraint"] += 1
            elif len(overlap) < len(req.object_terms):
                object_counts["object-partial-match"] += 1
            else:
                object_counts["object-constraint-match"] += 1
            if POSSESSIVE.search(query):
                object_counts["possessive-attachment"] += 1
            if len(req.object_terms) > 1:
                object_counts["multiple-related-objects"] += 1
        else:
            object_counts["cases_without_explicit_object_constraints"] += 1

        temporal_counts[_temporal_label(query)] += 1

        per_case.append(
            {
                "case_ref": _case_ref(str(case["id"])),
                "first_blocking_reason": blocker,
                "subject_extra_anchor": bool(extra),
                "subject_missing_anchor": bool(missing),
                "incorrect_mandatory_anchor": bool(extra),
                "diagnostic_flags": flags,
            }
        )

    denom = max(1, len(answerable))
    result = {
        "schema_version": "candidate-v12-historical-frame-taxonomy-v1",
        "purpose": "diagnostic-only historical Candidate-v11 Protected failure taxonomy",
        "integrity": {
            "candidate_v11_formal_rerun_performed": False,
            "candidate_v11_source_modified": False,
            "historical_formal_execution_counts_modified": False,
            "exact_protected_text_emitted": False,
            "exact_entity_or_value_emitted": False,
            "exact_case_ids_emitted": False,
            "generator_family_labels_used_at_inference": False,
            "development_fixture_generated_from_protected": False,
        },
        "source": {
            "benchmark_path": str(BENCHMARK.relative_to(ROOT)),
            "benchmark_sha256": hashlib.sha256(raw).hexdigest(),
            "case_count": len(cases),
            "answerable_count": len(answerable),
            "no_evidence_count": len(no_evidence),
        },
        "subject_anchor_contamination": {
            "counts": dict(subject_counts),
            "extra_anchor_rate": subject_counts["cases_with_extra_anchor"] / denom,
            "missing_anchor_rate": subject_counts["cases_with_missing_anchor"] / denom,
            "incorrect_mandatory_anchor_rate": subject_counts["cases_with_incorrect_mandatory_anchor"] / denom,
            "category_counts": dict(subject_category_counts),
        },
        "entity_span_failure": dict(entity_span_counts),
        "relation_extraction": {
            "query_form_counts": dict(relation_query_forms),
            "failure_form_counts": dict(relation_failure_forms),
        },
        "object_constraint_extraction": dict(object_counts),
        "temporal_interpretation": dict(temporal_counts),
        "eligibility_collapse_decomposition": {
            "first_blocking_reason_counts": dict(first_blockers),
            "classified_answerable_count": sum(first_blockers.values()),
        },
        "per_case_hashed_diagnostics": per_case,
        "research_interpretation_guardrail": (
            "This artifact may motivate architecture-level hypotheses only. It must not be copied "
            "into Candidate-v12 development tests, templates, token blacklists, or inference rules."
        ),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
