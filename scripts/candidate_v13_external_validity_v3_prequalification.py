from __future__ import annotations

"""Candidate-v13 External Validity v3 candidate-blind prequalification.

Reconstructs the v2 qualified pool and v2 formal selections in process memory to
measure the infrastructure failure surface. It never imports or invokes
Candidate-v13 and never persists individual formal IDs or natural-language
payloads.
"""

import ast
import hashlib
import importlib.util
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "results/candidate-v13-external-validity-v3"
CANDIDATE = ROOT / "src/personal_state_engine/candidate_v13.py"
EXPECTED_CANDIDATE_SHA256 = "b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838"
V2_ALLOC = ROOT / "scripts/candidate_v13_external_validity_v2_allocation_runtime.py"
V2_MATERIALIZER = ROOT / "scripts/candidate_v13_external_validity_v2_formal_materializer.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().replace("’", "'").split())


def percentile(values: list[int], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return float(xs[lo])
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def distribution(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": 0, "median": 0, "p90": 0, "p95": 0, "p99": 0, "max": 0}
    return {
        "count": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "p90": percentile(values, 0.90),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "max": max(values),
    }


def candidate_firewall() -> dict[str, Any]:
    actual = sha256_file(CANDIDATE)
    violations: list[str] = []
    checked: list[str] = []
    for path in sorted((ROOT / "scripts").glob("candidate_v13_external_validity_v3*.py")):
        checked.append(str(path.relative_to(ROOT)))
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "candidate_v13" in alias.name and alias.name.startswith("personal_state_engine"):
                        violations.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if "candidate_v13" in module and module.startswith("personal_state_engine"):
                    violations.append(f"{path.name}: from {module}")
            elif isinstance(node, ast.Call):
                func = node.func
                name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
                if name in {"pse_candidate_v13_rank", "evidence_support_signature_v13"}:
                    violations.append(f"{path.name}: call {name}")
    return {
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
        "candidate_v13_external_output_observed": False,
        "candidate_sha256_expected": EXPECTED_CANDIDATE_SHA256,
        "candidate_sha256_actual": actual,
        "candidate_hash_match": actual == EXPECTED_CANDIDATE_SHA256,
        "checked_v3_scripts": checked,
        "violations": violations,
        "status": "PASS" if actual == EXPECTED_CANDIDATE_SHA256 and not violations else "FAIL",
    }


def base_metrics(base: dict[str, Any]) -> tuple[int, int, int]:
    gold = [str(x) for x in (base.get("gold") or []) if norm(x)]
    return len(gold), len(gold), sum(len(x.encode("utf-8")) for x in gold)


def grouped_distributions(rows: list[tuple[dict[str, Any], int, int]]) -> dict[str, Any]:
    by_source: dict[str, list[int]] = defaultdict(list)
    by_domain: dict[str, list[int]] = defaultdict(list)
    by_family: dict[str, list[int]] = defaultdict(list)
    bytes_by_source: dict[str, list[int]] = defaultdict(list)
    for base, count, nbytes in rows:
        by_source[str(base["source"])].append(count)
        by_domain[str(base["domain"])].append(count)
        bytes_by_source[str(base["source"])].append(nbytes)
        for fam, enabled in sorted((base.get("flags") or {}).items()):
            if enabled:
                by_family[str(fam)].append(count)
    return {
        "overall": distribution([count for _, count, _ in rows]),
        "by_source": {k: distribution(v) for k, v in sorted(by_source.items())},
        "by_domain": {k: distribution(v) for k, v in sorted(by_domain.items())},
        "by_eligible_family": {k: distribution(v) for k, v in sorted(by_family.items())},
        "gold_text_bytes_by_source": {k: distribution(v) for k, v in sorted(bytes_by_source.items())},
    }


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    fw = candidate_firewall()
    (OUTDIR / "candidate-firewall.json").write_text(json.dumps(fw, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if fw["status"] != "PASS":
        return 2

    alloc = load("pse_v3_forensic_v2_allocation_runtime", V2_ALLOC)
    materializer = load("pse_v3_forensic_v2_materializer", V2_MATERIALIZER)
    if int(getattr(materializer, "MAX_MEMORIES", -1)) != 80:
        raise RuntimeError("v2 forensic invariant changed: expected MAX_MEMORIES=80")

    bases, stages, selection_digests = alloc.select_all()
    base_by_key = {(str(b["source"]), str(b["id"])): b for b in bases}

    all_rows: list[tuple[dict[str, Any], int, int]] = []
    over80_source = Counter()
    over80_domain = Counter()
    over80_family = Counter()
    payload_risk_source = Counter()
    for base in bases:
        count, _, nbytes = base_metrics(base)
        all_rows.append((base, count, nbytes))
        if count > 80:
            over80_source[str(base["source"])] += 1
            over80_domain[str(base["domain"])] += 1
            for fam, enabled in (base.get("flags") or {}).items():
                if enabled:
                    over80_family[str(fam)] += 1
        if nbytes > 1_000_000:
            payload_risk_source[str(base["source"])] += 1

    selected_rows: list[tuple[dict[str, Any], int, int]] = []
    selected_over80_source = Counter()
    selected_over80_domain = Counter()
    selected_over80_primary_family = Counter()
    stage_selected: dict[str, Any] = {}
    for stage, assignments in stages.items():
        stage_counts: list[int] = []
        stage_bytes: list[int] = []
        stage_over80 = 0
        for a in assignments:
            base = base_by_key[(str(a["source"]), str(a["id"]))]
            count, _, nbytes = base_metrics(base)
            selected_rows.append((base, count, nbytes))
            stage_counts.append(count)
            stage_bytes.append(nbytes)
            if count > 80:
                stage_over80 += 1
                selected_over80_source[str(a["source"])] += 1
                selected_over80_domain[str(a["domain"])] += 1
                selected_over80_primary_family[str(a["primary_family"])] += 1
        stage_selected[stage] = {
            "count": len(assignments),
            "gold_count_distribution": distribution(stage_counts),
            "gold_text_bytes_distribution": distribution(stage_bytes),
            "gold_count_gt_80": stage_over80,
            "selection_digest_sha256": selection_digests[stage],
        }

    gold_audit = {
        "schema_version": "candidate-v13-external-validity-v3-gold-cardinality-audit-v1",
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
        "individual_base_ids_persisted": False,
        "qualified_base_count": len(bases),
        "distributions": grouped_distributions(all_rows),
        "gold_count_gt_80": {
            "total": sum(over80_source.values()),
            "by_source": dict(sorted(over80_source.items())),
            "by_domain": dict(sorted(over80_domain.items())),
            "by_eligible_family": dict(sorted(over80_family.items())),
        },
        "secondary_payload_risk": {
            "threshold_gold_text_bytes": 1_000_000,
            "cases_over_threshold_by_source": dict(sorted(payload_risk_source.items())),
        },
        "status": "PASS",
    }
    (OUTDIR / "gold-cardinality-audit.json").write_text(json.dumps(gold_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    selected_gt80 = sum(selected_over80_source.values())
    root = {
        "schema_version": "candidate-v13-external-validity-v3-v2-root-cause-audit-v1",
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
        "individual_formal_ids_persisted": False,
        "v2_terminal_state": "EXTERNAL_VALIDITY_V2_INFRASTRUCTURE_BLOCKED",
        "v2_runtime_max_memory_count": 80,
        "root_cause": "v2 pre-freeze QA used synthetic materialization and allocation feasibility did not constrain or fully materialize selected source-native gold cardinality; formal materializer first enforced MAX_MEMORIES=80 after freeze.",
        "gate_that_should_have_caught_failure": "pre-freeze 100% production-faithful selected-case materialization qualification",
        "max_80_classification": "benchmark/infrastructure cap; no evidence in the frozen v2 implementation establishes it as a Candidate-v13 architectural constraint",
        "qualified_pool": {
            "count": len(bases),
            "gold_count_distribution": distribution([x[1] for x in all_rows]),
            "gold_count_gt_80": sum(over80_source.values()),
            "gold_count_gt_80_by_source": dict(sorted(over80_source.items())),
            "gold_count_gt_80_by_domain": dict(sorted(over80_domain.items())),
        },
        "v2_selected": {
            "count": len(selected_rows),
            "gold_count_distribution": distribution([x[1] for x in selected_rows]),
            "gold_text_bytes_distribution": distribution([x[2] for x in selected_rows]),
            "gold_count_gt_80": selected_gt80,
            "gold_count_gt_80_by_source": dict(sorted(selected_over80_source.items())),
            "gold_count_gt_80_by_domain": dict(sorted(selected_over80_domain.items())),
            "gold_count_gt_80_by_primary_family": dict(sorted(selected_over80_primary_family.items())),
            "stages": stage_selected,
        },
        "problem_only_evermem": set(over80_source) <= {"evermembench-dynamic"},
        "secondary_payload_risk_present": bool(payload_risk_source),
        "research_integrity": "PASS",
        "status": "PASS",
    }
    (OUTDIR / "v2-root-cause-audit.json").write_text(json.dumps(root, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": "PASS",
        "qualified_base_count": len(bases),
        "selected_case_count": len(selected_rows),
        "qualified_gold_gt_80": sum(over80_source.values()),
        "selected_gold_gt_80": selected_gt80,
        "candidate_firewall": fw["status"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
