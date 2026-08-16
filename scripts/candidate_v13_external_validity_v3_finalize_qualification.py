from __future__ import annotations

"""Finalize v3 infrastructure qualification with real formal-runner QA."""

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
    ROOT / "scripts/candidate_v13_external_validity_v3_evaluator.py",
    ROOT / "scripts/candidate_v13_external_validity_v3_formal_runner.py",
    ROOT / "scripts/candidate_v13_external_validity_v3_formal_sequence.py",
    ROOT / "scripts/candidate_v13_external_validity_v3_freeze.py",
]
CANDIDATE = ROOT / "src/personal_state_engine/candidate_v13.py"
EXPECTED = "b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838"


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
                    if alias.name == "personal_state_engine.candidate_v13" or alias.name.endswith(".candidate_v13"):
                        violations.append(f"{path.name}: static import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "personal_state_engine.candidate_v13" or mod.endswith(".candidate_v13"):
                    violations.append(f"{path.name}: static from-import {mod}")
    candidate_hash = hashlib.sha256(CANDIDATE.read_bytes()).hexdigest()
    candidate_blind = "personal_state_engine.candidate_v13" not in sys.modules and candidate_hash == EXPECTED
    workflow = ROOT / ".github/workflows/candidate-v13-external-validity-v3-formal-sequence.yml"
    workflow_text = workflow.read_text(encoding="utf-8") if workflow.exists() else ""
    workflow_dispatch_absent = "workflow_dispatch" not in workflow_text
    qa_pass = all(v == "PASS" for v in compile_status.values()) and not violations and candidate_blind and workflow.exists() and workflow_dispatch_absent

    formal_path = OUT / "formal-infrastructure-qualification.json"
    formal = json.loads(formal_path.read_text(encoding="utf-8")) if formal_path.exists() else {}
    formal.update({
        "formal_runner_compile": compile_status,
        "formal_runner_static_candidate_import_violations": violations,
        "formal_runner_candidate_firewall": "PASS" if candidate_blind else "FAIL",
        "formal_sequence_workflow_dispatch_absent": workflow_dispatch_absent,
        "real_formal_runner_qa": "PASS" if qa_pass else "FAIL",
        "status": "PASS" if qa_pass and formal.get("evaluator_qa", {}).get("pass") else "FAIL",
    })
    formal_path.write_text(json.dumps(formal, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    infra_path = OUT / "infrastructure-qualification.json"
    infra = json.loads(infra_path.read_text(encoding="utf-8"))
    infra["gates"]["FORMAL_RUNNER_QA_PASS"] = qa_pass and formal["status"] == "PASS"
    infra["status"] = "PASS" if all(bool(v) for v in infra["gates"].values()) else "FAIL"
    infra["formal_authorized"] = infra["status"] == "PASS"
    infra["candidate_v13_imported"] = False
    infra["candidate_v13_invoked"] = False
    infra_path.write_text(json.dumps(infra, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": infra["status"], "FORMAL_RUNNER_QA_PASS": infra["gates"]["FORMAL_RUNNER_QA_PASS"]}, sort_keys=True))
    return 0 if infra["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
