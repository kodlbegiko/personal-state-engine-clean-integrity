from __future__ import annotations

"""Fail-closed one-shot formal sequence for Candidate-v13 External Validity v2.

Important ordering invariant for every stage:
  freeze verification -> deterministic selection digest verification -> in-memory
  materialization -> ledger 0->1 committed/pushed -> Candidate-v13 import/call.

The module intentionally contains no static Candidate-v13 import.
"""

import hashlib
import importlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "research/candidate-v13-external-validity-infra-v2"
OUT = ROOT / "results/candidate-v13-external-validity-v2"
DOC = ROOT / "docs/research/candidate-v13-external-validity-v2"
LEDGER_PATH = OUT / "formal-ledger.json"
FREEZE_PATH = OUT / "infrastructure-freeze-manifest.json"
INFRA_PATH = OUT / "infrastructure-qualification.json"
ALLOCATION_RESULT = OUT / "allocation-feasibility.json"
SOURCE_MANIFEST = DOC / "source-manifest-v2.json"
POLICY_PATH = DOC / "evaluation-policy-v2.json"
AUTH_PATH = DOC / "formal-authorization-lock.json"
CANDIDATE_PATH = ROOT / "src/personal_state_engine/candidate_v13.py"
EXPECTED_CANDIDATE_SHA256 = "b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838"
STAGES = ["ev_a_v2", "ev_b_v2", "ev_c_v2"]
SUMMARY_PATHS = {
    "ev_a_v2": OUT / "ev-a-v2-summary.json",
    "ev_b_v2": OUT / "ev-b-v2-summary.json",
    "ev_c_v2": OUT / "ev-c-v2-summary.json",
}
MATERIALIZATION_PATHS = {
    "ev_a_v2": OUT / "ev-a-v2-materialization-summary.json",
    "ev_b_v2": OUT / "ev-b-v2-materialization-summary.json",
    "ev_c_v2": OUT / "ev-c-v2-materialization-summary.json",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, check=check, capture_output=True)


def commit_and_push(paths: list[Path], message: str) -> str:
    rel = [str(p.relative_to(ROOT)) for p in paths]
    git("add", *rel)
    diff = git("diff", "--cached", "--quiet", check=False)
    if diff.returncode != 0:
        git("commit", "-m", message)
        git("push", "origin", f"HEAD:{BRANCH}")
    return git("rev-parse", "HEAD").stdout.strip()


def verify_freeze() -> dict[str, Any]:
    if not FREEZE_PATH.exists():
        raise RuntimeError("FREEZE_MISMATCH: infrastructure freeze manifest missing")
    freeze = read_json(FREEZE_PATH)
    if freeze.get("status") != "FROZEN":
        raise RuntimeError("FREEZE_MISMATCH: infrastructure status is not FROZEN")
    if not AUTH_PATH.exists():
        raise RuntimeError("PREREGISTRATION_VIOLATION: formal authorization lock missing")
    auth = read_json(AUTH_PATH)
    if auth.get("authorized") is not True:
        raise RuntimeError("PREREGISTRATION_VIOLATION: formal authorization is not true")
    if sha256_file(CANDIDATE_PATH) != EXPECTED_CANDIDATE_SHA256:
        raise RuntimeError("FREEZE_MISMATCH: Candidate-v13 SHA256 changed")
    for rel, expected in freeze.get("files", {}).items():
        path = ROOT / rel
        if not path.exists():
            raise RuntimeError(f"FREEZE_MISMATCH: frozen file missing: {rel}")
        actual_sha = sha256_file(path)
        actual_blob = git_blob(path)
        if actual_sha != expected.get("sha256") or actual_blob != expected.get("git_blob_sha"):
            raise RuntimeError(f"FREEZE_MISMATCH: {rel}")
    infra = read_json(INFRA_PATH)
    if infra.get("status") != "PASS" or infra.get("formal_authorized") is not True:
        raise RuntimeError("PREREGISTRATION_VIOLATION: infrastructure qualification is not PASS")
    allocation = read_json(ALLOCATION_RESULT)
    if allocation.get("status") != "PASS":
        raise RuntimeError("PREREGISTRATION_VIOLATION: allocation feasibility is not PASS")
    return freeze


