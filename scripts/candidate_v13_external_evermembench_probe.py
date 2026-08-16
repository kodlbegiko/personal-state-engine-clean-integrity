from __future__ import annotations

"""Pre-performance EverMemBench-Dynamic source-integrity probe.

No Candidate-v13 import/call. No natural-language dialogue or QA payload is
persisted. The probe pins the Hugging Face dataset revision, downloads the QAR
and dialogue JSON files, and verifies every source-native reference entry
against topic/date/group/message_index. Only aggregate counts and hashes are
written to the repository.
"""

import hashlib
import json
import re
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity/evermembench-dynamic-probe.json"
HF_REPO = "EverMind-AI/EverMemBench-Dynamic"
USER_AGENT = "pse-evermembench-dynamic-probe/1.0"


def request_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as response:
        return response.read()


def hf_url(revision: str, rel: str) -> str:
    quoted = "/".join(urllib.parse.quote(part, safe="") for part in rel.split("/"))
    return f"https://huggingface.co/datasets/{HF_REPO}/resolve/{revision}/{quoted}?download=true"


def expand_indices(value: Any) -> set[str]:
    """Parse source-native message_index forms like '1, 4-6, 8'."""
    out: set[str] = set()
    if value is None:
        return out
    for chunk in str(value).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if re.fullmatch(r"\d+", chunk):
            out.add(str(int(chunk)))
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", chunk)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            if hi >= lo and hi - lo <= 1000:
                out.update(str(x) for x in range(lo, hi + 1))
    return out


