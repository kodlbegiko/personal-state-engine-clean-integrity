from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v10/development-freeze-manifest-v1.json"

FROZEN_FILES = [
    "src/personal_state_engine/candidate_v10.py",
    "scripts/generate_candidate_v10_benchmark.py",
    "scripts/generate_candidate_v10_benchmark_v2.py",
    "scripts/evaluate_candidate_v10.py",
    "scripts/audit_candidate_v10_cross_stage_freshness.py",
    "scripts/run_candidate_v10_formal_mission.py",
    "experiments/configs/candidate-v10-v1.json",
    "tests/test_candidate_v10.py",
    "docs/research/candidate-v10/preregistration.md",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if OUT.exists():
        raise SystemExit("freeze manifest already exists; Candidate-v10 is already frozen")
    dev = json.loads((ROOT / "results/candidate-v10/development-summary-v1.json").read_text())
    if dev.get("verdict") != "PASS":
        raise SystemExit("development is not PASS")
    src_hash = sha(ROOT / "src/personal_state_engine/candidate_v10.py")
    if dev.get("candidate_v10_source_sha256") != src_hash:
        raise SystemExit("development PASS does not correspond to current candidate_v10.py")
    missing = [p for p in FROZEN_FILES if not (ROOT / p).exists()]
    if missing:
        raise SystemExit(f"cannot freeze; missing files: {missing}")
    manifest = {
        "schema_version": "candidate-v10-development-freeze-v1",
        "state": "CANDIDATE_V10_DEVELOPMENT_FROZEN",
        "freeze_commit_parent": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "development_verdict": dev["verdict"],
        "development_metrics": dev["candidate_v10"],
        "development_benchmark_sha256": dev["benchmark_sha256"],
        "development_result_sha256": sha(ROOT / "results/candidate-v10/development-summary-v1.json"),
        "development_freshness_audit_sha256": sha(ROOT / "results/candidate-v10/freshness-audit-development-v1.json"),
        "frozen_files": {p: sha(ROOT / p) for p in FROZEN_FILES},
        "formal_execution_counts_at_freeze": {"protected": 0, "confirmatory": 0, "final": 0},
        "post_freeze_policy": "No frozen file may change before or during protected/confirmatory/final formal execution.",
        "monetary_cost_usd": 0,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
