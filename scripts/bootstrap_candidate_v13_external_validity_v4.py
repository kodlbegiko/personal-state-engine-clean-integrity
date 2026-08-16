from __future__ import annotations

"""Deterministically bootstrap the fresh Candidate-v13 External Validity v4 lineage.

This script is candidate-blind. It reuses v3 engineering implementations only as
source material, rewrites them into a fresh v4 namespace, changes allocation
seeds before any Candidate invocation, preserves the v3 scientific thresholds,
and records the v3 terminal/orchestration forensics.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC3 = ROOT / "docs/research/candidate-v13-external-validity-v3"
OUT3 = ROOT / "results/candidate-v13-external-validity-v3"
DOC4 = ROOT / "docs/research/candidate-v13-external-validity-v4"
OUT4 = ROOT / "results/candidate-v13-external-validity-v4"
CANDIDATE = ROOT / "src/personal_state_engine/candidate_v13.py"
EXPECTED = "b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838"
V3_TERMINAL_COMMIT = "21d1bb3a645c9c38000294694a78be3fcedbea16"
V3_FREEZE_COMMIT = "6ac49d8e069d25f2497195fa7010a72e940dfaf1"

SCRIPT_STEMS = [
    "prequalification",
    "core",
    "materializer",
    "contamination",
    "qualification_runner",
    "evaluator",
    "formal_runner",
    "formal_sequence",
    "freeze",
    "infrastructure_qualification",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def transform(text: str) -> str:
    # Narrow namespace/lineage transformation; v2 dependencies remain v2.
    text = text.replace("candidate_v13_external_validity_v3", "candidate_v13_external_validity_v4")
    text = text.replace("candidate-v13-external-validity-infra-v3", "candidate-v13-external-validity-infra-v4")
    text = text.replace("candidate-v13-external-validity-v3", "candidate-v13-external-validity-v4")
    text = text.replace("EXTERNAL_VALIDITY_V3", "EXTERNAL_VALIDITY_V4")
    text = text.replace("ev_a_v3", "ev_a_v4").replace("ev_b_v3", "ev_b_v4").replace("ev_c_v3", "ev_c_v4")
    text = text.replace("EV-A-v3", "EV-A-v4").replace("EV-B-v3", "EV-B-v4").replace("EV-C-v3", "EV-C-v4")
    text = text.replace("pse_v3_", "pse_v4_")
    text = text.replace("evaluation_policy_v3", "evaluation_policy_v4")
    text = text.replace("preregistration_lock_completeness_v3", "preregistration_lock_completeness_v4")
    text = text.replace("source_manifest_enriched_v3", "source_manifest_enriched_v4")
    text = text.replace("gold_cardinality_runtime_requirement_enriched_v3", "gold_cardinality_runtime_requirement_enriched_v4")
    text = text.replace("formal-ledger.json", "formal-ledger-v4.json")
    text = text.replace("fresh v3 seeds", "fresh v4 seeds")
    text = text.replace("v3 runtime-memory policy", "v4 runtime-memory policy")
    text = text.replace("External Validity v3", "External Validity v4")
    return text


def verify_v3_history() -> None:
    if "personal_state_engine.candidate_v13" in sys.modules:
        raise RuntimeError("Candidate module imported before v4 bootstrap")
    if sha256(CANDIDATE) != EXPECTED:
        raise RuntimeError("Candidate-v13 SHA mismatch before v4 bootstrap")
    subprocess.check_call(["git", "cat-file", "-e", f"{V3_TERMINAL_COMMIT}^{{commit}}"], cwd=ROOT)
    subprocess.check_call(["git", "cat-file", "-e", f"{V3_FREEZE_COMMIT}^{{commit}}"], cwd=ROOT)
    terminal = read_json(OUT3 / "terminal-summary.json")
    ledger = read_json(OUT3 / "formal-ledger.json")
    if terminal.get("terminal_state") != "EXTERNAL_VALIDITY_V3_INFRASTRUCTURE_BLOCKED":
        raise RuntimeError("v3 terminal state changed")
    if terminal.get("candidate_v13_formal_invocation") is not False:
        raise RuntimeError("v3 terminal summary reports Candidate invocation")
    if [ledger.get("ev_a_v3"), ledger.get("ev_b_v3"), ledger.get("ev_c_v3")] != [0, 0, 0]:
        raise RuntimeError("v3 formal ledger is not 0/0/0")
    if ledger.get("formal_reruns") != 0 or ledger.get("illegal_formal_reruns") is not False:
        raise RuntimeError("v3 rerun invariant changed")

    qualification = (ROOT / ".github/workflows/candidate-v13-external-validity-v3-infrastructure-qualification.yml").read_text(encoding="utf-8")
    formal = (ROOT / ".github/workflows/candidate-v13-external-validity-v3-formal-sequence.yml").read_text(encoding="utf-8")
    causal = (
        "git push origin HEAD:research/candidate-v13-external-validity-infra-v3" in qualification
        and "formal-authorization-lock-v3.json" in formal
        and "on:" in formal
        and "push:" in formal
    )
    if not causal:
        raise RuntimeError("v3 orchestration root cause could not be mechanically re-established")

    DOC4.mkdir(parents=True, exist_ok=True)
    OUT4.mkdir(parents=True, exist_ok=True)
    audit = {
        "schema_version": "candidate-v13-external-validity-v4-v3-history-audit-v1",
        "v3_terminal_commit": V3_TERMINAL_COMMIT,
        "v3_freeze_commit": V3_FREEZE_COMMIT,
        "v3_terminal_state": terminal["terminal_state"],
        "v3_formal_ledger": {k: ledger[k] for k in ("ev_a_v3", "ev_b_v3", "ev_c_v3")},
        "v3_candidate_formal_invocation": False,
        "v3_formal_reruns": 0,
        "candidate_v13_sha256": sha256(CANDIDATE),
        "candidate_v13_modified": False,
        "root_cause_confirmed": causal,
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
        "status": "PASS",
    }
    write_json(OUT4 / "v3-history-audit.json", audit)
    (DOC4 / "V3_TERMINAL_PRESERVATION_AUDIT.md").write_text(
        "# V3 Terminal Preservation Audit\n\n"
        f"- v3 terminal commit: `{V3_TERMINAL_COMMIT}`\n"
        f"- v3 freeze commit: `{V3_FREEZE_COMMIT}`\n"
        "- terminal state: `EXTERNAL_VALIDITY_V3_INFRASTRUCTURE_BLOCKED`\n"
        "- formal ledger: `0 / 0 / 0`\n"
        "- Candidate-v13 formal invocation: `false`\n"
        "- formal reruns: `0`\n"
        "- preservation gate: `PASS`\n\n"
        "The v3 lineage remains historical and is not modified by v4.\n",
        encoding="utf-8",
    )
    (DOC4 / "V3_LAUNCH_ROOT_CAUSE_AUDIT.md").write_text(
        "# V3 Launch Root-Cause Audit\n\n"
        "`V3_ROOT_CAUSE_CONFIRMED_PASS`\n\n"
        "The v3 infrastructure qualification workflow committed and pushed the freeze/authorization artifacts using the workflow `GITHUB_TOKEN`. The separate formal-sequence workflow depended on a later `push` of `formal-authorization-lock-v3.json`. That recursive event did not launch the second workflow, so no formal Candidate invocation occurred. v4 removes the second-event dependency and keeps formal execution in the same already-running workflow graph.\n",
        encoding="utf-8",
    )


def copy_v3_engineering() -> None:
    for stem in SCRIPT_STEMS:
        src = ROOT / "scripts" / f"candidate_v13_external_validity_v3_{stem}.py"
        dst = ROOT / "scripts" / f"candidate_v13_external_validity_v4_{stem}.py"
        text = transform(src.read_text(encoding="utf-8"))
        if stem == "core":
            old = 'STAGE_SEEDS = {"ev_a_v4": 73101, "ev_b_v4": 73102, "ev_c_v4": 73103}'
            new = 'STAGE_SEEDS = {"ev_a_v4": 84101, "ev_b_v4": 84102, "ev_c_v4": 84103}'
            if old not in text:
                raise RuntimeError("could not locate transformed v4 stage seed declaration")
            text = text.replace(old, new)
        if stem == "formal_runner":
            text = text.replace('OUT / "terminal-summary.json"', 'OUT / "formal-terminal-preliminary.json"')
            text = text.replace('DOC / "TERMINAL_REPORT.md"', 'DOC / "FORMAL_PRELIMINARY_REPORT.md"')
        if stem == "freeze":
            workflow_block = '''        ROOT / ".github/workflows/candidate-v13-external-validity-v4-source-qualification.yml",\n        ROOT / ".github/workflows/candidate-v13-external-validity-v4-infrastructure-qualification.yml",\n        ROOT / ".github/workflows/candidate-v13-external-validity-v4-formal-infrastructure-qualification.yml",\n        ROOT / ".github/workflows/candidate-v13-external-validity-v4-freeze.yml",\n        ROOT / ".github/workflows/candidate-v13-external-validity-v4-formal-sequence.yml",'''
            replacement = '''        ROOT / ".github/workflows/candidate-v13-external-validity-v4.yml",\n        ROOT / "scripts/bootstrap_candidate_v13_external_validity_v4.py",\n        ROOT / "scripts/candidate_v13_external_validity_v4_launch_path_qa.py",\n        ROOT / "scripts/candidate_v13_external_validity_v4_lock_preregistration.py",\n        ROOT / "scripts/candidate_v13_external_validity_v4_final_integrity_audit.py",\n        DOC / "orchestration-contract-v4.json",\n        OUT / "launch-path-qa.json",'''
            if workflow_block not in text:
                raise RuntimeError("could not patch v4 freeze workflow dependency block")
            text = text.replace(workflow_block, replacement)
            marker = '    if prereg.get("stage_order") != ["ev_a_v4", "ev_b_v4", "ev_c_v4"] or prereg.get("rerun_prohibition") is not True:\n        raise RuntimeError("preregistration stage/rerun semantics invalid")\n'
            insertion = marker + '    launch = read_json(OUT / "launch-path-qa.json")\n    if launch.get("status") != "PASS" or launch.get("candidate_v13_imported") is not False or launch.get("candidate_v13_invoked") is not False:\n        raise RuntimeError("LAUNCH_PATH_QA not PASS")\n'
            if marker not in text:
                raise RuntimeError("could not patch v4 freeze launch-path gate")
            text = text.replace(marker, insertion)
        dst.write_text(text, encoding="utf-8")

    memory_src = DOC3 / "runtime-memory-policy-v3.json"
    (DOC4 / "runtime-memory-policy-v4.json").write_text(transform(memory_src.read_text(encoding="utf-8")), encoding="utf-8")
    write_json(DOC4 / "preregistration-lock-v4.json", {})
    write_json(DOC4 / "orchestration-contract-v4.json", {
        "schema_version": "candidate-v13-external-validity-v4-orchestration-contract-v1",
        "lineage": "fresh-v4-event-independent",
        "single_top_level_workflow": ".github/workflows/candidate-v13-external-validity-v4.yml",
        "ordered_phases": [
            "bootstrap",
            "prequalification",
            "qualification",
            "formal_runner_qa",
            "launch_path_qa",
            "preregistration_lock",
            "freeze_and_authorize",
            "verify_freeze",
            "ev_a_v4",
            "ev_a_gate",
            "ev_b_v4",
            "ev_b_gate",
            "ev_c_v4",
            "independent_final_integrity_audit",
            "terminal_decision",
        ],
        "post_freeze_repository_event_required": False,
        "recursive_github_token_trigger_required": False,
        "manual_formal_dispatch_permitted": False,
        "automatic_candidate_retry_permitted": False,
        "formal_reruns_permitted": False,
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
        "status": "CANDIDATE_BLIND_PRE_FREEZE",
    })


def main() -> int:
    verify_v3_history()
    copy_v3_engineering()
    if "personal_state_engine.candidate_v13" in sys.modules:
        raise RuntimeError("Candidate module imported during v4 bootstrap")
    print(json.dumps({
        "status": "PASS",
        "v3_root_cause": "V3_ROOT_CAUSE_CONFIRMED_PASS",
        "candidate_sha256": sha256(CANDIDATE),
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
        "fresh_v4_seeds": {"ev_a_v4": 84101, "ev_b_v4": 84102, "ev_c_v4": 84103},
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
