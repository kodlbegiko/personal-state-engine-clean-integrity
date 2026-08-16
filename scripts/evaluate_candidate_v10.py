from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v10 import pse_candidate_v10_rank

BOOTSTRAP_SEEDS = {"development": 2026081525, "protected": 2026081526, "confirmatory": 2026081527, "final": 2026081528}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reciprocal_rank(case: dict, ranking: list[str]) -> float:
    relevant = set(case["relevant_memory_ids"])
    return next((1.0 / (idx + 1) for idx, mid in enumerate(ranking) if mid in relevant), 0.0)


def evaluate(cases: list[dict], ranker) -> dict:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    negatives = [c for c in cases if not c["relevant_memory_ids"]]
    rrs: list[float] = []
    r1: list[float] = []
    r3: list[float] = []
    r5: list[float] = []
    false_abstentions = 0
    relevant_retrieved = 0
    order_violations = 0
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
        v2_full = pse_candidate_v2_rank(case, max(5, len(case["memories"])))
        expected = [mid for mid in v2_full if mid in set(ranking)]
        order_violations += int(ranking != expected[: len(ranking)])
    negative_rankings = [ranker(c, 5) for c in negatives]
    false_retrievals = sum(bool(r) for r in negative_rankings)
    return {
        "MRR": sum(rrs) / len(rrs),
        "R@1": sum(r1) / len(r1),
        "R@3": sum(r3) / len(r3),
        "R@5": sum(r5) / len(r5),
        "answerable_recall": relevant_retrieved / len(answerable),
        "false_abstention": false_abstentions / len(answerable),
        "abstention_accuracy": 1.0 - false_retrievals / len(negatives),
        "false_retrieval": false_retrievals / len(negatives),
        "order_preservation_violations": order_violations,
        "answerable_count": len(answerable),
        "no_evidence_count": len(negatives),
    }


def paired_bootstrap(cases: list[dict], seed: int, iterations: int = 10000, margin: float = -0.03) -> dict:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    deltas = [reciprocal_rank(c, pse_candidate_v10_rank(c, 5)) - reciprocal_rank(c, pse_candidate_v2_rank(c, 5)) for c in answerable]
    rng = random.Random(seed)
    samples = sorted(sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas) for _ in range(iterations))
    lo = samples[int(0.025 * (len(samples) - 1))]
    hi = samples[int(0.975 * (len(samples) - 1))]
    return {
        "iterations": iterations,
        "seed": seed,
        "delta": sum(deltas) / len(deltas),
        "ci95": [lo, hi],
        "margin": margin,
        "noninferiority": lo >= margin,
    }


def gate_checks(stage: str, v2: dict, v10: dict, boot: dict) -> dict:
    reduction = v2["false_retrieval"] - v10["false_retrieval"]
    if stage == "development":
        return {
            "mrr": v10["MRR"] >= 0.98,
            "r1": v10["R@1"] >= 0.98,
            "r3": v10["R@3"] >= 0.99,
            "r5": v10["R@5"] >= 0.99,
            "answerable_recall": v10["answerable_recall"] >= 0.98,
            "false_abstention": v10["false_abstention"] <= 0.02,
            "false_retrieval": v10["false_retrieval"] <= 0.05,
            "abstention_accuracy": v10["abstention_accuracy"] >= 0.95,
            "order_preservation": v10["order_preservation_violations"] == 0,
            "paired_bootstrap_noninferiority": boot["ci95"][0] >= -0.03,
        }
    thresholds = {
        "protected": {"mrr": 0.97, "r1": 0.96, "r3": 0.98, "r5": 0.98, "recall": 0.98, "fa": 0.02},
        "confirmatory": {"mrr": 0.96, "r1": 0.95, "r3": 0.97, "r5": 0.97, "recall": 0.97, "fa": 0.03},
        "final": {"mrr": 0.96, "r1": 0.95, "r3": 0.97, "r5": 0.97, "recall": 0.97, "fa": 0.03},
    }[stage]
    return {
        "mrr": v10["MRR"] >= thresholds["mrr"],
        "r1": v10["R@1"] >= thresholds["r1"],
        "r3": v10["R@3"] >= thresholds["r3"],
        "r5": v10["R@5"] >= thresholds["r5"],
        "answerable_recall": v10["answerable_recall"] >= thresholds["recall"],
        "false_abstention": v10["false_abstention"] <= thresholds["fa"],
        "false_retrieval": v10["false_retrieval"] <= 0.05,
        "abstention_accuracy": v10["abstention_accuracy"] >= 0.95,
        "order_preservation": v10["order_preservation_violations"] == 0,
        "paired_bootstrap_noninferiority": boot["ci95"][0] >= -0.03,
        "absolute_false_retrieval_reduction": reduction >= 0.80,
    }


def evaluate_payload(benchmark: Path, stage: str) -> dict:
    payload = json.loads(benchmark.read_text())
    cases = payload["cases"]
    v2 = evaluate(cases, pse_candidate_v2_rank)
    v10 = evaluate(cases, pse_candidate_v10_rank)
    boot = paired_bootstrap(cases, BOOTSTRAP_SEEDS[stage])
    reduction = v2["false_retrieval"] - v10["false_retrieval"]
    checks = gate_checks(stage, v2, v10, boot)
    return {
        "schema_version": "candidate-v10-evaluation-v1",
        "stage": stage,
        "benchmark_name": payload["name"],
        "benchmark_sha256": sha(benchmark),
        "candidate_v10_source_sha256": sha(ROOT / "src/personal_state_engine/candidate_v10.py"),
        "candidate_v2": v2,
        "candidate_v10": v10,
        "candidate_v10_absolute_false_retrieval_reduction_vs_candidate_v2": reduction,
        "paired_bootstrap": boot,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "monetary_cost_usd": 0,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("benchmark", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--stage", choices=BOOTSTRAP_SEEDS, required=True)
    p.add_argument("--no-fail", action="store_true")
    args = p.parse_args()
    result = evaluate_payload(args.benchmark, args.stage)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"stage": args.stage, "candidate_v2": result["candidate_v2"], "candidate_v10": result["candidate_v10"], "paired_bootstrap": result["paired_bootstrap"], "checks": result["checks"], "verdict": result["verdict"]}, indent=2))
    if result["verdict"] != "PASS" and not args.no_fail:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
