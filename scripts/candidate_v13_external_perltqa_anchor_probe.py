from __future__ import annotations

"""PerLTQA source-native Memory Anchors resolution probe.

No Candidate-v13 import/call. No QA question/answer/memory text is persisted.
The script tests whether PerLTQA's own Memory Anchors can uniquely identify the
referenced memory within the same character and section despite broken public
Reference Memory IDs. Only aggregate counts and source hashes are written.
"""

import hashlib
import json
import tempfile
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity/perltqa-anchor-probe.json"
REPO = "Elvin-Yiming-Du/PerLTQA"
REV = "8d9e19868e239740ef701e603ec205cd581f221b"
MEM_REL = "Dataset/en/perltmem_en.json"
QA_REL = "Dataset/en/perltqa_en.json"
SECTIONS = {"profile", "social_relationship", "events", "dialogues"}


def download(rel: str, dst: Path) -> str:
    req = urllib.request.Request(
        f"https://raw.githubusercontent.com/{REPO}/{REV}/{rel}",
        headers={"User-Agent": "pse-perltqa-anchor-probe/1.0"},
    )
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=300) as src, dst.open("wb") as out:
        while True:
            block = src.read(1024 * 1024)
            if not block:
                break
            h.update(block)
            out.write(block)
    return h.hexdigest()


