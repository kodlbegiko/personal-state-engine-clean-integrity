from __future__ import annotations

"""One-shot fail-closed formal runner for Candidate-v13 External Validity v3."""

import hashlib
import importlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "research/candidate-v13-external-validity-infra-v3"
OUT = ROOT / "results/candidate-v13-external-validity-v3"
DOC = ROOT / "docs/research/candidate-v13-external-validity-v3"
CANDIDATE_MODULE = "personal_state_engine.candidate_v13"
CANDIDATE = ROOT / "src/personal_state_engine/candidate_v13.py"
EXPECTED_CANDIDATE_SHA256 = "b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838"
MATERIALIZER = ROOT / "scripts/candidate_v13_external_validity_v3_materializer.py"
EVALUATOR = ROOT / "scripts/candidate_v13_external_validity_v3_evaluator.py"
LEDGER = OUT / "formal-ledger.json"
FREEZE = OUT / "infrastructure-freeze-manifest-v3.json"
INFRA = OUT / "infrastructure-qualification.json"
PREREG = DOC / "preregistration-lock-v3.json"
AUTH = DOC / "formal-authorization-lock-v3.json"
EVAL_POLICY = DOC / "evaluation-policy-v3.json"
STAGES = ["ev_a_v3", "ev_b_v3", "ev_c_v3"]
SUMMARY_PATHS = {
    "ev_a_v3": OUT / "ev-a-v3-summary.json",
    "ev_b_v3": OUT / "ev-b-v3-summary.json",
    "ev_c_v3": OUT / "ev-c-v3-summary.json",
}
MATERIALIZATION_PATHS = {
    "ev_a_v3": OUT / "ev-a-v3-materialization-summary.json",
    "ev_b_v3": OUT / "ev-b-v3-materialization-summary.json",
    "ev_c_v3": OUT / "ev-c-v3-materialization-summary.json",
}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, check=check, capture_output=True)


def git_blob(path: Path) -> str:
    return git("hash-object", str(path)).stdout.strip()


def commit_and_push(paths: list[Path], message: str) -> str:
    rel = [str(p.relative_to(ROOT)) for p in paths]
    git("add", *rel)
    if git("diff", "--cached", "--quiet", check=False).returncode != 0:
        git("commit", "-m", message)
        git("push", "origin", f"HEAD:{BRANCH}")
    return git("rev-parse", "HEAD").stdout.strip()


def candidate_loaded() -> bool:
    return CANDIDATE_MODULE in sys.modules


def unload_candidate() -> None:
    sys.modules.pop(CANDIDATE_MODULE, None)
    package = sys.modules.get("personal_state_engine")
    if package is not None and hasattr(package, "candidate_v13"):
        try:
            delattr(package, "candidate_v13")
        except Exception:
            pass


def verify_freeze() -> tuple[dict[str, Any], dict[str, Any]]:
    if candidate_loaded():
        raise RuntimeError("CANDIDATE_FIREWALL_FAIL: Candidate imported before freeze verification")
    if sha256_file(CANDIDATE) != EXPECTED_CANDIDATE_SHA256:
        raise RuntimeError("FREEZE_MISMATCH: Candidate-v13 SHA256")
    if not FREEZE.exists() or not AUTH.exists() or not PREREG.exists():
        raise RuntimeError("FREEZE_MISMATCH: freeze/authorization/preregistration evidence missing")
    freeze = read_json(FREEZE)
    auth = read_json(AUTH)
    if freeze.get("status") != "FROZEN" or auth.get("authorized") is not True:
        raise RuntimeError("FREEZE_MISMATCH: formal authorization not frozen")
    if auth.get("freeze_manifest_sha256") != sha256_file(FREEZE):
        raise RuntimeError("FREEZE_MISMATCH: authorization does not bind freeze manifest")
    for rel, expected in freeze.get("files", {}).items():
        path = ROOT / rel
        if not path.exists():
            raise RuntimeError(f"FREEZE_MISMATCH: missing {rel}")
        if sha256_file(path) != expected.get("sha256") or git_blob(path) != expected.get("git_blob_sha"):
            raise RuntimeError(f"FREEZE_MISMATCH: {rel}")
    infra = read_json(INFRA)
    if infra.get("status") != "PASS" or infra.get("formal_authorized") is not True:
        raise RuntimeError("PREREGISTRATION_VIOLATION: infrastructure qualification not PASS")
    return freeze, read_json(PREREG)


