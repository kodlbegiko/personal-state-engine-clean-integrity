from __future__ import annotations

"""Candidate-blind qualification of the frozen formal execution infrastructure."""

import ast
import importlib.util
import json
import py_compile
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity-v2/formal-infrastructure-qualification.json"
FILES = [
    ROOT / "scripts/candidate_v13_external_validity_v2_allocation_runtime.py",
    ROOT / "scripts/candidate_v13_external_validity_v2_formal_materializer.py",
    ROOT / "scripts/candidate_v13_external_validity_v2_evaluator.py",
    ROOT / "scripts/candidate_v13_external_validity_v2_formal_runner.py",
    ROOT / "scripts/candidate_v13_external_validity_v2_formal_sequence.py",
]
CANDIDATE_MODULE = "personal_state_engine.candidate_v13"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def static_candidate_import_audit() -> dict[str, Any]:
    violations = []
    for path in FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == CANDIDATE_MODULE:
                        violations.append(f"{path.name}: static import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "") == CANDIDATE_MODULE:
                    violations.append(f"{path.name}: static from-import {node.module}")
    return {"violations": violations, "pass": not violations}


def synthetic_materializer_test(materializer: Any) -> dict[str, Any]:
    bases = []
    for i in range(12):
        bases.append({
            "source": "synthetic-source",
            "id": f"synthetic:{i}",
            "domain": "D6",
            "query": f"Synthetic query {i}",
            "gold": [f"Synthetic source-native memory unit {i}"],
            "subject": "same-subject" if i < 8 else f"subject-{i}",
            "relation": "same-relation" if i < 6 else f"relation-{i}",
            "flags": {f"N{x}": True for x in range(1, 13)},
        })
    revisions = {"synthetic-source": "0" * 40}
    assignments = [
        {"source":"synthetic-source","id":"synthetic:0","domain":"D6","primary_family":"N1","no_evidence":False},
        {"source":"synthetic-source","id":"synthetic:1","domain":"D6","primary_family":"N10","no_evidence":True},
    ]
    cases, summary = materializer.materialize_stage(assignments, bases, revisions, 42018)
    answerable = cases[0]
    no_evidence = cases[1]
    checks = {
        "case_count": len(cases) == 2,
        "answerable_gold_present": bool(answerable["relevant_memory_ids"]) and set(answerable["relevant_memory_ids"]).issubset({m["id"] for m in answerable["memories"]}),
        "no_evidence_runtime_gold_empty": no_evidence["relevant_memory_ids"] == [],
        "no_evidence_withheld_gold_private": bool(no_evidence["withheld_gold_ids"]),
        "memory_min": min(len(c["memories"]) for c in cases) >= 5,
        "memory_max": max(len(c["memories"]) for c in cases) <= 80,
        "minimum_distractors": all(len([m for m in c["memories"] if m["id"] not in set(c["relevant_memory_ids"])]) >= 4 for c in cases),
        "deterministic_digest": summary["status"] == "PASS" and bool(summary["transformation_digest_sha256"]),
    }
    return {"checks": checks, "pass": all(checks.values())}


def synthetic_evaluator_test(evaluator: Any) -> dict[str, Any]:
    policy = json.loads((ROOT / "docs/research/candidate-v13-external-validity-v2/evaluation-policy-v2.json").read_text(encoding="utf-8"))
    cases = []
    families = [f"N{i}" for i in range(1, 13)]
    # 384 = 8 domains × 48 = 12 families × 32. Exactly 240 answerable / 144 no-evidence.
    for i in range(384):
        answerable = i < 240
        gold_id = f"gold-{i}"
        memories = [{"id": gold_id, "text": f"Gold {i}", "timestamp": None}]
        memories.extend({"id": f"d-{i}-{j}", "text": f"Distractor {i}-{j}", "timestamp": None} for j in range(4))
        cases.append({
            "source_dataset": "synthetic-source",
            "domain": f"D{(i % 8) + 1}",
            "primary_family": families[i % 12],
            "query": f"Synthetic evaluator query {i}",
            "memories": memories,
            "answerable": answerable,
            "relevant_memory_ids": [gold_id] if answerable else [],
        })
    # Reorder answerability within each domain/family is not relevant to aggregate quotas.
    def oracle(runtime: dict[str, Any], k: int) -> list[str]:
        qid = int(runtime["query"].rsplit(" ", 1)[-1])
        return [f"gold-{qid}"] if qid < 240 else []
    result = evaluator.evaluate("ev_a_v2", cases, oracle, policy)
    checks = {
        "status_pass": result["status"] == "PASS",
        "coverage_one": result["coverage"] == 1.0,
        "invalid_zero": result["invalid_rate"] == 0.0,
        "determinism_pass": result["integrity"]["determinism"] == "PASS",
        "candidate_source_pass": result["integrity"]["candidate_source_invariant"] == "PASS",
    }
    return {"checks": checks, "pass": all(checks.values()), "status": result["status"]}


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if CANDIDATE_MODULE in sys.modules:
        raise RuntimeError("CANDIDATE_FIREWALL_FAIL: Candidate-v13 already imported")

    compile_results = {}
    for path in FILES:
        try:
            py_compile.compile(str(path), doraise=True)
            compile_results[str(path.relative_to(ROOT))] = "PASS"
        except Exception as exc:
            compile_results[str(path.relative_to(ROOT))] = f"FAIL:{type(exc).__name__}:{exc}"

    static_audit = static_candidate_import_audit()
    allocation = load("pse_v2_allocation_runtime_qa", FILES[0])
    runtime_selection = allocation.aggregate_check()
    materializer = load("pse_v2_formal_materializer_qa", FILES[1])
    evaluator = load("pse_v2_formal_evaluator_qa", FILES[2])
    materializer_test = synthetic_materializer_test(materializer)
    evaluator_test = synthetic_evaluator_test(evaluator)

    candidate_still_blind = CANDIDATE_MODULE not in sys.modules
    gates = {
        "PY_COMPILE_PASS": all(v == "PASS" for v in compile_results.values()),
        "STATIC_CANDIDATE_IMPORT_AUDIT_PASS": static_audit["pass"],
        "RUNTIME_SELECTION_DIGEST_PASS": runtime_selection["status"] == "PASS",
        "SYNTHETIC_FORMAL_MATERIALIZER_PASS": materializer_test["pass"],
        "SYNTHETIC_EVALUATOR_PASS": evaluator_test["pass"],
        "CANDIDATE_FIREWALL_PASS": candidate_still_blind,
    }
    result = {
        "schema_version": "candidate-v13-external-validity-v2-formal-infrastructure-qualification-v1",
        "status": "PASS" if all(gates.values()) else "FAIL",
        "candidate_v13_imported": not candidate_still_blind,
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "gates": gates,
        "compile": compile_results,
        "static_candidate_import_audit": static_audit,
        "runtime_selection": runtime_selection,
        "synthetic_materializer": materializer_test,
        "synthetic_evaluator": evaluator_test,
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
