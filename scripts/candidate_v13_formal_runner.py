from __future__ import annotations

"""Frozen one-shot formal runner for Candidate-v13."""

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from candidate_v13_benchmark import materialize
from evaluate_candidate_v13 import evaluate

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/research/candidate-v13/freeze-manifest.json"
LEDGER = ROOT / "results/candidate-v13/formal-ledger.json"
TERMINAL_MD = ROOT / "docs/research/candidate-v13/terminal-decision.md"
TERMINAL_JSON = ROOT / "results/candidate-v13/terminal-summary.json"

STAGE_ORDER = ("protected", "confirmatory", "final")
FAIL_STATE = {
    "protected": "CANDIDATE_V13_PROTECTED_FAIL",
    "confirmatory": "CANDIDATE_V13_CONFIRMATORY_FAIL",
    "final": "CANDIDATE_V13_FINAL_GATE_F_FAIL",
}
PASS_STATE = {
    "protected": "CANDIDATE_V13_PROTECTED_PASS — READY_FOR_CONFIRMATORY",
    "confirmatory": "CANDIDATE_V13_CONFIRMATORY_PASS — READY_FOR_FINAL_GATE_F",
    "final": "CANDIDATE_V13_FINAL_GATE_F_PASS",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=ROOT, text=True).strip()


def commit_push(message: str, paths: list[Path]) -> None:
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    for path in unique:
        subprocess.check_call(("git", "add", str(path.relative_to(ROOT))), cwd=ROOT)
    subprocess.check_call(("git", "commit", "-m", message), cwd=ROOT)
    subprocess.check_call(
        ("git", "push", "origin", "HEAD:research/candidate-v13-fresh-lineage"),
        cwd=ROOT,
    )


def load_manifest() -> dict[str, Any]:
    if not MANIFEST.exists():
        raise RuntimeError("freeze manifest missing")
    return json.loads(MANIFEST.read_text())


def load_ledger() -> dict[str, Any]:
    return json.loads(LEDGER.read_text())


def save_ledger(ledger: dict[str, Any]) -> None:
    LEDGER.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")


def verify_frozen(manifest: dict[str, Any]) -> None:
    if manifest.get("status") != "FROZEN_AFTER_DEVELOPMENT_PASS":
        raise RuntimeError("freeze status invalid")
    if manifest.get("development_acceptance") != "PASS":
        raise RuntimeError("Development PASS missing")
    for rel, expected in manifest["frozen_files"].items():
        path = ROOT / rel
        if not path.exists():
            raise RuntimeError(f"frozen file missing: {rel}")
        if sha256(path) != expected["sha256"]:
            raise RuntimeError(f"frozen SHA256 mismatch: {rel}")
        if git("hash-object", str(path)) != expected["git_blob_sha"]:
            raise RuntimeError(f"frozen blob mismatch: {rel}")
    prereg = ROOT / "docs/research/candidate-v13/preregistration.md"
    if sha256(prereg) != manifest["preregistration_sha256"]:
        raise RuntimeError("preregistration SHA mismatch")


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def audit_freshness(stage: str, current_path: Path) -> dict[str, Any]:
    current = json.loads(current_path.read_text())
    current_queries = {c["query"] for c in current["cases"]}
    current_norm = {normalized(c["query"]) for c in current["cases"]}
    current_memories = {m["text"] for c in current["cases"] for m in c["memories"]}
    current_entities = {c["generator_metadata"]["gold_frame"]["subject_entity"] for c in current["cases"]}
    violations: dict[str, list[str]] = {
        "exact_query_overlap": [], "normalized_query_overlap": [],
        "exact_memory_overlap": [], "entity_overlap": [],
        "grammar_family_overlap": [], "discourse_family_overlap": [],
    }
    for earlier in ("development", "protected", "confirmatory"):
        if earlier == stage:
            break
        path = ROOT / f"experiments/benchmarks/candidate-v13-{earlier}-v1.json"
        if not path.exists():
            continue
        prior = json.loads(path.read_text())
        prior_queries = {c["query"] for c in prior["cases"]}
        prior_norm = {normalized(c["query"]) for c in prior["cases"]}
        prior_memories = {m["text"] for c in prior["cases"] for m in c["memories"]}
        prior_entities = {c["generator_metadata"]["gold_frame"]["subject_entity"] for c in prior["cases"]}
        if current_queries & prior_queries: violations["exact_query_overlap"].append(earlier)
        if current_norm & prior_norm: violations["normalized_query_overlap"].append(earlier)
        if current_memories & prior_memories: violations["exact_memory_overlap"].append(earlier)
        if current_entities & prior_entities: violations["entity_overlap"].append(earlier)
        if set(current["grammar_families"]) & set(prior["grammar_families"]):
            violations["grammar_family_overlap"].append(earlier)
        if set(current["discourse_families"]) & set(prior["discourse_families"]):
            violations["discourse_family_overlap"].append(earlier)
    return {"stage": stage, "pass": not any(violations.values()), "violations": violations}