def read_ledger() -> dict[str, Any]:
    ledger = read_json(LEDGER)
    for stage in STAGES:
        if ledger.get(stage) not in {0, 1}:
            raise RuntimeError(f"LEDGER_INCONSISTENCY: {stage}={ledger.get(stage)!r}")
    return ledger


def consume(stage: str) -> None:
    if candidate_loaded():
        raise RuntimeError(f"CANDIDATE_FIREWALL_FAIL: Candidate imported before {stage} ledger consumption")
    ledger = read_ledger()
    if ledger[stage] != 0:
        raise RuntimeError(f"FORMAL_RERUN_DETECTED: {stage}")
    idx = STAGES.index(stage)
    for earlier in STAGES[:idx]:
        if ledger[earlier] != 1 or not SUMMARY_PATHS[earlier].exists() or read_json(SUMMARY_PATHS[earlier]).get("status") != "PASS":
            raise RuntimeError(f"LEDGER_INCONSISTENCY: {stage} before completed PASS {earlier}")
    ledger[stage] = 1
    ledger["last_consumed_stage"] = stage
    write_json(LEDGER, ledger)
    commit_and_push([LEDGER], f"candidate-v13 external validity v3: consume {stage} one-shot ledger")
    if read_ledger()[stage] != 1:
        raise RuntimeError(f"LEDGER_INCONSISTENCY: {stage} transition not persisted")


def mark_first_invocation_attempt(stage: str) -> None:
    ledger = read_ledger()
    ledger["candidate_v13_external_invocation_occurred"] = True
    attempts = dict(ledger.get("formal_invocation_attempts", {}))
    attempts[stage] = int(attempts.get(stage, 0)) + 1
    ledger["formal_invocation_attempts"] = attempts
    write_json(LEDGER, ledger)
    commit_and_push([LEDGER], f"candidate-v13 external validity v3: record {stage} formal invocation attempt")


def stage_state(stage: str) -> str:
    return str(read_json(SUMMARY_PATHS[stage]).get("status", "INVALID")) if SUMMARY_PATHS[stage].exists() else "NOT_EXECUTED"


def candidate_ranker(stage: str):
    if candidate_loaded():
        raise RuntimeError(f"CANDIDATE_FIREWALL_FAIL: Candidate imported before authorized {stage} import")
    module = importlib.import_module(CANDIDATE_MODULE)
    rank = getattr(module, "pse_candidate_v13_rank")
    first_attempt_recorded = False

    def wrapped(runtime: dict[str, Any], k: int) -> list[str]:
        nonlocal first_attempt_recorded
        try:
            return list(rank(runtime, k))
        finally:
            if not first_attempt_recorded:
                first_attempt_recorded = True
                mark_first_invocation_attempt(stage)

    return wrapped


