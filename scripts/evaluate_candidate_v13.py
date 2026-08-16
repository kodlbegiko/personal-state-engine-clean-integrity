from __future__ import annotations

"""Evaluate Candidate-v13 without exposing individual-case outcomes."""

import argparse
import hashlib
import json
import random
from copy import deepcopy
from pathlib import Path
from typing import Any

from personal_state_engine.candidate_v12 import pse_candidate_v12_rank
from personal_state_engine.candidate_v13 import (
    candidate_source_invariant_v13,
    parse_query_frame_v13,
    pse_candidate_v13_rank,
)

ROOT = Path(__file__).resolve().parents[1]

THRESHOLDS = {
    "development": {
        "mrr": 0.985, "r_at_1": 0.980, "r_at_3": 0.995, "r_at_5": 0.998,
        "answerable_recall": 0.995, "false_abstention_rate_max": 0.005,
        "false_retrieval_rate_max": 0.020, "abstention_accuracy": 0.980,
        "eligible_rank1_accuracy": 0.980,
        "structural": {"S1": 0.990, "S2": 0.985, "S3": 0.985},
        "discourse_contamination_rate_max": 0.010,
    },
    "protected": {
        "mrr": 0.980, "r_at_1": 0.970, "r_at_3": 0.990, "r_at_5": 0.995,
        "answerable_recall": 0.990, "false_abstention_rate_max": 0.010,
        "false_retrieval_rate_max": 0.030, "abstention_accuracy": 0.970,
        "eligible_rank1_accuracy": 0.970,
        "structural": {"S1":0.970,"S2":0.960,"S3":0.960,"S4":0.960,
                       "S5":0.970,"S6":0.970,"S7":0.960},
    },
    "confirmatory": {
        "mrr": 0.975, "r_at_1": 0.965, "r_at_3": 0.990, "r_at_5": 0.995,
        "answerable_recall": 0.990, "false_abstention_rate_max": 0.010,
        "false_retrieval_rate_max": 0.030, "abstention_accuracy": 0.970,
        "eligible_rank1_accuracy": 0.965,
        "structural": {"S1":0.960,"S2":0.950,"S3":0.950,"S4":0.950,
                       "S5":0.960,"S6":0.960,"S7":0.950},
    },
    "final": {
        "mrr": 0.975, "r_at_1": 0.965, "r_at_3": 0.990, "r_at_5": 0.995,
        "answerable_recall": 0.990, "false_abstention_rate_max": 0.010,
        "false_retrieval_rate_max": 0.030, "abstention_accuracy": 0.970,
        "eligible_rank1_accuracy": 0.965,
        "structural": {"S1":0.960,"S2":0.950,"S3":0.950,"S4":0.950,
                       "S5":0.960,"S6":0.960,"S7":0.950},
    },
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _case_correct(case: dict[str, Any], ranked: list[str]) -> bool:
    relevant = set(case["relevant_memory_ids"])
    if relevant:
        return bool(ranked and ranked[0] in relevant and all(x in relevant for x in ranked))
    return not ranked


def _frame_correct(case: dict[str, Any], frame: Any) -> tuple[bool, bool, bool]:
    gold = case["generator_metadata"]["gold_frame"]
    subject = len(frame.target_subject) == 1 and frame.target_subject[0] == gold["subject_entity"]
    relation = len(frame.target_relation) == 1 and frame.target_relation[0] == gold["relation_frame"]
    temporal = frame.temporal_scope == gold["temporal_scope"]
    return subject, relation, temporal


def evaluate_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    no_evidence = [c for c in cases if not c["relevant_memory_ids"]]
    reciprocal: list[float] = []
    hits = {1: 0, 3: 0, 5: 0}
    false_abstention = 0
    false_retrieval_cases = 0
    no_evidence_abstain = 0
    eligible_answerable = 0
    eligible_rank1_correct = 0
    integrity = {"source": 0, "metadata": 0, "determinism": 0}
    structural_counts = {s: 0 for s in ("S1","S2","S3","S4","S5","S6","S7")}
    structural_correct = {s: 0 for s in structural_counts}
    subject_ok_n = relation_ok_n = temporal_ok_n = contamination_n = 0
    paired_v13_r1: list[int] = []
    paired_v12_r1: list[int] = []

    for case in cases:
        ranked = pse_candidate_v13_rank(case, 5)
        ranked_again = pse_candidate_v13_rank(case, 5)
        integrity["determinism"] += int(ranked != ranked_again)
        integrity["source"] += int(not candidate_source_invariant_v13(case, 5)["pass"])

        mutated = deepcopy(case)
        mutated["relevant_memory_ids"] = ["FORBIDDEN-GOLD"]
        mutated["preferred_memory_id"] = "FORBIDDEN-PREFERRED"
        mutated["designation"] = "FORBIDDEN-STAGE"
        mutated["answerability_label"] = "FORBIDDEN"
        mutated["expected_relation"] = "FORBIDDEN"
        mutated["expected_subject"] = "FORBIDDEN"
        mutated["expected_output"] = "FORBIDDEN"
        mutated["distractor_label"] = "FORBIDDEN"
        mutated["case_id"] = "FORBIDDEN"
        mutated["generator_metadata"] = {
            "grammar_family": "FORBIDDEN", "discourse_family": "FORBIDDEN",
            "structural_family": "FORBIDDEN", "answer": "FORBIDDEN",
            "template_provenance": "FORBIDDEN",
        }
        integrity["metadata"] += int(pse_candidate_v13_rank(mutated, 5) != ranked)

        frame = parse_query_frame_v13(case["query"], case["memories"])
        subj_ok, rel_ok, temp_ok = _frame_correct(case, frame)
        subject_ok_n += int(subj_ok)
        relation_ok_n += int(rel_ok)
        temporal_ok_n += int(temp_ok)
        contamination_n += int(not subj_ok)

        sf = case["generator_metadata"]["structural_family"]
        structural_counts[sf] += 1
        outcome_ok = _case_correct(case, ranked)
        if sf == "S1": sf_ok = subj_ok
        elif sf == "S2": sf_ok = rel_ok
        elif sf == "S3": sf_ok = temp_ok and outcome_ok
        elif sf == "S4": sf_ok = subj_ok and rel_ok and frame.parse_valid
        elif sf == "S5": sf_ok = outcome_ok
        elif sf == "S6": sf_ok = outcome_ok
        elif sf == "S7": sf_ok = bool(ranked and ranked[0] == case["preferred_memory_id"])
        else: raise AssertionError(sf)
        structural_correct[sf] += int(sf_ok)

        relevant = set(case["relevant_memory_ids"])
        if relevant:
            nonrel = [x for x in ranked if x not in relevant]
            false_retrieval_cases += int(bool(nonrel))
            if ranked:
                eligible_answerable += 1
                eligible_rank1_correct += int(ranked[0] in relevant)
            else:
                false_abstention += 1
            hit_rank = next((i for i, mid in enumerate(ranked, 1) if mid in relevant), None)
            reciprocal.append(1.0 / hit_rank if hit_rank else 0.0)
            for k in hits:
                hits[k] += int(hit_rank is not None and hit_rank <= k)
            v12_ranked = pse_candidate_v12_rank(case, 1)
            paired_v13_r1.append(int(bool(ranked and ranked[0] in relevant)))
            paired_v12_r1.append(int(bool(v12_ranked and v12_ranked[0] in relevant)))
        else:
            if ranked: false_retrieval_cases += 1
            else: no_evidence_abstain += 1

    a, n, total = max(1, len(answerable)), max(1, len(no_evidence)), max(1, len(cases))
    metrics = {
        "case_count": len(cases), "answerable_count": len(answerable),
        "no_evidence_count": len(no_evidence), "mrr": sum(reciprocal) / a,
        "r_at_1": hits[1] / a, "r_at_3": hits[3] / a, "r_at_5": hits[5] / a,
        "answerable_recall": hits[5] / a, "false_abstention_rate": false_abstention / a,
        "false_retrieval_rate": false_retrieval_cases / total,
        "abstention_accuracy": no_evidence_abstain / n,
        "eligible_rank1_accuracy": eligible_rank1_correct / max(1, eligible_answerable),
        "eligible_answerable_count": eligible_answerable,
    }
    frame_metrics = {
        "subject_binding_accuracy": subject_ok_n / total,
        "relation_binding_accuracy": relation_ok_n / total,
        "temporal_scope_accuracy": temporal_ok_n / total,
        "discourse_contamination_rate": contamination_n / total,
    }
    structural = {s: {"count": structural_counts[s], "correct": structural_correct[s],
                      "accuracy": structural_correct[s] / max(1, structural_counts[s])}
                  for s in structural_counts}
    integrity_summary = {
        "candidate_source_violations": integrity["source"],
        "metadata_firewall_violations": integrity["metadata"],
        "determinism_violations": integrity["determinism"],
        "candidate_source_invariant": "PASS" if integrity["source"] == 0 else "FAIL",
        "metadata_firewall": "PASS" if integrity["metadata"] == 0 else "FAIL",
        "determinism": "PASS" if integrity["determinism"] == 0 else "FAIL",
    }
    return {"metrics": metrics, "frame_metrics": frame_metrics, "structural": structural,
            "integrity": integrity_summary, "paired_v13_r1": paired_v13_r1,
            "paired_v12_r1": paired_v12_r1}


def bootstrap_noninferiority(v13: list[int], v12: list[int]) -> dict[str, Any]:
    if len(v13) != len(v12) or not v13:
        return {"status": "NOT_EVALUABLE", "reason": "paired outcomes unavailable"}
    diffs = [a - b for a, b in zip(v13, v12)]
    rng = random.Random(73129)
    n = len(diffs)
    boot = [sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(10000)]
    boot.sort()
    lo = boot[int(0.025 * len(boot))]
    hi = boot[min(len(boot) - 1, int(0.975 * len(boot)))]
    return {"status": "PASS" if lo >= -0.01 else "FAIL",
            "candidate_v13_r_at_1": sum(v13) / n, "baseline_v12_r_at_1": sum(v12) / n,
            "difference": sum(diffs) / n, "ci_95_percentile": [lo, hi], "margin": -0.01,
            "seed": 73129, "iterations": 10000}


def anti_collapse(cases: list[dict[str, Any]], result: dict[str, Any]) -> dict[str, Any]:
    retrieve = sum(bool(pse_candidate_v13_rank(c, 1)) for c in cases)
    abstain = len(cases) - retrieve
    total = max(1, len(cases))
    both_classes = (sum(bool(c["relevant_memory_ids"]) for c in cases) / total >= 0.30 and
                    sum(not c["relevant_memory_ids"] for c in cases) / total >= 0.30)
    catastrophic = [s for s, d in result["structural"].items()
                    if d["count"] and d["accuracy"] < 0.50]
    near_abstention = abstain / total >= 0.95
    near_retrieval = retrieve / total >= 0.95 and result["metrics"]["false_retrieval_rate"] > 0.10
    single_class = max(retrieve, abstain) / total >= 0.95 and both_classes
    return {"retrieve_count": retrieve, "abstain_count": abstain,
            "near_universal_abstention": near_abstention,
            "near_universal_retrieval": near_retrieval,
            "single_class_prediction_collapse": single_class,
            "catastrophic_structural_families": catastrophic,
            "pass": not (near_abstention or near_retrieval or single_class or catastrophic)}


def acceptance(stage: str, result: dict[str, Any], anti: dict[str, Any],
               no_formal_payload_exposure: bool = True,
               noninferiority: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
    t, m = THRESHOLDS[stage], result["metrics"]
    failures: list[str] = []
    for key in ("mrr","r_at_1","r_at_3","r_at_5","answerable_recall",
                "abstention_accuracy","eligible_rank1_accuracy"):
        if m[key] < t[key]: failures.append(f"{key}<{t[key]}")
    if m["false_abstention_rate"] > t["false_abstention_rate_max"]: failures.append("false_abstention_rate")
    if m["false_retrieval_rate"] > t["false_retrieval_rate_max"]: failures.append("false_retrieval_rate")
    if stage == "development":
        fm = result["frame_metrics"]
        if fm["subject_binding_accuracy"] < 0.990: failures.append("subject_binding_accuracy")
        if fm["relation_binding_accuracy"] < 0.985: failures.append("relation_binding_accuracy")
        if fm["temporal_scope_accuracy"] < 0.985: failures.append("temporal_scope_accuracy")
        if fm["discourse_contamination_rate"] > t["discourse_contamination_rate_max"]: failures.append("discourse_contamination_rate")
        if not no_formal_payload_exposure: failures.append("formal_payload_exposure")
    else:
        for sf, floor in t["structural"].items():
            if result["structural"][sf]["accuracy"] < floor: failures.append(f"{sf}<{floor}")
        if not anti["pass"]: failures.append("anti_collapse")
        if stage == "protected" and noninferiority and noninferiority["status"] == "FAIL":
            failures.append("noninferiority")
    for key in ("candidate_source_invariant","metadata_firewall","determinism"):
        if result["integrity"][key] != "PASS": failures.append(key)
    return not failures, failures


def evaluate(stage: str, benchmark: Path, output: Path,
             baseline_provenance_verified: bool = False) -> dict[str, Any]:
    payload = json.loads(benchmark.read_text(encoding="utf-8"))
    if payload["stage"] != stage: raise RuntimeError("benchmark stage mismatch")
    cases = payload["cases"]
    result = evaluate_cases(cases)
    anti = anti_collapse(cases, result)
    no_formal_exposure = True
    if stage == "development":
        no_formal_exposure = not any((ROOT / "experiments/benchmarks" / f"candidate-v13-{s}-v1.json").exists()
                                     for s in ("protected","confirmatory","final"))
    if stage == "protected":
        noninferiority = (bootstrap_noninferiority(result["paired_v13_r1"], result["paired_v12_r1"])
                          if baseline_provenance_verified else
                          {"status": "NOT_EVALUABLE", "reason": "Candidate-v12 baseline provenance not verified"})
    else:
        noninferiority = None
    passed, failures = acceptance(stage, result, anti, no_formal_exposure, noninferiority)
    result.pop("paired_v13_r1", None); result.pop("paired_v12_r1", None)
    summary = {
        "schema_version": "candidate-v13-evaluation-summary-v1", "candidate": "v13",
        "stage": stage, "formal_execution": stage != "development",
        "benchmark_path": str(benchmark.relative_to(ROOT)), "benchmark_sha256": sha256_file(benchmark),
        "acceptance": "PASS" if passed else "FAIL", "threshold_failures": failures,
        "thresholds": THRESHOLDS[stage], **result, "anti_collapse": anti,
        "no_formal_payload_exposure": no_formal_exposure if stage == "development" else None,
        "noninferiority": noninferiority,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=tuple(THRESHOLDS), required=True)
    parser.add_argument("--benchmark", type=Path); parser.add_argument("--output", type=Path)
    parser.add_argument("--baseline-provenance-verified", action="store_true")
    args = parser.parse_args()
    benchmark = args.benchmark or ROOT / "experiments/benchmarks" / f"candidate-v13-{args.stage}-v1.json"
    output = args.output or ROOT / "results/candidate-v13" / f"{args.stage}-summary-v1.json"
    summary = evaluate(args.stage, benchmark, output, args.baseline_provenance_verified)
    print(json.dumps({"stage": args.stage, "acceptance": summary["acceptance"],
                      "metrics": summary["metrics"], "frame_metrics": summary["frame_metrics"],
                      "structural": summary["structural"], "integrity": summary["integrity"],
                      "anti_collapse": summary["anti_collapse"],
                      "threshold_failures": summary["threshold_failures"],
                      "noninferiority": summary["noninferiority"]}, sort_keys=True))


if __name__ == "__main__":
    main()