def normalized_topic(value: Any) -> str:
    s = str(value or "").strip()
    if s.isdigit():
        return s.zfill(2)
    return s


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    meta = request_json(f"https://huggingface.co/api/datasets/{HF_REPO}")
    revision = str(meta.get("sha") or "")
    if not revision:
        raise RuntimeError("Hugging Face dataset revision missing")
    license_value = str((meta.get("cardData") or {}).get("license") or "")
    siblings = {str(item.get("rfilename")) for item in meta.get("siblings", []) if item.get("rfilename")}

    q_rel = "EverMemBench_QAR.json"
    d_rel = "EverMemBench_Dialogues.json"
    p_rel = "profiles.json"
    for rel in [q_rel, d_rel, p_rel]:
        if rel not in siblings:
            raise RuntimeError(f"required file missing: {rel}")

    q_raw = fetch(hf_url(revision, q_rel))
    d_raw = fetch(hf_url(revision, d_rel))
    p_raw = fetch(hf_url(revision, p_rel))
    qars = json.loads(q_raw)
    dialogues = json.loads(d_raw)
    profiles = json.loads(p_raw)

    # Build exact source-native index.
    index: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    dialogue_rows = dialogues if isinstance(dialogues, list) else []
    dialogue_topic_counts = Counter()
    message_counts = Counter()
    malformed_dialogue_rows = 0
    for row in dialogue_rows:
        if not isinstance(row, dict):
            malformed_dialogue_rows += 1
            continue
        topic = normalized_topic(row.get("topic_id"))
        date = str(row.get("date") or "")[:10]
        groups = row.get("dialogues")
        if not topic or not date or not isinstance(groups, dict):
            malformed_dialogue_rows += 1
            continue
        dialogue_topic_counts[topic] += 1
        for group, messages in groups.items():
            if not isinstance(messages, list):
                continue
            key = (topic, date, str(group))
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                idx = msg.get("message_index")
                if idx is None:
                    message_counts["missing_message_index"] += 1
                    continue
                index[key].add(str(idx))
                message_counts["indexed_messages"] += 1

    qar_rows = qars if isinstance(qars, list) else []
    topic_counts = Counter()
    topic_full_resolved = Counter()
    ref_count_hist = Counter()
    referenced_message_count_hist = Counter()
    aggregate = Counter()
    unresolved_reason = Counter()

    for item in qar_rows:
        if not isinstance(item, dict):
            aggregate["malformed_qar"] += 1
            continue
        aggregate["qar_total"] += 1
        topic = normalized_topic(item.get("topic_id"))
        topic_counts[topic] += 1
        question_ok = bool(str(item.get("Q") or "").strip())
        answer_ok = bool(str(item.get("A") or "").strip())
        if not question_ok:
            aggregate["qar_missing_question"] += 1
        if not answer_ok:
            aggregate["qar_missing_answer"] += 1
        refs = item.get("R")
        refs = refs if isinstance(refs, list) else []
        ref_count_hist[len(refs)] += 1
        if not refs:
            aggregate["qar_without_reference"] += 1
            continue
        all_ok = True
        total_message_ids = 0
        for ref in refs:
            if not isinstance(ref, dict):
                unresolved_reason["reference_not_dict"] += 1
                all_ok = False
                continue
            date = str(ref.get("date") or "")[:10]
            group = str(ref.get("group") or "")
            requested = expand_indices(ref.get("message_index"))
            total_message_ids += len(requested)
            if not date or not group or not requested:
                unresolved_reason["malformed_reference_fields"] += 1
                all_ok = False
                continue
            available = index.get((topic, date, group))
            if available is None:
                unresolved_reason["missing_topic_date_group"] += 1
                all_ok = False
                continue
            missing = requested - available
            if missing:
                unresolved_reason["missing_message_index"] += 1
                aggregate["unresolved_message_ids_total"] += len(missing)
                all_ok = False
        referenced_message_count_hist[total_message_ids] += 1
        if all_ok and question_ok and answer_ok:
            aggregate["qar_fully_resolved"] += 1
            topic_full_resolved[topic] += 1
        elif all_ok:
            aggregate["qar_reference_resolved_but_missing_qa_text"] += 1
        else:
            aggregate["qar_unresolved_reference"] += 1

    profile_count = len(profiles) if isinstance(profiles, list) else len(profiles) if isinstance(profiles, dict) else 0
    result = {
        "schema_version": "candidate-v13-external-evermembench-dynamic-probe-v1",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "dataset": HF_REPO,
        "revision": revision,
        "license": license_value,
        "source_files": {
            q_rel: {"bytes": len(q_raw), "sha256": hashlib.sha256(q_raw).hexdigest()},
            d_rel: {"bytes": len(d_raw), "sha256": hashlib.sha256(d_raw).hexdigest()},
            p_rel: {"bytes": len(p_raw), "sha256": hashlib.sha256(p_raw).hexdigest()},
        },
        "profile_count": profile_count,
        "dialogue_row_count": len(dialogue_rows),
        "dialogue_topic_counts": dict(sorted(dialogue_topic_counts.items())),
        "message_counts": dict(sorted(message_counts.items())),
        "malformed_dialogue_rows": malformed_dialogue_rows,
        "qar_topic_counts": dict(sorted(topic_counts.items())),
        "qar_fully_resolved_by_topic": dict(sorted(topic_full_resolved.items())),
        "reference_entry_count_histogram": dict(sorted(ref_count_hist.items())),
        "referenced_message_count_histogram": dict(sorted(referenced_message_count_hist.items())),
        "aggregate_counts": dict(sorted(aggregate.items())),
        "unresolved_reference_reasons": dict(sorted(unresolved_reason.items())),
        "formal_domain_rule_candidate": {
            "topic_01": "D6 tools/devices because the benchmark paper/source labels T1 as Technology",
            "topic_02_to_05": "D7 memberships/projects because EverMemBench-Dynamic explicitly instantiates five workplace project domains; non-T1 topics are eligible as project-collaboration memories only, not reclassified by lexical content"
        },
        "formal_gold_rule_candidate": "Use each QAR's source-native R entries. For every R entry, exact-match topic_id/date/group and expand message_index singletons/ranges; all referenced message_index values must exist. Runtime gold IDs are topic_id::date::group::message_index. No answer-text matching or Candidate-v13 output is used."
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
