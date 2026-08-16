from __future__ import annotations

"""Independent post-formal integrity audit and final v4 terminalization.

This script never imports or invokes Candidate-v13. It validates frozen hashes,
one-shot ledger semantics, result provenance, and stage ordering, then turns the
formal runner's preliminary scientific outcome into the final terminal record.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/research/candidate-v13-external-validity-v4"
OUT = ROOT / "results/candidate-v13-external-validity-v4"
CANDIDATE = ROOT / "src/personal_state_engine/candidate_v13.py"
EXPECTED = "b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838"
STAGES = ["ev_a_v4", "ev_b_v4", "ev_c_v4"]
SUMMARY = {
    "ev_a_v4": OUT / "ev-a-v4-summary.json",
    "ev_b_v4": OUT / "ev-b-v4-summary.json",
    "ev_c_v4": OUT / "ev-c-v4-summary.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args: str, check: bool = True) -> str:
    p = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=check)
    return p.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal-exit-code", required=True)
    parser.add_argument("--freeze-commit", required=True)
    args = parser.parse_args()
    if "personal_state_engine.candidate_v13" in sys.modules:
        raise RuntimeError("Candidate unexpectedly imported in independent integrity audit process")

    freeze_path = OUT / "infrastructure-freeze-manifest-v4.json"
    ledger_path = OUT / "formal-ledger-v4.json"
    prereg_path = DOC / "preregistration-lock-v4.json"
    auth_path = DOC / "formal-authorization-lock-v4.json"
    freeze = read(freeze_path, {})
    ledger = read(ledger_path, {})
    prereg = read(prereg_path, {})
    auth = read(auth_path, {})
    preliminary = read(OUT / "formal-terminal-preliminary.json", None)

    frozen_mismatches = []
    for rel, expected in freeze.get("files", {}).items():
        path = ROOT / rel
        if not path.exists():
            frozen_mismatches.append(f"missing:{rel}")
            continue
        actual_sha = sha256(path)
        actual_blob = git("hash-object", str(path))
        if actual_sha != expected.get("sha256") or actual_blob != expected.get("git_blob_sha"):
            frozen_mismatches.append(rel)

    attempts = {k: int(v) for k, v in (ledger.get("formal_invocation_attempts") or {}).items()}
    duplicate_attempts = {k: v for k, v in attempts.items() if v > 1}
    order_ok = True
    for idx, stage in enumerate(STAGES):
        if int(ledger.get(stage, 0)) == 1:
            for earlier in STAGES[:idx]:
                if int(ledger.get(earlier, 0)) != 1 or read(SUMMARY[earlier], {}).get("status") != "PASS":
                    order_ok = False
    missing_results = [s for s in STAGES if int(ledger.get(s, 0)) == 1 and not SUMMARY[s].exists()]
    rewrite_counts = {}
    for stage, path in SUMMARY.items():
        if path.exists():
            rel = str(path.relative_to(ROOT))
            count = len([x for x in git("log", "--format=%H", "--", rel, check=False).splitlines() if x.strip()])
            rewrite_counts[stage] = count
    result_rewrite_detected = any(v > 1 for v in rewrite_counts.values())

    checks = {
        "candidate_sha_match": sha256(CANDIDATE) == EXPECTED,
        "freeze_status": freeze.get("status") == "FROZEN",
        "authorization_valid": auth.get("authorized") is True and auth.get("freeze_manifest_sha256") == sha256(freeze_path),
        "preregistration_locked": prereg.get("status") == "LOCKED_PRE_FREEZE",
        "launch_path_qa_pass": prereg.get("launch_path_qa") == "PASS",
        "frozen_hashes_match": not frozen_mismatches,
        "freeze_commit_ancestor": subprocess.run(["git", "merge-base", "--is-ancestor", args.freeze_commit, "HEAD"], cwd=ROOT).returncode == 0,
        "formal_reruns_zero": int(ledger.get("formal_reruns", -1)) == 0,
        "illegal_formal_reruns_false": ledger.get("illegal_formal_reruns") is False,
        "duplicate_invocation_attempts_absent": not duplicate_attempts,
        "stage_order_valid": order_ok,
        "consumed_stage_results_present": not missing_results,
        "result_rewriting_absent": not result_rewrite_detected,
        "performance_driven_protocol_changes_zero": int(prereg.get("performance_driven_protocol_changes", -1)) == 0,
        "preauthorization_candidate_invoked_false": prereg.get("candidate_v13_invoked") is False and auth.get("candidate_v13_invoked") is False,
    }
    integrity_pass = all(checks.values())

    if not integrity_pass:
        terminal_state = "EXTERNAL_VALIDITY_V4_INVALID"
        conclusion = "scientifically invalid"
    elif preliminary is None:
        terminal_state = "EXTERNAL_VALIDITY_V4_INFRASTRUCTURE_BLOCKED"
        conclusion = "scientifically unknown due infrastructure failure"
    else:
        state = preliminary.get("terminal_state")
        allowed = {
            "EXTERNAL_VALIDITY_V4_PASS",
            "EXTERNAL_VALIDITY_V4_CANDIDATE_FAIL",
            "EXTERNAL_VALIDITY_V4_INFRASTRUCTURE_BLOCKED",
            "EXTERNAL_VALIDITY_V4_INVALID",
        }
        terminal_state = state if state in allowed else "EXTERNAL_VALIDITY_V4_INVALID"
        conclusion = {
            "EXTERNAL_VALIDITY_V4_PASS": "external validity supported",
            "EXTERNAL_VALIDITY_V4_CANDIDATE_FAIL": "external validity rejected",
            "EXTERNAL_VALIDITY_V4_INFRASTRUCTURE_BLOCKED": "scientifically unknown due infrastructure failure",
            "EXTERNAL_VALIDITY_V4_INVALID": "scientifically invalid",
        }[terminal_state]

    stage_results = {s: read(SUMMARY[s], {}) for s in STAGES}
    audit = {
        "schema_version": "candidate-v13-external-validity-v4-final-integrity-audit-v1",
        "research_integrity": "PASS" if integrity_pass else "FAIL",
        "checks": checks,
        "frozen_hash_mismatches": frozen_mismatches,
        "duplicate_invocation_attempts": duplicate_attempts,
        "missing_consumed_stage_results": missing_results,
        "result_commit_counts": rewrite_counts,
        "formal_exit_code": args.formal_exit_code,
        "freeze_commit": args.freeze_commit,
        "candidate_v13_imported_in_audit": False,
        "candidate_v13_invoked_in_audit": False,
        "status": "PASS" if integrity_pass else "FAIL",
    }
    (OUT / "final-integrity-audit-v4.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    infra = read(OUT / "infrastructure-qualification.json", {})
    full = read(OUT / "full-materialization-qualification.json", {})
    final = {
        "schema_version": "candidate-v13-external-validity-v4-terminal-summary-v1",
        "terminal_state": terminal_state,
        "candidate_integrity": {
            "expected_sha": EXPECTED,
            "observed_sha": sha256(CANDIDATE),
            "modified": sha256(CANDIDATE) != EXPECTED,
            "preauthorization_imported": False,
            "preauthorization_invoked": prereg.get("candidate_v13_invoked") is not False,
        },
        "infrastructure_qualification": infra,
        "formal_evaluation": {
            s: {
                "executed": int(ledger.get(s, 0)) == 1,
                "invocation_count": attempts.get(s, 0),
                "result": stage_results[s].get("status", "NOT_EXECUTED"),
            } for s in STAGES
        },
        "formal_integrity": {
            "formal_reruns": ledger.get("formal_reruns"),
            "illegal_reruns": ledger.get("illegal_formal_reruns"),
            "performance_driven_protocol_changes": prereg.get("performance_driven_protocol_changes"),
            "post_freeze_modifications": frozen_mismatches,
            "research_integrity_status": audit["research_integrity"],
        },
        "external_validity_metrics": {s: stage_results[s] for s in STAGES if stage_results[s]},
        "scientific_conclusion": conclusion,
        "selected_case_count": full.get("selected_case_count"),
        "successfully_materialized_case_count": full.get("successfully_materialized_case_count"),
        "gold_truncation_count": full.get("gold_truncation_count"),
        "runtime_gold_loss_count": full.get("runtime_gold_loss_count"),
        "materialization_exception_count": full.get("materialization_exception_count"),
        "branch": "research/candidate-v13-external-validity-infra-v4",
        "freeze_commit": args.freeze_commit,
        "terminal_commit": None,
    }
    (OUT / "terminal-summary.json").write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "external-validity-v4-summary.json").write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def stage_line(s: str) -> str:
        x = final["formal_evaluation"][s]
        return f"- {s}: executed={str(x['executed']).lower()}, invocation_count={x['invocation_count']}, result={x['result']}"

    report = f"""# Candidate-v13 Naturalistic External Validity v4 — Terminal Report

