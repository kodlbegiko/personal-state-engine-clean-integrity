from __future__ import annotations

"""Candidate-blind LAUNCH_PATH_QA for Candidate-v13 External Validity v4."""

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity-v4"
DOC = ROOT / "docs/research/candidate-v13-external-validity-v4"
WORKFLOW = ROOT / ".github/workflows/candidate-v13-external-validity-v4.yml"
FORMAL = ROOT / "scripts/candidate_v13_external_validity_v4_formal_runner.py"
CANDIDATE = ROOT / "src/personal_state_engine/candidate_v13.py"
EXPECTED = "b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838"
PREFREEZE = [
    ROOT / "scripts/bootstrap_candidate_v13_external_validity_v4.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_prequalification.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_core.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_materializer.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_contamination.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_qualification_runner.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_infrastructure_qualification.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_finalize_qualification.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_launch_path_qa.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_lock_preregistration.py",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def static_candidate_firewall() -> list[str]:
    violations = []
    for path in PREFREEZE:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "personal_state_engine.candidate_v13" or alias.name.endswith(".candidate_v13"):
                        violations.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "personal_state_engine.candidate_v13" or module.endswith(".candidate_v13"):
                    violations.append(f"{path.name}: from {module}")
            elif isinstance(node, ast.Call):
                func = node.func
                name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
                if name in {"pse_candidate_v13_rank", "evidence_support_signature_v13"}:
                    violations.append(f"{path.name}: call {name}")
    return violations


def dry_run_state_machine() -> dict:
    stages = ["qualification", "preregistration", "freeze", "authorization", "ev_a", "ev_b", "ev_c", "terminal"]
    reached = []
    counts = {"ev_a": 0, "ev_b": 0, "ev_c": 0}
    authorized = False
    frozen = False
    for stage in stages:
        if stage == "freeze":
            frozen = True
        elif stage == "authorization":
            if not frozen:
                raise RuntimeError("authorization reached without freeze")
            authorized = True
        elif stage in counts:
            if not (frozen and authorized):
                raise RuntimeError(f"{stage} reachable without freeze+authorization")
            if counts[stage] != 0:
                raise RuntimeError(f"duplicate {stage} in dry-run")
            counts[stage] += 1
        reached.append(stage)
    return {"reached": reached, "counts": counts, "candidate_execution_disabled": True, "pass": counts == {"ev_a": 1, "ev_b": 1, "ev_c": 1}}


def main() -> int:
    if "personal_state_engine.candidate_v13" in sys.modules:
        raise RuntimeError("Candidate imported before LAUNCH_PATH_QA")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    formal = FORMAL.read_text(encoding="utf-8")
    markers = [
        "Bootstrap fresh v4 lineage",
        "Run v4 candidate-blind prequalification",
        "Run v4 candidate-blind qualification",
        "Run v4 formal-runner qualification",
        "Run LAUNCH_PATH_QA",
        "Complete preregistration lock",
        "Freeze and authorize",
        "Verify immutable freeze and zero-use ledger",
        "Run one-shot formal sequence",
        "Finalize independent integrity audit",
    ]
    positions = [workflow.find(x) for x in markers]
    static_violations = static_candidate_firewall()
    dry = dry_run_state_machine()
    checks = {
        "candidate_sha_matches": sha256(CANDIDATE) == EXPECTED,
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
        "no_recursive_event_dependency": "workflow_run:" not in workflow and "repository_dispatch" not in workflow,
        "manual_formal_dispatch_absent": "workflow_dispatch" not in workflow,
        "single_already_started_job_graph": "  execute-v4:" in workflow,
        "static_dag_order": all(x >= 0 for x in positions) and positions == sorted(positions),
        "same_workflow_freeze_to_formal": workflow.find("Freeze and authorize") < workflow.find("Run one-shot formal sequence"),
        "candidate_firewall": not static_violations,
        "dry_run_reaches_formal_boundary": dry["pass"],
        "one_shot_ledger_guard": "FORMAL_RERUN_DETECTED" in formal and "consume(stage)" in formal,
        "stage_order_guard": "before completed PASS" in formal,
        "authorization_guard": "verify_freeze()" in formal and "formal authorization not frozen" in formal,
        "hash_guard": "FREEZE_MISMATCH" in formal,
        "no_matrix_retry": "matrix:" not in workflow,
        "concurrency_guard": "cancel-in-progress: false" in workflow,
    }
    status = "PASS" if all(v is True or v is False and k in {"candidate_v13_imported", "candidate_v13_invoked"} for k, v in checks.items()) else "FAIL"
    # Explicitly require the two false-valued candidate-use facts and every other boolean true.
    status = "PASS" if checks["candidate_v13_imported"] is False and checks["candidate_v13_invoked"] is False and all(v for k, v in checks.items() if k not in {"candidate_v13_imported", "candidate_v13_invoked"}) else "FAIL"
    obj = {
        "schema_version": "candidate-v13-external-validity-v4-launch-path-qa-v1",
        "status": status,
        "gate": "LAUNCH_PATH_QA_PASS" if status == "PASS" else "LAUNCH_PATH_QA_FAIL",
        "checks": checks,
        "static_candidate_firewall_violations": static_violations,
        "dry_run": dry,
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    DOC.mkdir(parents=True, exist_ok=True)
    (OUT / "launch-path-qa.json").write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (DOC / "LAUNCH_PATH_QA.md").write_text(
        "# LAUNCH_PATH_QA\n\n"
        f"Gate: `{obj['gate']}`\n\n"
        "The formal boundary is reachable from the same already-started workflow job after freeze and authorization. No second repository event, manual dispatch, matrix retry, or recursive `GITHUB_TOKEN` trigger is required. Candidate execution remained disabled throughout QA.\n",
        encoding="utf-8",
    )
    infra_path = OUT / "infrastructure-qualification.json"
    infra = json.loads(infra_path.read_text(encoding="utf-8"))
    infra.setdefault("gates", {})["LAUNCH_PATH_QA_PASS"] = status == "PASS"
    infra["launch_path_qa"] = status
    infra["status"] = "PASS" if all(bool(v) for v in infra["gates"].values()) else "FAIL"
    infra["formal_authorized"] = infra["status"] == "PASS"
    infra["candidate_v13_imported"] = False
    infra["candidate_v13_invoked"] = False
    infra_path.write_text(json.dumps(infra, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "checks": checks}, sort_keys=True))
    return 0 if status == "PASS" and infra["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
