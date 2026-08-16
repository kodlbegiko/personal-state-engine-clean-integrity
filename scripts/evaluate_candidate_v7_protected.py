from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v7 import pse_candidate_v7_rank

BENCH = ROOT / "experiments" / "benchmarks" / "candidate-v7-protected-validation-v1.json"
LOCK = ROOT / "experiments" / "benchmarks" / "candidate-v7-protected-validation-lock-v1.json"
RDIR = ROOT / "results" / "candidate-v7"
SOURCE = ROOT / "src" / "personal_state_engine" / "candidate_v7.py"
CONFIG = ROOT / "experiments" / "configs" / "candidate-v7-v1.json"
PROTOCOL = ROOT / "experiments" / "protocols" / "candidate-v7-protected-validation-v1.json"
SEED = 20260814
ITERATIONS = 10000
EXPECTED_SOURCE = "c9bc8a5cf70cca5e2f97240bb427d1ad1cd8d60d14af922a4e634ec9c870bdae"
EXPECTED_CONFIG = "7acc9a99938efa0d361791191960a60cf8a88b6a2ec022d60f54da3df29b7e62"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rr(case: dict, ranking: list[str]) -> float:
    relevant = set(case["relevant_memory_ids"])
    return next((1.0 / (i + 1) for i, mid in enumerate(ranking) if mid in relevant), 0.0)


def rank_safely(case: dict, ranker) -> list[str]:
    # The ranker receives the whole evaluator case object, but Candidate-v7
    # internally sanitizes to query + memory id/text/timestamp only. Leakage
    # tests in the frozen development suite verify the forbidden fields do not
    # affect inference.
    return ranker(case, 5)


def evaluate(cases: list[dict], ranker) -> tuple[dict, list[dict]]:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    negatives = [c for c in cases if not c["relevant_memory_ids"]]
    rows = []
    rrs, r1s, r3s, r5s = [], [], [], []
    false_abstention = 0
    for case in answerable:
        ranking = rank_safely(case, ranker)
        value = rr(case, ranking)
        relevant = set(case["relevant_memory_ids"])
        rrs.append(value)
        r1s.append(float(bool(relevant & set(ranking[:1]))))
        r3s.append(float(bool(relevant & set(ranking[:3]))))
        r5s.append(float(bool(relevant & set(ranking[:5]))))
        false_abstention += int(not ranking)
        rows.append({"id": case["id"], "answerable": True, "ranking": ranking, "rr": value})
    false_retrieval_count = 0
    for case in negatives:
        ranking = rank_safely(case, ranker)
        false_retrieval_count += int(bool(ranking))
        rows.append({"id": case["id"], "answerable": False, "ranking": ranking, "false_retrieval": bool(ranking)})
    metrics = {
        "MRR": sum(rrs) / len(rrs),
        "R@1": sum(r1s) / len(r1s),
        "R@3": sum(r3s) / len(r3s),
        "R@5": sum(r5s) / len(r5s),
        "answerable_recall": 1.0 - false_abstention / len(answerable),
        "false_abstention": false_abstention / len(answerable),
        "abstention_accuracy": 1.0 - false_retrieval_count / len(negatives),
        "false_retrieval": false_retrieval_count / len(negatives),
    }
    return metrics, rows


def bootstrap(cases: list[dict]) -> dict:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    deltas = []
    for case in answerable:
        deltas.append(rr(case, rank_safely(case, pse_candidate_v7_rank)) - rr(case, rank_safely(case, pse_candidate_v2_rank)))
    rng = random.Random(SEED)
    samples = []
    for _ in range(ITERATIONS):
        samples.append(sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas))
    samples.sort()
    lo = samples[int(0.025 * (len(samples) - 1))]
    hi = samples[int(0.975 * (len(samples) - 1))]
    return {
        "metric": "answerable reciprocal-rank delta Candidate-v7 minus Candidate-v2",
        "iterations": ITERATIONS,
        "seed": SEED,
        "delta": sum(deltas) / len(deltas),
        "ci95": [lo, hi],
        "non_inferiority_margin": 0.03,
        "pass": lo >= -0.03,
    }