## Terminal State

`{terminal_state}`

## Candidate Integrity

- expected SHA: `{EXPECTED}`
- observed SHA: `{sha256(CANDIDATE)}`
- modified: `{str(sha256(CANDIDATE) != EXPECTED).lower()}`
- preauthorization imported: `false`
- preauthorization invoked: `{str(final['candidate_integrity']['preauthorization_invoked']).lower()}`

## Infrastructure Qualification

- source qualification: `{infra.get('gates', {}).get('SOURCE_QUALIFICATION_PASS')}`
- gold cardinality: `{infra.get('gates', {}).get('GOLD_CARDINALITY_AUDIT_PASS')}`
- capacity: `{infra.get('gates', {}).get('CAPACITY_PASS')}`
- contamination: `{infra.get('gates', {}).get('CONTAMINATION_PASS')}`
- dedup: `{infra.get('gates', {}).get('DEDUP_PASS')}`
- determinism: `{infra.get('gates', {}).get('DETERMINISM_PASS')}`
- full materialization: `{full.get('status')}`
- evaluator QA: `{read(OUT/'formal-infrastructure-qualification.json', {}).get('evaluator_qa', {}).get('pass')}`
- runner QA: `{infra.get('gates', {}).get('FORMAL_RUNNER_QA_PASS')}`
- Candidate firewall: `{infra.get('gates', {}).get('CANDIDATE_FIREWALL_PASS')}`
- launch-path QA: `{infra.get('gates', {}).get('LAUNCH_PATH_QA_PASS')}`
- preregistration completeness: `{infra.get('preregistration_lock_completeness_v4')}`
- freeze: `{freeze.get('status')}`

## Formal Evaluation

{stage_line('ev_a_v4')}
{stage_line('ev_b_v4')}
{stage_line('ev_c_v4')}

## Formal Integrity

- formal reruns: `{ledger.get('formal_reruns')}`
- illegal reruns: `{ledger.get('illegal_formal_reruns')}`
- performance-driven protocol changes: `{prereg.get('performance_driven_protocol_changes')}`
- post-freeze modifications: `{len(frozen_mismatches)}`
- research integrity status: `{audit['research_integrity']}`

## External-Validity Metrics

See the complete stage summaries embedded in `results/candidate-v13-external-validity-v4/terminal-summary.json`. No failed preregistered metric is omitted.

## Scientific Conclusion

`{conclusion}`

## Git Evidence

- branch: `research/candidate-v13-external-validity-infra-v4`
- v3 terminal ancestor: `21d1bb3a645c9c38000294694a78be3fcedbea16`
- freeze commit: `{args.freeze_commit}`
- terminal commit: populated by the final evidence commit in Git history
- Draft PR: maintained separately against `main`
"""
    (DOC / "TERMINAL_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"terminal_state": terminal_state, "research_integrity": audit["research_integrity"], "scientific_conclusion": conclusion}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
