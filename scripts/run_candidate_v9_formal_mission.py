from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "research/candidate-v9-fresh-lineage"
V8_TERMINAL = "86c440fc487c46a1e603144177e666d32a52e725"
DEV_SHA = "a398b718bd961482e7817b65f38e784ff43f5849301291ffd985485a921fd704"
FROZEN_FILES = {
    "source": ROOT / "src/personal_state_engine/candidate_v9.py",
    "config": ROOT / "experiments/configs/candidate-v9-v1.json",
    "generator": ROOT / "scripts/generate_candidate_v9_benchmark.py",
    "evaluator": ROOT / "scripts/evaluate_candidate_v9.py",
    "development_dataset": ROOT / "experiments/benchmarks/candidate-v9-development-v1.json",
    "development_result": ROOT / "results/candidate-v9/development-summary-iteration-3.json",
    "formal_runner": ROOT / "scripts/run_candidate_v9_formal_mission.py",
    "preregistration": ROOT / "docs/research/candidate-v9/preregistration.md",
    "evaluation_protocol": ROOT / "docs/research/candidate-v9/evaluation-protocol.md",
    "benchmark_design": ROOT / "docs/research/candidate-v9/fresh-benchmark-design.md",
    "architecture_selection": ROOT / "docs/research/candidate-v9/architecture-selection.md",
}
STAGES = {
    "protected": {"cases": 300, "answerable": 190, "negative": 110, "seed": 2026081511},
    "confirmatory": {"cases": 360, "answerable": 220, "negative": 140, "seed": 2026081513},
    "final": {"cases": 480, "answerable": 300, "negative": 180, "seed": 2026081515},
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str] | str, *, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=ROOT, shell=isinstance(cmd, str), text=True, capture_output=capture)
    if capture and result.stdout:
        print(result.stdout.strip())
    if capture and result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {cmd}")
    return result


def git(*args: str, capture: bool = True) -> str:
    result = run(["git", *args], capture=capture)
    return result.stdout.strip() if capture else ""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def commit(paths: list[Path], message: str) -> str:
    rels = [str(p.relative_to(ROOT)) for p in paths]
    run(["git", "add", *rels])
    run(["git", "commit", "-m", message])
    head = git("rev-parse", "HEAD")
    run(["git", "push", "origin", f"HEAD:{BRANCH}"])
    return head


def frozen_hashes() -> dict[str, str]:
    return {name: sha(path) for name, path in FROZEN_FILES.items()}


def verify_v8_integrity() -> None:
    remote = git("rev-parse", "origin/research/candidate-v8-fresh-lineage")
    if remote != V8_TERMINAL:
        raise RuntimeError(f"Candidate-v8 branch moved: {remote}")
    protected_paths = [
        "docs/research/candidate-v8", "results/candidate-v8",
        "src/personal_state_engine/candidate_v8.py",
        "scripts/generate_candidate_v8_benchmark.py", "scripts/evaluate_candidate_v8.py",
        "experiments/configs/candidate-v8-v1.json",
    ]
    diff = git("diff", "--name-only", V8_TERMINAL, "HEAD", "--", *protected_paths)
    if diff.strip():
        raise RuntimeError(f"Candidate-v8 immutable paths changed: {diff}")


def verify_leakage_boundary() -> None:
    tree = ast.parse(FROZEN_FILES["source"].read_text())
    allowed_case_keys = {"query", "memories"}
    forbidden_hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "case":
            sl = node.slice
            if isinstance(sl, ast.Constant) and isinstance(sl.value, str) and sl.value not in allowed_case_keys:
                forbidden_hits.append(sl.value)
    if forbidden_hits:
        raise RuntimeError(f"forbidden benchmark case metadata access: {sorted(set(forbidden_hits))}")


def verify_frozen_identity(expected: dict[str, str]) -> None:
    actual = frozen_hashes()
    mismatches = {k: {"expected": expected[k], "actual": actual[k]} for k in expected if actual.get(k) != expected[k]}
    if mismatches:
        raise RuntimeError(f"frozen identity mismatch: {json.dumps(mismatches, sort_keys=True)}")
    verify_v8_integrity()
    verify_leakage_boundary()