def normalize_memory(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    out: dict[str, Any] = {}
    if isinstance(raw, list):
        for character in raw:
            if not isinstance(character, dict):
                continue
            profile = character.get("profile")
            name = profile.get("Protagonist") if isinstance(profile, dict) else None
            if isinstance(name, str) and name:
                out[name] = character
    return out


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


def get_char(path: tuple[Any, ...], mem: dict[str, Any]) -> str | None:
    return next((x for x in path if isinstance(x, str) and x in mem), None)


def get_section(path: tuple[Any, ...]) -> str | None:
    return next((str(x) for x in path if str(x) in SECTIONS), None)


def anchor_pairs(value: Any) -> list[tuple[str, int, int]]:
    pairs: list[tuple[str, int, int]] = []
    if not isinstance(value, list):
        return pairs
    for item in value:
        if not isinstance(item, dict):
            continue
        for phrase, span in item.items():
            if not isinstance(phrase, str) or not isinstance(span, list) or len(span) != 2:
                continue
            try:
                start, end = int(span[0]), int(span[1])
            except (TypeError, ValueError):
                continue
            pairs.append((phrase, start, end))
    return pairs


def text_fields(section: str, record: Any) -> list[tuple[str, str]]:
    if section == "profile":
        return [("profile_value", str(record or ""))]
    if not isinstance(record, dict):
        return []
    fields: list[tuple[str, str]] = []
    if section == "events":
        for field in ["content", "summary"]:
            value = record.get(field)
            if isinstance(value, str) and value:
                fields.append((field, value))
    elif section == "social_relationship":
        value = record.get("Description")
        if isinstance(value, str) and value:
            fields.append(("Description", value))
    elif section == "dialogues":
        value = record.get("contents")
        if isinstance(value, str) and value:
            fields.append(("contents", value))
    return fields


def offset_matches(text: str, phrase: str, start: int, end: int) -> bool:
    if start < 0 or end < start:
        return False
    # Test both common half-open and inclusive-end conventions.
    return text[start:end] == phrase or (end < len(text) and text[start:end + 1] == phrase)


def candidate_match_modes(section: str, record: Any, anchors: list[tuple[str, int, int]]) -> set[str]:
    modes: set[str] = set()
    fields = text_fields(section, record)
    if not anchors or not fields:
        return modes
    for field_name, text in fields:
        if all(offset_matches(text, phrase, start, end) for phrase, start, end in anchors):
            modes.add(f"offset:{field_name}")
        if all(phrase in text for phrase, _, _ in anchors):
            modes.add(f"phrase:{field_name}")
    return modes


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="perltqa-anchor-") as td_raw:
        td = Path(td_raw)
        mem_path = td / "mem.json"
        qa_path = td / "qa.json"
        mem_sha = download(MEM_REL, mem_path)
        qa_sha = download(QA_REL, qa_path)
        mem = normalize_memory(json.loads(mem_path.read_text(encoding="utf-8")))
        qa = json.loads(qa_path.read_text(encoding="utf-8"))

    counts = Counter()
    by_section: dict[str, Counter[str]] = defaultdict(Counter)
    mode_counts = Counter()
    anchor_count_hist = Counter()
    unique_offset = 0
    unique_phrase = 0
    unique_any_offset = 0

    for path, row in walk_qa(qa):
        counts["canonical_qa_records"] += 1
        section = get_section(path)
        char = get_char(path, mem)
        if section:
            by_section[section]["qa_records"] += 1
        if not char or not section:
            counts["missing_character_or_section"] += 1
            continue
        anchors = anchor_pairs(row.get("Memory Anchors"))
        anchor_count_hist[len(anchors)] += 1
        if section == "profile":
            refs = row.get("Reference Memory")
            ref = refs[0] if isinstance(refs, list) and refs else refs if isinstance(refs, str) else None
            container = mem[char].get("profile") if isinstance(mem[char], dict) else None
            if isinstance(container, dict) and isinstance(ref, str) and ref in container:
                counts["profile_exact_reference"] += 1
                by_section[section]["profile_exact_reference"] += 1
            else:
                counts["profile_unresolved"] += 1
            continue
        if not anchors:
            counts["nonprofile_no_valid_anchors"] += 1
            by_section[section]["no_valid_anchors"] += 1
            continue
        container = mem[char].get(section) if isinstance(mem[char], dict) else None
        if not isinstance(container, dict):
            counts["nonprofile_missing_container"] += 1
            continue
        mode_to_keys: dict[str, list[str]] = defaultdict(list)
        any_offset_keys: set[str] = set()
        phrase_keys: set[str] = set()
        for key, record in container.items():
            modes = candidate_match_modes(section, record, anchors)
            for mode in modes:
                mode_to_keys[mode].append(str(key))
                if mode.startswith("offset:"):
                    any_offset_keys.add(str(key))
                if mode.startswith("phrase:"):
                    phrase_keys.add(str(key))
        for mode, keys in mode_to_keys.items():
            if len(keys) == 1:
                mode_counts[f"unique_{mode}"] += 1
            elif len(keys) > 1:
                mode_counts[f"ambiguous_{mode}"] += 1
        if len(any_offset_keys) == 1:
            unique_any_offset += 1
            counts["nonprofile_unique_by_any_offset_field"] += 1
            by_section[section]["unique_by_any_offset_field"] += 1
        elif len(any_offset_keys) > 1:
            counts["nonprofile_ambiguous_by_offset"] += 1
            by_section[section]["ambiguous_by_offset"] += 1
        if len(phrase_keys) == 1:
            unique_phrase += 1
            counts["nonprofile_unique_by_anchor_phrase"] += 1
            by_section[section]["unique_by_anchor_phrase"] += 1
        elif len(phrase_keys) > 1:
            counts["nonprofile_ambiguous_by_phrase"] += 1
            by_section[section]["ambiguous_by_phrase"] += 1
        if len(any_offset_keys) == 0 and len(phrase_keys) == 0:
            counts["nonprofile_no_anchor_match"] += 1
            by_section[section]["no_anchor_match"] += 1

    result = {
        "schema_version": "perltqa-anchor-probe-v1",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "repository": REPO,
        "revision": REV,
        "paths": {"memory": MEM_REL, "qa": QA_REL},
        "source_sha256": {"memory": mem_sha, "qa": qa_sha},
        "memory_character_count": len(mem),
        "aggregate_counts": dict(sorted(counts.items())),
        "by_section": {k: dict(sorted(v.items())) for k, v in sorted(by_section.items())},
        "anchor_count_histogram": dict(sorted(anchor_count_hist.items())),
        "mode_uniqueness_counts": dict(sorted(mode_counts.items())),
        "formal_rule_candidate": "Profile: exact Reference Memory field key. Non-profile: within the same QA character and section, require Memory Anchors to identify exactly one memory record by exact source-provided anchor offset against one of the section's canonical text fields. Phrase-only resolution is diagnostic and is not authorized for formal gold unless separately preregistered before Candidate-v13 execution.",
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
