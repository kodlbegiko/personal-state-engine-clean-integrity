from __future__ import annotations

"""Candidate-blind formal-runner QA for the event-independent v4 orchestration."""

import ast
import hashlib
import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity-v4"
WORKFLOW = ROOT / ".github/workflows/candidate-v13-external-validity-v4.yml"
CANDIDATE = ROOT / "src/personal_state_engine/candidate_v13.py"
EXPECTED = "b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838"
FILES = [
    ROOT / "scripts/bootstrap_candidate_v13_external_validity_v4.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_fix_names.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_core.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_materializer.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_contamination.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_qualification_runner.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_evaluator.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_formal_runner.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_formal_sequence.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_freeze.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_infrastructure_qualification.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_prequalification.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_launch_path_qa.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_lock_preregistration.py",
    ROOT / "scripts/candidate_v13_external_validity_v4_final_integrity_audit.py",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if "personal_state_engine.candidate_v13" in sys.modules:
        raise RuntimeError("Candidate imported before v4 formal-runner QA")
    compile_status = {}
    static_import_violations = []
    prefreeze = [p for p in FILES if p.name not in {"candidate_v13_external_validity_v4_formal_runner.py", "candidate_v13_external_validity_v4_formal_sequence.py"}]
    for path in FILES:
        try:
            py_compile.compile(str(path), doraise=True)
            compile_status[str(path.relative_to(ROOT))] = "PASS"
        except Exception as exc:
            compile_status[str(path.relative_to(ROOT))] = f"FAIL:{type(exc).__name__}:{exc}"
    for path in prefreeze:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "personal_state_engine.candidate_v13" or alias.name.endswith(".candidate_v13"):
                        static_import_violations.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "personal_state_engine.candidate_v13" or module.endswith(".candidate_v13"):
                    static_import_violations.append(f"{path.name}: from {module}")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    checks = {
        "candidate_hash_match": sha256(CANDIDATE) == EXPECTED,
        "candidate_not_imported": "personal_state_engine.candidate_v13" not in sys.modules,
        "all_v4_scripts_compile": all(v == "PASS" for v in compile_status.values()),
        "prefreeze_static_candidate_imports_absent": not static_import_violations,
        "workflow_dispatch_absent": "workflow_dispatch" not in workflow,
        "workflow_run_trigger_absent": "workflow_run:" not in workflow,
        "repository_dispatch_absent": "repository_dispatch" not in workflow,
        "single_execution_job": "  execute-v4:" in workflow,
        "freeze_before_formal_in_same_workflow": workflow.find("- name: Freeze and authorize") < workflow.find("- name: Run one-shot formal sequence"),
        "formal_runner_has_one_shot_guard": "FORMAL_RERUN_DETECTED" in (ROOT / "scripts/candidate_v13_external_validity_v4_formal_runner.py").read_text(encoding="utf-8"),
        "formal_runner_requires_authorization": "verify_freeze()" in (ROOT / "scripts/candidate_v13_external_validity_v4_formal_runner.py").read_text(encoding="utf-8"),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    formal_path = OUT / "formal-infrastructure-qualification.json"
    formal = json.loads(formal_path.read_text(encoding="utf-8")) if formal_path.exists() else {}
    formal.update({
        "schema_version": "candidate-v13-external-validity-v4-formal-infrastructure-qualification-v2",
        "compile": compile_status,
        "prefreeze_static_candidate_import_violations": static_import_violations,
        "event_independent_formal_runner_checks": checks,
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
        "real_formal_runner_qa": status,
        "status": status if formal.get("evaluator_qa", {}).get("pass", True) else "FAIL",
    })
    formal_path.write_text(json.dumps(formal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    infra_path = OUT / "infrastructure-qualification.json"
    infra = json.loads(infra_path.read_text(encoding="utf-8"))
    infra.setdefault("gates", {})["FORMAL_RUNNER_QA_PASS"] = formal["status"] == "PASS"
    infra["status"] = "PASS" if all(bool(v) for v in infra["gates"].values()) else "FAIL"
    infra["formal_authorized"] = infra["status"] == "PASS"
    infra["candidate_v13_imported"] = False
    infra["candidate_v13_invoked"] = False
    infra_path.write_text(json.dumps(infra, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": infra["status"], "checks": checks}, sort_keys=True))
    return 0 if infra["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