def reproduce_development() -> dict[str, Any]:
    if sha(FROZEN_FILES["development_dataset"]) != DEV_SHA:
        raise RuntimeError("development surface identity mismatch")
    tmp = ROOT / ".candidate-v9-development-repro.json"
    run([sys.executable, "scripts/evaluate_candidate_v9.py", str(FROZEN_FILES["development_dataset"].relative_to(ROOT)), str(tmp.relative_to(ROOT)), "--stage", "development", "--no-fail"])
    reproduced = json.loads(tmp.read_text())
    committed = json.loads(FROZEN_FILES["development_result"].read_text())
    tmp.unlink(missing_ok=True)
    for key in ("candidate_v2", "candidate_v9", "paired_bootstrap", "checks", "verdict"):
        if reproduced[key] != committed[key]:
            raise RuntimeError(f"development reproduction mismatch at {key}")
    if reproduced["verdict"] != "PASS":
        raise RuntimeError("development no longer passes")
    return reproduced


def make_freeze(test_record: str) -> tuple[str, dict[str, str]]:
    verify_v8_integrity()
    verify_leakage_boundary()
    dev = reproduce_development()
    hashes = frozen_hashes()
    manifest = ROOT / "results/candidate-v9/development-freeze-manifest-v1.json"
    tests = ROOT / "results/candidate-v9/development-freeze-test-record-v1.json"
    payload = {
        "schema_version": "candidate-v9-development-freeze-v1",
        "candidate": "Candidate-v9",
        "branch": BRANCH,
        "freeze_parent_head": git("rev-parse", "HEAD"),
        "frozen_at": now(),
        "frozen_hashes": hashes,
        "development_benchmark_sha256": DEV_SHA,
        "development_verdict": dev["verdict"],
        "development_metrics": dev["candidate_v9"],
        "development_bootstrap": dev["paired_bootstrap"],
        "stage_specs": STAGES,
        "protected_execution_count": 0,
        "confirmatory_execution_count": 0,
        "final_execution_count": 0,
        "rerun_flags": {"protected": False, "confirmatory": False, "final": False},
        "candidate_v8_terminal_commit": V8_TERMINAL,
        "candidate_v8_immutable": True,
        "retired_99_case_semantic_payload_opened": False,
        "paid_api_cost_usd": 0,
    }
    write_json(manifest, payload)
    write_json(tests, {"full_test_output": test_record.strip(), "workflow_run_id": os.environ.get("GITHUB_RUN_ID"), "recorded_at": now()})
    freeze_commit = commit([manifest, tests], "candidate-v9: freeze before protected validation")
    return freeze_commit, hashes


def signatures(path: Path) -> set[str]:
    payload = json.loads(path.read_text())
    return {str(c.get("surface_sha256")) for c in payload["cases"] if c.get("surface_sha256")}


