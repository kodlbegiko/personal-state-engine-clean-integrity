from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v10 import pse_candidate_v10_rank
from personal_state_engine.candidate_v11 import (
    candidate_source_invariant_v11,
    pse_candidate_v11_rank,
)

CONFIG = json.loads((ROOT / "config/candidate-v11.json").read_text())
Ranker = Callable[[dict[str, Any], int], list[str]]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reciprocal_rank(case: dict[str, Any], ranking: list[str]) -> float:
    relevant = set(case["relevant_memory_ids"])
    return next(
        (1.0 / (index + 1) for index, memory_id in enumerate(ranking) if memory_id in relevant),
        0.0,
    )


def evaluate_ranker(cases: list[dict[str, Any]], ranker: Ranker, *, candidate_v11: bool = False) -> dict[str, Any]:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    negatives = [case for case in cases if not case["relevant_memory_ids"]]
    rrs: list[float] = []
    r1: list[float] = []
    r3: list[float] = []
    r5: list[float] = []
    relevant_retrieved = 0
    false_abstentions = 0
    source_violations = 0

    for case in answerable:
        ranking = ranker(case, 5)
        relevant = set(case["relevant_memory_ids"])
        hit = bool(relevant & set(ranking))
        relevant_retrieved += int(hit)
        false_abstentions += int(not hit)
        rrs.append(reciprocal_rank(case, ranking))
        r1.append(float(bool(relevant & set(ranking[:1]))))
        r3.append(float(bool(relevant & set(ranking[:3]))))
        r5.append(float(bool(relevant & set(ranking[:5]))))
        if candidate_v11 and not candidate_source_invariant_v11(case, 5)["pass"]:
            source_violations += 1

    negative_rankings = [ranker(case, 5) for case in negatives]
    false_retrievals = sum(bool(ranking) for ranking in negative_rankings)
    if candidate_v11:
        for case in negatives:
            if not candidate_source_invariant_v11(case, 5)["pass"]:
                source_violations += 1

    return {
        "MRR": sum(rrs) / len(rrs) if rrs else 0.0,
        "R@1": sum(r1) / len(r1) if r1 else 0.0,
        "R@3": sum(r3) / len(r3) if r3 else 0.0,
        "R@5": sum(r5) / len(r5) if r5 else 0.0,
        "answerable_recall": relevant_retrieved / len(answerable) if answerable else 0.0,
        "false_abstention": false_abstentions / len(answerable) if answerable else 0.0,
        "false_retrieval": false_retrievals / len(negatives) if negatives else 0.0,
        "abstention_accuracy": 1.0 - (false_retrievals / len(negatives) if negatives else 0.0),
        "answerable_count": len(answerable),
        "no_evidence_count": len(negatives),
        "candidate_source_invariant_violations": source_violations if candidate_v11 else None,
    }


def eligible_rank1_accuracy(cases: list[dict[str, Any]]) -> dict[str, Any]:
    eligible_answerable = 0
    rank1_hits = 0
    for case in cases:
        relevant = set(case["relevant_memory_ids"])
        if not relevant:
            continue
        # Candidate-v10 uses exactly the Layer-1 eligibility surface. Asking for
        # the full memory count prevents top-k truncation from redefining eligibility.
        eligible_ids = set(pse_candidate_v10_rank(case, max(5, len(case["memories"]))))
        if not (relevant & eligible_ids):
            continue
        eligible_answerable += 1
        rank1_hits += int(bool(relevant & set(pse_candidate_v11_rank(case, 1))))
    return {
        "eligible_answerable_count": eligible_answerable,
        "rank1_hits": rank1_hits,
        "accuracy": rank1_hits / eligible_answerable if eligible_answerable else 0.0,
    }


def paired_bootstrap_r1(cases: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [case for case in cases if case["relevant_memory_ids"]]
    deltas: list[float] = []
    for case in answerable:
        relevant = set(case["relevant_memory_ids"])
        v10_hit = float(bool(relevant & set(pse_candidate_v10_rank(case, 1))))
        v11_hit = float(bool(relevant & set(pse_candidate_v11_rank(case, 1))))
        deltas.append(v11_hit - v10_hit)

    seed = int(CONFIG["bootstrap"]["seed"])
    iterations = int(CONFIG["bootstrap"]["iterations"])
    margin = float(CONFIG["bootstrap"]["r1_noninferiority_margin"])
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(iterations):
        sample = sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas)
        samples.append(sample)
    samples.sort()
    lo = samples[int(0.025 * (len(samples) - 1))]
    hi = samples[int(0.975 * (len(samples) - 1))]
    delta = sum(deltas) / len(deltas)
    return {
        "metric": "paired_R@1_candidate_v11_minus_candidate_v10",
        "iterations": iterations,
        "seed": seed,
        "delta": delta,
        "ci95": [lo, hi],
        "noninferiority_margin": margin,
        "noninferiority": lo >= margin,
        "strict_improvement_observed": delta > 0.0,
    }


