from __future__ import annotations

"""Finalize all candidate-blind v3 gates with real formal-runner/workflow QA."""

import ast
import hashlib
import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity-v3"
FILES = [
    ROOT / "scripts/candidate_v13_external_validity_v3_core.py",
    ROOT / "scripts/candidate_v13_external_validity_v3_materializer.py",
    ROOT / "scripts/candidate_v13_external_validity_v3_contamination.py",
    ROOT / "scripts/candidate_v13_external_validity_v3_qualification_runner.py",
    ROOT / "scripts/candidate_v13_external_validity_v3_evaluator.py",
    ROOT / "scripts/candidate_v13_external_validity_v3_formal_runner.py",
    ROOT / "scripts/candidate_v13_external_validity_v3_formal_sequence.py",
    ROOT / "scripts/candidate_v13_external_validity_v3_freeze.py",
    ROOT / "scripts/candidate_v13_external_validity_v3_finalize_qualification.py",
]
CANDIDATE_MODULE = "personal_state_engine.candidate_v13"
CANDIDATE = ROOT / "src/personal_state_engine/candidate_v13.py"
EXPECTED = "b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838"
FORMAL_WORKFLOW = ROOT / ".github/workflows/candidate-v13-external-validity-v3-formal-sequence.yml"
FREEZE_WORKFLOW = ROOT / ".github/workflows/candidate-v13-external-validity-v3-freeze.yml"


def main() -> int:
    compile_status = {}
    violations = []
    for path in FILES:
        try:
            py_compile.compile(str(path), doraise=True)
            compile_status[str(path.relative_to(ROOT))] = "PASS"
        except Exception as exc:
            compile_status[str(path.relative_to(ROOT))] = f"FAIL:{type(exc).__name__}:{exc}"
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == CANDIDATE_MODULE or alias.name.endswith(".candidate_v13"):
                        violations.append(f"{path.name}: static import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == CANDIDATE_MODULE or module.endswith(".candidate_v13"):
                    violations.append(f"{path.name}: static from-import {module}")
    candidate_hash = hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()
    candidate_blind = CANDIDATE_MODULE not in sys.modules and candidate_hash == EXPECTED
    formal_text = FORMAL_WORKFLOW.read_text(encoding="utf-8") if FORMAL_WORKFLOW.exists() else ""
    freeze_text = FREEZE_WORKFLOW.read_text(encoding="utf-8") if FREEZE_WORKFLOW.exists() else ""
    workflow_dispatch_absent = "workflow_dispatch" not in formal_text
    formal_auth_trigger = "formal-authorization-lock-v3.json" in formal_text
    freeze_is_read_only = "contents: read" in freeze_text and "contents: write" not in freeze_text
    formal_runner_qa = (
        all(v == "PASS" for v in compile_status.values())
        and not violations
        and candidate_blind
        and FORMAL_WORKFLOW.exists()
        and FREEZE_WORKFLOW.exists()
        and workflow_dispatch_absent
        and formal_auth_trigger
        and freeze_is_read_only
    )

    formal_path = OUT / "formal-infrastructure-qualification.json"
    formal = json.loads(formal_path.read_text(encoding="utf-8")) if formal_path.exists() else {}
    formal.update({
        "formal_runner_compile": compile_status,
        "formal_runner_static_candidate_import_violations": violations,
        "formal_runner_candidate_firewall": "PASS" if candidate_blind else "FAIL",
        "formal_sequence_workflow_dispatch_absent": workflow_dispatch_absent,
        "formal_sequence_authorization_lock_trigger": formal_auth_trigger,
        "freeze_workflow_read_only_verification": freeze_is_read_only,
        "real_formal_runner_qa": "PASS" if formal_runner_qa else "FAIL",
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
        "status": "PASS" if formal_runner_qa and formal.get("evaluator_qa", {}).get("pass") else "FAIL",
    })
    formal_path.write_text(json.dumps(formal, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    infra_path = OUT / "infrastructure-qualification.json"
    infra = json.loads(infra_path.read_text(encoding="utf-8"))
    infra["gates"]["FORMAL_RUNNER_QA_PASS"] = formal_runner_qa and formal["status"] == "PASS"
    infra["status"] = "PASS" if all(bool(v) for v in infra["gates"].values()) else "FAIL"
    infra["formal_authorized"] = infra["status"] == "PASS"
    infra["candidate_v13_imported"] = False
    infra["candidate_v13_invoked"] = False
    infra_path.write_text(json.dumps(infra, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": infra["status"], "FORMAL_RUNNER_QA_PASS": infra["gates"]["FORMAL_RUNNER_QA_PASS"]}, sort_keys=True))
    return 0 if infra["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
