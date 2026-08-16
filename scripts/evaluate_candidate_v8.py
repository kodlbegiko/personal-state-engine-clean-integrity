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
from personal_state_engine.candidate_v8 import pse_candidate_v8_rank

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def reciprocal_rank(case: dict, ranking: list[str]) -> float:
    relevant = set(case["relevant_memory_ids"])
    return next((1.0 / (i + 1) for i, mid in enumerate(ranking) if mid in relevant), 0.0)

def evaluate(cases: list[dict], ranker) -> dict:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    negatives = [c for c in cases if not c["relevant_memory_ids"]]
    rrs, r1s, r3s, r5s = [], [], [], []
    false_abstentions = 0
    order_violations = 0
    for c in answerable:
        ranking = ranker(c, 5)
        relevant = set(c["relevant_memory_ids"])
        rrs.append(reciprocal_rank(c, ranking))
        r1s.append(float(bool(relevant & set(ranking[:1]))))
        r3s.append(float(bool(relevant & set(ranking[:3]))))
        r5s.append(float(bool(relevant & set(ranking[:5]))))
        false_abstentions += int(not ranking)
        v2 = pse_candidate_v2_rank(c, max(5, len(c["memories"])))
        expected = [mid for mid in v2 if mid in set(ranking)]
        order_violations += int(ranking != expected[: len(ranking)])
    negative_rankings = [ranker(c, 5) for c in negatives]
    false_retrievals = sum(bool(r) for r in negative_rankings)
    return {
        "MRR": sum(rrs) / len(rrs),
        "R@1": sum(r1s) / len(r1s),
        "R@3": sum(r3s) / len(r3s),
        "R@5": sum(r5s) / len(r5s),
        "answerable_recall": 1.0 - false_abstentions / len(answerable),
        "false_abstention": false_abstentions / len(answerable),
        "abstention_accuracy": 1.0 - false_retrievals / len(negatives),
        "false_retrieval": false_retrievals / len(negatives),
        "order_preservation_violations": order_violations,
        "answerable_count": len(answerable),
        "no_evidence_count": len(negatives),
    }

def paired_bootstrap(cases: list[dict], seed: int, iterations: int = 10000, margin: float = -0.03) -> dict:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    deltas = [
        reciprocal_rank(c, pse_candidate_v8_rank(c, 5)) - reciprocal_rank(c, pse_candidate_v2_rank(c, 5))
        for c in answerable
    ]
    rng = random.Random(seed)
    samples = sorted(
        sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas)
        for _ in range(iterations)
    )
    lo = samples[int(0.025 * (len(samples) - 1))]
    hi = samples[int(0.975 * (len(samples) - 1))]
    delta = sum(deltas) / len(deltas)
    return {
        "iterations": iterations,
        "seed": seed,
        "delta": delta,
        "ci95": [lo, hi],
        "margin": margin,
        "noninferiority": lo >= margin,
    }

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--bootstrap-seed", type=int, required=True)
    parser.add_argument("--stage", choices=["development","protected","confirmatory"], required=True)
    args = parser.parse_args()

    payload = json.loads(args.benchmark.read_text())
    cases = payload["cases"]
    v2 = evaluate(cases, pse_candidate_v2_rank)
    v8 = evaluate(cases, pse_candidate_v8_rank)
    boot = paired_bootstrap(cases, args.bootstrap_seed)

    gates = {
        "development": {
            "MRR_min": 0.97, "answerable_recall_min": 0.97,
            "false_retrieval_max": 0.05, "false_abstention_max": 0.03,
        },
        "protected": {
            "MRR_min": 0.95, "answerable_recall_min": 0.95,
            "false_retrieval_max": 0.08, "false_abstention_max": 0.05,
        },
        "confirmatory": {
            "MRR_min": 0.95, "answerable_recall_min": 0.95,
            "false_retrieval_max": 0.08, "false_abstention_max": 0.05,
        },
    }[args.stage]
    checks = {
        "mrr": v8["MRR"] >= gates["MRR_min"],
        "answerable_recall": v8["answerable_recall"] >= gates["answerable_recall_min"],
        "false_retrieval": v8["false_retrieval"] <= gates["false_retrieval_max"],
        "false_abstention": v8["false_abstention"] <= gates["false_abstention_max"],
        "order_preservation": v8["order_preservation_violations"] == 0,
    }
    if args.stage in {"protected","confirmatory"}:
        checks["paired_bootstrap_noninferiority"] = boot["noninferiority"]
    if args.stage == "confirmatory":
        reduction = v2["false_retrieval"] - v8["false_retrieval"]
        checks["absolute_false_retrieval_reduction"] = reduction >= 0.70
    else:
        reduction = v2["false_retrieval"] - v8["false_retrieval"]

    result = {
        "schema_version": "candidate-v8-evaluation-v1",
        "stage": args.stage,
        "benchmark_name": payload["name"],
        "benchmark_sha256": sha(args.benchmark),
        "candidate_v8_source_sha256": sha(ROOT / "src/personal_state_engine/candidate_v8.py"),
        "candidate_v2": v2,
        "candidate_v8": v8,
        "candidate_v8_absolute_false_retrieval_reduction_vs_candidate_v2": reduction,
        "paired_bootstrap": boot,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "monetary_cost_usd": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if result["verdict"] != "PASS":
        raise SystemExit(2)

if __name__ == "__main__":
    main()
