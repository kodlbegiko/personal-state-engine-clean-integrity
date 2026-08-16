from __future__ import annotations

"""Schema-only PerLTQA mapping probe.

No Candidate-v13 imports/calls. No natural-language text is written to output.
The output contains only counts, field names, structural paths and reference IDs
needed to implement a deterministic Reference Memory -> memory-record mapping.
"""

import hashlib
import json
import re
import tempfile
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity/perltqa-mapping-probe.json"
REPO = "Elvin-Yiming-Du/PerLTQA"
REV = "8d9e19868e239740ef701e603ec205cd581f221b"


def download(rel: str, dst: Path) -> str:
    url = f"https://raw.githubusercontent.com/{REPO}/{REV}/{rel}"
    req = urllib.request.Request(url, headers={"User-Agent": "pse-perltqa-mapping-probe/1.0"})
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=300) as src, dst.open("wb") as out:
        while True:
            block = src.read(1024 * 1024)
            if not block:
                break
            h.update(block)
            out.write(block)
    return h.hexdigest()


def walk_qa(node: Any, path: tuple[Any, ...] = ()) -> Iterator[tuple[tuple[Any, ...], dict[str, Any]]]:
    if isinstance(node, dict):
        if {"Question", "Answer", "Reference Memory"}.issubset(node):
            yield path, node
            return
        for k, v in node.items():
            yield from walk_qa(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_qa(v, path + (i,))


def type_schema(value: Any, depth: int = 0) -> Any:
    if depth >= 3:
        return type(value).__name__
    if isinstance(value, dict):
        result = {"type": "dict", "keys": sorted(map(str, value.keys()))[:80]}
        child = next(iter(value.values()), None)
        if child is not None:
            result["sample_value_schema"] = type_schema(child, depth + 1)
        return result
    if isinstance(value, list):
        result = {"type": "list", "length": len(value)}
        if value:
            result["sample_item_schema"] = type_schema(value[0], depth + 1)
        return result
    return type(value).__name__


def ref_shape(value: Any) -> str:
    s = str(value)
    return re.sub(r"\d+", "N", s)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="perltqa-map-") as td:
        td = Path(td)
        mem_path = td / "mem.json"
        qa_path = td / "qa.json"
        mem_sha = download("Dataset/en_v2/perltmem_en_v2.json", mem_path)
        qa_sha = download("Dataset/en_v2/perltqa_en_v2.json", qa_path)
        mem = json.loads(mem_path.read_text(encoding="utf-8"))
        qa = json.loads(qa_path.read_text(encoding="utf-8"))

    records = list(walk_qa(qa))
    path_depths = Counter(len(path) for path, _ in records)
    section_counts: Counter[str] = Counter()
    ref_shapes: Counter[str] = Counter()
    ref_examples: dict[str, list[str]] = defaultdict(list)
    path_examples: dict[str, list[list[Any]]] = defaultdict(list)
    for path, record in records:
        section = next((str(x) for x in reversed(path) if str(x) in {"profile", "social_relationship", "events", "dialogues"}), "UNKNOWN")
        section_counts[section] += 1
        ref = record.get("Reference Memory")
        shape = ref_shape(ref)
        ref_shapes[shape] += 1
        if len(ref_examples[section]) < 20:
            ref_examples[section].append(str(ref))
        if len(path_examples[section]) < 8:
            safe_path = [x if isinstance(x, int) else str(x) for x in path]
            path_examples[section].append(safe_path)

    memory_characters = list(mem.keys()) if isinstance(mem, dict) else []
    qa_characters: set[str] = set()
    for path, _ in records:
        for x in path:
            if isinstance(x, str) and x in mem:
                qa_characters.add(x)
                break

    section_schemas: dict[str, Any] = {}
    first_common = next((c for c in memory_characters if c in qa_characters), None)
    if first_common:
        char = mem[first_common]
        for section in ["profile", "profile_description", "social_relationship", "events", "dialogues"]:
            if isinstance(char, dict) and section in char:
                section_schemas[section] = type_schema(char[section])

    # Pure structural resolution candidates: interpret underscore-delimited
    # numeric components only against container indexes/keys. Report rates, not text.
    resolution = Counter()
    for path, record in records:
        char_name = next((x for x in path if isinstance(x, str) and x in mem), None)
        section = next((str(x) for x in reversed(path) if str(x) in {"profile", "social_relationship", "events", "dialogues"}), None)
        ref = str(record.get("Reference Memory", ""))
        parts = ref.split("_")
        if not char_name or not section:
            resolution["missing_character_or_section"] += 1
            continue
        target = mem[char_name].get(section) if isinstance(mem[char_name], dict) else None
        if section == "profile":
            # profile references may name a field or use numeric conventions.
            if ref in target if isinstance(target, dict) else False:
                resolution["profile_direct_key"] += 1
            else:
                resolution["profile_needs_rule"] += 1
            continue
        last = parts[-1] if parts else ref
        if isinstance(target, list) and last.isdigit() and 0 <= int(last) < len(target):
            resolution["last_component_list_index"] += 1
        elif isinstance(target, dict) and last in target:
            resolution["last_component_dict_key"] += 1
        else:
            resolution["needs_rule"] += 1

    result = {
        "schema_version": "perltqa-mapping-probe-v1",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "repository": REPO,
        "revision": REV,
        "source_sha256": {"memory": mem_sha, "qa": qa_sha},
        "canonical_qa_records": len(records),
        "qa_path_depth_counts": dict(sorted(path_depths.items())),
        "qa_section_counts": dict(sorted(section_counts.items())),
        "reference_id_shape_counts": dict(sorted(ref_shapes.items(), key=lambda kv: (-kv[1], kv[0]))),
        "reference_id_examples_by_section": dict(ref_examples),
        "qa_path_examples_by_section": dict(path_examples),
        "memory_character_count": len(memory_characters),
        "qa_character_count_resolved_against_memory": len(qa_characters),
        "first_common_character_redacted": bool(first_common),
        "memory_section_schemas": section_schemas,
        "simple_structural_resolution_counts": dict(sorted(resolution.items())),
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
