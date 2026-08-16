from __future__ import annotations

"""Pre-performance SGD carry-over memory probe.

Builds no formal cases and never imports/invokes Candidate-v13. It scans the
pinned Schema-Guided Dialogue corpus for naturally elliptical USER turns whose
source-native dialogue state carries a slot/value from an earlier USER turn
where that same slot/value was explicitly span-annotated. The earlier turn is
therefore a deterministic supporting-memory candidate for N11/N5 stress.
Only aggregate counts are persisted.
"""

import hashlib
import io
import json
import re
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity/sgd-carryover-probe.json"
REPO = "google-research-datasets/dstc8-schema-guided-dialogue"
REV = "e852981ae34990f4358979625854259302feaa78"
ARCHIVE = f"https://github.com/{REPO}/archive/{REV}.zip"
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_'’-]*")
COREF = {"he", "she", "they", "them", "their", "his", "her", "hers", "it", "its", "this", "that", "these", "those", "former", "latter"}

DOMAIN_BY_SERVICE_PREFIX = {
    "Calendar": "D3",
    "Events": "D3",
    "Banks": "D4",
    "Media": "D4",
    "Messaging": "D4",
    "Movies": "D4",
    "Music": "D4",
    "Payment": "D4",
    "Services": "D4",
    "Buses": "D5",
    "Flights": "D5",
    "Hotels": "D5",
    "RentalCars": "D5",
    "Ridesharing": "D5",
    "Trains": "D5",
    "Travel": "D5",
}


def norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def tokens(text: str) -> list[str]:
    return [m.group(0).casefold().replace("’", "'") for m in TOKEN_RE.finditer(text)]


def service_domain(service: str) -> str | None:
    prefix = service.split("_", 1)[0]
    return DOMAIN_BY_SERVICE_PREFIX.get(prefix)


def state_values(frame: dict[str, Any]) -> dict[str, set[str]]:
    state = frame.get("state")
    raw = state.get("slot_values") if isinstance(state, dict) else None
    out: dict[str, set[str]] = {}
    if isinstance(raw, dict):
        for slot, values in raw.items():
            if isinstance(values, list):
                normalized = {norm(v) for v in values if norm(v)}
                if normalized:
                    out[str(slot)] = normalized
    return out