def source_revisions() -> dict[str, str]:
    manifest = read_json(SOURCE_MANIFEST)
    revisions = {}
    for item in manifest["sources"]:
        source_id = str(item["source_id"])
        revision = str(item.get("revision") or "")
        if revision:
            revisions[source_id] = revision
    return revisions


def read_ledger() -> dict[str, Any]:
    ledger = read_json(LEDGER_PATH)
    for stage in STAGES:
        if ledger.get(stage) not in {0, 1}:
            raise RuntimeError(f"LEDGER_INCONSISTENCY: {stage}={ledger.get(stage)!r}")
    return ledger


def consume_ledger(stage: str) -> dict[str, Any]:
    ledger = read_ledger()
    if ledger[stage] != 0:
        raise RuntimeError(f"FORMAL_RERUN_DETECTED: {stage} ledger already {ledger[stage]}")
    idx = STAGES.index(stage)
    for earlier in STAGES[:idx]:
        if ledger[earlier] != 1:
            raise RuntimeError(f"LEDGER_INCONSISTENCY: {stage} before {earlier}")
    ledger[stage] = 1
    ledger["last_consumed_stage"] = stage
    ledger["formal_reruns"] = int(ledger.get("formal_reruns", 0))
    ledger["illegal_formal_reruns"] = False
    write_json(LEDGER_PATH, ledger)
    commit_and_push([LEDGER_PATH], f"candidate-v13 external validity v2: consume {stage} one-shot ledger")
    # Re-read the committed file; Candidate import is forbidden before this point.
    committed = read_ledger()
    if committed[stage] != 1:
        raise RuntimeError(f"LEDGER_INCONSISTENCY: {stage} consumption did not persist")
    return committed


def stage_state(stage: str) -> str:
    path = SUMMARY_PATHS[stage]
    if not path.exists():
        return "NOT_EXECUTED"
    return str(read_json(path).get("status", "INVALID"))


def stage_result_exists_consistently(stage: str, ledger: dict[str, Any]) -> bool:
    exists = SUMMARY_PATHS[stage].exists()
    if ledger[stage] == 0 and exists:
        raise RuntimeError(f"LEDGER_INCONSISTENCY: {stage} summary exists with ledger 0")
    if ledger[stage] == 1 and not exists:
        return False
    return True


