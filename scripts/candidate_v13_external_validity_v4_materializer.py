from __future__ import annotations

"""Production-faithful, candidate-blind materializer for External Validity v4.

Selection/allocation stays in candidate_v13_external_validity_v4_core.py. This
module re-exports that candidate-blind allocation API and replaces only runtime
materialization with an indexed deterministic implementation. No Candidate-v13
import or execution is permitted here.
"""

import hashlib
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE_CORE = ROOT / "scripts/candidate_v13_external_validity_v4_core.py"
MEMORY_POLICY = ROOT / "docs/research/candidate-v13-external-validity-v4/runtime-memory-policy-v3.json"


def _load_base_core():
    name = "pse_v4_candidate_blind_allocation_core"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, BASE_CORE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load v3 allocation core")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_base = _load_base_core()
STAGES = _base.STAGES
STAGE_SEEDS = _base.STAGE_SEEDS
SOURCE_REVISIONS = _base.SOURCE_REVISIONS
fresh_policy = _base.fresh_policy
build_pool = _base.build_pool
select_stage = _base.select_stage
select_all = _base.select_all
sha = _base.sha
norm = _base.norm


def memory_id(base: dict[str, Any], index: int, text: str) -> str:
    return "m-" + sha(base["source"], base["id"], index, norm(text))[:32]