def write_decision(stage: str, state: str, summary: dict[str, Any],
                   freshness: dict[str, Any], terminal: bool) -> list[Path]:
    decision = ROOT / f"docs/research/candidate-v13/{stage}-terminal-decision.md"
    decision.parent.mkdir(parents=True, exist_ok=True)
    decision.write_text(
        f"# Candidate-v13 {stage.title()} Decision\n\nState: `{state}`\n\n"
        f"UTC: `{utc_now()}`\n\nAcceptance: `{summary['acceptance']}`\n\n"
        f"Benchmark SHA256: `{summary['benchmark_sha256']}`\n\n"
        f"Freshness audit: `{'PASS' if freshness['pass'] else 'FAIL'}`\n\n"
        "This decision was produced by the frozen one-shot formal runner.\n"
    )
    paths = [decision]
    if terminal:
        ledger = load_ledger()
        ledger["terminal_state"] = state
        save_ledger(ledger)
        TERMINAL_MD.write_text(
            "# Candidate-v13 Terminal Decision\n\n"
            f"`{state}`\n\nUTC: `{utc_now()}`\n\n"
            f"Formal ledger: Protected={ledger['protected']}, "
            f"Confirmatory={ledger['confirmatory']}, Final={ledger['final']}.\n"
        )
        TERMINAL_JSON.write_text(json.dumps({
            "candidate": "v13", "terminal_state": state, "utc": utc_now(),
            "formal_ledger": {"protected": ledger["protected"],
                              "confirmatory": ledger["confirmatory"], "final": ledger["final"]},
            "last_stage": stage, "last_stage_acceptance": summary["acceptance"],
            "last_stage_metrics": summary["metrics"],
            "last_stage_structural": summary["structural"],
            "last_stage_integrity": summary["integrity"],
            "last_stage_anti_collapse": summary["anti_collapse"],
            "last_stage_noninferiority": summary.get("noninferiority"),
        }, indent=2, sort_keys=True) + "\n")
        paths.extend([LEDGER, TERMINAL_MD, TERMINAL_JSON])
    return paths


def seal_invalid(reason: str, formal_started: bool) -> None:
    state = "CANDIDATE_V13_RESEARCH_INTEGRITY_FAILURE" if formal_started else "CANDIDATE_V13_INFRASTRUCTURE_BLOCKED"
    ledger = load_ledger() if LEDGER.exists() else {"protected": 0, "confirmatory": 0, "final": 0}
    ledger["terminal_state"] = state
    save_ledger(ledger)
    TERMINAL_MD.parent.mkdir(parents=True, exist_ok=True)
    TERMINAL_MD.write_text(f"# Candidate-v13 Terminal Decision\n\n`{state}`\n\nReason: {reason}\n\nUTC: `{utc_now()}`\n")
    TERMINAL_JSON.parent.mkdir(parents=True, exist_ok=True)
    TERMINAL_JSON.write_text(json.dumps({
        "candidate": "v13", "terminal_state": state, "reason": reason,
        "formal_started": formal_started,
        "formal_ledger": {k: ledger.get(k, 0) for k in STAGE_ORDER}, "utc": utc_now(),
    }, indent=2, sort_keys=True) + "\n")
    commit_push(f"candidate-v13: seal {state}", [LEDGER, TERMINAL_MD, TERMINAL_JSON])


def authorize(stage: str, manifest: dict[str, Any]) -> None:
    verify_frozen(manifest)
    ledger = load_ledger()
    if ledger.get("terminal_state"): raise RuntimeError("lineage already terminal")
    idx = STAGE_ORDER.index(stage)
    for earlier in STAGE_ORDER[:idx]:
        if ledger[earlier] != 1: raise RuntimeError(f"stage order violation before {stage}")
    if ledger[stage] != 0: raise RuntimeError(f"{stage} execution already consumed")
    for later in STAGE_ORDER[idx + 1:]:
        if ledger[later] != 0: raise RuntimeError(f"future stage count nonzero: {later}")
    ledger[stage] = 1
    save_ledger(ledger)
    start = ROOT / f"results/candidate-v13/{stage}-run-start.json"
    start.write_text(json.dumps({
        "candidate": "v13", "stage": stage, "execution_count": 1,
        "authorized_utc": utc_now(), "freeze_source_commit": manifest["freeze_source_commit"],
    }, indent=2, sort_keys=True) + "\n")
    commit_push(f"candidate-v13: authorize {stage.title()} one-shot execution", [LEDGER, start])


def execute_stage(stage: str, manifest: dict[str, Any]) -> bool:
    verify_frozen(manifest)
    if load_ledger()[stage] != 1: raise RuntimeError(f"{stage} not authorized")
    benchmark = ROOT / f"experiments/benchmarks/candidate-v13-{stage}-v1.json"
    result_path = ROOT / f"results/candidate-v13/{stage}-summary-v1.json"
    freshness_path = ROOT / f"results/candidate-v13/{stage}-freshness-audit-v1.json"
    materialize(stage, benchmark, formal_authorized=True)
    freshness = audit_freshness(stage, benchmark)
    freshness_path.write_text(json.dumps(freshness, indent=2, sort_keys=True) + "\n")
    if not freshness["pass"]: raise RuntimeError(f"{stage} freshness audit failed")
    baseline_verified = bool(stage == "protected" and manifest["candidate_v12_baseline"]["provenance_verified"])
    summary = evaluate(stage, benchmark, result_path, baseline_verified)
    passed = summary["acceptance"] == "PASS"
    state = PASS_STATE[stage] if passed else FAIL_STATE[stage]
    terminal = (not passed) or stage == "final"
    decision_paths = write_decision(stage, state, summary, freshness, terminal)
    commit_push(f"candidate-v13: record {stage.title()} one-shot decision",
                [benchmark, result_path, freshness_path, *decision_paths, LEDGER])
    return passed


def mission() -> None:
    manifest = load_manifest()
    formal_started = False
    try:
        verify_frozen(manifest)
        if load_ledger() != {"candidate": "v13", "protected": 0, "confirmatory": 0,
                             "final": 0, "terminal_state": None}:
            raise RuntimeError("formal ledger is not initial 0/0/0")
        for stage in STAGE_ORDER:
            authorize(stage, manifest)
            formal_started = True
            if not execute_stage(stage, manifest):
                return
    except Exception as exc:
        if TERMINAL_JSON.exists():
            raise
        seal_invalid(str(exc), formal_started)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] != "mission":
        raise SystemExit("usage: candidate_v13_formal_runner.py mission")
    mission()
