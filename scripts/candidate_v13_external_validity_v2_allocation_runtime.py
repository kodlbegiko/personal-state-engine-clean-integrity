from __future__ import annotations

"""Runtime reconstruction of the pre-freeze allocation.

Candidate-blind. No assignments are persisted. The formal runner must compare
its reconstructed digest against the pre-freeze feasibility artifact before
any formal ledger is consumed or Candidate-v13 is imported.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FEASIBILITY_SCRIPT = ROOT / "scripts/candidate_v13_external_validity_v2_allocation_feasibility.py"
FEASIBILITY_RESULT = ROOT / "results/candidate-v13-external-validity-v2/allocation-feasibility.json"


def load_module():
    name = "pse_v2_allocation_feasibility_runtime"
    spec = importlib.util.spec_from_file_location(name, FEASIBILITY_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load allocation feasibility module")
    module = importlib.util.module_from_spec(spec)
    # dataclasses inspects sys.modules[cls.__module__] while decorators execute.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def select_stage(stage: str, seed: int, bases: list[dict[str, Any]], used_ids: set[str]) -> tuple[list[dict[str, Any]], str]:
    mod = load_module()
    policy = mod.POLICY
    cells = policy["source_domain_targets"][stage]
    family_targets = policy["family_targets"][stage]
    required_total = sum(int(x) for x in family_targets.values())

    candidates_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for domain, source_map in cells.items():
        for source, target in source_map.items():
            if int(target) <= 0:
                continue
            rows = [
                b for b in bases
                if b["source"] == source and b["domain"] == domain and b["id"] not in used_ids
            ]
            rows.sort(key=lambda b: (mod.seeded_key(seed, b), b["id"]))
            candidates_by_cell[(source, domain)] = rows

    d = mod.Dinic()
    s = d.node()
    t = d.node()
    family_node = {fam: d.node() for fam in sorted(family_targets)}
    for fam in sorted(family_targets):
        d.add(family_node[fam], t, int(family_targets[fam]))

    base_info: dict[int, dict[str, Any]] = {}
    base_family_edges: dict[int, list[tuple[str, int, int]]] = {}
    for domain in sorted(cells):
        for source in sorted(cells[domain]):
            target = int(cells[domain][source])
            if target <= 0:
                continue
            cnode = d.node()
            d.add(s, cnode, target)
            for base in candidates_by_cell[(source, domain)]:
                bnode = d.node()
                d.add(cnode, bnode, 1)
                base_info[bnode] = base
                base_family_edges[bnode] = []
                for fam in sorted(family_targets):
                    if bool((base.get("flags") or {}).get(fam)):
                        edge_index = d.add(bnode, family_node[fam], 1)
                        base_family_edges[bnode].append((fam, bnode, edge_index))

    achieved = d.flow(s, t)
    if achieved != required_total:
        raise RuntimeError(f"{stage}: reconstructed max-flow {achieved} != {required_total}")

    selected: list[tuple[dict[str, Any], str]] = []
    for bnode, edges in base_family_edges.items():
        for fam, u, idx in edges:
            edge = d.g[u][idx]
            if edge.original == 1 and edge.cap == 0:
                selected.append((base_info[bnode], fam))
                break
    if len(selected) != required_total:
        raise RuntimeError(f"{stage}: selected {len(selected)} != {required_total}")

    no_evidence_target = int(policy["answerability_targets"][stage]["no_evidence"])
    mandatory = {(b["id"], fam) for b, fam in selected if fam == "N10"}
    if len(mandatory) > no_evidence_target:
        raise RuntimeError(f"{stage}: mandatory N10 exceeds no-evidence target")
    extra_needed = no_evidence_target - len(mandatory)
    optional = [(b, fam) for b, fam in selected if fam != "N10"]
    optional.sort(key=lambda x: hashlib.sha256(f"{seed}\x1f{x[0]['id']}\x1fno-evidence".encode()).hexdigest())
    extra = {(b["id"], fam) for b, fam in optional[:extra_needed]}
    no_evidence = mandatory | extra

    digest_rows = sorted(
        f"{b['source']}\x1f{b['domain']}\x1f{b['id']}\x1f{fam}\x1f{int((b['id'], fam) in no_evidence)}"
        for b, fam in selected
    )
    digest = hashlib.sha256("\n".join(digest_rows).encode()).hexdigest()
    assignments = [
        {
            "source": str(b["source"]),
            "id": str(b["id"]),
            "domain": str(b["domain"]),
            "primary_family": str(fam),
            "no_evidence": (b["id"], fam) in no_evidence,
        }
        for b, fam in selected
    ]
    assignments.sort(key=lambda a: hashlib.sha256(
        f"{seed}\x1f{a['source']}\x1f{a['domain']}\x1f{a['id']}\x1f{a['primary_family']}".encode()
    ).hexdigest())
    return assignments, digest


def select_all() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, str]]:
    mod = load_module()
    bases = mod.build_pool()
    expected = json.loads(FEASIBILITY_RESULT.read_text(encoding="utf-8"))
    if expected.get("status") != "PASS":
        raise RuntimeError("pre-freeze allocation feasibility is not PASS")
    used: set[str] = set()
    stages: dict[str, list[dict[str, Any]]] = {}
    digests: dict[str, str] = {}
    for stage in mod.POLICY["stage_order"]:
        assignments, digest = select_stage(stage, int(mod.POLICY["stage_seeds"][stage]), bases, used)
        expected_digest = expected["stages"][stage]["selection_digest_sha256"]
        if digest != expected_digest:
            raise RuntimeError(f"FREEZE_MISMATCH: {stage} selection digest {digest} != {expected_digest}")
        ids = {a["id"] for a in assignments}
        if used & ids:
            raise RuntimeError(f"{stage}: cross-stage base reuse detected")
        used.update(ids)
        stages[stage] = assignments
        digests[stage] = digest
    if len(used) != int(expected["cross_stage_selected_count"]):
        raise RuntimeError("cross-stage selected count mismatch")
    return bases, stages, digests


def aggregate_check() -> dict[str, Any]:
    _, stages, digests = select_all()
    return {
        "schema_version": "candidate-v13-external-validity-v2-runtime-selection-check-v1",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "individual_assignments_persisted": False,
        "stage_counts": {k: len(v) for k, v in stages.items()},
        "selection_digests": digests,
        "cross_stage_selected_count": sum(len(v) for v in stages.values()),
        "status": "PASS",
    }
