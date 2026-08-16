from __future__ import annotations

"""Candidate-blind core for Candidate-v13 External Validity Infrastructure v3.

This module reconstructs pinned source pools, creates a fresh v3 allocation, and
materializes 100% of future formal cases before freeze. It must never import or
invoke Candidate-v13.
"""

import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V2_FEASIBILITY = ROOT / "scripts/candidate_v13_external_validity_v2_allocation_feasibility.py"
V2_POLICY = ROOT / "docs/research/candidate-v13-external-validity-v2/allocation-policy-v2.json"
MEMORY_POLICY = ROOT / "docs/research/candidate-v13-external-validity-v3/runtime-memory-policy-v3.json"
STAGES = ["ev_a_v3", "ev_b_v3", "ev_c_v3"]
STAGE_SEEDS = {"ev_a_v3": 73101, "ev_b_v3": 73102, "ev_c_v3": 73103}
SOURCE_REVISIONS = {
    "personamem-v2": "b7b42b78917157afed063527a1c959e98f6109f2",
    "longmemeval-cleaned": "98d7416c24c778c2fee6e6f3006e7a073259d48f",
    "locomo": "3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376",
    "sgd-carryover": "e852981ae34990f4358979625854259302feaa78",
    "evermembench-dynamic": "a6b210a32248e841967b7b64a64281d2ff3f669d",
    "rhelm": "4799f7b5757c6d9a945770fe8660c7ccfafca4c5",
}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def sha(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(str(x) for x in parts).encode("utf-8")).hexdigest()


def norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().replace("’", "'").split())


def fresh_policy() -> dict[str, Any]:
    old = json.loads(V2_POLICY.read_text(encoding="utf-8"))
    stage_map = {"ev_a_v2": "ev_a_v3", "ev_b_v2": "ev_b_v3", "ev_c_v2": "ev_c_v3"}
    def remap_stage_dict(value: dict[str, Any]) -> dict[str, Any]:
        return {stage_map[k]: v for k, v in value.items() if k in stage_map}
    return {
        "schema_version": "candidate-v13-external-validity-v3-allocation-policy-v1",
        "status": "CANDIDATE_BLIND_PRE_FREEZE",
        "candidate_v13_external_performance_observed": False,
        "stage_order": STAGES,
        "stage_seeds": STAGE_SEEDS,
        "domain_targets": remap_stage_dict(old["domain_targets"]),
        "family_targets": remap_stage_dict(old["family_targets"]),
        "answerability_targets": remap_stage_dict(old["answerability_targets"]),
        "source_domain_targets": remap_stage_dict(old["source_domain_targets"]),
        "source_totals": remap_stage_dict(old["source_totals"]),
        "reserve_source": old["reserve_source"],
        "allocation_algorithm": {
            **old["allocation_algorithm"],
            "lineage": "fresh v3 seeds and fresh deterministic selections; v2 individual assignments are not reused",
            "gold_cardinality_feasibility": "all selected cases must pass v3 runtime-memory policy and 100% production-faithful materialization before freeze",
        },
        "no_evidence_assignment": old["no_evidence_assignment"],
        "integrity": old["integrity"],
        "performance_driven_protocol_changes": 0,
    }


def build_pool() -> list[dict[str, Any]]:
    mod = load("pse_v3_pool_from_pinned_v2_loader", V2_FEASIBILITY)
    # v2's candidate-blind pool builder reloads every source from the immutable
    # revisions stored in its source contract, including pinned EverMem/RHELM.
    return mod.build_pool()


def seeded_key(seed: int, base: dict[str, Any]) -> str:
    return sha(seed, base["source"], base["domain"], base["id"])


