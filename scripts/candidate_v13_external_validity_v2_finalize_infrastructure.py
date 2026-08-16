from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity-v2"
DOC = ROOT / "docs/research/candidate-v13-external-validity-v2"


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "MISSING", "_missing": str(path.relative_to(ROOT))}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    source = load(OUT / "source-qualification.json")
    capacity = load(OUT / "source-capacity-audit.json")
    schema = load(OUT / "source-schema-manifest.json")
    firewall = load(OUT / "candidate-firewall.json")
    dedup = load(OUT / "dedup-audit.json")
    contamination = load(OUT / "contamination-audit.json")
    determinism = load(OUT / "determinism-audit.json")
    dry = load(OUT / "materialization-dry-run.json")
    allocation = load(OUT / "allocation-feasibility.json")
    contract = load(DOC / "source-contract-v2.json")

    expected_revisions = {
        "evermembench-dynamic": contract.get("supplemental_sources", {}).get("evermembench-dynamic", {}).get("revision"),
        "rhelm": contract.get("reserve_sources", {}).get("rhelm", {}).get("revision"),
    }
    actual_revisions = {
        name: source.get("sources", {}).get(name, {}).get("revision")
        for name in expected_revisions
    }
    revision_match = expected_revisions == actual_revisions and all(expected_revisions.values())

    supplemental = [
        source.get("sources", {}).get("evermembench-dynamic", {}),
        source.get("sources", {}).get("rhelm", {}),
    ]
    license_pass = all(
        str(item.get("license", "")).casefold() in {"apache-2.0", "cc-by-4.0"}
        for item in supplemental
    )
    source_ok = source.get("status") == "PASS" and revision_match
    capacity_ok = capacity.get("status") == "PASS" and not capacity.get("hard_domain_shortfalls") and not capacity.get("family_shortfalls")
    strict_contam = contamination.get("schema_version") == "candidate-v13-external-validity-v2-contamination-audit-v2"
    dry_v2 = dry.get("schema_version") == "candidate-v13-external-validity-v2-materialization-dry-run-v2"
    allocation_ok = (
        allocation.get("schema_version") == "candidate-v13-external-validity-v2-allocation-feasibility-v1"
        and allocation.get("status") == "PASS"
        and allocation.get("formal_case_materialized") is False
        and allocation.get("individual_formal_ids_persisted") is False
        and allocation.get("cross_stage_base_reuse_count") == 0
    )

    gates = {
        "SOURCE_ACCESS_PASS": source_ok,
        "LICENSE_PASS": license_pass,
        "SCHEMA_PASS": source_ok and bool(schema),
        "PARSER_PASS": source_ok,
        "GOLD_RESOLUTION_PASS": source_ok,
        "DOMAIN_MAPPING_PASS": source_ok,
        "CAPACITY_PASS": capacity_ok,
        "ALLOCATION_FEASIBILITY_PASS": allocation_ok,
        "DEDUP_PASS": dedup.get("status") == "PASS",
        "CONTAMINATION_PASS": strict_contam and contamination.get("status") == "PASS",
        "DETERMINISM_PASS": determinism.get("status") == "PASS" and determinism.get("hash_match") is True,
        "MATERIALIZATION_DRY_RUN_PASS": dry_v2 and dry.get("status") == "PASS" and dry.get("synthetic_only") is True and dry.get("real_external_payload_materialized") is False,
        "CANDIDATE_FIREWALL_PASS": firewall.get("pass") is True and firewall.get("candidate_v13_invoked") is False and firewall.get("formal_case_materialized") is False,
    }
    all_pass = all(gates.values())
    status = "PASS" if all_pass else "BLOCKED"
    result = {
        "schema_version": "candidate-v13-external-validity-v2-infrastructure-qualification-v4",
        "status": status,
        "formal_authorized": all_pass,
        "gates": gates,
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "source_revision_expected": expected_revisions,
        "source_revision_actual": actual_revisions,
        "source_revision_match": revision_match,
        "domain_capacity": capacity.get("domain_capacity", {}),
        "capacity_safety_warnings": capacity.get("safety_margin_warnings", []),
        "allocation_summary": {
            "status": allocation.get("status"),
            "cross_stage_selected_count": allocation.get("cross_stage_selected_count"),
            "cross_stage_base_reuse_count": allocation.get("cross_stage_base_reuse_count"),
            "stage_selection_digests": {
                stage: data.get("selection_digest_sha256")
                for stage, data in allocation.get("stages", {}).items()
            },
        },
        "contamination_summary": {
            "status": contamination.get("status"),
            "material_overlap_count": contamination.get("material_overlap_count"),
            "methods": contamination.get("methods", []),
        },
        "dedup_summary": {
            "status": dedup.get("status"),
            "pre_dedup": dedup.get("pre_dedup"),
            "post_dedup": dedup.get("post_dedup"),
        },
        "determinism_summary": {
            "status": determinism.get("status"),
            "pool_case_count": determinism.get("pool_case_count"),
            "canonical_hash": determinism.get("canonical_hash_run_1"),
        },
        "materialization_dry_run": {
            "status": dry.get("status"),
            "memory_count": dry.get("memory_count"),
            "non_gold_distractor_count": dry.get("non_gold_distractor_count"),
            "runtime_projection_fields": dry.get("runtime_projection_fields"),
        },
    }
    (OUT / "infrastructure-qualification.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
