from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(ROOT / "src"))

from personal_state_engine.candidate_v2 import content_tokens, pse_candidate_v2_rank
from personal_state_engine.candidate_v10 import (
    ASSIGNMENT,
    certify_memory_v10,
    pse_candidate_v10_rank,
    semantic_requirements_v10,
)

BENCHMARK = ROOT / "experiments/benchmarks/candidate-v10-final-v1.json"
OUTPUT = ROOT / "results/candidate-v11/candidate-v10-final-rank1-failure-taxonomy.json"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def lexical_overlap(query: str, text: str) -> float:
    q = set(content_tokens(query))
    m = set(content_tokens(text))
    if not q or not m:
        return 0.0
    return len(q & m) / len(q | m)


def temporal_class(text: str) -> str:
    t = text.casefold()
    if re.search(r"\b(?:used to|formerly|previously|historically|before|last year|old)\b", t):
        return "historical"
    if re.search(r"\b(?:plans? to|will|would|might|may|intends? to|scheduled to)\b", t):
        return "planned_or_hypothetical"
    if re.search(r"\b(?:every|daily|weekly|monthly|recurring|usually|regularly)\b", t):
        return "recurring"
    if re.search(r"\b(?:completed|finished|ended|done)\b", t):
        return "completed"
    if re.search(r"\b(?:current|currently|now|today|latest|these days)\b", t):
        return "current_explicit"
    return "current_or_unspecified"


def assertion_strength(text: str) -> str:
    t = text.casefold()
    if re.search(r"\b(?:perhaps|maybe|might|may|possibly|uncertain|unverified|no verified)\b", t):
        return "weak_or_uncertain"
    if ASSIGNMENT.search(text):
        if re.search(r"\b(?:recorded as|listed as|shows|contains|says|states|is|are|has|uses|owns|takes|speaks|works as|serves as)\b", t):
            return "direct_assertion"
        return "assignment_assertion"
    if re.search(r"\b(?:mentioned|discussed|about|regarding|agenda|note)\b", t):
        return "narrative_mention"
    return "weak_implication"


def subject_specificity(query: str, text: str, req: Any) -> str:
    lowered = text.casefold()
    anchors = tuple(req.base.subject_anchors)
    if anchors and all(re.search(rf"(?<![a-z0-9_-]){re.escape(a)}(?![a-z0-9_-])", lowered) for a in anchors):
        return "exact_subject"
    if anchors and any(re.search(rf"(?<![a-z0-9_-]){re.escape(a)}(?![a-z0-9_-])", lowered) for a in anchors):
        return "partial_subject"
    if re.search(r"\b(?:he|she|they|his|her|their)\b", lowered):
        return "pronoun_binding"
    return "implicit_or_related_subject"


def supported_clause_summary(query: str, memory: dict[str, Any], req: Any) -> dict[str, Any]:
    cert = certify_memory_v10(query, memory, req)
    clauses = cert["clauses"]
    if not clauses:
        return {
            "supported": False,
            "completeness": 0,
            "subject_ok": False,
            "relation_ok": False,
            "value_type_ok": False,
            "value_bearing": False,
            "assertion_ok": False,
            "temporal_ok": False,
            "blocker": "no_clause",
            "relation_signals": [],
            "proof": [],
        }
    def score(c: Any) -> tuple[int, int]:
        completeness = sum(bool(x) for x in (
            c.subject_ok, c.relation_ok, c.value_type_ok,
            c.value_bearing, c.assertion_ok, c.temporal_ok,
        ))
        return (int(c.supported), completeness)
    best = max(clauses, key=score)
    completeness = sum(bool(x) for x in (
        best.subject_ok, best.relation_ok, best.value_type_ok,
        best.value_bearing, best.assertion_ok, best.temporal_ok,
    ))
    return {
        "supported": bool(best.supported),
        "completeness": completeness,
        "subject_ok": bool(best.subject_ok),
        "relation_ok": bool(best.relation_ok),
        "value_type_ok": bool(best.value_type_ok),
        "value_bearing": bool(best.value_bearing),
        "assertion_ok": bool(best.assertion_ok),
        "temporal_ok": bool(best.temporal_ok),
        "blocker": best.blocker,
        "relation_signals": list(best.relation_signals),
        "proof": list(best.proof),
    }


def object_alignment(req: Any, text: str) -> dict[str, Any]:
    objects = set(req.object_terms)
    stems = set(content_tokens(text))
    overlap = sorted(objects & stems)
    return {
        "query_object_terms": sorted(objects),
        "matched_object_terms": overlap,
        "object_match": bool(overlap) if objects else None,
    }


def root_causes(rel: dict[str, Any], dist: dict[str, Any]) -> list[str]:
    causes: list[str] = []
    if rel["certification"]["completeness"] > dist["certification"]["completeness"]:
        causes.append("candidate_v2_order_preserved_over_higher_semantic_completeness")
    if dist["lexical_overlap"] > rel["lexical_overlap"] and rel["certification"]["completeness"] >= dist["certification"]["completeness"]:
        causes.append("lexical_overlap_priority_over_semantic_proof_quality")
    if rel["certification"]["relation_ok"] and dist["certification"]["relation_ok"]:
        causes.append("multiple_certification_compatible_relation_candidates")
    if rel["object_alignment"]["object_match"] is True and dist["object_alignment"]["object_match"] is False:
        causes.append("object_constraint_underweighted_after_eligibility")
    direct_order = {"weak_or_uncertain": 0, "weak_implication": 1, "narrative_mention": 2, "assignment_assertion": 3, "direct_assertion": 4}
    if direct_order.get(rel["assertion_strength"], 0) > direct_order.get(dist["assertion_strength"], 0):
        causes.append("assertion_directness_underweighted_after_eligibility")
    if rel["temporal_class"] == "current_explicit" and dist["temporal_class"] != "current_explicit":
        causes.append("temporal_specificity_underweighted_after_eligibility")
    if rel["subject_specificity"] == "exact_subject" and dist["subject_specificity"] != "exact_subject":
        causes.append("subject_specificity_underweighted_after_eligibility")
    if len(dist["certification"]["relation_signals"]) > len(rel["certification"]["relation_signals"]):
        causes.append("broad_relation_signal_ambiguity")
    if not causes:
        causes.append("eligible_tie_left_to_candidate_v2_original_order")
    return causes