def terminal(state: str, integrity: str, reason: str | None = None) -> None:
    ledger = read_ledger() if LEDGER.exists() else {s: 0 for s in STAGES}
    summaries = {s: read_json(SUMMARY_PATHS[s]) if SUMMARY_PATHS[s].exists() else {} for s in STAGES}
    full = read_json(OUT / "full-materialization-qualification.json") if (OUT / "full-materialization-qualification.json").exists() else {}
    obj = {
        "terminal_state": state,
        "infrastructure": read_json(INFRA).get("status") if INFRA.exists() else "UNKNOWN",
        "gold_cardinality_qualification": read_json(OUT / "gold-cardinality-audit.json").get("status") if (OUT / "gold-cardinality-audit.json").exists() else "UNKNOWN",
        "full_production_materialization": full.get("status", "UNKNOWN"),
        "selected_cases_materialized": f"{full.get('successfully_materialized_case_count', 0)}/{full.get('selected_case_count', 0)}",
        "gold_truncation_count": full.get("gold_truncation_count", 0),
        "ev_a_v3": summaries["ev_a_v3"],
        "ev_b_v3": summaries["ev_b_v3"],
        "ev_c_v3": summaries["ev_c_v3"],
        "formal_ledger": {s: ledger.get(s, 0) for s in STAGES},
        "candidate_v13_modified": sha256_file(CANDIDATE) != EXPECTED_CANDIDATE_SHA256,
        "candidate_v13_formal_invocation": bool(ledger.get("candidate_v13_external_invocation_occurred", False)),
        "formal_invocation_attempts": ledger.get("formal_invocation_attempts", {}),
        "formal_reruns": int(ledger.get("formal_reruns", 0)),
        "illegal_formal_reruns": bool(ledger.get("illegal_formal_reruns", False)),
        "performance_driven_protocol_changes": 0,
        "research_integrity": integrity,
        "reason": reason,
    }
    write_json(OUT / "terminal-summary.json", obj)
    report = [
        "# Candidate-v13 External Validity v3 — Terminal Report", "",
        f"- Terminal state: `{state}`",
        f"- Infrastructure: `{obj['infrastructure']}`",
        f"- Full production materialization: `{obj['full_production_materialization']}`",
        f"- Selected cases materialized: `{obj['selected_cases_materialized']}`",
        f"- Gold truncation count: `{obj['gold_truncation_count']}`",
        f"- EV-A-v3: `{stage_state('ev_a_v3')}`",
        f"- EV-B-v3: `{stage_state('ev_b_v3')}`",
        f"- EV-C-v3: `{stage_state('ev_c_v3')}`",
        f"- Candidate-v13 modified: `{'YES' if obj['candidate_v13_modified'] else 'NO'}`",
        f"- Candidate-v13 formal invocation: `{'YES' if obj['candidate_v13_formal_invocation'] else 'NO'}`",
        f"- Formal reruns: `{obj['formal_reruns']}`",
        f"- Research integrity: `{integrity}`",
    ]
    if reason:
        report += ["", "## Reason", "", reason]
    (DOC / "TERMINAL_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    commit_and_push([OUT / "terminal-summary.json", DOC / "TERMINAL_REPORT.md"], f"candidate-v13 external validity v3: terminal {state}")


def execute() -> int:
    try:
        unload_candidate()
        _, prereg = verify_freeze()
        ledger = read_ledger()
        if any(ledger[s] == 1 and not SUMMARY_PATHS[s].exists() for s in STAGES):
            terminal("EXTERNAL_VALIDITY_V3_INVALID", "FAIL", "A formal ledger was consumed without a legal stage result; rerun is forbidden.")
            return 3

        materializer = load("pse_v3_materializer_formal", MATERIALIZER)
        evaluator = load("pse_v3_evaluator_formal", EVALUATOR)
        policy = read_json(EVAL_POLICY)
        bases, assignments, allocation = materializer.select_all()
        for stage in STAGES:
            if allocation["stages"][stage]["selection_digest_sha256"] != prereg["selection_digests"][stage]:
                raise RuntimeError(f"FREEZE_MISMATCH: {stage} selection digest")

        materialized: dict[str, tuple[list[dict[str, Any]], dict[str, Any]]] = {}
        for stage in STAGES:
            cases, summary = materializer.materialize_stage(assignments[stage], bases, int(materializer.STAGE_SEEDS[stage]))
            if summary["materialization_digest_sha256"] != prereg["materialization_digests"][stage]:
                raise RuntimeError(f"FREEZE_MISMATCH: {stage} materialization digest")
            if summary["runtime_payload_digest_sha256"] != prereg["runtime_payload_digests"][stage]:
                raise RuntimeError(f"FREEZE_MISMATCH: {stage} runtime payload digest")
            materialized[stage] = (cases, summary)
        if candidate_loaded():
            raise RuntimeError("CANDIDATE_FIREWALL_FAIL: Candidate imported before all digest verification")

        for stage in STAGES:
            ledger = read_ledger()
            state = stage_state(stage)
            if ledger[stage] == 1:
                if state == "PASS":
                    unload_candidate()
                    continue
                if state == "NOT_EXECUTED":
                    terminal("EXTERNAL_VALIDITY_V3_INVALID", "FAIL", f"{stage} consumed with missing result")
                    return 3
                if state == "FAIL":
                    terminal("EXTERNAL_VALIDITY_V3_CANDIDATE_FAIL", "PASS", f"{stage} previously failed preregistered criteria")
                    return 2
                terminal("EXTERNAL_VALIDITY_V3_INVALID", "FAIL", f"{stage} previous result invalid")
                return 3
            if state != "NOT_EXECUTED":
                terminal("EXTERNAL_VALIDITY_V3_INVALID", "FAIL", f"{stage} result exists with ledger 0")
                return 3
            if candidate_loaded():
                terminal("EXTERNAL_VALIDITY_V3_INVALID", "FAIL", f"Candidate module remained loaded before {stage} ledger consumption")
                return 3

            cases, mat = materialized[stage]
            consume(stage)
            ranker = candidate_ranker(stage)
            try:
                summary = evaluator.evaluate(stage, cases, ranker, policy)
            except Exception as exc:
                unload_candidate()
                terminal("EXTERNAL_VALIDITY_V3_INVALID", "FAIL", f"{stage} execution failed after ledger consumption: {type(exc).__name__}: {exc}")
                return 3
            unload_candidate()

            summary.update({
                "selection_digest_sha256": prereg["selection_digests"][stage],
                "materialization_digest_sha256": mat["materialization_digest_sha256"],
                "runtime_payload_digest_sha256": mat["runtime_payload_digest_sha256"],
                "candidate_sha256": sha256_file(CANDIDATE),
                "formal_invocation_count": 1,
                "formal_rerun_count": 0,
                "frozen_hash_audit": "PASS",
            })
            mat["candidate_v13_invoked"] = False
            mat["individual_case_contents_persisted"] = False
            write_json(SUMMARY_PATHS[stage], summary)
            write_json(MATERIALIZATION_PATHS[stage], mat)
            commit_and_push([SUMMARY_PATHS[stage], MATERIALIZATION_PATHS[stage]], f"candidate-v13 external validity v3: persist {stage} one-shot result")
            if summary["status"] == "INVALID":
                terminal("EXTERNAL_VALIDITY_V3_INVALID", "FAIL", f"{stage} violated formal integrity")
                return 3
            if summary["status"] != "PASS":
                terminal("EXTERNAL_VALIDITY_V3_CANDIDATE_FAIL", "PASS", f"{stage} failed preregistered performance criteria")
                return 2

        terminal("EXTERNAL_VALIDITY_V3_PASS", "PASS")
        return 0
    except RuntimeError as exc:
        unload_candidate()
        message = str(exc)
        if "FREEZE_MISMATCH" in message or "CANDIDATE_FIREWALL_FAIL" in message or "LEDGER_INCONSISTENCY" in message or "FORMAL_RERUN_DETECTED" in message:
            terminal("EXTERNAL_VALIDITY_V3_INVALID", "FAIL", message)
            return 3
        terminal("EXTERNAL_VALIDITY_V3_INFRASTRUCTURE_BLOCKED", "PASS", message)
        return 4
    except Exception as exc:
        unload_candidate()
        if LEDGER.exists() and any(read_ledger().get(s) == 1 and not SUMMARY_PATHS[s].exists() for s in STAGES):
            terminal("EXTERNAL_VALIDITY_V3_INVALID", "FAIL", f"Unexpected failure after ledger consumption: {type(exc).__name__}: {exc}")
            return 3
        terminal("EXTERNAL_VALIDITY_V3_INFRASTRUCTURE_BLOCKED", "PASS", f"Unexpected pre-formal infrastructure failure: {type(exc).__name__}: {exc}")
        return 4


if __name__ == "__main__":
    raise SystemExit(execute())