def normalized_signature(case: dict[str, Any]) -> str:
    parts = [str(case["query"]).strip().casefold()] + sorted(str(m["text"]).strip().casefold() for m in case["memories"])
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def freshness_audit(stage: str, dataset: Path) -> dict[str, Any]:
    payload = json.loads(dataset.read_text())
    spec = STAGES[stage]
    if payload["case_count"] != spec["cases"] or payload["answerable_count"] != spec["answerable"] or payload["no_evidence_count"] != spec["negative"]:
        raise RuntimeError(f"{stage} count mismatch")
    if payload["seed"] != spec["seed"]:
        raise RuntimeError(f"{stage} seed mismatch")
    stage_sigs = signatures(dataset)
    if len(stage_sigs) != spec["cases"]:
        raise RuntimeError(f"{stage} duplicate or missing surface signatures")

    prior_paths = [FROZEN_FILES["development_dataset"]]
    if stage in {"confirmatory", "final"}:
        prior_paths.append(ROOT / "experiments/benchmarks/candidate-v9-protected-v1.json")
    if stage == "final":
        prior_paths.append(ROOT / "experiments/benchmarks/candidate-v9-confirmatory-v1.json")
    overlaps: dict[str, int] = {}
    for p in prior_paths:
        ov = stage_sigs & signatures(p)
        overlaps[p.name] = len(ov)
        if ov:
            raise RuntimeError(f"{stage} overlaps earlier Candidate-v9 surface {p.name}")

    # Historical Candidate-v8 semantics were legally opened only after Candidate-v9 preregistration.
    # Use them here only as a one-way exact-duplicate audit; they never generate or modify Candidate-v9 cases.
    v8_path = ROOT / "experiments/benchmarks/candidate-v8-protected-validation-v1.json"
    v8 = json.loads(v8_path.read_text())
    v8_sigs = {normalized_signature(c) for c in v8["cases"]}
    hist_overlap = stage_sigs & v8_sigs
    if hist_overlap:
        raise RuntimeError(f"{stage} exact semantic duplicate with retired Candidate-v8 protected surface")

    ids = [c["id"] for c in payload["cases"]]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"{stage} duplicate IDs")
    return {
        "stage": stage,
        "case_count": spec["cases"],
        "answerable_count": spec["answerable"],
        "no_evidence_count": spec["negative"],
        "seed": spec["seed"],
        "namespace": payload["namespace"],
        "dataset_sha256": sha(dataset),
        "unique_surface_signatures": len(stage_sigs),
        "overlap_with_prior_candidate_v9": overlaps,
        "exact_overlap_with_v8_historical_protected": len(hist_overlap),
        "payload_manually_inspected": False,
        "historical_payload_used_as_template": False,
    }


def stage_paths(stage: str) -> dict[str, Path]:
    return {
        "lock": ROOT / f"results/candidate-v9/{stage}-lock-v1.json",
        "dataset": ROOT / f"experiments/benchmarks/candidate-v9-{stage}-v1.json",
        "manifest": ROOT / f"results/candidate-v9/{stage}-materialization-manifest-v1.json",
        "authorization": ROOT / f"results/candidate-v9/{stage}-authorization-v1.json",
        "result": ROOT / f"results/candidate-v9/{stage}-summary-v1.json",
        "execution": ROOT / f"results/candidate-v9/{stage}-execution-record-v1.json",
    }