def metadata_firewall_check(cases: list[dict[str, Any]]) -> dict[str, Any]:
    checked = 0
    violations = 0
    for case in cases[: min(40, len(cases))]:
        baseline = pse_candidate_v11_rank(case, 5)
        mutated = deepcopy(case)
        mutated["id"] = "MUTATED-HIDDEN-ID"
        mutated["relevant_memory_ids"] = ["INJECTED-GOLD-ID"]
        mutated["answer"] = "INJECTED-ANSWER"
        mutated["labels"] = {"gold": "INJECTED-GOLD-ID"}
        mutated["designation"] = "HIDDEN-STAGE"
        mutated["generator_metadata"] = {
            "query_grammar_family": "HIDDEN-FAMILY",
            "semantic_domain": "HIDDEN-DOMAIN",
            "template_provenance": "HIDDEN-TEMPLATE",
            "stage": "HIDDEN-STAGE",
            "relevant_ids": ["INJECTED-GOLD-ID"],
        }
        changed = pse_candidate_v11_rank(mutated, 5)
        checked += 1
        violations += int(changed != baseline)
    return {"checked": checked, "violations": violations, "pass": violations == 0}


def determinism_check(cases: list[dict[str, Any]]) -> dict[str, Any]:
    if not cases:
        return {"repetitions": 100, "violations": 0, "pass": True}
    probe = cases[0]
    expected = pse_candidate_v11_rank(probe, 5)
    violations = 0
    for _ in range(100):
        violations += int(pse_candidate_v11_rank(probe, 5) != expected)
    return {"repetitions": 100, "violations": violations, "pass": violations == 0}


def gate_checks(stage: str, v11: dict[str, Any], eligible: dict[str, Any], bootstrap: dict[str, Any], firewall: dict[str, Any], determinism: dict[str, Any]) -> dict[str, bool]:
    thresholds = CONFIG["thresholds"][stage]
    checks = {
        "mrr": v11["MRR"] >= thresholds["MRR"],
        "r1": v11["R@1"] >= thresholds["R@1"],
        "r3": v11["R@3"] >= thresholds["R@3"],
        "r5": v11["R@5"] >= thresholds["R@5"],
        "answerable_recall": v11["answerable_recall"] >= thresholds["answerable_recall"],
        "false_abstention": v11["false_abstention"] <= thresholds["false_abstention_max"],
        "false_retrieval": v11["false_retrieval"] <= thresholds["false_retrieval_max"],
        "abstention_accuracy": v11["abstention_accuracy"] >= thresholds["abstention_accuracy"],
        "candidate_source_invariant": v11["candidate_source_invariant_violations"] == 0,
        "metadata_firewall": firewall["pass"],
        "determinism": determinism["pass"],
        "paired_r1_noninferiority_vs_v10": bootstrap["noninferiority"],
    }
    if stage == "development":
        checks["eligible_rank1_accuracy"] = eligible["accuracy"] >= thresholds["eligible_rank1_accuracy"]
    return checks


def evaluate_payload(benchmark: Path, stage: str) -> dict[str, Any]:
    payload = json.loads(benchmark.read_text())
    if payload.get("stage") != stage:
        raise ValueError(f"benchmark stage mismatch: expected {stage}, found {payload.get('stage')}")
    cases = payload["cases"]
    v2 = evaluate_ranker(cases, pse_candidate_v2_rank)
    v10 = evaluate_ranker(cases, pse_candidate_v10_rank)
    v11 = evaluate_ranker(cases, pse_candidate_v11_rank, candidate_v11=True)
    eligible = eligible_rank1_accuracy(cases)
    bootstrap = paired_bootstrap_r1(cases)
    firewall = metadata_firewall_check(cases)
    determinism = determinism_check(cases)
    checks = gate_checks(stage, v11, eligible, bootstrap, firewall, determinism)
    return {
        "schema_version": "candidate-v11-evaluation-v1",
        "stage": stage,
        "benchmark_name": payload["name"],
        "benchmark_sha256": sha256(benchmark),
        "candidate_v2_source_sha256": sha256(ROOT / "src/personal_state_engine/candidate_v2.py"),
        "candidate_v10_source_sha256": sha256(ROOT / "src/personal_state_engine/candidate_v10.py"),
        "candidate_v11_source_sha256": sha256(ROOT / "src/personal_state_engine/candidate_v11.py"),
        "config_sha256": sha256(ROOT / "config/candidate-v11.json"),
        "candidate_v2": v2,
        "candidate_v10": v10,
        "candidate_v11": v11,
        "eligible_rank1": eligible,
        "paired_bootstrap_r1": bootstrap,
        "metadata_firewall": firewall,
        "determinism": determinism,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "monetary_cost_usd": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--stage", choices=tuple(CONFIG["benchmark"]), required=True)
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args()
    result = evaluate_payload(args.benchmark, args.stage)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "stage": args.stage,
        "candidate_v2": result["candidate_v2"],
        "candidate_v10": result["candidate_v10"],
        "candidate_v11": result["candidate_v11"],
        "eligible_rank1": result["eligible_rank1"],
        "paired_bootstrap_r1": result["paired_bootstrap_r1"],
        "checks": result["checks"],
        "verdict": result["verdict"],
    }, indent=2))
    if result["verdict"] != "PASS" and not args.no_fail:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
