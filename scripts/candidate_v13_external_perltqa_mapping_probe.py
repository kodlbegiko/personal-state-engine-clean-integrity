from __future__ import annotations

"""Schema-only PerLTQA reference-integrity probe.

No Candidate-v13 imports/calls. No natural-language question, answer, or memory
text is written to output. The probe compares the repository's English v1 and
v2 memory/QA pairs using only structural IDs and aggregate counts so that a
formal adapter is chosen from source integrity rather than model performance.
"""

import hashlib
import json
import tempfile
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity/perltqa-mapping-probe.json"
REPO = "Elvin-Yiming-Du/PerLTQA"
REV = "8d9e19868e239740ef701e603ec205cd581f221b"
SECTIONS = {"profile", "social_relationship", "events", "dialogues"}


def download(rel: str, dst: Path) -> str:
    url = f"https://raw.githubusercontent.com/{REPO}/{REV}/{rel}"
    req = urllib.request.Request(url, headers={"User-Agent": "pse-perltqa-reference-integrity-probe/3.0"})
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


def character_from_path(path: tuple[Any, ...], mem: Any) -> str | None:
    if not isinstance(mem, dict):
        return None
    return next((x for x in path if isinstance(x, str) and x in mem), None)


def section_from_path(path: tuple[Any, ...]) -> str | None:
    return next((str(x) for x in path if str(x) in SECTIONS), None)


def global_key_index(mem: Any) -> dict[str, dict[str, set[str]]]:
    index: dict[str, dict[str, set[str]]] = {s: defaultdict(set) for s in SECTIONS}
    if not isinstance(mem, dict):
        return index
    for char_name, char in mem.items():
        if not isinstance(char, dict):
            continue
        for section in SECTIONS:
            container = char.get(section)
            if isinstance(container, dict):
                for key in container:
                    index[section][str(key)].add(str(char_name))
    return index


def analyze_pair(mem: Any, qa: Any) -> dict[str, Any]:
    records = list(walk_qa(qa))
    index = global_key_index(mem)
    counts = Counter()
    by_section: dict[str, Counter[str]] = defaultdict(Counter)
    ref_cardinality = Counter()
    qa_chars: set[str] = set()
    qa_path_char_tokens: Counter[str] = Counter()

    for path, record in records:
        section = section_from_path(path)
        char = character_from_path(path, mem)
        rlist = refs(record.get("Reference Memory"))
        ref_cardinality[len(rlist)] += 1
        if section:
            by_section[section]["qa_records"] += 1
        if char:
            qa_chars.add(char)
        elif any(isinstance(x, str) and x not in SECTIONS for x in path):
            qa_path_char_tokens["unresolved_string_token_present"] += 1
        if not char or not section:
            counts["missing_character_or_section"] += 1
            by_section[section or "UNKNOWN"]["missing_character_or_section"] += 1
            continue
        target = mem[char].get(section) if isinstance(mem[char], dict) else None
        if not isinstance(target, dict) or not rlist:
            counts["unresolved_structure"] += 1
            by_section[section]["unresolved_structure"] += 1
            continue
        if all(ref in target for ref in rlist):
            counts["exact_same_character"] += 1
            by_section[section]["exact_same_character"] += 1
            continue
        global_sets = [index[section].get(ref, set()) for ref in rlist]
        if all(len(chars) == 1 for chars in global_sets):
            counts["exact_global_unique"] += 1
            by_section[section]["exact_global_unique"] += 1
        elif all(len(chars) >= 1 for chars in global_sets):
            common = set.intersection(*(set(x) for x in global_sets)) if global_sets else set()
            if len(common) == 1:
                counts["exact_global_common_unique_character"] += 1
                by_section[section]["exact_global_common_unique_character"] += 1
            else:
                counts["exact_global_ambiguous"] += 1
                by_section[section]["exact_global_ambiguous"] += 1
        else:
            counts["reference_key_absent_globally"] += 1
            by_section[section]["reference_key_absent_globally"] += 1

    exact_or_unique = counts["exact_same_character"] + counts["exact_global_unique"] + counts["exact_global_common_unique_character"]
    return {
        "canonical_qa_records": len(records),
        "memory_character_count": len(mem) if isinstance(mem, dict) else 0,
        "qa_character_count_resolved_against_memory": len(qa_chars),
        "reference_cardinality_counts": dict(sorted(ref_cardinality.items())),
        "mapping_counts": dict(sorted(counts.items())),
        "mapping_by_section": {k: dict(sorted(v.items())) for k, v in sorted(by_section.items())},
        "mechanically_resolvable_exact_or_unique_global": exact_or_unique,
        "mechanically_resolvable_fraction": exact_or_unique / len(records) if records else 0.0,
        "unresolved_path_character_token_counts": dict(sorted(qa_path_char_tokens.items())),
        "formal_mapping_policy_candidate": "Prefer same-character exact key. A global exact key may be used only if the Reference Memory key maps to exactly one character in the same section, or multiple reference keys have exactly one common character. No question/answer/memory text matching is permitted."
    }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    versions = {
        "en_v1": ("Dataset/en/perltmem_en.json", "Dataset/en/perltqa_en.json"),
        "en_v2": ("Dataset/en_v2/perltmem_en_v2.json", "Dataset/en_v2/perltqa_en_v2.json"),
    }
    result: dict[str, Any] = {
        "schema_version": "perltqa-reference-integrity-probe-v3",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "repository": REPO,
        "revision": REV,
        "versions": {},
    }
    with tempfile.TemporaryDirectory(prefix="perltqa-ref-") as td_raw:
        td = Path(td_raw)
        for version, (mem_rel, qa_rel) in versions.items():
            mem_path = td / f"{version}-mem.json"
            qa_path = td / f"{version}-qa.json"
            mem_sha = download(mem_rel, mem_path)
            qa_sha = download(qa_rel, qa_path)
            mem = json.loads(mem_path.read_text(encoding="utf-8"))
            qa = json.loads(qa_path.read_text(encoding="utf-8"))
            result["versions"][version] = {
                "paths": {"memory": mem_rel, "qa": qa_rel},
                "source_sha256": {"memory": mem_sha, "qa": qa_sha},
                **analyze_pair(mem, qa),
            }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
