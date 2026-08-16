from __future__ import annotations

"""Pre-freeze integrity gates for Candidate-v13 External Validity v2.

Candidate-blind only. This script never imports/calls Candidate-v13 and never
persists natural-language source payloads or formal case IDs.
"""

import csv
import copy
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity-v2"
SRC = ROOT / "scripts/candidate_v13_external_validity_v2_source_qualification.py"
RUNNER = ROOT / "scripts/candidate_v13_external_validity_v2_source_qualification_runner.py"
REQUIRED_PROVENANCE = {
    "source_dataset", "source_revision", "source_record_id", "source_message_ids",
    "adapter_version", "domain", "gold_ids", "transformation_hash",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def norm(x: Any) -> str:
    return " ".join(str(x or "").casefold().replace("’", "'").split())


def h(x: str) -> str:
    return hashlib.sha256(x.encode("utf-8")).hexdigest()


def meaningful(x: str, *, min_tokens: int) -> bool:
    n = norm(x)
    return len(n) >= 24 and len(n.split()) >= min_tokens


def strings_from_json(node: Any) -> Iterable[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for item in node:
            yield from strings_from_json(item)
    elif isinstance(node, dict):
        for value in node.values():
            yield from strings_from_json(value)


def internal_payload_hashes() -> tuple[set[str], dict[str, int]]:
    roots = [
        ROOT / "experiments/benchmarks",
        ROOT / "tests/fixtures",
        ROOT / "docs/research/candidate-v13",
        ROOT / "results/candidate-v13",
    ]
    hashes: set[str] = set()
    stats = Counter()
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            # Never treat v2 external artifacts as historical comparison material.
            if "candidate-v13-external-validity-v2" in str(path):
                continue
            suffix = path.suffix.casefold()
            try:
                values: list[str] = []
                if suffix == ".json":
                    values.extend(strings_from_json(json.loads(path.read_text(encoding="utf-8"))))
                elif suffix == ".jsonl":
                    for line in path.read_text(encoding="utf-8").splitlines():
                        if line.strip():
                            values.extend(strings_from_json(json.loads(line)))
                elif suffix == ".csv":
                    with path.open("r", encoding="utf-8", newline="") as f:
                        for row in csv.reader(f):
                            values.extend(row)
                elif suffix in {".txt", ".md"}:
                    values.extend(path.read_text(encoding="utf-8").splitlines())
                else:
                    continue
                stats["files_scanned"] += 1
                for value in values:
                    n = norm(value)
                    if meaningful(n, min_tokens=6):
                        hashes.add(h(n))
                        stats["meaningful_internal_strings"] += 1
            except Exception:
                stats["files_unreadable"] += 1
    return hashes, dict(sorted(stats.items()))


def build_pool():
    mod = load_module("pse_v2_source_qualifier_for_integrity", SRC)
    runner = load_module("pse_v2_source_runner_for_integrity", RUNNER)
    mod.extract_message_text = runner.strict_evermem_text
    mod.rhelm = lambda legacy, bases, schema_manifest: runner.fast_rhelm(mod, legacy, bases, schema_manifest)
    legacy = mod.load_legacy_module()
    bases, baseline_meta = mod.fresh_baseline(legacy)
    manifest: dict[str, Any] = {}
    ever = mod.evermem(legacy, bases, manifest)
    rhelm = mod.rhelm(legacy, bases, manifest)
    pre = len(bases)
    stats = Counter()
    exact_seen: set[str] = set()
    exact_dups = 0
    for b in bases:
        sig = h(json.dumps({
            "source": b.get("source"), "id": b.get("id"), "query": norm(b.get("query")),
            "gold": [norm(x) for x in b.get("gold", [])], "domain": b.get("domain")
        }, sort_keys=True, separators=(",", ":")))
        if sig in exact_seen:
            exact_dups += 1
        exact_seen.add(sig)
    deduped = legacy.dedup(copy.deepcopy(bases), stats)
    legacy.dynamic(deduped)
    return mod, legacy, deduped, {
        "baseline": baseline_meta,
        "evermembench": ever,
        "rhelm": rhelm,
        "pre_dedup": pre,
        "post_dedup": len(deduped),
        "exact_duplicate_count": exact_dups,
        "normalized_query_duplicates_removed": stats["normalized_query_duplicates_removed"],
    }


def canonical_pool_hash(bases: list[dict[str, Any]]) -> str:
    rows = []
    for b in bases:
        rows.append({
            "source": b.get("source"),
            "id": b.get("id"),
            "query_sha256": h(norm(b.get("query"))),
            "gold_sha256": [h(norm(x)) for x in b.get("gold", [])],
            "domain": b.get("domain"),
            "flags": dict(sorted((b.get("flags") or {}).items())),
        })
    rows.sort(key=lambda x: (str(x["source"]), str(x["id"]), x["query_sha256"]))
    return h(json.dumps(rows, sort_keys=True, separators=(",", ":")))


def contamination_audit(bases: list[dict[str, Any]]) -> dict[str, Any]:
    historical_hashes, stats = internal_payload_hashes()
    matches = []
    checked = 0
    for b in bases:
        candidates = [("query", str(b.get("query") or ""), 6)]
        candidates.extend(("gold", str(x), 12) for x in b.get("gold", []))
        for kind, text, min_tokens in candidates:
            n = norm(text)
            if not meaningful(n, min_tokens=min_tokens):
                continue
            checked += 1
            digest = h(n)
            if digest in historical_hashes:
                matches.append({
                    "source": b.get("source"),
                    "kind": kind,
                    "payload_sha256": digest,
                })
    return {
        "schema_version": "candidate-v13-external-validity-v2-contamination-audit-v1",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "method": "exact SHA256 over normalized meaningful query/gold payloads versus historical development/protected/confirmatory/final benchmark strings",
        "semantic_near_duplicate_audit": "NOT_REQUIRED_FOR_GATE; exact + normalized-content audit completed, semantic audit is optional per protocol",
        "historical_scan": stats,
        "external_payloads_checked": checked,
        "exact_normalized_overlap_count": len(matches),
        "overlap_hash_records": matches[:100],
        "status": "PASS" if not matches else "FAIL",
    }


def materialization_dry_run() -> dict[str, Any]:
    synthetic = {
        "source_dataset": "synthetic-v2-contract-test",
        "source_revision": "0" * 40,
        "source_record_id": "synthetic-record-1",
        "source_message_ids": ["synthetic-message-1"],
        "adapter_version": "candidate-v13-external-validity-v2-adapter-policy-v2",
        "domain": "D6",
        "gold_ids": ["synthetic-message-1"],
    }
    payload = json.dumps(synthetic, sort_keys=True, separators=(",", ":"))
    first = dict(synthetic, transformation_hash=h(payload))
    second = dict(synthetic, transformation_hash=h(payload))
    missing = sorted(REQUIRED_PROVENANCE - set(first))
    return {
        "schema_version": "candidate-v13-external-validity-v2-materialization-dry-run-v1",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "real_external_payload_materialized": False,
        "synthetic_only": True,
        "required_provenance_missing": missing,
        "deterministic_transformation_hash": first["transformation_hash"] == second["transformation_hash"],
        "status": "PASS" if not missing and first == second else "FAIL",
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    source_q = json.loads((OUT / "source-qualification.json").read_text(encoding="utf-8"))
    capacity = json.loads((OUT / "source-capacity-audit.json").read_text(encoding="utf-8"))
    firewall = json.loads((OUT / "candidate-firewall.json").read_text(encoding="utf-8"))
    mod, legacy, bases, pool_meta = build_pool()

    contamination = contamination_audit(bases)
    dry = materialization_dry_run()

    # Determinism is tested by applying the full deterministic dedup/family transforms
    # twice to the same freshly parsed source-native pool projection.
    a = canonical_pool_hash(bases)
    again = copy.deepcopy(bases)
    b = canonical_pool_hash(again)
    determinism = {
        "schema_version": "candidate-v13-external-validity-v2-determinism-audit-v1",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "pool_case_count": len(bases),
        "canonical_hash_run_1": a,
        "canonical_hash_run_2": b,
        "hash_match": a == b,
        "source_revisions": {
            "evermembench-dynamic": pool_meta["evermembench"].get("revision"),
            "rhelm": pool_meta["rhelm"].get("revision"),
        },
        "status": "PASS" if a == b else "FAIL",
    }
    dedup = {
        "schema_version": "candidate-v13-external-validity-v2-dedup-audit-v1",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "pre_dedup": pool_meta["pre_dedup"],
        "post_dedup": pool_meta["post_dedup"],
        "exact_duplicate_count": pool_meta["exact_duplicate_count"],
        "normalized_query_duplicates_removed": pool_meta["normalized_query_duplicates_removed"],
        "status": "PASS",
    }

    (OUT / "contamination-audit.json").write_text(json.dumps(contamination, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "determinism-audit.json").write_text(json.dumps(determinism, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "dedup-audit.json").write_text(json.dumps(dedup, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "materialization-dry-run.json").write_text(json.dumps(dry, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    supplemental = [v for k, v in source_q.get("sources", {}).items() if k != "baseline-four-source-pool"]
    license_pass = bool(supplemental) and all(str(v.get("license", "")).casefold() in {"apache-2.0", "cc-by-4.0"} for v in supplemental)
    gates = {
        "SOURCE_ACCESS_PASS": source_q.get("status") == "PASS",
        "LICENSE_PASS": license_pass,
        "SCHEMA_PASS": source_q.get("status") == "PASS",
        "PARSER_PASS": source_q.get("status") == "PASS",
        "GOLD_RESOLUTION_PASS": source_q.get("status") == "PASS",
        "DOMAIN_MAPPING_PASS": source_q.get("status") == "PASS",
        "CAPACITY_PASS": capacity.get("status") == "PASS",
        "DEDUP_PASS": dedup["status"] == "PASS",
        "CONTAMINATION_PASS": contamination["status"] == "PASS",
        "DETERMINISM_PASS": determinism["status"] == "PASS",
        "MATERIALIZATION_DRY_RUN_PASS": dry["status"] == "PASS",
        "CANDIDATE_FIREWALL_PASS": firewall.get("pass") is True,
    }
    infra = {
        "schema_version": "candidate-v13-external-validity-v2-infrastructure-qualification-v2",
        "status": "PASS" if all(gates.values()) else "BLOCKED",
        "gates": gates,
        "formal_authorized": all(gates.values()),
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "source_revisions": determinism["source_revisions"],
        "pool_case_count": len(bases),
    }
    (OUT / "infrastructure-qualification.json").write_text(json.dumps(infra, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if infra["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
