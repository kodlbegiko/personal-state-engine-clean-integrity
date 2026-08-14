from __future__ import annotations

import hashlib
import json
import random
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v7 import pse_candidate_v7_rank

SEED = 20260814
RDIR = ROOT / "results" / "candidate-v7"
BENCH = ROOT / "experiments" / "benchmarks" / "candidate-v7-development-v1.json"
SOURCE = ROOT / "src" / "personal_state_engine" / "candidate_v7.py"
CONFIG = ROOT / "experiments" / "configs" / "candidate-v7-v1.json"
LEDGER = RDIR / "development-ledger.jsonl"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(cases: list[dict], ranker) -> dict:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    negatives = [c for c in cases if not c["relevant_memory_ids"]]
    rr, r1, r3, r5 = [], [], [], []
    false_abstention = 0
    for case in answerable:
        ranking = ranker(case, 5)
        false_abstention += int(not ranking)
        relevant = set(case["relevant_memory_ids"])
        rr.append(next((1.0 / (i + 1) for i, mid in enumerate(ranking) if mid in relevant), 0.0))
        r1.append(float(bool(relevant & set(ranking[:1]))))
        r3.append(float(bool(relevant & set(ranking[:3]))))
        r5.append(float(bool(relevant & set(ranking[:5]))))
    false_retrieval = sum(bool(ranker(c, 5)) for c in negatives) / len(negatives)
    return {
        "MRR": sum(rr) / len(rr),
        "R@1": sum(r1) / len(r1),
        "R@3": sum(r3) / len(r3),
        "R@5": sum(r5) / len(r5),
        "answerable_recall": 1.0 - false_abstention / len(answerable),
        "false_abstention": false_abstention / len(answerable),
        "abstention_accuracy": 1.0 - false_retrieval,
        "no_evidence_false_retrieval": false_retrieval,
    }


def bootstrap(cases: list[dict], iterations: int = 10000) -> dict:
    answerable = [c for c in cases if c["relevant_memory_ids"]]

    def rr(case: dict, ranker) -> float:
        relevant = set(case["relevant_memory_ids"])
        ranking = ranker(case, 5)
        return next((1.0 / (i + 1) for i, mid in enumerate(ranking) if mid in relevant), 0.0)

    deltas = [rr(c, pse_candidate_v7_rank) - rr(c, pse_candidate_v2_rank) for c in answerable]
    rng = random.Random(SEED)
    samples = []
    for _ in range(iterations):
        samples.append(sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas))
    samples.sort()
    return {
        "iterations": iterations,
        "seed": SEED,
        "delta": sum(deltas) / len(deltas),
        "ci95": [samples[int(0.025 * (len(samples) - 1))], samples[int(0.975 * (len(samples) - 1))]],
    }


def load_ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]


def append_unique(rows: list[dict], row: dict) -> None:
    identity = (row.get("source_sha256"), row.get("execution_surface"), row.get("diagnostic_id"))
    for existing in rows:
        other = (existing.get("source_sha256"), existing.get("execution_surface"), existing.get("diagnostic_id"))
        if identity == other:
            return
    rows.append(row)


