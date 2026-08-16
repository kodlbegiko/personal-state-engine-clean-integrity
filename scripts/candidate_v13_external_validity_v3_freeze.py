from __future__ import annotations

"""Freeze Candidate-v13 External Validity v3 after all candidate-blind gates pass."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity-v3"
DOC = ROOT / "docs/research/candidate-v13-external-validity-v3"
CANDIDATE = ROOT / "src/personal_state_engine/candidate_v13.py"
EXPECTED_CANDIDATE_SHA256 = "b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> int:
    if "personal_state_engine.candidate_v13" in sys.modules:
        raise RuntimeError("CANDIDATE_FIREWALL_FAIL: Candidate-v13 imported before freeze")
    if sha256_file(CANDIDATE) != EXPECTED_CANDIDATE_SHA256:
        raise RuntimeError("CANDIDATE_FIREWALL_FAIL: Candidate-v13 hash mismatch")
    infra = read_json(OUT / "infrastructure-qualification.json")
    if infra.get("status") != "PASS" or infra.get("formal_authorized") is not True:
        raise RuntimeError("infrastructure qualification not PASS")
    full = read_json(OUT / "full-materialization-qualification.json")
    if full.get("status") != "PASS" or full.get("ALL_SELECTED_CASES_PRODUCTION_MATERIALIZABLE_PASS") is not True:
        raise RuntimeError("full materialization qualification not PASS")
    prereg = DOC / "preregistration-lock-v3.json"
    if not prereg.exists() or read_json(prereg).get("status") != "LOCKED_PRE_FREEZE":
        raise RuntimeError("preregistration lock missing or invalid")

    freeze_files = [
        CANDIDATE,
        DOC / "source-contract-v3.json",
        DOC / "source-manifest-v3.json",
        DOC / "adapter-policy-v3.json",
        DOC / "runtime-memory-policy-v3.json",
        DOC / "allocation-policy-v3.json",
        DOC / "materializer-contract-v3.json",
        DOC / "evaluation-policy-v3.json",
        DOC / "preregistration-v3.md",
        DOC / "preregistration-lock-v3.json",
        ROOT / "scripts/candidate_v13_external_validity_v3_core.py",
        ROOT / "scripts/candidate_v13_external_validity_v3_evaluator.py",
        ROOT / "scripts/candidate_v13_external_validity_v3_formal_runner.py",
        ROOT / "scripts/candidate_v13_external_validity_v3_formal_sequence.py",
        ROOT / "scripts/candidate_v13_external_validity_v3_freeze.py",
        OUT / "candidate-firewall.json",
        OUT / "gold-cardinality-audit.json",
        OUT / "source-schema-manifest.json",
        OUT / "source-qualification.json",
        OUT / "source-capacity-audit.json",
        OUT / "contamination-audit.json",
        OUT / "dedup-audit.json",
        OUT / "determinism-audit.json",
        OUT / "allocation-feasibility.json",
        OUT / "full-materialization-qualification.json",
        OUT / "formal-infrastructure-qualification.json",
        OUT / "infrastructure-qualification.json",
    ]
    missing = [str(p.relative_to(ROOT)) for p in freeze_files if not p.exists()]
    if missing:
        raise RuntimeError(f"freeze files missing: {missing}")
    files = {}
    for path in freeze_files:
        rel = str(path.relative_to(ROOT))
        files[rel] = {"sha256": sha256_file(path), "git_blob_sha": git("hash-object", str(path))}
    manifest = {
        "schema_version": "candidate-v13-external-validity-v3-freeze-manifest-v1",
        "status": "FROZEN",
        "candidate_v13_sha256": sha256_file(CANDIDATE),
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
        "preregistration_commit": git("rev-parse", "HEAD"),
        "files": files,
    }
    freeze_path = OUT / "infrastructure-freeze-manifest-v3.json"
    write_json(freeze_path, manifest)
    ledger = {
        "schema_version": "candidate-v13-external-validity-v3-formal-ledger-v1",
        "ev_a_v3": 0, "ev_b_v3": 0, "ev_c_v3": 0,
        "formal_reruns": 0, "illegal_formal_reruns": False,
        "candidate_v13_external_invocation_occurred": False,
    }
    write_json(OUT / "formal-ledger.json", ledger)
    auth = {
        "schema_version": "candidate-v13-external-validity-v3-formal-authorization-lock-v1",
        "authorized": True,
        "freeze_manifest_sha256": sha256_file(freeze_path),
        "stage_order": ["ev_a_v3", "ev_b_v3", "ev_c_v3"],
        "reruns_permitted": False,
        "candidate_v13_invoked": False,
    }
    write_json(DOC / "formal-authorization-lock-v3.json", auth)
    print(json.dumps({"status": "FROZEN", "candidate_v13_invoked": False, "files": len(files)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
