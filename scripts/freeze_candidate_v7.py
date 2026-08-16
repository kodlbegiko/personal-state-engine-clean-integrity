from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RDIR = ROOT / "results" / "candidate-v7"
SOURCE = ROOT / "src" / "personal_state_engine" / "candidate_v7.py"
CONFIG = ROOT / "experiments" / "configs" / "candidate-v7-v1.json"
DEV = ROOT / "experiments" / "benchmarks" / "candidate-v7-development-v1.json"
STRESS = ROOT / "experiments" / "benchmarks" / "candidate-v7-development-stress-v1.json"
V2 = ROOT / "src" / "personal_state_engine" / "candidate_v2.py"
BASE = ROOT / "src" / "personal_state_engine" / "zero_cost_baselines.py"
EXPECTED_SOURCE = "c9bc8a5cf70cca5e2f97240bb427d1ad1cd8d60d14af922a4e634ec9c870bdae"
EXPECTED_CONFIG = "7acc9a99938efa0d361791191960a60cf8a88b6a2ec022d60f54da3df29b7e62"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    source_sha = sha(SOURCE)
    config_sha = sha(CONFIG)
    if source_sha != EXPECTED_SOURCE:
        raise SystemExit(f"freeze denied: source identity changed: {source_sha}")
    if config_sha != EXPECTED_CONFIG:
        raise SystemExit(f"freeze denied: config identity changed: {config_sha}")

    summary = json.loads((RDIR / "development-summary-v1.json").read_text())
    stress = json.loads((RDIR / "development-stress-summary-v1.json").read_text())
    decon = json.loads((RDIR / "decontamination-report-v1.json").read_text())
    ledger = [json.loads(line) for line in (RDIR / "development-ledger.jsonl").read_text().splitlines() if line.strip()]

    checks = {
        "development_verdict_pass": summary.get("verdict") == "PASS",
        "development_source_identity_match": summary.get("candidate_v7_source_sha256") == source_sha,
        "development_config_identity_match": summary.get("config_sha256") == config_sha,
        "all_development_guardrails_pass": bool(summary.get("guardrails")) and all(summary["guardrails"].values()),
        "development_tests_210_of_210": summary.get("tests") == {"passed": 210, "failed": 0, "total": 210},
        "stress_pass": stress.get("verdict") == "PASS",
        "stress_source_identity_match": stress.get("candidate_v7_source_sha256") == source_sha,
        "stress_answerable_20_of_20": stress.get("answerable_supported_and_ranking_preserved") == 20,
        "stress_negative_20_of_20": stress.get("negative_correct_abstention") == 20,
        "decontamination_pass": decon.get("status") == "PASS",
        "retired_intersection_zero": decon.get("intersection_count") == 0,
        "retired_semantic_payload_not_accessed": decon.get("retired_payload_accessed") is False,
        "negative_development_evidence_retained": sum(row.get("status") == "FAILED_RETAINED" for row in ledger) >= 4,
        "iteration5_pass_present": any(row.get("iteration") == 5 and row.get("source_sha256") == source_sha and row.get("status") == "PASS" for row in ledger),
        "iteration4_fail_present": any(row.get("iteration") == 4 and row.get("status") == "FAILED_RETAINED" for row in ledger),
    }
    if not all(checks.values()):
        raise SystemExit("freeze denied: " + json.dumps({k: v for k, v in checks.items() if not v}, sort_keys=True))

    freeze_boundary_commit = git("rev-parse", "HEAD")
    manifest = {
        "schema_version": "candidate-v7-freeze-manifest-v1",
        "candidate_v7_frozen": True,
        "freeze_boundary_commit": freeze_boundary_commit,
        "freeze_rule": "Candidate-v7 source/config must not change after this boundary commit; later commits may only add evaluation protocols, benchmarks, evidence, reports, and non-candidate tooling.",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_source_sha256": source_sha,
        "config_sha256": config_sha,
        "dependency_identities": {
            "candidate_v2_source_sha256": sha(V2),
            "zero_cost_baselines_sha256": sha(BASE),
            "candidate_v6_historical_source_sha256": "c540056c6f30f0145ab8ef8c10be3abcae2ed24e6a087a2d9a3531bc5e545325",
            "candidate_v6_historical_config_sha256": "067bfa64d97bf2eb1f7208082c36d202118a0e50a2414fc345bf328f83cab5b1"
        },
        "development_benchmark_sha256": sha(DEV),
        "stress_development_benchmark_sha256": sha(STRESS),
        "development_metrics": summary["candidate_v7_metrics"],
        "candidate_v2_development_metrics": summary["candidate_v2_metrics"],
        "development_guardrails": summary["guardrails"],
        "test_result": summary["tests"],
        "stress_result": {
            "answerable_supported_and_ranking_preserved": stress["answerable_supported_and_ranking_preserved"],
            "answerable_total": stress["answerable_total"],
            "negative_correct_abstention": stress["negative_correct_abstention"],
            "negative_total": stress["negative_total"],
            "verdict": stress["verdict"]
        },
        "decontamination": {
            "retired_count": decon["retired_count"],
            "intersection_count": decon["intersection_count"],
            "retired_payload_accessed": decon["retired_payload_accessed"],
            "status": decon["status"]
        },
        "freeze_checks": checks,
        "monetary_cost_usd": 0
    }
    out = RDIR / "freeze-manifest-v1.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({
        "freeze_boundary_commit": freeze_boundary_commit,
        "candidate_source_sha256": source_sha,
        "config_sha256": config_sha,
        "candidate_v7_frozen": True
    }, indent=2))


if __name__ == "__main__":
    main()
