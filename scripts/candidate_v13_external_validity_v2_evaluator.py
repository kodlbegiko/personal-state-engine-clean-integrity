from __future__ import annotations

"""Candidate-agnostic evaluator for Candidate-v13 External Validity v2.

The module intentionally does not import Candidate-v13. The authorized formal
runner supplies a ranker callback only after one-shot ledger consumption and
freeze verification.
"""

import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

Ranker = Callable[[dict[str, Any], int], list[str]]


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    if total <= 0:
        return None
    p = successes / total
    den = 1 + z * z / total
    center = (p + z * z / (2 * total)) / den
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / den
    return [max(0.0, center - half), min(1.0, center + half)]


def bootstrap_mean(values: list[float], iterations: int, seed: int) -> list[float] | None:
    if not values:
        return None
    rng = random.Random(seed)
    n = len(values)
    samples = []
    for _ in range(iterations):
        samples.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    samples.sort()
    lo = samples[int(0.025 * iterations)]
    hi = samples[min(iterations - 1, int(0.975 * iterations))]
    return [lo, hi]


def safe_div(a: int | float, b: int | float) -> float:
    return float(a) / float(b) if b else 0.0


def score_subset(records: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [r for r in records if r["answerable"]]
    no_evidence = [r for r in records if not r["answerable"]]
    reciprocal = [float(r["reciprocal_rank"]) for r in answerable]
    hits = {k: sum(bool(r[f"hit_at_{k}"]) for r in answerable) for k in (1, 3, 5)}
    false_abst = sum(bool(r["abstained"]) for r in answerable)
    false_ret = sum(bool(r["false_retrieval"]) for r in records)
    abstain_ok = sum(bool(r["abstained"]) for r in no_evidence)
    eligible = [r for r in answerable if not r["abstained"]]
    eligible_r1 = sum(bool(r["rank1_relevant"]) for r in eligible)
    return {
        "case_count": len(records),
        "answerable_count": len(answerable),
        "no_evidence_count": len(no_evidence),
        "mrr": safe_div(sum(reciprocal), len(answerable)),
        "r_at_1": safe_div(hits[1], len(answerable)),
        "r_at_3": safe_div(hits[3], len(answerable)),
        "r_at_5": safe_div(hits[5], len(answerable)),
        "answerable_recall": safe_div(hits[5], len(answerable)),
        "false_abstention_rate": safe_div(false_abst, len(answerable)),
        "false_retrieval_rate": safe_div(false_ret, len(records)),
        "abstention_accuracy": safe_div(abstain_ok, len(no_evidence)),
        "eligible_rank1_accuracy": safe_div(eligible_r1, len(eligible)),
        "counts": {
            "r1_hits": hits[1], "r3_hits": hits[3], "r5_hits": hits[5],
            "false_abstentions": false_abst, "false_retrievals": false_ret,
            "correct_abstentions": abstain_ok, "eligible_rank1_hits": eligible_r1,
            "eligible_answerable": len(eligible),
        },
    }


def intervals(metrics: dict[str, Any], reciprocal: list[float], iterations: int, seed: int) -> dict[str, Any]:
    c = metrics["counts"]
    a = metrics["answerable_count"]
    n = metrics["no_evidence_count"]
    total = metrics["case_count"]
    return {
        "mrr": bootstrap_mean(reciprocal, iterations, seed),
        "r_at_1": wilson(c["r1_hits"], a),
        "r_at_3": wilson(c["r3_hits"], a),
        "r_at_5": wilson(c["r5_hits"], a),
        "answerable_recall": wilson(c["r5_hits"], a),
        "false_abstention_rate": wilson(c["false_abstentions"], a),
        "false_retrieval_rate": wilson(c["false_retrievals"], total),
        "abstention_accuracy": wilson(c["correct_abstentions"], n),
        "eligible_rank1_accuracy": wilson(c["eligible_rank1_hits"], c["eligible_answerable"]),
    }


def evaluate(stage: str, cases: list[dict[str, Any]], ranker: Ranker, policy: dict[str, Any]) -> dict[str, Any]:
    cfg = policy[stage]
    common = policy["common_integrity_gates"]
    uncertainty = policy["uncertainty"]
    expected_count = int(cfg["case_count"])
    records: list[dict[str, Any]] = []
    integrity = Counter()
    invalid = Counter()
    source_distribution = Counter()

    for case in cases:
        source_distribution[str(case["source_dataset"])] += 1
        runtime = {"query": case["query"], "memories": case["memories"]}
        memory_ids = {str(m["id"]) for m in runtime["memories"]}
        relevant = set(str(x) for x in case.get("relevant_memory_ids", []))
        answerable = bool(case["answerable"])

        if answerable and (not relevant or not relevant.issubset(memory_ids)):
            invalid["answerable_gold_missing_from_runtime"] += 1
            continue
        if not answerable and relevant:
            invalid["no_evidence_has_runtime_gold"] += 1
            continue
        if len(runtime["memories"]) < 5 or len(memory_ids) != len(runtime["memories"]):
            invalid["runtime_memory_contract"] += 1
            continue

        ranked = [str(x) for x in ranker(runtime, 5)]
        ranked_again = [str(x) for x in ranker(runtime, 5)]
        if ranked != ranked_again:
            integrity["determinism_violations"] += 1
        if any(x not in memory_ids for x in ranked):
            integrity["candidate_source_violations"] += 1

        # Metadata firewall: Candidate receives only the freshly projected runtime
        # object; evaluator-only metadata is never present in either invocation.
        integrity["metadata_firewall_invocations"] += 2

        hit_rank = next((i for i, mid in enumerate(ranked, 1) if mid in relevant), None) if answerable else None
        false_retrieval = (bool(ranked) if not answerable else any(mid not in relevant for mid in ranked))
        records.append({
            "answerable": answerable,
            "abstained": not ranked,
            "false_retrieval": false_retrieval,
            "rank1_relevant": bool(ranked and ranked[0] in relevant),
            "reciprocal_rank": (1.0 / hit_rank if hit_rank else 0.0),
            "hit_at_1": bool(hit_rank and hit_rank <= 1),
            "hit_at_3": bool(hit_rank and hit_rank <= 3),
            "hit_at_5": bool(hit_rank and hit_rank <= 5),
            "domain": str(case["domain"]),
            "family": str(case["primary_family"]),
            "source": str(case["source_dataset"]),
        })

    overall = score_subset(records)
    reciprocal = [r["reciprocal_rank"] for r in records if r["answerable"]]
    overall_intervals = intervals(
        overall, reciprocal,
        int(uncertainty["bootstrap_iterations"]), int(uncertainty["bootstrap_seed"]),
    )

    domains = {}
    for domain in sorted({r["domain"] for r in records}):
        subset = [r for r in records if r["domain"] == domain]
        domains[domain] = score_subset(subset)
    families = {}
    for family in sorted({r["family"] for r in records}):
        subset = [r for r in records if r["family"] == family]
        m = score_subset(subset)
        # Family accuracy is outcome correctness: answerable rank-1 relevant or no-evidence abstention.
        correct = sum((r["rank1_relevant"] if r["answerable"] else r["abstained"]) for r in subset)
        m["accuracy"] = safe_div(correct, len(subset))
        families[family] = m

    retrieve_count = sum(not r["abstained"] for r in records)
    abstain_count = len(records) - retrieve_count
    retrieve_rate = safe_div(retrieve_count, len(records))
    abstain_rate = safe_div(abstain_count, len(records))
    catastrophic = [
        f for f, m in families.items()
        if m["case_count"] and m["accuracy"] < float(policy["anti_collapse"]["catastrophic_family_accuracy"])
    ]
    anti = {
        "retrieve_count": retrieve_count,
        "abstain_count": abstain_count,
        "retrieve_rate": retrieve_rate,
        "abstain_rate": abstain_rate,
        "near_universal_retrieval": retrieve_rate > float(policy["anti_collapse"]["near_universal_retrieval_rate"]),
        "near_universal_abstention": abstain_rate > float(policy["anti_collapse"]["near_universal_abstention_rate"]),
        "catastrophic_families": catastrophic,
    }
    anti["pass"] = not anti["near_universal_retrieval"] and not anti["near_universal_abstention"] and not catastrophic

    materialized_count = len(cases)
    invalid_count = sum(invalid.values())
    invalid_rate = safe_div(invalid_count, materialized_count)
    failures: list[str] = []
    if materialized_count != expected_count:
        failures.append(f"case_count:{materialized_count}!={expected_count}")
    if invalid_rate > float(common["invalid_rate_max"]):
        failures.append("invalid_rate")

    agg = cfg["aggregate"]
    for metric, suffix in [
        ("mrr","min"),("r_at_1","min"),("r_at_3","min"),("r_at_5","min"),
        ("answerable_recall","min"),("abstention_accuracy","min"),("eligible_rank1_accuracy","min")
    ]:
        threshold = float(agg[f"{metric}_{suffix}"])
        if overall[metric] < threshold:
            failures.append(f"{metric}<{threshold}")
    for metric in ("false_abstention_rate", "false_retrieval_rate"):
        threshold = float(agg[f"{metric}_max"])
        if overall[metric] > threshold:
            failures.append(f"{metric}>{threshold}")

    for family, floor in cfg["family_accuracy_floors"].items():
        if family not in families:
            failures.append(f"{family}:missing")
        elif families[family]["accuracy"] < float(floor):
            failures.append(f"{family}:accuracy<{floor}")

    df = cfg["domain_floors"]
    for domain in [f"D{i}" for i in range(1, 9)]:
        if domain not in domains:
            failures.append(f"{domain}:missing")
            continue
        m = domains[domain]
        if m["case_count"] != int(df["case_count"]): failures.append(f"{domain}:case_count")
        if m["r_at_1"] < float(df["r_at_1_min"]): failures.append(f"{domain}:r_at_1")
        if m["answerable_recall"] < float(df["answerable_recall_min"]): failures.append(f"{domain}:recall")
        if m["false_retrieval_rate"] > float(df["false_retrieval_rate_max"]): failures.append(f"{domain}:false_retrieval")
        if m["abstention_accuracy"] < float(df["abstention_accuracy_min"]): failures.append(f"{domain}:abstention")

    if integrity["determinism_violations"]: failures.append("determinism")
    if integrity["candidate_source_violations"]: failures.append("candidate_source_invariant")
    if not anti["pass"]: failures.append("anti_collapse")

    integrity_status = {
        "metadata_firewall": "PASS",
        "candidate_source_invariant": "PASS" if integrity["candidate_source_violations"] == 0 else "FAIL",
        "determinism": "PASS" if integrity["determinism_violations"] == 0 else "FAIL",
        "anti_collapse": "PASS" if anti["pass"] else "FAIL",
        "candidate_source_violations": integrity["candidate_source_violations"],
        "determinism_violations": integrity["determinism_violations"],
    }
    invalid_integrity = integrity_status["candidate_source_invariant"] != "PASS" or integrity_status["determinism"] != "PASS"
    status = "INVALID" if invalid_integrity else ("PASS" if not failures else "FAIL")

    return {
        "schema_version": "candidate-v13-external-validity-v2-stage-summary-v1",
        "stage": stage,
        "status": status,
        "overall_metrics": {k: v for k, v in overall.items() if k != "counts"},
        "rank_metrics": {
            "mrr": overall["mrr"], "r_at_1": overall["r_at_1"],
            "r_at_3": overall["r_at_3"], "r_at_5": overall["r_at_5"]
        },
        "confidence_intervals_95": overall_intervals,
        "domain_metrics": domains,
        "family_metrics": families,
        "coverage": safe_div(len(records), materialized_count),
        "invalid_rate": invalid_rate,
        "invalid_counts": dict(sorted(invalid.items())),
        "error_counts": {
            "false_abstentions": overall["counts"]["false_abstentions"],
            "false_retrievals": overall["counts"]["false_retrievals"],
        },
        "dataset_source_distribution": dict(sorted(source_distribution.items())),
        "anti_collapse": anti,
        "integrity": integrity_status,
        "acceptance_failures": failures,
    }