def explicit_slots(frame: dict[str, Any]) -> set[str]:
    spans = frame.get("slots")
    if not isinstance(spans, list):
        return set()
    return {str(item.get("slot")) for item in spans if isinstance(item, dict) and item.get("slot")}


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(ARCHIVE, headers={"User-Agent": "pse-sgd-carryover-probe/1.0"})
    with urllib.request.urlopen(req, timeout=300) as response:
        raw = response.read()
    archive_sha = hashlib.sha256(raw).hexdigest()

    counts = Counter()
    domain_counts = Counter()
    service_counts = Counter()
    family_counts = Counter()
    split_counts = Counter()
    dialogue_file_hashes: list[tuple[str, str]] = []

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = sorted(
            name for name in zf.namelist()
            if re.search(r"/(train|dev|test)/dialogues_\d+\.json$", name)
        )
        for name in names:
            split = next(x for x in ["train", "dev", "test"] if f"/{x}/" in name)
            payload = zf.read(name)
            dialogue_file_hashes.append((name.split(f"/{split}/", 1)[1], hashlib.sha256(payload).hexdigest()))
            dialogues = json.loads(payload)
            for dialog in dialogues if isinstance(dialogues, list) else []:
                counts["dialogues"] += 1
                split_counts[split] += 1
                turns = dialog.get("turns") if isinstance(dialog, dict) else None
                if not isinstance(turns, list):
                    continue
                prior_explicit: dict[tuple[str, str, str], list[int]] = defaultdict(list)
                for turn_index, turn in enumerate(turns):
                    if not isinstance(turn, dict) or turn.get("speaker") != "USER":
                        continue
                    utterance = str(turn.get("utterance", ""))
                    qtokens = tokens(utterance)
                    qset = set(qtokens)
                    frames = turn.get("frames")
                    if not isinstance(frames, list):
                        continue
                    # Evaluate carry-over against prior source-native state before
                    # registering this turn's explicit mentions as future evidence.
                    carryover_relations: list[tuple[str, str, str, int]] = []
                    for frame in frames:
                        if not isinstance(frame, dict):
                            continue
                        service = str(frame.get("service", ""))
                        domain = service_domain(service)
                        if domain is None:
                            continue
                        current_state = state_values(frame)
                        current_explicit = explicit_slots(frame)
                        for slot, values in current_state.items():
                            if slot in current_explicit:
                                continue
                            for value in sorted(values):
                                prior = prior_explicit.get((service, slot, value), [])
                                if prior:
                                    carryover_relations.append((service, slot, value, prior[-1]))
                    # Deduplicate by service+slot+gold turn; values can have aliases.
                    unique = {(s, slot, gold): (s, slot, value, gold) for s, slot, value, gold in carryover_relations}
                    for service, slot, _value, gold_turn in unique.values():
                        counts["eligible_carryover_relations"] += 1
                        domain = service_domain(service)
                        assert domain is not None
                        domain_counts[domain] += 1
                        service_counts[service.split("_", 1)[0]] += 1
                        family_counts["N11"] += 1
                        if qset & COREF:
                            family_counts["N5"] += 1
                        if len(qtokens) >= 18 or sum(utterance.count(ch) for ch in [",", ";", "(", ")"]) >= 2:
                            family_counts["N2"] += 1
                        if len(qtokens) <= 12:
                            family_counts["N11_short_le_12"] += 1
                        if not utterance.rstrip().endswith("?"):
                            family_counts["N11_no_terminal_question"] += 1
                        # Same current turn can carry multiple relations.
                        if len(unique) >= 2:
                            family_counts["N4_multi_relation_turn"] += 1
                        counts["gold_prior_turn_distance_sum"] += turn_index - gold_turn
                        counts["gold_prior_turn_distance_max"] = max(counts["gold_prior_turn_distance_max"], turn_index - gold_turn)
                    # Register current explicit slot/value source evidence.
                    for frame in frames:
                        if not isinstance(frame, dict):
                            continue
                        service = str(frame.get("service", ""))
                        if service_domain(service) is None:
                            continue
                        current_state = state_values(frame)
                        for slot in explicit_slots(frame):
                            for value in current_state.get(slot, set()):
                                prior_explicit[(service, slot, value)].append(turn_index)

    digest = hashlib.sha256()
    for rel, value in dialogue_file_hashes:
        digest.update(rel.encode("utf-8")); digest.update(b"\0"); digest.update(value.encode("ascii")); digest.update(b"\n")
    result = {
        "schema_version": "candidate-v13-external-sgd-carryover-probe-v1",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "repository": REPO,
        "revision": REV,
        "archive_sha256": archive_sha,
        "dialogue_file_count": len(dialogue_file_hashes),
        "dialogue_files_combined_sha256": digest.hexdigest(),
        "aggregate_counts": dict(sorted(counts.items())),
        "split_dialogue_counts": dict(sorted(split_counts.items())),
        "domain_eligible_counts": dict(sorted(domain_counts.items())),
        "service_prefix_eligible_counts": dict(sorted(service_counts.items())),
        "structural_eligibility_counts": dict(sorted(family_counts.items())),
        "gold_rule": "For a USER turn/frame, a carried slot/value is eligible when it is present in source-native state.slot_values but the slot is absent from the current frame.slots; gold is the nearest earlier USER turn in the same dialogue/service where frame.slots explicitly names that slot and source-native state.slot_values contains the same normalized value. No language-model inference or text-semantic matching is used.",
        "domain_rule": DOMAIN_BY_SERVICE_PREFIX,
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