def write_terminal(terminal_state: str, research_integrity: str, reason: str | None = None) -> None:
    ledger = read_ledger()
    infra = read_json(INFRA_PATH)
    freeze = read_json(FREEZE_PATH) if FREEZE_PATH.exists() else {}
    sources = [x.get("source_id") for x in read_json(SOURCE_MANIFEST).get("sources", [])] if SOURCE_MANIFEST.exists() else []
    summaries = {stage: (read_json(SUMMARY_PATHS[stage]) if SUMMARY_PATHS[stage].exists() else {}) for stage in STAGES}
    terminal = {
        "terminal_state": terminal_state,
        "candidate": "Candidate-v13",
        "candidate_modified": sha256_file(CANDIDATE_PATH) != EXPECTED_CANDIDATE_SHA256,
        "candidate_sha256": sha256_file(CANDIDATE_PATH),
        "infrastructure": {
            "status": infra.get("status", "UNKNOWN"),
            "sources": sources,
            "capacity": infra.get("domain_capacity", {}),
            "freeze_manifest": str(FREEZE_PATH.relative_to(ROOT)),
            "preregistration_commit": freeze.get("preregistration_commit", "")
        },
        "formal_ledger": {stage: ledger.get(stage, 0) for stage in STAGES},
        "ev_a_v2": summaries["ev_a_v2"],
        "ev_b_v2": summaries["ev_b_v2"],
        "ev_c_v2": summaries["ev_c_v2"],
        "formal_reruns": int(ledger.get("formal_reruns", 0)),
        "illegal_formal_reruns": bool(ledger.get("illegal_formal_reruns", False)),
        "performance_driven_changes": 0,
        "research_integrity": research_integrity,
        "reason": reason,
    }
    write_json(OUT / "terminal-summary.json", terminal)

    report = [
        "# Candidate-v13 External Validity v2 — Terminal Report",
        "",
        f"1. **Terminal classification:** `{terminal_state}`",
        f"2. **Infrastructure v2 completed:** `{infra.get('status', 'UNKNOWN')}`",
        f"3. **Source pool:** {', '.join(str(x) for x in sources)}",
        "4. **Domain capacity:** " + json.dumps({k: v.get("eligible") for k, v in infra.get("domain_capacity", {}).items()}, sort_keys=True),
        f"5. **EV-A-v2:** `{stage_state('ev_a_v2')}`",
        f"6. **EV-B-v2:** `{stage_state('ev_b_v2')}`",
        f"7. **EV-C-v2:** `{stage_state('ev_c_v2')}`",
        f"8. **Formal reruns:** `{ledger.get('formal_reruns', 0)}`",
        f"9. **Candidate-v13 modified:** `{'YES' if terminal['candidate_modified'] else 'NO'}`",
        "10. **Performance-driven protocol changes:** `0`",
        f"11. **Research integrity:** `{research_integrity}`",
        "12. **Next scientifically legal action:** " + (
            "Preserve the completed external-validity evidence; do not start Candidate-v14 without a new explicit authorization."
            if terminal_state == "EXTERNAL_VALIDITY_V2_PASS" else
            "Preserve this terminal state and evidence. Candidate-v14 requires a separately authorized fresh-development lineage."
        ),
    ]
    if reason:
        report.extend(["", "## Terminal reason", "", reason])
    (DOC / "TERMINAL_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    commit_and_push(
        [OUT / "terminal-summary.json", DOC / "TERMINAL_REPORT.md"],
        f"candidate-v13 external validity v2: terminal {terminal_state}",
    )


def formal_ranker():
    if "personal_state_engine.candidate_v13" in sys.modules:
        raise RuntimeError("CANDIDATE_FIREWALL_FAIL: Candidate-v13 imported before formal authorization")
    module = importlib.import_module("personal_state_engine.candidate_v13")
    rank = getattr(module, "pse_candidate_v13_rank")
    return lambda runtime, k: list(rank(runtime, k))


