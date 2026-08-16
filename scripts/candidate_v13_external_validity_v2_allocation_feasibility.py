from __future__ import annotations

"""Candidate-blind exact source×domain×family allocation feasibility audit.

No Candidate-v13 import/call. No formal IDs or natural-language payloads are
persisted. The solver selects bases in memory only and emits aggregate counts
plus irreversible SHA256 digests.
"""

import hashlib
import importlib.util
import json
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / "docs/research/candidate-v13-external-validity-v2/allocation-policy-v2.json").read_text(encoding="utf-8"))
INTEGRITY_RUNNER = ROOT / "scripts/candidate_v13_external_validity_v2_integrity_runner.py"
OUT = ROOT / "results/candidate-v13-external-validity-v2/allocation-feasibility.json"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seeded_key(seed: int, base: dict[str, Any]) -> str:
    raw = f"{seed}\x1f{base['source']}\x1f{base['domain']}\x1f{base['id']}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass
class Edge:
    to: int
    rev: int
    cap: int
    original: int


class Dinic:
    def __init__(self) -> None:
        self.g: list[list[Edge]] = []

    def node(self) -> int:
        self.g.append([])
        return len(self.g) - 1

    def add(self, u: int, v: int, cap: int) -> int:
        ui = len(self.g[u])
        vi = len(self.g[v])
        self.g[u].append(Edge(v, vi, cap, cap))
        self.g[v].append(Edge(u, ui, 0, 0))
        return ui

    def flow(self, s: int, t: int) -> int:
        total = 0
        n = len(self.g)
        while True:
            level = [-1] * n
            q = deque([s])
            level[s] = 0
            while q:
                u = q.popleft()
                for e in self.g[u]:
                    if e.cap > 0 and level[e.to] < 0:
                        level[e.to] = level[u] + 1
                        q.append(e.to)
            if level[t] < 0:
                return total
            it = [0] * n

            def dfs(u: int, f: int) -> int:
                if u == t:
                    return f
                while it[u] < len(self.g[u]):
                    e = self.g[u][it[u]]
                    if e.cap > 0 and level[e.to] == level[u] + 1:
                        pushed = dfs(e.to, min(f, e.cap))
                        if pushed:
                            e.cap -= pushed
                            self.g[e.to][e.rev].cap += pushed
                            return pushed
                    it[u] += 1
                return 0

            while True:
                pushed = dfs(s, 1 << 60)
                if not pushed:
                    break
                total += pushed


def build_pool() -> list[dict[str, Any]]:
    # Reuse the candidate-blind integrity pool builder; it binds the verified
    # EverMem schema and RHELM resolver but does not import/call Candidate-v13.
    runner = load("pse_v2_integrity_runner_for_allocation", INTEGRITY_RUNNER)
    integrity = load("pse_v2_integrity_core_for_allocation", ROOT / "scripts/candidate_v13_external_validity_v2_integrity_qualification.py")
    strict = load("pse_v2_strict_contam_for_allocation", ROOT / "scripts/candidate_v13_external_validity_v2_strict_contamination.py")

    def fixed_build_pool():
        mod = integrity.load_module("pse_v2_source_qualifier_for_alloc", integrity.SRC)
        src_runner = integrity.load_module("pse_v2_source_runner_for_alloc", integrity.RUNNER)
        src_runner.bind_schema_verified_evermem(mod)
        mod.rhelm = lambda legacy, bases, schema_manifest: src_runner.fast_rhelm(mod, legacy, bases, schema_manifest)
        legacy = mod.load_legacy_module()
        bases, _ = mod.fresh_baseline(legacy)
        manifest: dict[str, Any] = {}
        mod.evermem(legacy, bases, manifest)
        mod.rhelm(legacy, bases, manifest)
        from collections import Counter
        stats = Counter()
        bases = legacy.dedup(bases, stats)
        legacy.dynamic(bases)
        return mod, legacy, bases, {}

    integrity.build_pool = fixed_build_pool
    integrity.contamination_audit = lambda bases: strict.audit(ROOT, bases)
    _, _, bases, _ = fixed_build_pool()
    return bases