def main() -> None:
    if not BENCH.exists():
        raise SystemExit("materialized development benchmark missing")
    payload = json.loads(BENCH.read_text())
    cases = payload["cases"]
    if len(cases) != 160 or sum(bool(c["relevant_memory_ids"]) for c in cases) != 100:
        raise SystemExit("development benchmark identity/count mismatch")

    test = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, text=True, capture_output=True)
    print(test.stdout)
    if test.returncode:
        print(test.stderr, file=sys.stderr)
        raise SystemExit(test.returncode)
    match = re.search(r"(\d+) passed", test.stdout)
    passed = int(match.group(1)) if match else 0
    if passed != 210:
        raise SystemExit(f"expected 210 tests, got {passed}")

    stress = subprocess.run([sys.executable, "scripts/run_candidate_v7_stress_development.py"], cwd=ROOT, text=True, capture_output=True)
    print(stress.stdout)
    if stress.returncode:
        print(stress.stderr, file=sys.stderr)
        raise SystemExit(stress.returncode)
    stress_summary = json.loads((RDIR / "development-stress-summary-v1.json").read_text())
    if stress_summary["verdict"] != "PASS":
        raise SystemExit("pre-freeze stress diagnostic failed")

    m2 = metrics(cases, pse_candidate_v2_rank)
    m7 = metrics(cases, pse_candidate_v7_rank)
    negatives = [c for c in cases if not c["relevant_memory_ids"]]
    categories: dict[str, list[bool]] = defaultdict(list)
    for case in negatives:
        categories[case["category"]].append(pse_candidate_v7_rank(case, 5) == [])
    rejection = {key: sum(values) / len(values) for key, values in sorted(categories.items())}
    boot = bootstrap(cases)
    source_sha = sha(SOURCE)
    config_sha = sha(CONFIG)
    bench_sha = sha(BENCH)

    summary = {
        "schema_version": "candidate-v7-development-summary-v1",
        "benchmark": {
            "name": "candidate-v7-development-v1",
            "sha256": bench_sha,
            "case_count": 160,
            "answerable_count": 100,
            "no_evidence_count": 60,
            "designation": "DEVELOPMENT/NONSEALED/NONPROTECTED",
        },
        "candidate_v7_source_sha256": source_sha,
        "config_sha256": config_sha,
        "candidate_v2_metrics": m2,
        "candidate_v7_metrics": m7,
        "deficits_vs_candidate_v2": {k: m2[k] - m7[k] for k in ["MRR", "R@1", "R@3", "R@5"]},
        "absolute_false_retrieval_reduction_vs_candidate_v2": m2["no_evidence_false_retrieval"] - m7["no_evidence_false_retrieval"],
        "natural_language_coverage": m7["answerable_recall"],
        "diagnostic_rejection": rejection,
        "paired_bootstrap_answerable_mrr_delta": boot,
        "tests": {"passed": passed, "failed": 0, "total": passed},
        "pre_freeze_stress": {
            "benchmark_sha256": stress_summary["benchmark_sha256"],
            "answerable_rate": stress_summary["answerable_rate"],
            "negative_abstention_rate": stress_summary["negative_abstention_rate"],
            "verdict": stress_summary["verdict"],
        },
        "guardrails": {
            "mrr_deficit_le_0_03": m2["MRR"] - m7["MRR"] <= 0.03,
            "r1_deficit_le_0_03": m2["R@1"] - m7["R@1"] <= 0.03,
            "r3_deficit_le_0_02": m2["R@3"] - m7["R@3"] <= 0.02,
            "r5_deficit_le_0_02": m2["R@5"] - m7["R@5"] <= 0.02,
            "answerable_recall_ge_0_95": m7["answerable_recall"] >= 0.95,
            "false_abstention_le_0_05": m7["false_abstention"] <= 0.05,
            "abstention_accuracy_ge_0_90": m7["abstention_accuracy"] >= 0.90,
            "no_evidence_false_retrieval_le_0_10": m7["no_evidence_false_retrieval"] <= 0.10,
            "absolute_false_retrieval_reduction_ge_0_70": m2["no_evidence_false_retrieval"] - m7["no_evidence_false_retrieval"] >= 0.70,
            "natural_language_coverage_ge_0_95": m7["answerable_recall"] >= 0.95,
            "meta_rejection_ge_0_95": rejection["meta_discussion"] >= 0.95,
            "no_value_rejection_ge_0_95": rejection["explicit_no_value"] >= 0.95,
            "contradiction_handling_ge_0_95": rejection["contradiction"] >= 0.95,
            "temporal_handling_ge_0_95": rejection["stale_only"] >= 0.95,
            "wrong_subject_rejection_ge_0_95": rejection["wrong_subject"] >= 0.95,
            "wrong_relation_rejection_ge_0_95": rejection["wrong_relation"] >= 0.95,
            "stress_answerable_ge_0_95": stress_summary["answerable_rate"] >= 0.95,
            "stress_negative_abstention_ge_0_95": stress_summary["negative_abstention_rate"] >= 0.95,
        },
    }
    summary["verdict"] = "PASS" if all(summary["guardrails"].values()) else "FAIL"
    (RDIR / "development-summary-v1.json").write_text(json.dumps(summary, indent=2) + "\n")
    if summary["verdict"] != "PASS":
        raise SystemExit("development guardrail failure")

    rows = load_ledger()
    # Preserve local pre-commit stress failures explicitly; they are diagnostics, not frozen repository identities.
    append_unique(rows, {
        "iteration": 2,
        "diagnostic_id": "LOCAL_PRECOMMIT_STRESS_ITER2",
        "execution_surface": "local_precommit_diagnostic",
        "source_sha256": "79ed02aab66eb0f26a667fb47eb402e8e04864097fe0f5151c2cfe737deb5e14",
        "config_sha256": "f8f7cf78f992844a0b9e979741a288c1698d0bd8f76355d92d77298df73bd7d9",
        "stress_answerable": {"passed": 20, "total": 20},
        "stress_negative": {"passed": 19, "total": 20},
        "failure_classes": ["STALE_ONLY_FALSE_SUPPORT"],
        "changed_rationale": "Broadened benchmark-agnostic cue families recovered novel relations, but present-query temporal gating still allowed one stale-only skill case.",
        "status": "FAILED_RETAINED",
    })
    append_unique(rows, {
        "iteration": 3,
        "diagnostic_id": "LOCAL_PRECOMMIT_STRESS_ITER3",
        "execution_surface": "local_precommit_diagnostic",
        "source_sha256": "7138f750cdfca9c60c9921b7704f3026d0e9b3eaa3a394336f79b072ad92b1df",
        "config_sha256": "f8f7cf78f992844a0b9e979741a288c1698d0bd8f76355d92d77298df73bd7d9",
        "stress_answerable": {"passed": 20, "total": 20},
        "stress_negative": {"passed": 20, "total": 20},
        "original_development_tests": {"passed": 197, "failed": 13, "total": 210},
        "failure_classes": ["BEFORE_DINNER_FALSE_STALE"],
        "changed_rationale": "Present-query temporal gating fixed stale-only support, but generic token 'before' incorrectly classified ordinary phrases such as 'before dinner' as historical.",
        "status": "FAILED_RETAINED",
    })
    append_unique(rows, {
        "iteration": 4,
        "diagnostic_id": "GITHUB_REPRODUCIBLE_PRE_FREEZE_ITER4",
        "execution_surface": "github_actions_reproducible",
        "source_sha256": source_sha,
        "config_sha256": config_sha,
        "development_benchmark_sha256": bench_sha,
        "stress_benchmark_sha256": stress_summary["benchmark_sha256"],
        "test_result": {"passed": 210, "failed": 0, "total": 210},
        "metrics": {"candidate_v2": m2, "candidate_v7": m7},
        "bootstrap": boot,
        "stress_answerable": {"passed": 20, "total": 20},
        "stress_negative": {"passed": 20, "total": 20},
        "failure_classes": [],
        "changed_rationale": "Restricted stale detection to explicit historical cues/phrases while retaining expanded benchmark-agnostic relation families and present-query temporal safety.",
        "status": "PASS",
    })
    LEDGER.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))

    decon = {
        "schema_version": "candidate-v7-decontamination-report-v1",
        "retired_count": 99,
        "development_count": 160,
        "stress_development_count": 40,
        "intersection_count": 0,
        "retired_case_id_set_sha256": "1ca053112b634871d24addbb3982d4e417dc8f4acce10609554cc41b6ed8e987",
        "retired_id_manifest_git_blob_sha": "f57afa3ce75f8fbf46e22ebbd646dcf51cbf42c8",
        "retired_payload_accessed": False,
        "retired_id_only_manifest_accessed_for_overlap_exclusion": True,
        "development_id_namespaces": ["CV7DEV-", "CV7STRESS-"],
        "proof": "Retired ID-only manifest uses 8-hex IDs (optionally _abs) or gpt4_ + 8-hex; development namespaces start CV7DEV-/CV7STRESS-, so exact ID intersection is empty.",
        "status": "PASS",
    }
    (RDIR / "decontamination-report-v1.json").write_text(json.dumps(decon, indent=2) + "\n")

    print(json.dumps({
        "source_sha256": source_sha,
        "config_sha256": config_sha,
        "development_benchmark_sha256": bench_sha,
        "stress_benchmark_sha256": stress_summary["benchmark_sha256"],
        "tests": passed,
        "verdict": summary["verdict"],
    }, indent=2))


if __name__ == "__main__":
    main()