def select_stage(
    stage: str,
    seed: int,
    bases: list[dict[str, Any]],
    used: set[tuple[str, str]],
    policy: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    helper = load(f"pse_v3_flow_helper_{stage}", V2_FEASIBILITY)
    cells = policy["source_domain_targets"][stage]
    family_targets = policy["family_targets"][stage]
    required_total = sum(int(x) for x in family_targets.values())
    candidates: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for domain, source_map in cells.items():
        for source, target in source_map.items():
            if int(target) <= 0:
                continue
            rows = [b for b in bases if b["source"] == source and b["domain"] == domain and (str(b["source"]), str(b["id"])) not in used]
            rows.sort(key=lambda b: (seeded_key(seed, b), str(b["id"])))
            candidates[(source, domain)] = rows

    d = helper.Dinic()
    source_node = d.node()
    sink = d.node()
    family_node = {fam: d.node() for fam in sorted(family_targets)}
    for fam in sorted(family_targets):
        d.add(family_node[fam], sink, int(family_targets[fam]))

    base_info: dict[int, dict[str, Any]] = {}
    base_edges: dict[int, list[tuple[str, int, int]]] = {}
    cell_targets: dict[tuple[str, str], int] = {}
    for domain in sorted(cells):
        for source in sorted(cells[domain]):
            target = int(cells[domain][source])
            if target <= 0:
                continue
            cell_targets[(source, domain)] = target
            cnode = d.node()
            d.add(source_node, cnode, target)
            for base in candidates[(source, domain)]:
                bnode = d.node()
                d.add(cnode, bnode, 1)
                base_info[bnode] = base
                base_edges[bnode] = []
                for fam in sorted(family_targets):
                    if bool((base.get("flags") or {}).get(fam)):
                        idx = d.add(bnode, family_node[fam], 1)
                        base_edges[bnode].append((fam, bnode, idx))

    achieved = d.flow(source_node, sink)
    if achieved != required_total:
        raise RuntimeError(f"{stage}: max-flow {achieved} != {required_total}")
    selected: list[tuple[dict[str, Any], str]] = []
    for bnode, edges in base_edges.items():
        for fam, u, idx in edges:
            edge = d.g[u][idx]
            if edge.original == 1 and edge.cap == 0:
                selected.append((base_info[bnode], fam))
                break
    if len(selected) != required_total:
        raise RuntimeError(f"{stage}: selected {len(selected)} != {required_total}")

    no_evidence_target = int(policy["answerability_targets"][stage]["no_evidence"])
    mandatory = {(str(b["source"]), str(b["id"]), fam) for b, fam in selected if fam == "N10"}
    if len(mandatory) > no_evidence_target:
        raise RuntimeError(f"{stage}: N10 exceeds no-evidence quota")
    optional = [(b, fam) for b, fam in selected if fam != "N10"]
    optional.sort(key=lambda x: sha(seed, x[0]["source"], x[0]["id"], "no-evidence"))
    extra = {
        (str(b["source"]), str(b["id"]), fam)
        for b, fam in optional[: no_evidence_target - len(mandatory)]
    }
    no_evidence = mandatory | extra

    assignments = [{
        "source": str(b["source"]),
        "id": str(b["id"]),
        "domain": str(b["domain"]),
        "primary_family": str(fam),
        "no_evidence": (str(b["source"]), str(b["id"]), fam) in no_evidence,
    } for b, fam in selected]
    assignments.sort(key=lambda a: sha(seed, a["source"], a["domain"], a["id"], a["primary_family"]))

    source_counts = Counter(a["source"] for a in assignments)
    domain_counts = Counter(a["domain"] for a in assignments)
    family_counts = Counter(a["primary_family"] for a in assignments)
    cell_counts = Counter((a["source"], a["domain"]) for a in assignments)
    answer_counts = Counter("no_evidence" if a["no_evidence"] else "answerable" for a in assignments)
    digest_rows = sorted(f"{a['source']}\x1f{a['domain']}\x1f{a['id']}\x1f{a['primary_family']}\x1f{int(a['no_evidence'])}" for a in assignments)
    digest = hashlib.sha256("\n".join(digest_rows).encode()).hexdigest()

    checks = {
        "exact_count": len(assignments) == required_total,
        "exact_domains": all(domain_counts[d] == int(n) for d, n in policy["domain_targets"][stage].items()),
        "exact_families": all(family_counts[f] == int(n) for f, n in family_targets.items()),
        "exact_source_domain_cells": all(cell_counts[(s, dname)] == int(n) for dname, sm in cells.items() for s, n in sm.items()),
        "exact_answerability": answer_counts["answerable"] == int(policy["answerability_targets"][stage]["answerable"]) and answer_counts["no_evidence"] == no_evidence_target,
        "maximum_source_share": max(source_counts.values()) / len(assignments) <= float(policy["integrity"]["maximum_source_share_per_stage"]),
    }
    if not all(checks.values()):
        raise RuntimeError(f"{stage}: allocation aggregate checks failed {checks}")
    return assignments, {
        "selected_count": len(assignments),
        "selection_digest_sha256": digest,
        "source_counts": dict(sorted(source_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "answerability_counts": dict(sorted(answer_counts.items())),
        "checks": checks,
        "status": "PASS",
    }


def select_all(bases: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, Any]]:
    policy = fresh_policy()
    bases = build_pool() if bases is None else bases
    used: set[tuple[str, str]] = set()
    assignments: dict[str, list[dict[str, Any]]] = {}
    stage_summaries: dict[str, Any] = {}
    for stage in STAGES:
        rows, summary = select_stage(stage, int(STAGE_SEEDS[stage]), bases, used, policy)
        keys = {(a["source"], a["id"]) for a in rows}
        if used & keys:
            raise RuntimeError(f"{stage}: cross-stage base reuse")
        used |= keys
        assignments[stage] = rows
        stage_summaries[stage] = summary
    total = sum(len(x) for x in assignments.values())
    if total != 3744 or len(used) != 3744:
        raise RuntimeError(f"fresh v3 allocation count/reuse failure total={total} unique={len(used)}")
    return bases, assignments, {
        "schema_version": "candidate-v13-external-validity-v3-allocation-feasibility-v1",
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
        "individual_formal_ids_persisted": False,
        "cross_stage_selected_count": len(used),
        "cross_stage_base_reuse_count": total - len(used),
        "stages": stage_summaries,
        "status": "PASS",
    }


def memory_id(base: dict[str, Any], index: int, text: str) -> str:
    return "m-" + sha(base["source"], base["id"], index, norm(text))[:32]


def base_memories(base: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for i, raw in enumerate(base.get("gold") or []):
        text = str(raw)
        if not norm(text):
            continue
        out.append({
            "id": memory_id(base, i, text), "text": text, "timestamp": None,
            "_base": str(base["id"]), "_subject": str(base.get("subject", "")),
            "_relation": str(base.get("relation", "")), "_domain": str(base["domain"]),
            "_source": str(base["source"]),
        })
    return out


def distractor_priority(target: dict[str, Any], other: dict[str, Any]) -> int:
    if str(other["source"]) != str(target["source"]): return 9
    same_subject = bool(norm(target.get("subject"))) and norm(other.get("subject")) == norm(target.get("subject"))
    same_relation = bool(norm(target.get("relation"))) and norm(other.get("relation")) == norm(target.get("relation"))
    same_domain = str(other["domain"]) == str(target["domain"])
    if same_subject and same_relation: return 0
    if same_subject: return 1
    if same_domain: return 2
    return 9


def materialize_case(assignment: dict[str, Any], base_by_key: dict[tuple[str, str], dict[str, Any]], by_source: dict[str, list[dict[str, Any]]], stage_seed: int) -> dict[str, Any]:
    source, base_id = assignment["source"], assignment["id"]
    base = base_by_key.get((source, base_id))
    if base is None: raise RuntimeError(f"selected base missing: {source}:{base_id}")
    gold = base_memories(base)
    if not gold: raise RuntimeError(f"no materializable gold: {source}:{base_id}")
    policy = json.loads(MEMORY_POLICY.read_text(encoding="utf-8"))
    minimum_context = int(policy["minimum_context"])
    min_distractors = int(policy["minimum_non_gold_distractors"])
    ceiling = int(policy["global_infrastructure_safety_ceiling"])
    target = max(minimum_context, len(gold) + min_distractors)
    if target > ceiling:
        raise RuntimeError(f"selected case exceeds v3 infrastructure ceiling: {source}:{base_id}:{target}>{ceiling}")

    gold_ids = [m["id"] for m in gold]
    gold_text_hashes = {sha(norm(m["text"])) for m in gold}
    no_evidence = bool(assignment["no_evidence"])
    memories = [] if no_evidence else list(gold)
    ids = {m["id"] for m in memories}
    texts = {sha(norm(m["text"])) for m in memories}
    pool = []
    for other in by_source.get(source, []):
        if str(other["id"]) == base_id: continue
        priority = distractor_priority(base, other)
        if priority >= 9: continue
        for unit in base_memories(other):
            th = sha(norm(unit["text"]))
            if th in gold_text_hashes or unit["id"] in ids or th in texts: continue
            pool.append((priority, sha(stage_seed, source, base_id, priority, other["id"], unit["id"]), unit))
    pool.sort(key=lambda x: (x[0], x[1], x[2]["id"]))
    for _, _, unit in pool:
        if len(memories) >= target: break
        th = sha(norm(unit["text"]))
        if unit["id"] in ids or th in texts: continue
        memories.append(unit); ids.add(unit["id"]); texts.add(th)
    runtime_gold = [] if no_evidence else gold_ids
    non_gold = [m for m in memories if m["id"] not in set(runtime_gold)]
    if len(memories) != target: raise RuntimeError(f"materialized memory target not reached: {source}:{base_id}:{len(memories)}!={target}")
    if len(non_gold) < min_distractors: raise RuntimeError(f"insufficient distractors: {source}:{base_id}")
    if not set(runtime_gold).issubset({m["id"] for m in memories}): raise RuntimeError(f"runtime gold loss: {source}:{base_id}")
    if no_evidence and any(sha(norm(m["text"])) in gold_text_hashes for m in memories): raise RuntimeError(f"withheld gold leaked: {source}:{base_id}")
    clean = [{"id": m["id"], "text": m["text"], "timestamp": m["timestamp"]} for m in memories]
    clean.sort(key=lambda m: sha(stage_seed, source, base_id, "runtime-order", m["id"]))
    runtime_payload = {"query": str(base["query"]), "memories": clean}
    provenance = {
        "source_dataset": source, "source_revision": SOURCE_REVISIONS[source], "source_record_id": base_id,
        "domain": str(base["domain"]), "primary_family": assignment["primary_family"], "no_evidence": no_evidence,
        "gold_ids": gold_ids, "runtime_gold_ids": runtime_gold,
    }
    transformation_hash = sha(json.dumps({**provenance, **runtime_payload}, sort_keys=True, separators=(",", ":")))
    payload_hash = sha(json.dumps(runtime_payload, sort_keys=True, separators=(",", ":")))
    return {
        **provenance, **runtime_payload,
        "answerable": not no_evidence,
        "relevant_memory_ids": runtime_gold,
        "withheld_gold_ids": gold_ids if no_evidence else [],
        "runtime_target": target,
        "transformation_hash": transformation_hash,
        "runtime_payload_hash": payload_hash,
    }


def materialize_stage(assignments: list[dict[str, Any]], bases: list[dict[str, Any]], stage_seed: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    base_by_key = {(str(b["source"]), str(b["id"])): b for b in bases}
    if len(base_by_key) != len(bases): raise RuntimeError("duplicate source/base IDs")
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for base in bases:
        if base.get("gold"): by_source[str(base["source"])].append(base)
    cases = [materialize_case(a, base_by_key, by_source, stage_seed) for a in assignments]
    if len({(c["source_dataset"], c["source_record_id"]) for c in cases}) != len(cases):
        raise RuntimeError("duplicate selected base within materialized stage")
    transformation_digest = hashlib.sha256("\n".join(sorted(c["transformation_hash"] for c in cases)).encode()).hexdigest()
    payload_digest = hashlib.sha256("\n".join(sorted(c["runtime_payload_hash"] for c in cases)).encode()).hexdigest()
    return cases, {
        "case_count": len(cases),
        "successfully_materialized_case_count": len(cases),
        "gold_truncation_count": 0,
        "runtime_gold_loss_count": 0,
        "materialization_exception_count": 0,
        "minimum_memory_count": min(len(c["memories"]) for c in cases),
        "maximum_memory_count": max(len(c["memories"]) for c in cases),
        "materialization_digest_sha256": transformation_digest,
        "runtime_payload_digest_sha256": payload_digest,
        "status": "PASS",
    }