def base_memories(base: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(base.get("gold") or []):
        text = str(raw)
        if not norm(text):
            continue
        out.append({
            "id": memory_id(base, i, text),
            "text": text,
            "timestamp": None,
            "_base": str(base["id"]),
            "_subject": str(base.get("subject", "")),
            "_relation": str(base.get("relation", "")),
            "_domain": str(base["domain"]),
            "_source": str(base["source"]),
        })
    out.sort(key=lambda m: m["id"])
    return out


class MaterializationIndex:
    def __init__(self, bases: list[dict[str, Any]]) -> None:
        self.base_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        self.units_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self.by_subject_relation: dict[tuple[str, str, str], list[tuple[str, str]]] = defaultdict(list)
        self.by_subject: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
        self.by_domain: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
        for base in bases:
            key = (str(base["source"]), str(base["id"]))
            if key in self.base_by_key:
                raise RuntimeError(f"duplicate source/base ID: {key}")
            self.base_by_key[key] = base
            units = base_memories(base)
            self.units_by_key[key] = units
            if not units:
                continue
            source = key[0]
            subject = norm(base.get("subject"))
            relation = norm(base.get("relation"))
            domain = str(base["domain"])
            if subject and relation:
                self.by_subject_relation[(source, subject, relation)].append(key)
            if subject:
                self.by_subject[(source, subject)].append(key)
            self.by_domain[(source, domain)].append(key)
        for mapping in (self.by_subject_relation, self.by_subject, self.by_domain):
            for bucket, rows in mapping.items():
                rows.sort(key=lambda key: sha("v3-materializer-index", *bucket, *key))


_INDEX_CACHE: dict[int, MaterializationIndex] = {}


def get_index(bases: list[dict[str, Any]]) -> MaterializationIndex:
    token = id(bases)
    index = _INDEX_CACHE.get(token)
    if index is None:
        index = MaterializationIndex(bases)
        _INDEX_CACHE.clear()
        _INDEX_CACHE[token] = index
    return index


def cyclic_rows(rows: list[tuple[str, str]], stage_seed: int, source: str, base_id: str, tier: str):
    if not rows:
        return
    offset = int(sha(stage_seed, source, base_id, tier), 16) % len(rows)
    for i in range(len(rows)):
        yield rows[(offset + i) % len(rows)]


def candidate_base_keys(index: MaterializationIndex, base: dict[str, Any], stage_seed: int):
    source = str(base["source"])
    base_id = str(base["id"])
    subject = norm(base.get("subject"))
    relation = norm(base.get("relation"))
    domain = str(base["domain"])
    tiers: list[tuple[str, list[tuple[str, str]]]] = []
    if subject and relation:
        tiers.append(("same-subject-relation", index.by_subject_relation.get((source, subject, relation), [])))
    if subject:
        tiers.append(("same-subject", index.by_subject.get((source, subject), [])))
    tiers.append(("same-domain", index.by_domain.get((source, domain), [])))
    seen: set[tuple[str, str]] = set()
    target_key = (source, base_id)
    for tier, rows in tiers:
        for key in cyclic_rows(rows, stage_seed, source, base_id, tier):
            if key == target_key or key in seen:
                continue
            seen.add(key)
            yield key


def materialize_case(assignment: dict[str, Any], index: MaterializationIndex, stage_seed: int) -> dict[str, Any]:
    source = str(assignment["source"])
    base_id = str(assignment["id"])
    key = (source, base_id)
    base = index.base_by_key.get(key)
    if base is None:
        raise RuntimeError(f"selected base missing: {source}:{base_id}")
    gold = list(index.units_by_key.get(key, []))
    if not gold:
        raise RuntimeError(f"no materializable gold: {source}:{base_id}")

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

    for other_key in candidate_base_keys(index, base, stage_seed):
        for unit in index.units_by_key[other_key]:
            if len(memories) >= target:
                break
            text_hash = sha(norm(unit["text"]))
            if unit["id"] in ids or text_hash in texts or text_hash in gold_text_hashes:
                continue
            memories.append(unit)
            ids.add(unit["id"])
            texts.add(text_hash)
        if len(memories) >= target:
            break

    runtime_gold = [] if no_evidence else gold_ids
    runtime_ids = {m["id"] for m in memories}
    non_gold = [m for m in memories if m["id"] not in set(runtime_gold)]
    if len(memories) != target:
        raise RuntimeError(f"materialized memory target not reached: {source}:{base_id}:{len(memories)}!={target}")
    if len(non_gold) < min_distractors:
        raise RuntimeError(f"insufficient distractors: {source}:{base_id}")
    if not set(runtime_gold).issubset(runtime_ids):
        raise RuntimeError(f"runtime gold loss: {source}:{base_id}")
    if no_evidence and any(sha(norm(m["text"])) in gold_text_hashes for m in memories):
        raise RuntimeError(f"withheld gold leaked: {source}:{base_id}")

    clean = [{"id": m["id"], "text": m["text"], "timestamp": m["timestamp"]} for m in memories]
    clean.sort(key=lambda m: sha(stage_seed, source, base_id, "runtime-order", m["id"]))
    runtime_payload = {"query": str(base["query"]), "memories": clean}
    provenance = {
        "source_dataset": source,
        "source_revision": SOURCE_REVISIONS[source],
        "source_record_id": base_id,
        "domain": str(base["domain"]),
        "primary_family": str(assignment["primary_family"]),
        "no_evidence": no_evidence,
        "gold_ids": gold_ids,
        "runtime_gold_ids": runtime_gold,
    }
    transformation_hash = sha(json.dumps({**provenance, **runtime_payload}, sort_keys=True, separators=(",", ":")))
    payload_hash = sha(json.dumps(runtime_payload, sort_keys=True, separators=(",", ":")))
    return {
        **provenance,
        **runtime_payload,
        "answerable": not no_evidence,
        "relevant_memory_ids": runtime_gold,
        "withheld_gold_ids": gold_ids if no_evidence else [],
        "runtime_target": target,
        "transformation_hash": transformation_hash,
        "runtime_payload_hash": payload_hash,
    }


def materialize_stage(assignments: list[dict[str, Any]], bases: list[dict[str, Any]], stage_seed: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = get_index(bases)
    cases = [materialize_case(a, index, stage_seed) for a in assignments]
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
        "indexed_materializer": True,
        "distractor_selection": "same-subject-relation -> same-subject -> same-domain, deterministic cyclic offset per stage/target/tier",
        "status": "PASS",
    }