def formal_stage(stage: str, freeze_commit: str, hashes: dict[str, str]) -> tuple[bool, dict[str, Any], dict[str, str]]:
    verify_frozen_identity(hashes)
    paths = stage_paths(stage)
    for p in paths.values():
        if p.exists():
            raise RuntimeError(f"refusing formal stage {stage}: pre-existing formal artifact {p.relative_to(ROOT)}")

    lock_payload = {
        "schema_version": f"candidate-v9-{stage}-lock-v1",
        "stage": stage,
        "locked_at": now(),
        "freeze_commit": freeze_commit,
        "frozen_hashes": hashes,
        "formal_execution_count": 0,
        "rerun": False,
        "payload_manually_inspected": False,
        "semantic_payload_accessed": False,
        "spec": STAGES[stage],
    }
    write_json(paths["lock"], lock_payload)
    lock_commit = commit([paths["lock"]], f"candidate-v9: lock fresh {stage} evaluation")

    verify_frozen_identity(hashes)
    run([sys.executable, "scripts/generate_candidate_v9_benchmark.py", "--stage", stage, "--output", str(paths["dataset"].relative_to(ROOT))])
    audit = freshness_audit(stage, paths["dataset"])
    manifest_payload = {
        "schema_version": f"candidate-v9-{stage}-materialization-v1",
        "stage": stage,
        "lock_commit": lock_commit,
        "materialized_at": now(),
        "freshness_audit": audit,
        "dataset_sha256": sha(paths["dataset"]),
        "frozen_hashes": hashes,
        "formal_execution_count": 0,
        "rerun": False,
        "payload_manually_inspected": False,
        "semantic_payload_executed": False,
    }
    write_json(paths["manifest"], manifest_payload)
    materialization_commit = commit([paths["dataset"], paths["manifest"]], f"candidate-v9: materialize fresh {stage} evaluation")

    verify_frozen_identity(hashes)
    authorization_payload = {
        "schema_version": f"candidate-v9-{stage}-authorization-v1",
        "stage": stage,
        "authorized_at": now(),
        "lock_commit": lock_commit,
        "materialization_commit": materialization_commit,
        "dataset_sha256": sha(paths["dataset"]),
        "frozen_hashes": hashes,
        "formal_execution_count": 0,
        "rerun": False,
        "payload_manually_inspected": False,
        "authorized_for_exactly_one_semantic_execution": True,
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
    }
    write_json(paths["authorization"], authorization_payload)
    authorization_commit = commit([paths["authorization"]], f"candidate-v9: authorize {stage} evaluation once")

    verify_frozen_identity(hashes)
    # The sole semantic execution for this stage. No retry loop exists.
    result = run([
        sys.executable, "scripts/evaluate_candidate_v9.py",
        str(paths["dataset"].relative_to(ROOT)), str(paths["result"].relative_to(ROOT)),
        "--stage", stage, "--no-fail",
    ], check=False)
    if result.returncode not in {0}:
        raise RuntimeError(f"formal evaluator infrastructure failure at {stage}: {result.returncode}")
    summary = json.loads(paths["result"].read_text())
    execution_payload = {
        "schema_version": f"candidate-v9-{stage}-execution-record-v1",
        "stage": stage,
        "executed_at": now(),
        "lock_commit": lock_commit,
        "materialization_commit": materialization_commit,
        "authorization_commit": authorization_commit,
        "dataset_sha256": sha(paths["dataset"]),
        "result_sha256": sha(paths["result"]),
        "frozen_hashes": hashes,
        "formal_execution_count": 1,
        "rerun": False,
        "payload_manually_inspected": False,
        "semantic_payload_executed": True,
        "verdict": summary["verdict"],
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "monetary_cost_usd": 0,
    }
    write_json(paths["execution"], execution_payload)
    result_commit = commit([paths["result"], paths["execution"]], f"candidate-v9: {stage} evaluation {summary['verdict']}")
    return summary["verdict"] == "PASS", summary, {
        "lock_commit": lock_commit,
        "materialization_commit": materialization_commit,
        "authorization_commit": authorization_commit,
        "result_commit": result_commit,
    }


def load_if(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text()) if path.exists() else None


