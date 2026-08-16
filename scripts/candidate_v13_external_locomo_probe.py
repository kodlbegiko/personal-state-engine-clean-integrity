from __future__ import annotations

"""Pre-performance LoCoMo source-integrity probe.

No Candidate-v13 import/call. No natural-language question, answer, or dialogue
text is persisted. The probe verifies that source-native QA evidence IDs map
exactly to dialog turn IDs in the pinned LoCoMo release and reports aggregate
category/evidence statistics only.
"""

import hashlib
import json
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity/locomo-probe.json"
REPO = "snap-research/locomo"
REV = "3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376"
DATA_REL = "data/locomo10.json"
LICENSE_REL = "LICENSE.txt"


def fetch(rel: str) -> bytes:
    req = urllib.request.Request(
        f"https://raw.githubusercontent.com/{REPO}/{REV}/{rel}",
        headers={"User-Agent": "pse-locomo-source-probe/1.0"},
    )
    with urllib.request.urlopen(req, timeout=300) as response:
        return response.read()


def as_evidence_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def session_keys(conversation: dict[str, Any]) -> list[str]:
    keys = []
    for key, value in conversation.items():
        if not key.startswith("session_") or key.endswith("_date_time"):
            continue
        if isinstance(value, list):
            suffix = key.removeprefix("session_")
            if suffix.isdigit():
                keys.append(key)
    return sorted(keys, key=lambda k: int(k.removeprefix("session_")))


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    raw = fetch(DATA_REL)
    license_raw = fetch(LICENSE_REL)
    data_sha = hashlib.sha256(raw).hexdigest()
    license_sha = hashlib.sha256(license_raw).hexdigest()
    data = json.loads(raw)

    counts = Counter()
    category_counts = Counter()
    category_with_evidence = Counter()
    category_without_evidence = Counter()
    evidence_cardinality = Counter()
    missing_id_multiplicity = Counter()
    session_count_hist = Counter()
    qa_count_per_sample = Counter()
    duplicate_dia_id_samples = 0
    global_duplicate_dia_ids = Counter()
    seen_global: set[str] = set()

    for sample in data if isinstance(data, list) else []:
        counts["samples"] += 1
        conversation = sample.get("conversation") if isinstance(sample, dict) else None
        qa = sample.get("qa") if isinstance(sample, dict) else None
        if not isinstance(conversation, dict) or not isinstance(qa, list):
            counts["malformed_samples"] += 1
            continue
        keys = session_keys(conversation)
        session_count_hist[len(keys)] += 1
        dia_ids: list[str] = []
        for key in keys:
            for turn in conversation.get(key, []):
                if not isinstance(turn, dict):
                    continue
                dia_id = turn.get("dia_id")
                if dia_id is None:
                    counts["turns_without_dia_id"] += 1
                    continue
                dia_ids.append(str(dia_id))
                counts["dialogue_turns"] += 1
        if len(set(dia_ids)) != len(dia_ids):
            duplicate_dia_id_samples += 1
        dia_set = set(dia_ids)
        for dia_id in dia_set:
            if dia_id in seen_global:
                global_duplicate_dia_ids[dia_id] += 1
            seen_global.add(dia_id)

        qa_count_per_sample[len(qa)] += 1
        for item in qa:
            if not isinstance(item, dict):
                counts["malformed_qa"] += 1
                continue
            counts["qa_total"] += 1
            category = str(item.get("category", "MISSING"))
            category_counts[category] += 1
            question_ok = bool(str(item.get("question", "")).strip())
            answer_ok = item.get("answer") is not None and bool(str(item.get("answer", "")).strip())
            if not question_ok:
                counts["qa_missing_question"] += 1
            if not answer_ok:
                counts["qa_missing_answer"] += 1
            eids = as_evidence_ids(item.get("evidence"))
            evidence_cardinality[len(eids)] += 1
            if eids:
                counts["qa_with_evidence"] += 1
                category_with_evidence[category] += 1
                missing = [eid for eid in eids if eid not in dia_set]
                if missing:
                    counts["qa_with_unresolved_evidence"] += 1
                    counts["unresolved_evidence_ids_total"] += len(missing)
                    missing_id_multiplicity[len(missing)] += 1
                else:
                    counts["qa_with_fully_resolved_evidence"] += 1
            else:
                counts["qa_without_evidence"] += 1
                category_without_evidence[category] += 1

    counts["samples_with_duplicate_dia_ids"] = duplicate_dia_id_samples
    result = {
        "schema_version": "candidate-v13-external-locomo-probe-v1",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "repository": REPO,
        "revision": REV,
        "data_path": DATA_REL,
        "license_path": LICENSE_REL,
        "data_sha256": data_sha,
        "license_sha256": license_sha,
        "license_class": "CC BY-NC 4.0",
        "aggregate_counts": dict(sorted(counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "category_with_evidence_counts": dict(sorted(category_with_evidence.items())),
        "category_without_evidence_counts": dict(sorted(category_without_evidence.items())),
        "evidence_cardinality_histogram": dict(sorted(evidence_cardinality.items())),
        "unresolved_evidence_multiplicity": dict(sorted(missing_id_multiplicity.items())),
        "session_count_histogram": dict(sorted(session_count_hist.items())),
        "qa_count_per_sample_histogram": dict(sorted(qa_count_per_sample.items())),
        "global_duplicate_dia_id_count": len(global_duplicate_dia_ids),
        "formal_gold_rule_candidate": "For QA entries with nonempty source-native evidence, every evidence value must exact-match a dia_id within the same sample conversation. Those matched turns are the gold memory IDs. QA entries with empty evidence are not automatically labeled no-evidence until their category semantics are separately audited from source documentation/code; no answer-text matching is permitted.",
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
