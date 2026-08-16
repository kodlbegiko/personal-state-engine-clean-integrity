from __future__ import annotations

"""Freeze Candidate-v13 External Validity v3 after every candidate-blind gate passes."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity-v3"
DOC = ROOT / "docs/research/candidate-v13-external-validity-v3"
CANDIDATE_MODULE = "personal_state_engine.candidate_v13"
CANDIDATE = ROOT / "src/personal_state_engine/candidate_v13.py"
EXPECTED_CANDIDATE_SHA256 = "b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838"
REQUIRED_PREREG_KEYS = {
    "source_revisions", "adapter_versions", "benchmark_sizes", "seeds",
    "source_domain_quotas", "family_quotas", "answerability_quotas",
    "memory_policy", "distractor_rule", "gold_cardinality_handling",
    "transformation_policy", "evaluation_metrics_and_thresholds",
    "anti_collapse_rules", "stage_order", "stop_rules", "rerun_prohibition",
    "reserve_source_activation_rule", "candidate_v13_sha256",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> int:
    if CANDIDATE_MODULE in sys.modules:
        raise RuntimeError("CANDIDATE_FIREWALL_FAIL: Candidate-v13 imported before freeze")
    if sha256_file(CANDIDATE) != EXPECTED_CANDIDATE_SHA256:
        raise RuntimeError("CANDIDATE_FIREWALL_FAIL: Candidate-v13 hash mismatch")
    infra = read_json(OUT / "infrastructure-qualification.json")
    if infra.get("status") != "PASS" or infra.get("formal_authorized") is not True:
        raise RuntimeError("infrastructure qualification not PASS")
    if infra.get("preregistration_lock_completeness_v3") != "PASS":
        raise RuntimeError("preregistration completeness gate not PASS")
    full = read_json(OUT / "full-materialization-qualification.json")
    if full.get("status") != "PASS" or full.get("ALL_SELECTED_CASES_PRODUCTION_MATERIALIZABLE_PASS") is not True:
        raise RuntimeError("full materialization qualification not PASS")
    if full.get("selected_case_count") != 3744 or full.get("successfully_materialized_case_count") != 3744:
        raise RuntimeError("full materialization count is not 3744/3744")
    if any(int(full.get(k, -1)) != 0 for k in ("gold_truncation_count", "runtime_gold_loss_count", "materialization_exception_count")):
        raise RuntimeError("full materialization integrity counters are not zero")
    prereg_path = DOC / "preregistration-lock-v3.json"
    prereg = read_json(prereg_path)
    if prereg.get("status") != "LOCKED_PRE_FREEZE":
        raise RuntimeError("preregistration lock missing or invalid")
    missing_prereg = sorted(REQUIRED_PREREG_KEYS - set(prereg))
    if missing_prereg:
        raise RuntimeError(f"preregistration lock incomplete: {missing_prereg}")
    if prereg.get("candidate_v13_sha256") != EXPECTED_CANDIDATE_SHA256 or prereg.get("candidate_v13_invoked") is not False:
        raise RuntimeError("preregistration Candidate-v13 boundary invalid")
    if prereg.get("benchmark_sizes") != {"ev_a_v3": 384, "ev_b_v3": 1440, "ev_c_v3": 1920}:
        raise RuntimeError("preregistration benchmark sizes invalid")
    if prereg.get("stage_order") != ["ev_a_v3", "ev_b_v3", "ev_c_v3"] or prereg.get("rerun_prohibition") is not True:
        raise RuntimeError("preregistration stage/rerun semantics invalid")

    freeze_files = [
        CANDIDATE,
        DOC / "source-contract-v3.json", DOC / "source-manifest-v3.json", DOC / "adapter-policy-v3.json",
        DOC / "runtime-memory-policy-v3.json", DOC / "allocation-policy-v3.json", DOC / "materializer-contract-v3.json",
        DOC / "evaluation-policy-v3.json", DOC / "preregistration-v3.md", prereg_path,
        ROOT / "scripts/candidate_v13_external_validity_v3_prequalification.py",
        ROOT / "scripts/candidate_v13_external_validity_v3_core.py",
        ROOT / "scripts/candidate_v13_external_validity_v3_materializer.py",
        ROOT / "scripts/candidate_v13_external_validity_v3_contamination.py",
        ROOT / "scripts/candidate_v13_external_validity_v3_qualification_runner.py",
        ROOT / "scripts/candidate_v13_external_validity_v3_infrastructure_qualification.py",
        ROOT / "scripts/candidate_v13_external_validity_v3_evaluator.py",
        ROOT / "scripts/candidate_v13_external_validity_v3_formal_runner.py",
        ROOT / "scripts/candidate_v13_external_validity_v3_formal_sequence.py",
        ROOT / "scripts/candidate_v13_external_validity_v3_freeze.py",
        ROOT / "scripts/candidate_v13_external_validity_v3_finalize_qualification.py",
        ROOT / ".github/workflows/candidate-v13-external-validity-v3-source-qualification.yml",
        ROOT / ".github/workflows/candidate-v13-external-validity-v3-infrastructure-qualification.yml",
        ROOT / ".github/workflows/candidate-v13-external-validity-v3-formal-infrastructure-qualification.yml",
        ROOT / ".github/workflows/candidate-v13-external-validity-v3-freeze.yml",
        ROOT / ".github/workflows/candidate-v13-external-validity-v3-formal-sequence.yml",
        # Frozen transitive candidate-blind source/allocation dependencies.
        ROOT / "scripts/candidate_v13_external_validity_v2_allocation_feasibility.py",
        ROOT / "scripts/candidate_v13_external_validity_v2_integrity_runner.py",
        ROOT / "scripts/candidate_v13_external_validity_v2_integrity_qualification.py",
        ROOT / "scripts/candidate_v13_external_validity_v2_strict_contamination.py",
        ROOT / "scripts/candidate_v13_external_validity_v2_source_qualification.py",
        ROOT / "scripts/candidate_v13_external_validity_v2_source_qualification_runner.py",
        ROOT / "docs/research/candidate-v13-external-validity-v2/allocation-policy-v2.json",
        ROOT / "docs/research/candidate-v13-external-validity-v2/source-contract-v2.json",
        ROOT / "docs/research/candidate-v13-external-validity/adapter-policy.json",
        ROOT / "docs/research/candidate-v13-external-validity/allocation-policy.json",
        ROOT / "scripts/candidate_v13_external_capacity_audit_v2.py",
        OUT / "candidate-firewall.json", OUT / "v2-root-cause-audit.json", OUT / "gold-cardinality-audit.json",
        OUT / "source-schema-manifest.json", OUT / "source-qualification.json", OUT / "source-capacity-audit.json",
        OUT / "contamination-audit.json", OUT / "dedup-audit.json", OUT / "determinism-audit.json",
        OUT / "allocation-feasibility.json", OUT / "full-materialization-qualification.json",
        OUT / "formal-infrastructure-qualification.json", OUT / "infrastructure-qualification.json",
    ]
    missing = [str(p.relative_to(ROOT)) for p in freeze_files if not p.exists()]
    if missing:
        raise RuntimeError(f"freeze files missing: {missing}")
    files = {}
    for path in freeze_files:
        rel = str(path.relative_to(ROOT))
        files[rel] = {"sha256": sha256_file(path), "git_blob_sha": git("hash-object", str(path))}
    manifest = {
        "schema_version": "candidate-v13-external-validity-v3-freeze-manifest-v4",
        "status": "FROZEN",
        "candidate_v13_sha256": sha256_file(CANDIDATE),
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
        "preregistration_commit": git("rev-parse", "HEAD"),
        "preregistration_lock_sha256": sha256_file(prereg_path),
        "transitive_runtime_dependencies_frozen": True,
        "files": files,
    }
    freeze_path = OUT / "infrastructure-freeze-manifest-v3.json"
    write_json(freeze_path, manifest)
    write_json(OUT / "formal-ledger.json", {
        "schema_version": "candidate-v13-external-validity-v3-formal-ledger-v2",
        "ev_a_v3": 0, "ev_b_v3": 0, "ev_c_v3": 0,
        "formal_reruns": 0, "illegal_formal_reruns": False,
        "candidate_v13_external_invocation_occurred": False,
        "formal_invocation_attempts": {},
    })
    write_json(DOC / "formal-authorization-lock-v3.json", {
        "schema_version": "candidate-v13-external-validity-v3-formal-authorization-lock-v2",
        "authorized": True,
        "freeze_manifest_sha256": sha256_file(freeze_path),
        "stage_order": ["ev_a_v3", "ev_b_v3", "ev_c_v3"],
        "reruns_permitted": False,
        "candidate_v13_invoked": False,
    })
    print(json.dumps({"status": "FROZEN", "candidate_v13_invoked": False, "files": len(files)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
