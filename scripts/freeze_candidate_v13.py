from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANCHOR = "16dfcbfeb47cf8ad9bf78c639150d17404f4a685"
FROZEN_FILES = (
    "src/personal_state_engine/candidate_v13.py",
    "scripts/candidate_v13_benchmark.py",
    "scripts/evaluate_candidate_v13.py",
    "scripts/candidate_v13_formal_runner.py",
    "scripts/freeze_candidate_v13.py",
    "tests/test_candidate_v13.py",
    "docs/research/candidate-v13/preregistration.md",
    "docs/research/candidate-v13/preregistration-lock.json",
    ".github/workflows/candidate-v13-development.yml",
    ".github/workflows/candidate-v13-freeze.yml",
    ".github/workflows/candidate-v13-formal.yml",
)


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    dev_benchmark = ROOT / "experiments/benchmarks/candidate-v13-development-v1.json"
    dev_result = ROOT / "results/candidate-v13/development-summary-v1.json"
    if not dev_benchmark.exists() or not dev_result.exists():
        raise SystemExit("Development evidence missing")
    result = json.loads(dev_result.read_text())
    if result["acceptance"] != "PASS":
        raise SystemExit("Development has not passed; freeze forbidden")
    for stage in ("protected", "confirmatory", "final"):
        if (ROOT / f"experiments/benchmarks/candidate-v13-{stage}-v1.json").exists():
            raise SystemExit("formal payload already materialized; freeze forbidden")

    lock = json.loads((ROOT / "docs/research/candidate-v13/preregistration-lock.json").read_text())
    if lock["status"] != "PREREGISTRATION_LOCKED":
        raise SystemExit("preregistration lock invalid")

    head = run("git", "rev-parse", "HEAD")
    frozen = {}
    for rel in FROZEN_FILES:
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"missing frozen component: {rel}")
        frozen[rel] = {
            "sha256": sha256(path),
            "git_blob_sha": run("git", "rev-parse", f"HEAD:{rel}"),
        }

    current_v12_blob = run("git", "rev-parse", "HEAD:src/personal_state_engine/candidate_v12.py")
    historical_v12_blob = run("git", "rev-parse", f"{ANCHOR}:src/personal_state_engine/candidate_v12.py")
    baseline_verified = current_v12_blob == historical_v12_blob

    ledger = {
        "candidate": "v13",
        "protected": 0,
        "confirmatory": 0,
        "final": 0,
        "terminal_state": None,
    }
    ledger_path = ROOT / "results/candidate-v13/formal-ledger.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")

    manifest = {
        "schema_version": "candidate-v13-freeze-manifest-v1",
        "candidate": "v13",
        "status": "FROZEN_AFTER_DEVELOPMENT_PASS",
        "repository": "kodlbegiko/personal-state-engine-clean-integrity",
        "branch": "research/candidate-v13-fresh-lineage",
        "freeze_source_commit": head,
        "historical_parent_anchor": ANCHOR,
        "preregistration_commit_sha": lock["preregistration_commit_sha"],
        "preregistration_git_blob_sha": lock["preregistration_git_blob_sha"],
        "preregistration_sha256": lock["preregistration_sha256"],
        "development_benchmark_sha256": sha256(dev_benchmark),
        "development_result_sha256": sha256(dev_result),
        "development_acceptance": result["acceptance"],
        "inference_entrypoint": "personal_state_engine.candidate_v13:pse_candidate_v13_rank",
        "runtime": {"python": sys.version, "platform": platform.platform()},
        "frozen_files": frozen,
        "safety_gates": {
            "metadata_firewall": result["integrity"]["metadata_firewall"],
            "candidate_v2_source_invariant": result["integrity"]["candidate_source_invariant"],
            "determinism": result["integrity"]["determinism"],
            "no_formal_payload_exposure": result["no_formal_payload_exposure"],
        },
        "formal_execution_ledger_initial": {"protected": 0, "confirmatory": 0, "final": 0},
        "candidate_v12_baseline": {
            "historical_anchor": ANCHOR,
            "historical_blob_sha": historical_v12_blob,
            "current_blob_sha": current_v12_blob,
            "provenance_verified": baseline_verified,
        },
    }
    out = ROOT / "docs/research/candidate-v13/freeze-manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