def main() -> None:
    summary_path = RDIR / "protected-validation-summary-v1.json"
    stats_path = RDIR / "protected-validation-statistics-v1.json"
    if summary_path.exists() or stats_path.exists():
        raise SystemExit("PROTECTED EXECUTION REFUSED: result already exists; formal execution is one-shot")

    if sha(SOURCE) != EXPECTED_SOURCE or sha(CONFIG) != EXPECTED_CONFIG:
        raise SystemExit("PROTECTED EXECUTION REFUSED: frozen Candidate-v7 identity changed")

    lock = json.loads(LOCK.read_text())
    protocol = json.loads(PROTOCOL.read_text())
    if lock.get("status") != "FROZEN_BEFORE_FORMAL_EXECUTION" or lock.get("formal_execution_count_before_run") != 0:
        raise SystemExit("PROTECTED EXECUTION REFUSED: benchmark lock invalid")
    if sha(BENCH) != lock["dataset_sha256"]:
        raise SystemExit("PROTECTED EXECUTION REFUSED: benchmark hash mismatch")
    if sha(Path(__file__)) != lock["evaluator_sha256"]:
        raise SystemExit("PROTECTED EXECUTION REFUSED: evaluator hash mismatch")
    generator_path = ROOT / lock["generator_path"]
    if sha(generator_path) != lock["generator_sha256"]:
        raise SystemExit("PROTECTED EXECUTION REFUSED: generator hash mismatch")

    payload = json.loads(BENCH.read_text())
    cases = payload["cases"]
    if len(cases) != 120 or sum(bool(c["relevant_memory_ids"]) for c in cases) != 70:
        raise SystemExit("PROTECTED EXECUTION REFUSED: case counts mismatch")

    v2, v2_rows = evaluate(cases, pse_candidate_v2_rank)
    v7, v7_rows = evaluate(cases, pse_candidate_v7_rank)
    boot = bootstrap(cases)
    deficits = {key: v2[key] - v7[key] for key in ["MRR", "R@1", "R@3", "R@5"]}
    false_reduction = v2["false_retrieval"] - v7["false_retrieval"]
    thresholds = protocol["thresholds"]
    guardrails = {
        "mrr_deficit": deficits["MRR"] <= thresholds["mrr_deficit_vs_candidate_v2_max"],
        "r1_deficit": deficits["R@1"] <= thresholds["r1_deficit_vs_candidate_v2_max"],
        "r3_deficit": deficits["R@3"] <= thresholds["r3_deficit_vs_candidate_v2_max"],
        "r5_deficit": deficits["R@5"] <= thresholds["r5_deficit_vs_candidate_v2_max"],
        "answerable_recall": v7["answerable_recall"] >= thresholds["answerable_recall_min"],
        "false_abstention": v7["false_abstention"] <= thresholds["false_abstention_max"],
        "abstention_accuracy": v7["abstention_accuracy"] >= thresholds["abstention_accuracy_min"],
        "false_retrieval": v7["false_retrieval"] <= thresholds["false_retrieval_max"],
        "absolute_false_retrieval_reduction": false_reduction >= thresholds["absolute_false_retrieval_reduction_vs_candidate_v2_min"],
        "natural_language_support": v7["answerable_recall"] >= thresholds["natural_language_support_min"],
        "paired_bootstrap_non_inferiority": boot["pass"],
    }
    verdict = "PASS" if all(guardrails.values()) else "FAIL"

    stats = {
        "schema_version": "candidate-v7-protected-validation-statistics-v1",
        "formal_execution_count": 1,
        "candidate_source_sha256": sha(SOURCE),
        "config_sha256": sha(CONFIG),
        "dataset_sha256": sha(BENCH),
        "generator_sha256": lock["generator_sha256"],
        "evaluator_sha256": lock["evaluator_sha256"],
        "candidate_v2": v2,
        "candidate_v7": v7,
        "deficits_vs_candidate_v2": deficits,
        "absolute_false_retrieval_reduction_vs_candidate_v2": false_reduction,
        "paired_bootstrap": boot,
        "guardrails": guardrails,
        "verdict": verdict,
    }
    summary = {
        "schema_version": "candidate-v7-protected-validation-summary-v1",
        "formal_execution_count": 1,
        "rerun": False,
        "post_result_editing": False,
        "benchmark": {
            "name": payload["name"],
            "case_count": payload["case_count"],
            "answerable_count": payload["answerable_count"],
            "no_evidence_count": payload["no_evidence_count"],
            "dataset_sha256": sha(BENCH),
            "status_before_execution": lock["status"],
        },
        "candidate_v7": v7,
        "candidate_v2": v2,
        "paired_bootstrap": boot,
        "guardrails": guardrails,
        "verdict": verdict,
        "terminal_state_if_fail": "CANDIDATE_V7_PROTECTED_VALIDATION_FAIL",
        "next_legal_action_if_pass": "PREREGISTER_FRESH_CONFIRMATORY_EVALUATION",
    }
    RDIR.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps(stats, indent=2) + "\n")
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    (RDIR / "protected-validation-per-case-v1.json").write_text(json.dumps({"candidate_v2": v2_rows, "candidate_v7": v7_rows}, indent=2) + "\n")
    print(json.dumps({"verdict": verdict, "candidate_v7": v7, "bootstrap": boot}, indent=2))
    if verdict != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
