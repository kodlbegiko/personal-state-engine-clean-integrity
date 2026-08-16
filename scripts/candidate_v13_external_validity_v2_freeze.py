from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity-v2"
DOC = ROOT / "docs/research/candidate-v13-external-validity-v2"
CANDIDATE = ROOT / "src/personal_state_engine/candidate_v13.py"
EXPECTED_CANDIDATE_SHA256 = "b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838"

FROZEN_FILES = [
    "src/personal_state_engine/candidate_v13.py",
    "scripts/candidate_v13_external_validity_v2_source_qualification.py",
    "scripts/candidate_v13_external_validity_v2_source_qualification_runner.py",
    "scripts/candidate_v13_external_validity_v2_strict_contamination.py",
    "scripts/candidate_v13_external_validity_v2_integrity_qualification.py",
    "scripts/candidate_v13_external_validity_v2_integrity_runner.py",
    "scripts/candidate_v13_external_validity_v2_allocation_feasibility.py",
    "scripts/candidate_v13_external_validity_v2_allocation_runtime.py",
    "scripts/candidate_v13_external_validity_v2_formal_materializer.py",
    "scripts/candidate_v13_external_validity_v2_evaluator.py",
    "scripts/candidate_v13_external_validity_v2_formal_runner.py",
    "scripts/candidate_v13_external_validity_v2_formal_sequence.py",
    "scripts/candidate_v13_external_validity_v2_formal_infrastructure_qualification.py",
    "scripts/candidate_v13_external_validity_v2_finalize_infrastructure.py",
    "scripts/candidate_v13_external_validity_v2_freeze.py",
    "docs/research/candidate-v13-external-validity-v2/source-contract-v2.json",
    "docs/research/candidate-v13-external-validity-v2/source-manifest-v2.json",
    "docs/research/candidate-v13-external-validity-v2/adapter-policy-v2.json",
    "docs/research/candidate-v13-external-validity-v2/allocation-policy-v2.json",
    "docs/research/candidate-v13-external-validity-v2/materializer-contract-v2.json",
    "docs/research/candidate-v13-external-validity-v2/evaluation-policy-v2.json",
    "docs/research/candidate-v13-external-validity-v2/preregistration.md",
    "docs/research/candidate-v13-external-validity-v2/preregistration-lock.json",
    "results/candidate-v13-external-validity-v2/source-schema-manifest.json",
    "results/candidate-v13-external-validity-v2/source-qualification.json",
    "results/candidate-v13-external-validity-v2/source-capacity-audit.json",
    "results/candidate-v13-external-validity-v2/contamination-audit.json",
    "results/candidate-v13-external-validity-v2/dedup-audit.json",
    "results/candidate-v13-external-validity-v2/determinism-audit.json",
    "results/candidate-v13-external-validity-v2/allocation-feasibility.json",
    "results/candidate-v13-external-validity-v2/formal-infrastructure-qualification.json",
    "results/candidate-v13-external-validity-v2/infrastructure-qualification.json",
    ".github/workflows/candidate-v13-external-validity-v2-formal-sequence.yml",
    ".github/workflows/candidate-v13-external-validity-v2-freeze.yml"
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def main() -> int:
    if sha256(CANDIDATE) != EXPECTED_CANDIDATE_SHA256:
        raise RuntimeError("FREEZE_MISMATCH: Candidate-v13 changed")
    infra = read_json(OUT / "infrastructure-qualification.json")
    formal = read_json(OUT / "formal-infrastructure-qualification.json")
    prereg = read_json(DOC / "preregistration-lock.json")
    allocation = read_json(OUT / "allocation-feasibility.json")
    contamination = read_json(OUT / "contamination-audit.json")
    if infra.get("status") != "PASS" or infra.get("formal_authorized") is not True:
        raise RuntimeError("infrastructure qualification is not PASS")
    if formal.get("status") != "PASS" or formal.get("candidate_v13_invoked") is not False:
        raise RuntimeError("formal infrastructure qualification is not PASS")
    if prereg.get("locked") is not True or prereg.get("candidate_v13_external_performance_observed") is not False:
        raise RuntimeError("preregistration is not legally locked")
    if allocation.get("status") != "PASS" or allocation.get("cross_stage_base_reuse_count") != 0:
        raise RuntimeError("allocation feasibility is not PASS")
    if contamination.get("status") != "PASS" or contamination.get("material_overlap_count") != 0:
        raise RuntimeError("contamination audit is not PASS")

    files = {}
    for rel in FROZEN_FILES:
        path = ROOT / rel
        if not path.exists():
            raise RuntimeError(f"required freeze file missing: {rel}")
        files[rel] = {"sha256": sha256(path), "git_blob_sha": blob(path)}

    result = {
        "schema_version": "candidate-v13-external-validity-v2-infrastructure-freeze-manifest-v1",
        "status": "FROZEN",
        "candidate": "Candidate-v13",
        "candidate_sha256": EXPECTED_CANDIDATE_SHA256,
        "candidate_modified": False,
        "candidate_v13_external_performance_observed_before_freeze": False,
        "candidate_v13_invoked_before_freeze": False,
        "formal_case_persisted_before_freeze": False,
        "preregistration_content_commit": prereg.get("preregistration_content_commit"),
        "preregistration_commit": prereg.get("preregistration_content_commit"),
        "selection_digests": {
            stage: data["selection_digest_sha256"]
            for stage, data in allocation["stages"].items()
        },
        "files": files,
        "source_revisions": {
            "evermembench-dynamic": infra.get("source_revision_actual", {}).get("evermembench-dynamic"),
            "rhelm": infra.get("source_revision_actual", {}).get("rhelm")
        },
        "research_integrity": "PASS"
    }
    (OUT / "infrastructure-freeze-manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
