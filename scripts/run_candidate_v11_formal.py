from __future__ import annotations

import hashlib
import json
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import audit_candidate_v11_freshness as freshness
import evaluate_candidate_v11 as evaluator
import generate_candidate_v11_benchmark_v5 as generator

COUNTS = ROOT / "results/candidate-v11/formal-execution-counts-v1.json"
LEDGER = ROOT / "results/candidate-v11/formal-execution-ledger-v1.jsonl"
MANIFEST = ROOT / "results/candidate-v11/development-freeze-manifest-v1.json"
TERMINAL_SNAPSHOT = ROOT / "results/candidate-v11/terminal-snapshot-v1.json"
TERMINAL_REPORT = ROOT / "docs/research/candidate-v11/terminal-report.md"
INFRA_ERROR = ROOT / "results/candidate-v11/infrastructure-error-v1.json"
DEV_BENCHMARK = ROOT / "experiments/benchmarks/candidate-v11-development-v5.json"

V10_TERMINAL = "f909c0da144ada1268145b2f42cf26571231818e"
V11_PREREG = "bf6c0d2b1435a9af868f1c6c3faf8f2853a5078b"

STAGE_TERMINALS = {
    "protected": "CANDIDATE_V11_PROTECTED_FAIL",
    "confirmatory": "CANDIDATE_V11_CONFIRMATORY_FAIL",
    "final": "CANDIDATE_V11_FINAL_GATE_F_FAIL",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def update_counts(counts: dict[str, Any]) -> None:
    write_json(COUNTS, counts)


def append_ledger(event: dict[str, Any]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def formal_benchmark_path(stage: str) -> Path:
    return ROOT / f"experiments/benchmarks/candidate-v11-{stage}-v1.json"


def formal_summary_path(stage: str) -> Path:
    return ROOT / f"results/candidate-v11/{stage}-summary-v1.json"


def formal_freshness_path(stage: str) -> Path:
    return ROOT / f"results/candidate-v11/{stage}-freshness-audit-v1.json"


def generate_formal_surface(stage: str) -> Path:
    path = formal_benchmark_path(stage)
    if path.exists():
        raise RuntimeError(f"formal benchmark already exists before generation: {path}")
    payload = generator.generate(stage)
    payload["schema_version"] = "candidate-v11-formal-benchmark-v1"
    payload["name"] = f"candidate-v11-{stage}-v1"
    payload["formal_generator_revision"] = 5
    payload["formal_single_shot"] = True
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded)
    return path


def audit_formal_freshness(paths: list[Path], output: Path) -> dict[str, Any]:
    rows = [freshness.summarize(path) for path in paths]
    pairs = [
        freshness.pair_audit(rows[i], rows[j])
        for i in range(len(rows))
        for j in range(i + 1, len(rows))
    ]
    per_stage_pass = all(
        row["exact_duplicate_count"] == 0 and row["normalized_duplicate_count"] == 0
        for row in rows
    )
    cross_stage_pass = all(pair["hard_freshness_pass"] for pair in pairs)
    result = {
        "schema_version": "candidate-v11-formal-freshness-audit-v1",
        "per_stage": [freshness.public_summary(row) for row in rows],
        "cross_stage": pairs,
        "per_stage_hard_freshness_pass": per_stage_pass,
        "cross_stage_hard_freshness_pass": cross_stage_pass,
        "verdict": "PASS" if per_stage_pass and cross_stage_pass else "FAIL",
        "skeleton_overlap_policy": (
            "reported for methodology review; exact/normalized/family/provenance/"
            "mechanism overlap are hard constraints"
        ),
    }
    write_json(output, result)
    return result


def ledger_event(stage: str, event: str, benchmark: Path, verdict: str | None) -> dict[str, Any]:
    return {
        "stage": stage,
        "event": event,
        "execution_number": 1,
        "run_id": os.environ.get("GITHUB_RUN_ID", "LOCAL"),
        "commit_sha": os.environ.get("GITHUB_SHA", "LOCAL"),
        "benchmark_sha256": sha256(benchmark),
        "candidate_source_sha256": sha256(ROOT / "src/personal_state_engine/candidate_v11.py"),
        "timestamp": now(),
        "verdict": verdict,
    }


def execute_stage(
    stage: str,
    counts: dict[str, Any],
    prior_benchmarks: list[Path],
) -> tuple[dict[str, Any] | None, str | None, list[Path]]:
    benchmark = generate_formal_surface(stage)
    audit = audit_formal_freshness(
        [DEV_BENCHMARK, *prior_benchmarks, benchmark],
        formal_freshness_path(stage),
    )
    if audit["verdict"] != "PASS":
        return None, "CANDIDATE_V11_RESEARCH_INTEGRITY_FAILURE", prior_benchmarks + [benchmark]

    if counts.get(stage) != 0:
        return None, "CANDIDATE_V11_RESEARCH_INTEGRITY_FAILURE", prior_benchmarks + [benchmark]

    counts[stage] = 1
    update_counts(counts)
    append_ledger(ledger_event(stage, "STARTED", benchmark, None))

    result = evaluator.evaluate_payload(benchmark, stage)
    write_json(formal_summary_path(stage), result)
    append_ledger(ledger_event(stage, "COMPLETED", benchmark, result["verdict"]))

    if result["verdict"] != "PASS":
        return result, STAGE_TERMINALS[stage], prior_benchmarks + [benchmark]
    return result, None, prior_benchmarks + [benchmark]


def development_rows() -> list[dict[str, Any]]:
    statuses = {
        1: "FAIL — generator negative-surface defect; evidence preserved",
        2: "PASS — safety-valid but under-discriminative",
        3: "PASS metrics — stress adequacy failed",
        4: "PASS metrics — stressor was not Layer-1 eligible",
        5: "PASS — accepted Development freeze surface",
    }
    rows = []
    for iteration in range(1, 6):
        path = ROOT / f"results/candidate-v11/development-summary-v{iteration}.json"
        if not path.exists():
            continue
        result = load_json(path)
        rows.append({
            "iteration": iteration,
            "status": statuses[iteration],
            "metrics": result["candidate_v11"],
            "candidate_v10": result["candidate_v10"],
            "benchmark_sha256": result["benchmark_sha256"],
        })
    return rows


def build_terminal_snapshot(
    terminal_state: str,
    counts: dict[str, Any],
    formal_results: dict[str, dict[str, Any]],
    integrity_note: str,
) -> dict[str, Any]:
    manifest = load_json(MANIFEST)
    return {
        "schema_version": "candidate-v11-terminal-snapshot-v1",
        "terminal_state": terminal_state,
        "formal_execution_counts": {
            "protected": counts.get("protected", 0),
            "confirmatory": counts.get("confirmatory", 0),
            "final": counts.get("final", 0),
        },
        "freeze_commit_sha": os.environ.get("GITHUB_SHA", "LOCAL"),
        "terminal_evidence_commit": "TERMINAL_EVIDENCE_COMMIT_PENDING",
        "v10_terminal_commit": V10_TERMINAL,
        "preregistration_commit": V11_PREREG,
        "development_freeze_manifest_sha256": sha256(MANIFEST),
        "frozen_candidate_v11_sha256": manifest["frozen_components_sha256"]["src/personal_state_engine/candidate_v11.py"],
        "formal_results": formal_results,
        "integrity": integrity_note,
        "no_paid_api": True,
        "monetary_cost_usd": 0,
        "generated_at": now(),
    }


def format_metrics(metrics: dict[str, Any]) -> str:
    return (
        f"MRR={metrics['MRR']:.6f}, R@1={metrics['R@1']:.6f}, "
        f"R@3={metrics['R@3']:.6f}, R@5={metrics['R@5']:.6f}, "
        f"recall={metrics['answerable_recall']:.6f}, "
        f"false_abstention={metrics['false_abstention']:.6f}, "
        f"false_retrieval={metrics['false_retrieval']:.6f}, "
        f"abstention_accuracy={metrics['abstention_accuracy']:.6f}"
    )


def write_terminal_report(snapshot: dict[str, Any]) -> None:
    historical = load_json(ROOT / "results/candidate-v11/candidate-v10-final-rank1-failure-taxonomy.json")
    comparison = load_json(ROOT / "results/candidate-v11/architecture-comparison-v1.json")
    dev_rows = development_rows()

    lines = [
        "# Candidate-v11 Terminal Report",
        "",
        "## Provenance",
        "",
        f"- Candidate-v10 terminal commit: `{V10_TERMINAL}`",
        f"- Candidate-v11 branch root / parent terminal commit: `{V10_TERMINAL}`",
        f"- Candidate-v11 preregistration commit: `{V11_PREREG}`",
        f"- Candidate-v11 freeze commit: `{snapshot['freeze_commit_sha']}`",
        f"- Candidate-v11 terminal evidence commit: `{snapshot['terminal_evidence_commit']}`",
        "",
        "## Historical diagnosis",
        "",
        f"Candidate-v10 Final rank-1 failure cases diagnosed: **{historical['rank1_failure_count']}**.",
        "",
        "Root-cause counts:",
        "",
    ]
    for name, count in historical["root_cause_counts"].items():
        lines.append(f"- `{name}`: {count}")
    lines += [
        "",
        "The central pathology was post-eligibility ordering: multiple memories could pass binary evidence certification while Candidate-v10 preserved Candidate-v2 order rather than preferring the more direct and complete semantic proof.",
        "",
        "## Architecture",
        "",
        "Alternatives evaluated on the accepted fresh Development-v5 surface:",
        "",
    ]
    for name, metrics in comparison["architectures"].items():
        lines.append(
            f"- `{name}` — MRR={metrics['MRR']:.6f}, R@1={metrics['R@1']:.6f}, "
            f"R@3={metrics['R@3']:.6f}, false retrieval={metrics['false_retrieval']:.6f}."
        )
    lines += [
        "",
        "Selected design: **Architecture C — lexicographic semantic proof ordering after hard evidence eligibility**. It matched the weighted alternative's Development rank performance without a compensatory score or weight-tuning surface, while the pure dominance alternative remained too conservative and fell back to Candidate-v2 ordering.",
        "",
        "Safety invariants: blocked evidence never enters Layer 2; Candidate-v11 may reorder only eligible Candidate-v2-returned candidates; no outside memory may be injected; metadata-only evaluation fields are removed at the inference boundary.",
        "",
        "## Development",
        "",
    ]
    for row in dev_rows:
        lines.append(f"### Iteration {row['iteration']} — {row['status']}")
        lines.append("")
        lines.append(f"Candidate-v11: {format_metrics(row['metrics'])}.")
        lines.append(f"Frozen Candidate-v10 on same surface: {format_metrics(row['candidate_v10'])}.")
        lines.append(f"Benchmark SHA256: `{row['benchmark_sha256']}`.")
        lines.append("")

    lines += ["## Formal", ""]
    for stage in ("protected", "confirmatory", "final"):
        result = snapshot["formal_results"].get(stage)
        if result is None:
            lines.append(f"### {stage.title()} — NOT EXECUTED")
            lines.append("")
            continue
        metrics = result["candidate_v11"]
        v10 = result["candidate_v10"]
        bootstrap = result["paired_bootstrap_r1"]
        lines.append(f"### {stage.title()} — {result['verdict']}")
        lines.append("")
        lines.append(f"- Execution count: 1")
        lines.append(f"- Benchmark SHA256: `{result['benchmark_sha256']}`")
        lines.append(f"- Candidate-v11: {format_metrics(metrics)}")
        lines.append(f"- Candidate-v10: {format_metrics(v10)}")
        lines.append(
            f"- Paired R@1 delta v11-v10: {bootstrap['delta']:.6f}; "
            f"95% CI [{bootstrap['ci95'][0]:.6f}, {bootstrap['ci95'][1]:.6f}]; "
            f"10,000 bootstrap iterations; seed {bootstrap['seed']}"
        )
        lines.append(f"- Metadata firewall: {'PASS' if result['metadata_firewall']['pass'] else 'FAIL'}")
        lines.append(f"- Determinism: {'PASS' if result['determinism']['pass'] else 'FAIL'}")
        lines.append(f"- Candidate-v2 source invariant violations: {metrics['candidate_source_invariant_violations']}")
        lines.append("")

    lines += [
        "## Integrity",
        "",
        f"- Frozen-hash verification: {snapshot['integrity']}",
        f"- Formal execution counts: Protected={snapshot['formal_execution_counts']['protected']}, Confirmatory={snapshot['formal_execution_counts']['confirmatory']}, Final={snapshot['formal_execution_counts']['final']}",
        "- Cross-stage freshness: required before every formal execution; hard overlap violations terminate as research-integrity failure.",
        "- Metadata firewall: evaluated on every executed stage.",
        "- Historical candidates: no write path in Candidate-v11 workflows targets v7/v8/v9/v10 branches or historical result files.",
        "- Candidate-v10 Final: not rerun.",
        "- Paid APIs: none; monetary cost recorded as USD 0.",
        "- Formal reruns: prohibited; execution ledger records at most one STARTED/COMPLETED pair per stage.",
        "",
        "## Verdict",
        "",
        f"`{snapshot['terminal_state']}`",
        "",
        "This report declares only the terminal state produced by the one-shot frozen formal mission. No post-formal tuning is permitted for Candidate-v11.",
    ]
    TERMINAL_REPORT.parent.mkdir(parents=True, exist_ok=True)
    TERMINAL_REPORT.write_text("\n".join(lines) + "\n")


def finalize_terminal(
    terminal_state: str,
    counts: dict[str, Any],
    formal_results: dict[str, dict[str, Any]],
    integrity_note: str,
) -> None:
    counts["terminal_state"] = terminal_state
    update_counts(counts)
    snapshot = build_terminal_snapshot(terminal_state, counts, formal_results, integrity_note)
    write_json(TERMINAL_SNAPSHOT, snapshot)
    write_terminal_report(snapshot)


def main() -> None:
    counts = load_json(COUNTS)
    formal_results: dict[str, dict[str, Any]] = {}
    integrity_note = "PASS — freeze verifier completed before formal runner"

    try:
        if any(counts.get(stage) != 0 for stage in ("protected", "confirmatory", "final")):
            finalize_terminal(
                "CANDIDATE_V11_RESEARCH_INTEGRITY_FAILURE",
                counts,
                formal_results,
                "FAIL — formal execution counts were non-zero at one-shot entry",
            )
            return

        preexisting = [
            str(formal_benchmark_path(stage).relative_to(ROOT))
            for stage in ("protected", "confirmatory", "final")
            if formal_benchmark_path(stage).exists()
        ]
        if preexisting:
            finalize_terminal(
                "CANDIDATE_V11_RESEARCH_INTEGRITY_FAILURE",
                counts,
                formal_results,
                f"FAIL — formal benchmark payloads preexisted: {preexisting}",
            )
            return

        prior: list[Path] = []
        for stage in ("protected", "confirmatory", "final"):
            result, terminal, prior = execute_stage(stage, counts, prior)
            if result is not None:
                formal_results[stage] = result
            if terminal is not None:
                finalize_terminal(terminal, counts, formal_results, integrity_note)
                return

        finalize_terminal(
            "CANDIDATE_V11_FINAL_GATE_F_PASS",
            counts,
            formal_results,
            integrity_note,
        )
    except Exception as exc:  # objective runner/tooling failure evidence
        error = {
            "schema_version": "candidate-v11-infrastructure-error-v1",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": traceback.format_exc(),
            "formal_execution_counts_at_error": {
                stage: counts.get(stage, 0) for stage in ("protected", "confirmatory", "final")
            },
            "timestamp": now(),
        }
        write_json(INFRA_ERROR, error)
        finalize_terminal(
            "CANDIDATE_V11_INFRASTRUCTURE_BLOCKED",
            counts,
            formal_results,
            f"INFRASTRUCTURE ERROR — {type(exc).__name__}: {exc}",
        )


if __name__ == "__main__":
    main()
