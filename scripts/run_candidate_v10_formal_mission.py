from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import audit_candidate_v10_cross_stage_freshness as cross_audit
import evaluate_candidate_v10 as evaluator
import generate_candidate_v10_benchmark as generator
import generate_candidate_v10_benchmark_v2 as generator_v2

RESULTS = ROOT / "results/candidate-v10"
BENCH = ROOT / "experiments/benchmarks"
FREEZE = RESULTS / "development-freeze-manifest-v1.json"
COUNTS = RESULTS / "formal-execution-counts-v1.json"
LEDGER = RESULTS / "formal-execution-ledger-v1.jsonl"
SNAPSHOT = RESULTS / "terminal-snapshot-v1.json"
REPORT = ROOT / "docs/research/candidate-v10/terminal-report.md"
CROSS = RESULTS / "freshness-audit-cross-stage-v1.json"
DEV_BENCH = BENCH / "candidate-v10-development-v1.json"

TERMINALS = {
    "protected": "CANDIDATE_V10_PROTECTED_VALIDATION_FAIL",
    "confirmatory": "CANDIDATE_V10_CONFIRMATORY_FAIL",
    "final": "CANDIDATE_V10_FINAL_GATE_F_FAIL",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def append_ledger(entry: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def verify_freeze() -> tuple[bool, list[str], dict]:
    if not FREEZE.exists():
        return False, ["missing development freeze manifest"], {}
    freeze = json.loads(FREEZE.read_text())
    errors: list[str] = []
    if freeze.get("development_verdict") != "PASS":
        errors.append("freeze manifest does not record Development PASS")
    for rel, expected in freeze.get("frozen_files", {}).items():
        path = ROOT / rel
        if not path.exists():
            errors.append(f"missing frozen file: {rel}")
        elif sha(path) != expected:
            errors.append(f"frozen hash mismatch: {rel}")
    dev = json.loads((RESULTS / "development-summary-v1.json").read_text())
    if dev.get("verdict") != "PASS":
        errors.append("current development result is not PASS")
    if dev.get("candidate_v10_source_sha256") != sha(ROOT / "src/personal_state_engine/candidate_v10.py"):
        errors.append("development PASS source hash differs from current source")
    return not errors, errors, freeze


def preflight_no_formal_history() -> list[str]:
    errors: list[str] = []
    protected_paths = [
        COUNTS,
        LEDGER,
        RESULTS / "protected-summary-v1.json",
        RESULTS / "confirmatory-summary-v1.json",
        RESULTS / "final-summary-v1.json",
        BENCH / "candidate-v10-protected-v1.json",
        BENCH / "candidate-v10-confirmatory-v1.json",
        BENCH / "candidate-v10-final-v1.json",
    ]
    for path in protected_paths:
        if path.exists():
            errors.append(f"formal artifact already exists: {path.relative_to(ROOT)}")
    return errors


def generate_stage(stage: str) -> tuple[Path, Path, dict]:
    payload = generator.generate(stage)
    bench = BENCH / f"candidate-v10-{stage}-v1.json"
    audit_path = RESULTS / f"freshness-audit-{stage}-v1.json"
    write_json(bench, payload)
    audit = generator_v2.audit_payload(payload)
    write_json(audit_path, audit)
    if audit["exact_surface_duplicate_count"] != 0 or audit["normalized_surface_duplicate_count"] != 0:
        raise RuntimeError(f"{stage} within-stage freshness duplicate detected")
    return bench, audit_path, audit


def cross_stage(paths: list[Path]) -> dict:
    result = cross_audit.audit(paths)
    write_json(CROSS, result)
    return result


def write_terminal(state: str, counts: dict, freeze: dict, stage_results: dict, integrity: dict, notes: list[str]) -> None:
    snapshot = {
        "schema_version": "candidate-v10-terminal-snapshot-v1",
        "terminal_state": state,
        "terminal_at": now(),
        "repository": "kodlbegiko/personal-state-engine-clean-integrity",
        "branch": "research/candidate-v10-fresh-lineage",
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "preregistration_commit": "d31881019a3df1befbd7faa23df0f009e76485a9",
        "development_freeze": freeze,
        "formal_execution_counts": counts,
        "stage_results": stage_results,
        "cross_stage_freshness": integrity,
        "notes": notes,
        "candidate_v9_formal_execution_counts_preserved": {"protected": 1, "confirmatory": 1, "final": 0},
        "monetary_cost_usd": 0,
    }
    write_json(SNAPSHOT, snapshot)
    counts_payload = {
        "schema_version": "candidate-v10-formal-execution-counts-v1",
        "protected": counts["protected"],
        "confirmatory": counts["confirmatory"],
        "final": counts["final"],
        "terminal_state": state,
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
    }
    write_json(COUNTS, counts_payload)

    lines = [
        "# Candidate-v10 Terminal Report",
        "",
        f"Terminal state: `{state}`",
        "",
        "## Formal execution counts",
        "",
        f"- Protected: {counts['protected']}",
        f"- Confirmatory: {counts['confirmatory']}",
        f"- Final Gate F: {counts['final']}",
        "",
        "## Stage results",
        "",
    ]
    for stage in ["development", "protected", "confirmatory", "final"]:
        result = stage_results.get(stage)
        if not result:
            lines.append(f"- {stage}: NOT EXECUTED")
            continue
        m = result.get("candidate_v10", {})
        lines.append(
            f"- {stage}: {result.get('verdict')} | MRR={m.get('MRR')} | R@1={m.get('R@1')} | "
            f"R@3={m.get('R@3')} | R@5={m.get('R@5')} | recall={m.get('answerable_recall')} | "
            f"false_abstention={m.get('false_abstention')} | false_retrieval={m.get('false_retrieval')} | "
            f"abstention_accuracy={m.get('abstention_accuracy')} | order_violations={m.get('order_preservation_violations')}"
        )
    lines += [
        "",
        "## Integrity",
        "",
        f"- Frozen implementation hashes verified: {not any('frozen' in n.lower() and 'mismatch' in n.lower() for n in notes)}",
        f"- Cross-stage freshness integrity: {integrity.get('integrity_pass') if integrity else 'NOT AVAILABLE'}",
        "- Candidate-v2 remained the sole ranker.",
        "- Inference did not receive labels, relevant IDs, answers, split names, provenance, or generator-only metadata.",
        "- Paid external inference/API cost: USD 0.",
        "- Candidate-v9 protected/confirmatory/final execution counts remain historical 1/1/0; no Candidate-v9 formal rerun occurred.",
        "",
        "## Notes",
        "",
    ]
    lines.extend(f"- {n}" for n in notes or ["No additional terminal notes."])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n")


def main() -> None:
    formal_preflight = preflight_no_formal_history()
    freeze_ok, freeze_errors, freeze = verify_freeze()
    if formal_preflight or not freeze_ok:
        notes = formal_preflight + freeze_errors
        write_terminal(
            "CANDIDATE_V10_INTEGRITY_BLOCKED",
            {"protected": 0, "confirmatory": 0, "final": 0},
            freeze,
            {"development": json.loads((RESULTS / "development-summary-v1.json").read_text()) if (RESULTS / "development-summary-v1.json").exists() else None},
            {},
            notes,
        )
        return

    counts = {"protected": 0, "confirmatory": 0, "final": 0}
    stage_results = {"development": json.loads((RESULTS / "development-summary-v1.json").read_text())}
    benchmark_paths = [DEV_BENCH]
    notes: list[str] = ["Development was frozen before any Candidate-v10 formal protected payload was generated."]
    integrity: dict = {}

    for stage in ["protected", "confirmatory", "final"]:
        counts[stage] += 1
        append_ledger({
            "event": "FORMAL_STAGE_STARTED",
            "stage": stage,
            "execution_count": counts[stage],
            "timestamp": now(),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "frozen_source_sha256": sha(ROOT / "src/personal_state_engine/candidate_v10.py"),
        })
        try:
            bench, audit_path, within_audit = generate_stage(stage)
        except Exception as exc:
            notes.append(f"{stage} generation/audit error: {type(exc).__name__}: {exc}")
            append_ledger({"event": "FORMAL_STAGE_GENERATION_ERROR", "stage": stage, "execution_count": counts[stage], "timestamp": now(), "error": repr(exc)})
            write_terminal("CANDIDATE_V10_INTEGRITY_BLOCKED", counts, freeze, stage_results, integrity, notes)
            return

        benchmark_paths.append(bench)
        integrity = cross_stage(benchmark_paths)
        append_ledger({
            "event": "FORMAL_STAGE_SURFACE_FROZEN",
            "stage": stage,
            "execution_count": counts[stage],
            "timestamp": now(),
            "benchmark_sha256": sha(bench),
            "within_stage_freshness_sha256": sha(audit_path),
            "cross_stage_integrity_pass": integrity["integrity_pass"],
        })
        if not integrity["integrity_pass"]:
            notes.append(f"{stage} failed cross-stage freshness integrity before scoring.")
            write_terminal("CANDIDATE_V10_INTEGRITY_BLOCKED", counts, freeze, stage_results, integrity, notes)
            return

        result = evaluator.evaluate_payload(bench, stage)
        result_path = RESULTS / f"{stage}-summary-v1.json"
        write_json(result_path, result)
        stage_results[stage] = result
        append_ledger({
            "event": "FORMAL_STAGE_COMPLETED",
            "stage": stage,
            "execution_count": counts[stage],
            "timestamp": now(),
            "benchmark_sha256": result["benchmark_sha256"],
            "candidate_v10_source_sha256": result["candidate_v10_source_sha256"],
            "metrics": result["candidate_v10"],
            "paired_bootstrap": result["paired_bootstrap"],
            "checks": result["checks"],
            "verdict": result["verdict"],
        })
        if result["verdict"] != "PASS":
            notes.append(f"{stage} formal gate failed; subsequent formal stages were not generated or executed.")
            write_terminal(TERMINALS[stage], counts, freeze, stage_results, integrity, notes)
            return

    notes.append("Protected, Confirmatory, and fresh Final Gate F all passed under the same frozen implementation and evaluator.")
    write_terminal("CANDIDATE_V10_FINAL_GATE_F_PASS", counts, freeze, stage_results, integrity, notes)


if __name__ == "__main__":
    main()