def main() -> None:
    payload = json.loads(BENCHMARK.read_text())
    failures: list[dict[str, Any]] = []

    for case in payload["cases"]:
        relevant = set(case["relevant_memory_ids"])
        if not relevant:
            continue
        ranking = pse_candidate_v10_rank(case, 5)
        if not (relevant & set(ranking[:3])) or (relevant & set(ranking[:1])):
            continue

        relevant_rank = next(i + 1 for i, mid in enumerate(ranking) if mid in relevant)
        relevant_id = ranking[relevant_rank - 1]
        distractor_id = ranking[0]
        by_id = {str(m["id"]): m for m in case["memories"]}
        rel_mem = by_id[relevant_id]
        dist_mem = by_id[distractor_id]
        req = semantic_requirements_v10(case["query"])

        rel = {
            "memory_id": relevant_id,
            "memory_text_sha256": sha256_text(str(rel_mem["text"])),
            "lexical_overlap": lexical_overlap(case["query"], str(rel_mem["text"])),
            "subject_specificity": subject_specificity(case["query"], str(rel_mem["text"]), req),
            "object_alignment": object_alignment(req, str(rel_mem["text"])),
            "temporal_class": temporal_class(str(rel_mem["text"])),
            "assertion_strength": assertion_strength(str(rel_mem["text"])),
            "certification": supported_clause_summary(case["query"], rel_mem, req),
        }
        dist = {
            "memory_id": distractor_id,
            "memory_text_sha256": sha256_text(str(dist_mem["text"])),
            "lexical_overlap": lexical_overlap(case["query"], str(dist_mem["text"])),
            "subject_specificity": subject_specificity(case["query"], str(dist_mem["text"]), req),
            "object_alignment": object_alignment(req, str(dist_mem["text"])),
            "temporal_class": temporal_class(str(dist_mem["text"])),
            "assertion_strength": assertion_strength(str(dist_mem["text"])),
            "certification": supported_clause_summary(case["query"], dist_mem, req),
        }

        causes = root_causes(rel, dist)
        failures.append({
            "case_id": case["id"],
            "query_sha256": sha256_text(str(case["query"])),
            "grammar_family": case.get("generator_metadata", {}).get("query_grammar_family"),
            "semantic_domain": case.get("generator_metadata", {}).get("semantic_domain"),
            "candidate_v10_rank": relevant_rank,
            "candidate_v10_top3": ranking[:3],
            "candidate_v2_top3": pse_candidate_v2_rank(case, 3),
            "query_requirements": {
                "subject_anchors": list(req.base.subject_anchors),
                "relations": list(req.relations),
                "object_terms": list(req.object_terms),
                "temporal_scope": req.base.temporal_scope,
            },
            "relevant_evidence": rel,
            "rank1_distractor": dist,
            "root_causes": causes,
            "ranking_score_pathology": "Candidate-v10 certifies eligibility but preserves Candidate-v2 ordering among all eligible candidates; semantic proof quality has no second-stage priority function.",
        })

    root_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()
    family_counter: Counter[str] = Counter()
    rank_counter: Counter[str] = Counter()
    for row in failures:
        root_counter.update(row["root_causes"])
        domain_counter.update([str(row["semantic_domain"])])
        family_counter.update([str(row["grammar_family"])])
        rank_counter.update([str(row["candidate_v10_rank"])])

    result = {
        "schema_version": "candidate-v11-v10-final-rank1-failure-taxonomy-v1",
        "source_benchmark": str(BENCHMARK.relative_to(ROOT)),
        "source_benchmark_sha256": hashlib.sha256(BENCHMARK.read_bytes()).hexdigest(),
        "diagnostic_only": True,
        "raw_query_or_memory_text_emitted": False,
        "answerable_count": payload["answerable_count"],
        "rank1_failure_count": len(failures),
        "expected_from_aggregate_r1": payload["answerable_count"] - 265,
        "all_failures_relevant_in_top3": all(row["candidate_v10_rank"] <= 3 for row in failures),
        "root_cause_counts": dict(root_counter.most_common()),
        "semantic_domain_counts": dict(domain_counter.most_common()),
        "grammar_family_counts": dict(family_counter.most_common()),
        "relevant_rank_counts": dict(rank_counter.most_common()),
        "failures": failures,
        "research_interpretation": {
            "primary_pathology": "eligibility_priority_conflation",
            "mechanism": "Candidate-v10 separates eligible from ineligible evidence but has no semantic quality ordering among eligible Candidate-v2 candidates.",
            "candidate_v11_implication": "Introduce a safety-preserving second-stage priority proof over eligible candidates only; never rescue blocked evidence and never inject candidates outside Candidate-v2 output.",
        },
    }

    if len(failures) != 15:
        raise SystemExit(f"expected 15 rank-1 failures from aggregate R@1, found {len(failures)}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "rank1_failure_count": len(failures),
        "root_cause_counts": result["root_cause_counts"],
        "grammar_family_counts": result["grammar_family_counts"],
        "relevant_rank_counts": result["relevant_rank_counts"],
    }, indent=2))


if __name__ == "__main__":
    main()
