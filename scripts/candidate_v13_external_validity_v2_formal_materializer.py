from __future__ import annotations

"""Deterministic source-native formal case materializer.

This module is candidate-blind. It operates only on the already-qualified base
pool and private pre-freeze allocation assignments. It never imports or calls
Candidate-v13.
"""

import hashlib
import json
from collections import defaultdict
from typing import Any

MIN_MEMORIES = 5
MIN_DISTRACTORS = 4
MAX_MEMORIES = 80
ADAPTER_VERSION = "candidate-v13-external-validity-v2-adapter-policy-v2"
MATERIALIZER_VERSION = "candidate-v13-external-validity-v2-formal-materializer-v1"


def norm(x: Any) -> str:
    return " ".join(str(x or "").casefold().replace("’", "'").split())


def sha(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(str(x) for x in parts).encode("utf-8")).hexdigest()


def memory_id(base: dict[str, Any], gold_index: int, text: str) -> str:
    return "m-" + sha(base["source"], base["id"], gold_index, norm(text))[:32]


def source_revision(base: dict[str, Any], revisions: dict[str, str]) -> str:
    value = revisions.get(str(base["source"]))
    if not value:
        raise RuntimeError(f"missing pinned source revision for {base['source']}")
    return value


def base_memories(base: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for i, text in enumerate(base.get("gold", [])):
        if not norm(text):
            continue
        out.append({
            "id": memory_id(base, i, text),
            "text": str(text),
            "timestamp": None,
            "_source_base_id": str(base["id"]),
            "_source_subject": str(base.get("subject", "")),
            "_source_relation": str(base.get("relation", "")),
            "_source_domain": str(base["domain"]),
            "_source_dataset": str(base["source"]),
        })
    return out


def distractor_priority(target: dict[str, Any], other: dict[str, Any]) -> int:
    if str(other["source"]) != str(target["source"]):
        return 9
    same_subject = norm(other.get("subject")) == norm(target.get("subject")) and bool(norm(target.get("subject")))
    same_relation = norm(other.get("relation")) == norm(target.get("relation")) and bool(norm(target.get("relation")))
    same_domain = str(other["domain"]) == str(target["domain"])
    if same_subject and same_relation:
        return 0
    if same_subject:
        return 1
    if same_domain:
        return 2
    return 9


def build_distractor_index(bases: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for base in bases:
        if base.get("gold"):
            by_source[str(base["source"])].append(base)
    return by_source


def materialize_case(
    assignment: dict[str, Any],
    bases_by_id: dict[tuple[str, str], dict[str, Any]],
    distractor_index: dict[str, list[dict[str, Any]]],
    revisions: dict[str, str],
    stage_seed: int,
) -> dict[str, Any]:
    source = str(assignment["source"])
    base_id = str(assignment["id"])
    base = bases_by_id.get((source, base_id))
    if base is None:
        raise RuntimeError(f"selected base missing: {source}:{base_id}")
    if str(base["domain"]) != str(assignment["domain"]):
        raise RuntimeError(f"selected base domain mismatch: {source}:{base_id}")

    gold_units = base_memories(base)
    if not gold_units:
        raise RuntimeError(f"selected base has no materializable gold: {source}:{base_id}")
    if len(gold_units) > MAX_MEMORIES:
        raise RuntimeError(f"selected base gold exceeds runtime maximum: {source}:{base_id}")
    gold_ids = [m["id"] for m in gold_units]
    gold_text_hashes = {sha(norm(m["text"])) for m in gold_units}
    no_evidence = bool(assignment["no_evidence"])

    candidate_memories: list[dict[str, Any]] = [] if no_evidence else list(gold_units)
    existing_ids = {m["id"] for m in candidate_memories}
    existing_text = {sha(norm(m["text"])) for m in candidate_memories}

    pool = []
    for other in distractor_index.get(source, []):
        if str(other["id"]) == base_id:
            continue
        priority = distractor_priority(base, other)
        if priority >= 9:
            continue
        for unit in base_memories(other):
            text_hash = sha(norm(unit["text"]))
            # In a no-evidence transform, source-native target evidence must not
            # reappear through a duplicate distractor from another source record.
            if text_hash in gold_text_hashes:
                continue
            if unit["id"] in existing_ids or text_hash in existing_text:
                continue
            key = sha(stage_seed, source, base_id, priority, other["id"], unit["id"])
            pool.append((priority, key, unit))
    pool.sort(key=lambda x: (x[0], x[1], x[2]["id"]))

    for _, _, unit in pool:
        if len(candidate_memories) >= MAX_MEMORIES:
            break
        if unit["id"] in existing_ids:
            continue
        text_hash = sha(norm(unit["text"]))
        if text_hash in existing_text:
            continue
        candidate_memories.append(unit)
        existing_ids.add(unit["id"])
        existing_text.add(text_hash)

    runtime_gold = [] if no_evidence else gold_ids
    non_gold = [m for m in candidate_memories if m["id"] not in set(runtime_gold)]
    if len(candidate_memories) < MIN_MEMORIES:
        raise RuntimeError(f"materialized memory count < {MIN_MEMORIES}: {source}:{base_id}")
    if len(non_gold) < MIN_DISTRACTORS:
        raise RuntimeError(f"materialized distractors < {MIN_DISTRACTORS}: {source}:{base_id}")
    if len(candidate_memories) > MAX_MEMORIES:
        raise RuntimeError(f"materialized memory count > {MAX_MEMORIES}: {source}:{base_id}")
    if len({m["id"] for m in candidate_memories}) != len(candidate_memories):
        raise RuntimeError(f"duplicate runtime memory IDs: {source}:{base_id}")
    if not set(runtime_gold).issubset({m["id"] for m in candidate_memories}):
        raise RuntimeError(f"runtime gold not subset of memories: {source}:{base_id}")
    if no_evidence and any(sha(norm(m["text"])) in gold_text_hashes for m in candidate_memories):
        raise RuntimeError(f"withheld gold text leaked into no-evidence runtime: {source}:{base_id}")

    # Remove provenance helper fields before runtime projection is ever possible.
    clean_memories = [
        {"id": m["id"], "text": m["text"], "timestamp": m["timestamp"]}
        for m in candidate_memories
    ]
    clean_memories.sort(key=lambda m: sha(stage_seed, source, base_id, "runtime-order", m["id"]))

    provenance = {
        "source_dataset": source,
        "source_revision": source_revision(base, revisions),
        "source_record_id": base_id,
        "source_message_ids": gold_ids,
        "adapter_version": ADAPTER_VERSION,
        "materializer_version": MATERIALIZER_VERSION,
        "domain": str(base["domain"]),
        "gold_ids": gold_ids,
        "primary_family": str(assignment["primary_family"]),
        "no_evidence": no_evidence,
    }
    transformation_hash = sha(json.dumps({
        **provenance,
        "query": str(base["query"]),
        "runtime_gold": runtime_gold,
        "memories": clean_memories,
    }, sort_keys=True, separators=(",", ":")))

    return {
        **provenance,
        "transformation_hash": transformation_hash,
        "query": str(base["query"]),
        "memories": clean_memories,
        "answerable": not no_evidence,
        "relevant_memory_ids": runtime_gold,
        "withheld_gold_ids": gold_ids if no_evidence else [],
    }


def materialize_stage(
    assignments: list[dict[str, Any]],
    bases: list[dict[str, Any]],
    revisions: dict[str, str],
    stage_seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    bases_by_id = {(str(b["source"]), str(b["id"])): b for b in bases}
    if len(bases_by_id) != len(bases):
        raise RuntimeError("qualified base pool contains duplicate source/base IDs")
    distractors = build_distractor_index(bases)
    cases = [
        materialize_case(a, bases_by_id, distractors, revisions, stage_seed)
        for a in assignments
    ]
    if len({(c["source_dataset"], c["source_record_id"]) for c in cases}) != len(cases):
        raise RuntimeError("formal materialization reused a source/base ID within stage")
    digest = sha("\n".join(sorted(c["transformation_hash"] for c in cases)))
    summary = {
        "schema_version": "candidate-v13-external-validity-v2-materialization-summary-v1",
        "candidate_v13_invoked": False,
        "case_count": len(cases),
        "answerable_count": sum(c["answerable"] for c in cases),
        "no_evidence_count": sum(not c["answerable"] for c in cases),
        "minimum_memory_count": min((len(c["memories"]) for c in cases), default=0),
        "maximum_memory_count": max((len(c["memories"]) for c in cases), default=0),
        "transformation_digest_sha256": digest,
        "status": "PASS",
    }
    return cases, summary