def solve_stage(stage: str, seed: int, bases: list[dict[str, Any]], used_ids: set[str]) -> tuple[dict[str, Any], set[str]]:
    cells = POLICY["source_domain_targets"][stage]
    family_targets = POLICY["family_targets"][stage]
    required_total = sum(family_targets.values())

    candidates_by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for domain, source_map in cells.items():
        for source, target in source_map.items():
            if target <= 0:
                continue
            rows = [b for b in bases if b["source"] == source and b["domain"] == domain and b["id"] not in used_ids]
            rows.sort(key=lambda b: (seeded_key(seed, b), b["id"]))
            candidates_by_cell[(source, domain)] = rows

    d = Dinic()
    s = d.node()
    t = d.node()
    family_node = {fam: d.node() for fam in sorted(family_targets)}
    for fam in sorted(family_targets):
        d.add(family_node[fam], t, int(family_targets[fam]))

    base_info: dict[int, dict[str, Any]] = {}
    base_family_edges: dict[int, list[tuple[str, int, int]]] = {}
    cell_nodes: dict[tuple[str, str], int] = {}
    cell_targets: dict[tuple[str, str], int] = {}

    for domain in sorted(cells):
        for source in sorted(cells[domain]):
            target = int(cells[domain][source])
            if target <= 0:
                continue
            cell = (source, domain)
            rows = candidates_by_cell[cell]
            cell_targets[cell] = target
            cnode = d.node()
            cell_nodes[cell] = cnode
            d.add(s, cnode, target)
            for b in rows:
                bnode = d.node()
                d.add(cnode, bnode, 1)
                base_info[bnode] = b
                base_family_edges[bnode] = []
                for fam in sorted(family_targets):
                    if bool((b.get("flags") or {}).get(fam)):
                        edge_idx = d.add(bnode, family_node[fam], 1)
                        base_family_edges[bnode].append((fam, bnode, edge_idx))

    achieved = d.flow(s, t)
    selected: list[tuple[dict[str, Any], str]] = []
    for bnode, edges in base_family_edges.items():
        for fam, u, idx in edges:
            e = d.g[u][idx]
            if e.original == 1 and e.cap == 0:
                selected.append((base_info[bnode], fam))
                break

    selected_ids = {b["id"] for b, _ in selected}
    # Since base IDs include source namespace prefixes in all loaders, IDs are
    # stable and unique across this v2 pool. Persist only their digest.
    no_evidence_target = int(POLICY["answerability_targets"][stage]["no_evidence"])
    mandatory = {(b["id"], fam) for b, fam in selected if fam == "N10"}
    if len(mandatory) > no_evidence_target:
        raise RuntimeError(f"{stage}: N10 family count exceeds no-evidence target")
    extra_needed = no_evidence_target - len(mandatory)
    optional = [(b, fam) for b, fam in selected if fam != "N10"]
    optional.sort(key=lambda x: hashlib.sha256(f"{seed}\x1f{x[0]['id']}\x1fno-evidence".encode()).hexdigest())
    extra = {(b["id"], fam) for b, fam in optional[:extra_needed]}
    no_evidence = mandatory | extra

    family_counts = Counter(fam for _, fam in selected)
    source_counts = Counter(b["source"] for b, _ in selected)
    domain_counts = Counter(b["domain"] for b, _ in selected)
    cell_counts = Counter((b["source"], b["domain"]) for b, _ in selected)
    answerability_counts = Counter("no_evidence" if (b["id"], fam) in no_evidence else "answerable" for b, fam in selected)
    digest_rows = sorted(
        f"{b['source']}\x1f{b['domain']}\x1f{b['id']}\x1f{fam}\x1f{int((b['id'], fam) in no_evidence)}"
        for b, fam in selected
    )
    selection_digest = hashlib.sha256("\n".join(digest_rows).encode()).hexdigest()

    expected_sources = POLICY["source_totals"][stage]
    source_share = {k: source_counts[k] / max(1, len(selected)) for k in sorted(source_counts)}
    source_checks = {
        "minimum_source_families": len([k for k, v in source_counts.items() if v > 0]) >= int(POLICY["integrity"]["minimum_source_families_per_stage"]),
        "maximum_source_share": max(source_share.values(), default=0.0) <= float(POLICY["integrity"]["maximum_source_share_per_stage"]),
        "exact_source_totals": all(source_counts[k] == int(v) for k, v in expected_sources.items() if k != "total"),
    }
    cell_check = all(cell_counts[cell] == target for cell, target in cell_targets.items())
    family_check = all(family_counts[f] == int(n) for f, n in family_targets.items())
    domain_check = all(domain_counts[dname] == int(n) for dname, n in POLICY["domain_targets"][stage].items())
    answerability_check = (
        answerability_counts["answerable"] == int(POLICY["answerability_targets"][stage]["answerable"])
        and answerability_counts["no_evidence"] == no_evidence_target
    )
    status = "PASS" if (
        achieved == required_total == len(selected)
        and cell_check and family_check and domain_check and answerability_check
        and all(source_checks.values())
    ) else "FAIL"

    result = {
        "status": status,
        "required_flow": required_total,
        "achieved_flow": achieved,
        "selected_count": len(selected),
        "selection_digest_sha256": selection_digest,
        "source_counts": dict(sorted(source_counts.items())),
        "source_shares": source_share,
        "domain_counts": dict(sorted(domain_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "source_domain_counts": {f"{sname}:{dname}": n for (sname, dname), n in sorted(cell_counts.items())},
        "answerability_counts": dict(sorted(answerability_counts.items())),
        "checks": {
            "exact_source_domain_cells": cell_check,
            "exact_domain_targets": domain_check,
            "exact_family_targets": family_check,
            "exact_answerability_targets": answerability_check,
            **source_checks,
        },
        "individual_ids_persisted": false if False else False
    }
    return result, selected_ids


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bases = build_pool()
    used: set[str] = set()
    stages: dict[str, Any] = {}
    overall = "PASS"
    for stage in POLICY["stage_order"]:
        stage_result, selected_ids = solve_stage(stage, int(POLICY["stage_seeds"][stage]), bases, used)
        stages[stage] = stage_result
        if stage_result["status"] != "PASS":
            overall = "FAIL"
            break
        used.update(selected_ids)

    result = {
        "schema_version": "candidate-v13-external-validity-v2-allocation-feasibility-v1",
        "candidate_v13_invoked": False,
        "candidate_v13_imported": False,
        "formal_case_materialized": False,
        "individual_formal_ids_persisted": False,
        "pool_case_count": len(bases),
        "stage_order": POLICY["stage_order"],
        "stages": stages,
        "cross_stage_selected_count": len(used),
        "cross_stage_base_reuse_count": sum(int(stages[s]["selected_count"]) for s in stages) - len(used),
        "status": overall,
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
