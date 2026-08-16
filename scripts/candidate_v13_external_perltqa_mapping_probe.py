from __future__ import annotations

"""Schema-only PerLTQA mapping probe.

No Candidate-v13 imports/calls. No natural-language text is written to output.
The output contains only aggregate counts, field names, structural paths and
reference-ID shapes needed to establish a deterministic source-native mapping.
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
    req = urllib.request.Request(url, headers={"User-Agent": "pse-perltqa-mapping-probe/2.0"})
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


def refs(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str):
        return [value]
    return []


def type_schema(value: Any, depth: int = 0) -> Any:
    if depth >= 3:
        return type(value).__name__
    if isinstance(value, dict):
        result: dict[str, Any] = {"type": "dict", "keys": sorted(map(str, value.keys()))[:80]}
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
    return re.sub(r"\d+", "N", str(value))


def strip_leading_namespace(ref: str) -> str:
    """Drop exactly the first numeric namespace before the first underscore.

    Dialogue '#turn' suffixes are retained. This is tested only as a source
    structural hypothesis; the probe reports uniqueness rather than assuming it.
    """
    parts = ref.split("_", 1)
    if len(parts) == 2 and parts[0].isdigit():
        return parts[1]
    return ref


def key_suffix_index(container: Any) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    if isinstance(container, dict):
        for key in container:
            out[strip_leading_namespace(str(key))].append(str(key))
    return out


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="perltqa-map-") as td_raw:
        td = Path(td_raw)
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
    for path, record in records:
        section = next((str(x) for x in reversed(path) if str(x) in {"profile", "social_relationship", "events", "dialogues"}), "UNKNOWN")
        section_counts[section] += 1
        ref_shapes[ref_shape(record.get("Reference Memory"))] += 1

    memory_characters = list(mem.keys()) if isinstance(mem, dict) else []
    qa_characters: set[str] = set()
    for path, _ in records:
        for x in path:
            if isinstance(x, str) and isinstance(mem, dict) and x in mem:
                qa_characters.add(x)
                break

    section_schemas: dict[str, Any] = {}
    first_common = next((c for c in memory_characters if c in qa_characters), None)
    if first_common:
        char = mem[first_common]
        for section in ["profile", "profile_description", "social_relationship", "events", "dialogues"]:
            if isinstance(char, dict) and section in char:
                section_schemas[section] = type_schema(char[section])

    # Evaluate source-structural mapping hypotheses without exposing QA text.
    mapping = Counter()
    section_mapping: dict[str, Counter[str]] = defaultdict(Counter)
    namespace_pair_counts: Counter[str] = Counter()
    suffix_collision_counts: Counter[str] = Counter()
    reference_cardinality = Counter()

    for path, record in records:
        char_name = next((x for x in path if isinstance(x, str) and isinstance(mem, dict) and x in mem), None)
        section = next((str(x) for x in reversed(path) if str(x) in {"profile", "social_relationship", "events", "dialogues"}), None)
        rlist = refs(record.get("Reference Memory"))
        reference_cardinality[len(rlist)] += 1
        if not char_name or not section:
            mapping["missing_character_or_section"] += 1
            section_mapping[section or "UNKNOWN"]["missing_character_or_section"] += 1
            continue
        target = mem[char_name].get(section) if isinstance(mem[char_name], dict) else None
        if section == "profile":
            if isinstance(target, dict) and rlist and all(ref in target for ref in rlist):
                mapping["profile_direct_exact"] += 1
                section_mapping[section]["direct_exact"] += 1
            else:
                mapping["profile_unresolved"] += 1
                section_mapping[section]["unresolved"] += 1
            continue
        if not isinstance(target, dict) or not rlist:
            mapping["nonprofile_unresolved_structure"] += 1
            section_mapping[section]["unresolved_structure"] += 1
            continue

        exact_ok = all(ref in target for ref in rlist)
        if exact_ok:
            mapping["nonprofile_exact_same_character"] += 1
            section_mapping[section]["exact_same_character"] += 1
            continue

        suffix_idx = key_suffix_index(target)
        suffix_matches = [suffix_idx.get(strip_leading_namespace(ref), []) for ref in rlist]
        unique_suffix_ok = all(len(matches) == 1 for matches in suffix_matches)
        if unique_suffix_ok:
            mapping["nonprofile_unique_suffix_same_character"] += 1
            section_mapping[section]["unique_suffix_same_character"] += 1
            for ref, matches in zip(rlist, suffix_matches):
                src_prefix = ref.split("_", 1)[0] if "_" in ref else "NO_PREFIX"
                dst = matches[0]
                dst_prefix = dst.split("_", 1)[0] if "_" in dst else "NO_PREFIX"
                namespace_pair_counts[f"{src_prefix}->{dst_prefix}"] += 1
            continue

        if any(len(matches) > 1 for matches in suffix_matches):
            mapping["nonprofile_suffix_collision"] += 1
            section_mapping[section]["suffix_collision"] += 1
            for matches in suffix_matches:
                if len(matches) > 1:
                    suffix_collision_counts[str(len(matches))] += 1
        else:
            mapping["nonprofile_suffix_missing"] += 1
            section_mapping[section]["suffix_missing"] += 1

    result = {
        "schema_version": "perltqa-mapping-probe-v2",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "repository": REPO,
        "revision": REV,
        "source_sha256": {"memory": mem_sha, "qa": qa_sha},
        "canonical_qa_records": len(records),
        "qa_path_depth_counts": dict(sorted(path_depths.items())),
        "qa_section_counts": dict(sorted(section_counts.items())),
        "reference_id_shape_counts": dict(sorted(ref_shapes.items(), key=lambda kv: (-kv[1], kv[0]))),
        "reference_cardinality_counts": dict(sorted(reference_cardinality.items())),
        "memory_character_count": len(memory_characters),
        "qa_character_count_resolved_against_memory": len(qa_characters),
        "first_common_character_redacted": bool(first_common),
        "memory_section_schemas": section_schemas,
        "mapping_hypothesis_counts": dict(sorted(mapping.items())),
        "mapping_by_section": {k: dict(sorted(v.items())) for k, v in sorted(section_mapping.items())},
        "namespace_prefix_pair_counts_for_unique_suffix_matches": dict(sorted(namespace_pair_counts.items())),
        "suffix_collision_multiplicity_counts": dict(sorted(suffix_collision_counts.items())),
        "mapping_rule_under_test": "For non-profile records only: if exact Reference Memory key is absent in the QA character's section, strip exactly the first numeric namespace component from both reference and candidate memory keys and require a unique suffix match within that same character and section. No text/content matching is used.",
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
