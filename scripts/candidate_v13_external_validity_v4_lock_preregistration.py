from __future__ import annotations

"""Complete and cryptographically bind the v4 preregistration before freeze."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/research/candidate-v13-external-validity-v4"
OUT = ROOT / "results/candidate-v13-external-validity-v4"
CANDIDATE = ROOT / "src/personal_state_engine/candidate_v13.py"
EXPECTED = "b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if "personal_state_engine.candidate_v13" in sys.modules:
        raise RuntimeError("Candidate imported before v4 preregistration lock")
    if sha256(CANDIDATE) != EXPECTED:
        raise RuntimeError("Candidate-v13 SHA mismatch")
    launch_path = OUT / "launch-path-qa.json"
    launch = read(launch_path)
    infra_path = OUT / "infrastructure-qualification.json"
    infra = read(infra_path)
    if launch.get("status") != "PASS" or infra.get("status") != "PASS":
        raise RuntimeError("cannot lock preregistration before all candidate-blind gates PASS")
    lock_path = DOC / "preregistration-lock-v4.json"
    lock = read(lock_path)
    required_stage_digests = read(OUT / "full-materialization-qualification.json")["stages"]
    lock.update({
        "schema_version": "candidate-v13-external-validity-v4-preregistration-lock-v3",
        "status": "LOCKED_PRE_FREEZE",
        "candidate_v13_sha256": EXPECTED,
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
        "performance_driven_protocol_changes": 0,
        "launch_path_qa": "PASS",
        "launch_path_qa_sha256": sha256(launch_path),
        "orchestration_contract_sha256": sha256(DOC / "orchestration-contract-v4.json"),
        "orchestration_workflow_sha256": sha256(ROOT / ".github/workflows/candidate-v13-external-validity-v4.yml"),
        "formal_runner_sha256": sha256(ROOT / "scripts/candidate_v13_external_validity_v4_formal_runner.py"),
        "evaluator_sha256": sha256(ROOT / "scripts/candidate_v13_external_validity_v4_evaluator.py"),
        "materializer_sha256": sha256(ROOT / "scripts/candidate_v13_external_validity_v4_materializer.py"),
        "freeze_logic_sha256": sha256(ROOT / "scripts/candidate_v13_external_validity_v4_freeze.py"),
        "final_integrity_audit_sha256": sha256(ROOT / "scripts/candidate_v13_external_validity_v4_final_integrity_audit.py"),
        "formal_ledger_initial_state": {"ev_a_v4": 0, "ev_b_v4": 0, "ev_c_v4": 0, "formal_reruns": 0},
        "selection_digests": {k: v["selection_digest_sha256"] for k, v in required_stage_digests.items()},
        "materialization_digests": {k: v["materialization_digest_sha256"] for k, v in required_stage_digests.items()},
        "runtime_payload_digests": {k: v["runtime_payload_digest_sha256"] for k, v in required_stage_digests.items()},
        "terminal_states": [
            "EXTERNAL_VALIDITY_V4_PASS",
            "EXTERNAL_VALIDITY_V4_CANDIDATE_FAIL",
            "EXTERNAL_VALIDITY_V4_INFRASTRUCTURE_BLOCKED",
            "EXTERNAL_VALIDITY_V4_INVALID",
        ],
    })
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    infra = read(infra_path)
    infra["preregistration_lock_completeness_v4"] = "PASS"
    infra["preregistration_lock_sha256"] = sha256(lock_path)
    infra["candidate_v13_imported"] = False
    infra["candidate_v13_invoked"] = False
    infra["formal_authorized"] = infra["status"] == "PASS"
    infra_path.write_text(json.dumps(infra, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PREREGISTRATION_V4_COMPLETE_PASS", "candidate_v13_invoked": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