def terminalize(
    terminal_state: str,
    freeze_commit: str | None,
    hashes: dict[str, str] | None,
    stage_summaries: dict[str, dict[str, Any]],
    stage_commits: dict[str, dict[str, str]],
    test_record: str,
    integrity_deviations: list[dict[str, Any]],
) -> str:
    protected_exec = load_if(ROOT / "results/candidate-v9/protected-execution-record-v1.json")
    confirm_exec = load_if(ROOT / "results/candidate-v9/confirmatory-execution-record-v1.json")
    final_exec = load_if(ROOT / "results/candidate-v9/final-execution-record-v1.json")
    historical = load_if(ROOT / "results/candidate-v9/historical-diagnostic-access-v1.json") or {}
    current_head = git("rev-parse", "HEAD")
    snapshot_path = ROOT / "results/candidate-v9/terminal-snapshot.json"
    report_path = ROOT / "docs/research/candidate-v9/terminal-report.md"
    next_action = (
        "Candidate-v9 research objective achieved"
        if terminal_state == "CANDIDATE_V9_FINAL_GATE_F_PASS"
        else "STOP; Candidate-v10 fresh lineage required for further semantic research"
    )
    snapshot = {
        "schema_version": "candidate-v9-terminal-snapshot-v1",
        "terminal_state": terminal_state,
        "branch": BRANCH,
        "HEAD": current_head,
        "head_semantics": "HEAD immediately before terminal evidence commit",
        "parent_v8_terminal_commit": V8_TERMINAL,
        "candidate_v9_source_sha256": (hashes or {}).get("source"),
        "generator_sha256": (hashes or {}).get("generator"),
        "evaluator_sha256": (hashes or {}).get("evaluator"),
        "config_sha256": (hashes or {}).get("config"),
        "development_result": load_if(ROOT / "results/candidate-v9/development-summary-iteration-3.json"),
        "development_freeze_commit": freeze_commit,
        "protected_dataset_hash": (protected_exec or {}).get("dataset_sha256"),
        "protected_materialization_commit": stage_commits.get("protected", {}).get("materialization_commit"),
        "protected_authorization_commit": stage_commits.get("protected", {}).get("authorization_commit"),
        "protected_execution_count": (protected_exec or {}).get("formal_execution_count", 0),
        "protected_result": stage_summaries.get("protected"),
        "confirmatory_execution_count": (confirm_exec or {}).get("formal_execution_count", 0),
        "confirmatory_result": stage_summaries.get("confirmatory"),
        "final_gate_f_execution_count": (final_exec or {}).get("formal_execution_count", 0),
        "final_gate_f_result": stage_summaries.get("final"),
        "rerun_flags": {
            "protected": (protected_exec or {}).get("rerun", False),
            "confirmatory": (confirm_exec or {}).get("rerun", False),
            "final": (final_exec or {}).get("rerun", False),
        },
        "historical_diagnostic_accesses": historical,
        "old_99_case_semantic_payload_opened": False,
        "monetary_cost_usd": 0,
        "full_test_output": test_record.strip(),
        "workflow_run_ids": [os.environ.get("GITHUB_RUN_ID")],
        "integrity_deviations": integrity_deviations,
        "next_legal_action": next_action,
        "recorded_at": now(),
    }
    write_json(snapshot_path, snapshot)

    dev = snapshot["development_result"] or {}
    devm = dev.get("candidate_v9", {})
    def stage_text(name: str) -> str:
        s = stage_summaries.get(name)
        if not s:
            return "NOT EXECUTED"
        m=s["candidate_v9"]
        b=s["paired_bootstrap"]
        return (
            f"cases={m['answerable_count'] + m['no_evidence_count']}; MRR={m['MRR']}; R@1={m['R@1']}; "
            f"R@3={m['R@3']}; R@5={m['R@5']}; recall={m['answerable_recall']}; "
            f"false_abstention={m['false_abstention']}; false_retrieval={m['false_retrieval']}; "
            f"abstention_accuracy={m['abstention_accuracy']}; order_violations={m['order_preservation_violations']}; "
            f"bootstrap_delta={b['delta']}; ci95={b['ci95']}; noninferiority={b['noninferiority']}; verdict={s['verdict']}"
        )
    deviations_md = "\n".join(f"- {json.dumps(x, sort_keys=True)}" for x in integrity_deviations) or "- None."
    report = f"""# Candidate-v9 Terminal Report

## 1. Terminal State

`{terminal_state}`

## 2. Branch / HEAD

- Branch: `{BRANCH}`
- HEAD at terminal snapshot generation: `{current_head}`
- Terminal evidence commit follows this recorded semantic HEAD.

## 3. Candidate-v8 Integrity

Verified. Candidate-v8 terminal branch remains `{V8_TERMINAL}` and frozen Candidate-v8 research/result/source/config paths were unchanged throughout Candidate-v9 execution.

## 4. Candidate-v9 Architecture

Typed Query Intent + Relation Canonicalization + Relation-Range Value Binding + inherited hard safety blockers. Candidate-v2 is the sole ranker; Candidate-v9 performs independent per-memory certification and returns an order-preserving subsequence.

## 5. Candidate-v8 Failure Diagnosis

All four historical Candidate-v8 protected false abstentions were relation-realization failures. Subject, value-bearing, temporal compatibility, and blocker checks were not the limiting mechanism. The historical protected surface was opened only after Candidate-v9 preregistration and was excluded from all Candidate-v9 formal evaluation.

## 6. Development

cases={devm.get('answerable_count', 0) + devm.get('no_evidence_count', 0)}; MRR={devm.get('MRR')}; R@1={devm.get('R@1')}; R@3={devm.get('R@3')}; R@5={devm.get('R@5')}; recall={devm.get('answerable_recall')}; false_abstention={devm.get('false_abstention')}; false_retrieval={devm.get('false_retrieval')}; abstention_accuracy={devm.get('abstention_accuracy')}; order_violations={devm.get('order_preservation_violations')}; bootstrap={dev.get('paired_bootstrap')}; verdict={dev.get('verdict')}; tests=`{test_record.strip()}`.

## 7. Protected Validation

{stage_text('protected')}

## 8. Confirmatory

{stage_text('confirmatory')}

## 9. Fresh Final Gate F

{stage_text('final')}

## 10. Formal Execution Counts

- protected: {(protected_exec or {}).get('formal_execution_count', 0)}
- confirmatory: {(confirm_exec or {}).get('formal_execution_count', 0)}
- final: {(final_exec or {}).get('formal_execution_count', 0)}

All recorded rerun flags are false.

## 11. Integrity Deviations

{deviations_md}

No deviation changed a formal benchmark after materialization or caused a formal semantic evaluation rerun. The retired 99-case Gate F semantic payload was not opened.

## 12. Research Conclusion

The only valid research conclusion is the terminal state above. Candidate-v9 success is claimed only if development, fresh protected, fresh confirmatory, and Fresh Final Gate F all pass their preregistered gates. Paid API cost was USD 0.

## 13. Next Legal Action

{next_action}
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    return commit([snapshot_path, report_path], f"candidate-v9: terminal {terminal_state}")


def main() -> int:
    if (ROOT / "results/candidate-v9/terminal-snapshot.json").exists():
        raise RuntimeError("Candidate-v9 already has terminal evidence; refusing rerun")
    verify_v8_integrity()
    verify_leakage_boundary()
    test_record = os.environ.get("CANDIDATE_V9_TEST_RECORD", "test record unavailable")
    integrity_deviations = []
    for run_id in ("31881331110", "31881376267"):
        p = ROOT / f"results/candidate-v9/predevelopment-generator-failure-run-{run_id}.json"
        if p.exists():
            integrity_deviations.append(json.loads(p.read_text()))

    freeze_commit: str | None = None
    hashes: dict[str, str] | None = None
    stage_summaries: dict[str, dict[str, Any]] = {}
    stage_commits: dict[str, dict[str, str]] = {}
    try:
        freeze_commit, hashes = make_freeze(test_record)
    except Exception as exc:
        integrity_deviations.append({"stage": "DEVELOPMENT_FREEZE", "failure": str(exc), "semantic_formal_payload_accessed": False})
        terminalize("CANDIDATE_V9_DEVELOPMENT_BLOCKED", freeze_commit, hashes, stage_summaries, stage_commits, test_record, integrity_deviations)
        raise

    for stage, fail_state in (
        ("protected", "CANDIDATE_V9_PROTECTED_VALIDATION_FAIL"),
        ("confirmatory", "CANDIDATE_V9_CONFIRMATORY_FAIL"),
        ("final", "CANDIDATE_V9_FINAL_GATE_F_FAIL"),
    ):
        passed, summary, commits = formal_stage(stage, freeze_commit, hashes)
        stage_summaries[stage] = summary
        stage_commits[stage] = commits
        if not passed:
            terminalize(fail_state, freeze_commit, hashes, stage_summaries, stage_commits, test_record, integrity_deviations)
            return 0

    terminalize("CANDIDATE_V9_FINAL_GATE_F_PASS", freeze_commit, hashes, stage_summaries, stage_commits, test_record, integrity_deviations)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
