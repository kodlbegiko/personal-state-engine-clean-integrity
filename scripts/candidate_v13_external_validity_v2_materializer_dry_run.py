from __future__ import annotations

"""Synthetic-only materializer qualification for Candidate-v13 External Validity v2."""

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity-v2/materialization-dry-run.json"
CONTRACT = json.loads((ROOT / "docs/research/candidate-v13-external-validity-v2/materializer-contract-v2.json").read_text(encoding="utf-8"))
SEED = 42018


def stable_hash(*parts: Any) -> str:
    raw = "\x1f".join(str(x) for x in parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def order_memories(case_id: str, memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(memories, key=lambda m: stable_hash(SEED, case_id, m["id"]))


def transform(case: dict[str, Any]) -> dict[str, Any]:
    memories = order_memories(case["source_record_id"], list(case["memories"]))
    canonical = {
        "source_dataset": case["source_dataset"],
        "source_revision": case["source_revision"],
        "source_record_id": case["source_record_id"],
        "source_message_ids": list(case["source_message_ids"]),
        "adapter_version": case["adapter_version"],
        "domain": case["domain"],
        "gold_ids": list(case["gold_ids"]),
        "query": case["query"],
        "memories": memories,
    }
    canonical["transformation_hash"] = stable_hash(json.dumps(canonical, sort_keys=True, separators=(",", ":")))
    return canonical


def validate(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    req = CONTRACT["case_requirements"]
    memories = case["memories"]
    ids = [m["id"] for m in memories]
    gold = set(case["gold_ids"])
    if len(memories) < int(req["minimum_memory_count"]):
        errors.append("minimum_memory_count")
    if len([x for x in ids if x not in gold]) < int(req["minimum_non_gold_distractors"]):
        errors.append("minimum_non_gold_distractors")
    if len(ids) != len(set(ids)):
        errors.append("unique_memory_ids")
    if not gold or not gold.issubset(set(ids)):
        errors.append("gold_ids_subset_of_memory_ids")
    if any(sorted(m) != ["id", "text", "timestamp"] for m in memories):
        errors.append("runtime_memory_fields")
    return errors


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    synthetic = {
        "source_dataset": "synthetic-v2-contract-test",
        "source_revision": "0" * 40,
        "source_record_id": "synthetic-record-1",
        "source_message_ids": [f"m{i}" for i in range(1, 6)],
        "adapter_version": "candidate-v13-external-validity-v2-adapter-policy-v2",
        "domain": "D6",
        "gold_ids": ["m3"],
        "query": "Which device configuration did the synthetic user select?",
        "memories": [
            {"id": "m1", "text": "Synthetic distractor one.", "timestamp": "2026-01-01T00:00:00Z"},
            {"id": "m2", "text": "Synthetic distractor two.", "timestamp": "2026-01-02T00:00:00Z"},
            {"id": "m3", "text": "Synthetic gold memory.", "timestamp": "2026-01-03T00:00:00Z"},
            {"id": "m4", "text": "Synthetic distractor four.", "timestamp": "2026-01-04T00:00:00Z"},
            {"id": "m5", "text": "Synthetic distractor five.", "timestamp": "2026-01-05T00:00:00Z"},
        ],
    }
    a = transform(synthetic)
    b = transform(synthetic)
    errors = validate(a)
    runtime_projection = {"query": a["query"], "memories": a["memories"]}
    result = {
        "schema_version": "candidate-v13-external-validity-v2-materialization-dry-run-v2",
        "candidate_v13_invoked": False,
        "candidate_v13_imported": False,
        "formal_case_materialized": False,
        "real_external_payload_materialized": False,
        "synthetic_only": True,
        "deterministic": a == b,
        "transformation_hash_stable": a["transformation_hash"] == b["transformation_hash"],
        "runtime_projection_fields": sorted(runtime_projection.keys()),
        "runtime_memory_fields": sorted(runtime_projection["memories"][0].keys()),
        "memory_count": len(a["memories"]),
        "non_gold_distractor_count": len([m for m in a["memories"] if m["id"] not in set(a["gold_ids"])]),
        "validation_errors": errors,
        "status": "PASS" if a == b and not errors else "FAIL",
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