def execute() -> int:
    freeze = verify_freeze()
    policy = read_json(POLICY_PATH)
    allocation_runtime = load_module(
        "pse_v2_allocation_runtime_formal",
        ROOT / "scripts/candidate_v13_external_validity_v2_allocation_runtime.py",
    )
    materializer = load_module(
        "pse_v2_formal_materializer",
        ROOT / "scripts/candidate_v13_external_validity_v2_formal_materializer.py",
    )
    evaluator = load_module(
        "pse_v2_formal_evaluator",
        ROOT / "scripts/candidate_v13_external_validity_v2_evaluator.py",
    )

    # All selection reconstruction is candidate-blind and must match the frozen
    # pre-freeze selection digests before any formal ledger can be consumed.
    bases, assignments_by_stage, digests = allocation_runtime.select_all()
    expected_digests = read_json(ALLOCATION_RESULT)["stages"]
    for stage in STAGES:
        if digests[stage] != expected_digests[stage]["selection_digest_sha256"]:
            raise RuntimeError(f"FREEZE_MISMATCH: {stage} selection digest")

    revisions = source_revisions()
    ledger = read_ledger()
    for stage in STAGES:
        # Resume is legal only across already-completed PASS stages; it must never
        # cause a second Candidate invocation for a consumed stage.
        state = stage_state(stage)
        if ledger[stage] == 1:
            if state == "NOT_EXECUTED":
                write_terminal(
                    "EXTERNAL_VALIDITY_V2_INVALID", "FAIL",
                    f"{stage} ledger was consumed but no summary exists; protected rerun is forbidden.",
                )
                return 3
            if state == "PASS":
                continue
            if state == "FAIL":
                write_terminal("EXTERNAL_VALIDITY_V2_PERFORMANCE_FAIL", "PASS", f"{stage} previously failed its preregistered gate.")
                return 2
            write_terminal("EXTERNAL_VALIDITY_V2_INVALID", "FAIL", f"{stage} previously ended INVALID.")
            return 3
        if state != "NOT_EXECUTED":
            raise RuntimeError(f"LEDGER_INCONSISTENCY: {stage} summary with unconsumed ledger")

        # Stage case materialization is in-memory only. No protected natural-language
        # payload or individual selected IDs are committed to the repository.
        cases, materialization_summary = materializer.materialize_stage(
            assignments_by_stage[stage], bases, revisions,
            int(allocation_runtime.load_module().POLICY["stage_seeds"][stage]),
        )
        materialization_summary["selection_digest_sha256"] = digests[stage]
        materialization_summary["formal_case_materialized"] = True
        materialization_summary["candidate_v13_invoked"] = False

        # Only after all materialization checks pass is the irreversible one-shot
        # ledger transition committed and pushed.
        consume_ledger(stage)
        ranker = formal_ranker()
        summary = evaluator.evaluate(stage, cases, ranker, policy)
        summary["selection_digest_sha256"] = digests[stage]
        summary["materialization_digest_sha256"] = materialization_summary["transformation_digest_sha256"]
        summary["candidate_sha256"] = sha256_file(CANDIDATE_PATH)
        summary["formal_invocation_count"] = 1
        summary["formal_rerun_count"] = 0
        summary["frozen_hash_audit"] = "PASS"
        write_json(SUMMARY_PATHS[stage], summary)
        write_json(MATERIALIZATION_PATHS[stage], materialization_summary)
        commit_and_push(
            [SUMMARY_PATHS[stage], MATERIALIZATION_PATHS[stage]],
            f"candidate-v13 external validity v2: persist {stage} one-shot result",
        )

        if summary["status"] == "INVALID":
            write_terminal("EXTERNAL_VALIDITY_V2_INVALID", "FAIL", f"{stage} violated a formal integrity invariant.")
            return 3
        if summary["status"] != "PASS":
            write_terminal("EXTERNAL_VALIDITY_V2_PERFORMANCE_FAIL", "PASS", f"{stage} failed preregistered performance thresholds.")
            return 2
        ledger = read_ledger()

    write_terminal("EXTERNAL_VALIDITY_V2_PASS", "PASS")
    return 0


def main() -> int:
    try:
        return execute()
    except Exception as exc:
        # If no formal ledger has been consumed, a frozen infrastructure failure is
        # BLOCKED. Once any protected stage is consumed, unexpected execution failure
        # makes the formal lineage INVALID rather than permitting a rerun.
        try:
            ledger = read_ledger() if LEDGER_PATH.exists() else {stage: 0 for stage in STAGES}
            consumed = sum(int(ledger.get(stage, 0)) for stage in STAGES)
            state = "EXTERNAL_VALIDITY_V2_INVALID" if consumed else "EXTERNAL_VALIDITY_V2_INFRASTRUCTURE_BLOCKED"
            integrity = "FAIL" if consumed else "PASS"
            if FREEZE_PATH.exists() and LEDGER_PATH.exists():
                write_terminal(state, integrity, f"{type(exc).__name__}: {exc}")
        except Exception:
            pass
        raise


if __name__ == "__main__":
    raise SystemExit(main())
