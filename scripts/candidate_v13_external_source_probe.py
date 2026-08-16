from __future__ import annotations

"""Pre-performance source probe for Candidate-v13 external validity.

This script never imports or invokes Candidate-v13. It pins public source
revisions, hashes source files, and records schema/count metadata needed before
adapter design. It does not materialize EV-A/EV-B/EV-C cases.
"""

import ast
import csv
import hashlib
import json
import tempfile
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity/source-probe.json"
USER_AGENT = "personal-state-engine-external-validity-source-probe/2.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def request_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)


def download(url: str, path: Path) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=300) as response, path.open("wb") as out:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            out.write(block)
    return {"bytes": path.stat().st_size, "sha256": sha256(path)}


def hf_metadata(repo: str) -> dict[str, Any]:
    data = request_json(f"https://huggingface.co/api/datasets/{repo}")
    siblings = sorted(x["rfilename"] for x in data.get("siblings", []) if x.get("rfilename"))
    return {
        "sha": data.get("sha"),
        "last_modified": data.get("lastModified"),
        "private": data.get("private"),
        "gated": data.get("gated"),
        "siblings": siblings,
    }


def hf_download(repo: str, revision: str, rel: str, path: Path) -> dict[str, Any]:
    quoted = "/".join(urllib.parse.quote(part, safe="") for part in rel.split("/"))
    return download(f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{quoted}?download=true", path)


def raw_github(repo: str, revision: str, rel: str, path: Path) -> dict[str, Any]:
    return download(f"https://raw.githubusercontent.com/{repo}/{revision}/{rel}", path)


def top_shape(data: Any) -> dict[str, Any]:
    if isinstance(data, list):
        keys = sorted({str(k) for item in data[:100] if isinstance(item, dict) for k in item})
        return {"type": "list", "length": len(data), "sample_union_keys": keys}
    if isinstance(data, dict):
        return {"type": "dict", "length": len(data), "keys": sorted(map(str, data.keys()))[:500]}
    return {"type": type(data).__name__}


def probe_personamem(tmp: Path) -> dict[str, Any]:
    repo = "bowen-upenn/PersonaMem-v2"
    meta = hf_metadata(repo)
    revision = meta.get("sha")
    if not revision:
        raise RuntimeError("PersonaMem-v2 Hugging Face revision missing")
    rel = "benchmark/text/benchmark.csv"
    path = tmp / "personamem.csv"
    info = hf_download(repo, revision, rel, path)
    rows = 0
    headers: list[str] = []
    nonempty: Counter[str] = Counter()
    field_values: dict[str, Counter[str]] = {
        "pref_type": Counter(), "who": Counter(), "updated": Counter(),
        "conversation_scenario": Counter(), "topic_query": Counter(), "topic_preference": Counter(),
    }
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        for row in reader:
            rows += 1
            for h in headers:
                value = str(row.get(h, "")).strip()
                if value:
                    nonempty[h] += 1
            for h in field_values:
                value = str(row.get(h, "")).strip()
                if value:
                    field_values[h][value] += 1
    return {
        "dataset_repo": repo,
        "dataset_revision": revision,
        "hf_metadata": {k: v for k, v in meta.items() if k != "siblings"},
        "required_file_present": rel in meta["siblings"],
        "file": {"path": rel, **info},
        "row_count": rows,
        "headers": headers,
        "nonempty_counts": dict(sorted(nonempty.items())),
        "field_cardinality": {k: len(v) for k, v in field_values.items()},
        "field_top_counts": {k: v.most_common(20) for k, v in field_values.items()},
    }


def probe_longmemeval(tmp: Path) -> dict[str, Any]:
    repo = "xiaowu0162/longmemeval-cleaned"
    meta = hf_metadata(repo)
    revision = meta.get("sha")
    if not revision:
        raise RuntimeError("LongMemEval-cleaned Hugging Face revision missing")
    rel = "longmemeval_oracle.json"
    path = tmp / "longmemeval.json"
    info = hf_download(repo, revision, rel, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data if isinstance(data, list) else []
    qtypes: Counter[str] = Counter()
    key_counts: Counter[str] = Counter()
    sessions_per_case: list[int] = []
    answer_sessions_per_case: list[int] = []
    sample_message_keys: set[str] = set()
    for item in records:
        if not isinstance(item, dict):
            continue
        key_counts.update(map(str, item.keys()))
        if item.get("question_type") is not None:
            qtypes[str(item["question_type"])] += 1
        sessions = item.get("haystack_sessions") or []
        sessions_per_case.append(len(sessions) if isinstance(sessions, list) else 0)
        answer_sessions = item.get("answer_session_ids") or []
        answer_sessions_per_case.append(len(answer_sessions) if isinstance(answer_sessions, list) else 0)
        if isinstance(sessions, list):
            for session in sessions[:3]:
                if isinstance(session, list):
                    for message in session[:5]:
                        if isinstance(message, dict):
                            sample_message_keys.update(map(str, message.keys()))
    return {
        "dataset_repo": repo,
        "dataset_revision": revision,
        "hf_metadata": {k: v for k, v in meta.items() if k != "siblings"},
        "required_file_present": rel in meta["siblings"],
        "file": {"path": rel, **info},
        "shape": top_shape(data),
        "record_key_counts": dict(sorted(key_counts.items())),
        "question_type_counts": dict(sorted(qtypes.items())),
        "session_count_range": [min(sessions_per_case or [0]), max(sessions_per_case or [0])],
        "answer_session_count_range": [min(answer_sessions_per_case or [0]), max(answer_sessions_per_case or [0])],
        "sample_message_keys": sorted(sample_message_keys),
    }


def iter_records(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        if any(str(k).casefold() in {"question", "answer", "reference memory", "reference_memory", "reference_memory_id"} for k in node):
            yield node
        for value in node.values():
            yield from iter_records(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_records(value)


def probe_perltqa(tmp: Path) -> dict[str, Any]:
    repo = "Elvin-Yiming-Du/PerLTQA"
    revision = "8d9e19868e239740ef701e603ec205cd581f221b"
    files: dict[str, dict[str, Any]] = {}
    for rel in ["LICENSE.txt", "Dataset/en_v2/perltmem_en_v2.json", "Dataset/en_v2/perltqa_en_v2.json"]:
        path = tmp / ("perltqa-" + rel.replace("/", "__"))
        files[rel] = {**raw_github(repo, revision, rel, path), "local": str(path)}
    mem = json.loads(Path(files["Dataset/en_v2/perltmem_en_v2.json"]["local"]).read_text(encoding="utf-8"))
    qa = json.loads(Path(files["Dataset/en_v2/perltqa_en_v2.json"]["local"]).read_text(encoding="utf-8"))
    qa_records = list(iter_records(qa))
    key_counts: Counter[str] = Counter()
    reference_present = 0
    anchor_present = 0
    for record in qa_records:
        key_counts.update(map(str, record.keys()))
        folded = {str(k).casefold().replace("_", " "): v for k, v in record.items()}
        if any(name in folded and folded[name] not in (None, "", [], {}) for name in ["reference memory", "reference memories"]):
            reference_present += 1
        if any("anchor" in name and value not in (None, "", [], {}) for name, value in folded.items()):
            anchor_present += 1
    mem_section_keys: Counter[str] = Counter()
    if isinstance(mem, dict):
        for value in mem.values():
            if isinstance(value, dict):
                mem_section_keys.update(map(str, value.keys()))
    for value in files.values():
        value.pop("local", None)
    return {
        "repository": repo,
        "revision": revision,
        "license": "CC BY-NC 4.0",
        "files": files,
        "memory_shape": top_shape(mem),
        "qa_shape": top_shape(qa),
        "qa_record_count_recursive": len(qa_records),
        "qa_record_key_counts": dict(sorted(key_counts.items())),
        "qa_records_with_reference_memory": reference_present,
        "qa_records_with_memory_anchor": anchor_present,
        "memory_section_key_counts": dict(sorted(mem_section_keys.items())),
    }


def probe_taskmaster(tmp: Path) -> dict[str, Any]:
    repo = "google-research-datasets/Taskmaster"
    revision = "d92cb6af3005f1dc09c39e75e7daf4a04905e00b"
    files: dict[str, dict[str, Any]] = {}
    for rel in ["TM-1-2019/sample.json", "TM-1-2019/ontology.json", "TM-1-2019/train-dev-test/train.csv", "TM-1-2019/train-dev-test/dev.csv", "TM-1-2019/train-dev-test/test.csv"]:
        path = tmp / ("taskmaster-" + rel.replace("/", "__"))
        files[rel] = {**raw_github(repo, revision, rel, path), "local": str(path)}
    sample = json.loads(Path(files["TM-1-2019/sample.json"]["local"]).read_text(encoding="utf-8"))
    split_rows: dict[str, int] = {}
    split_ids: set[str] = set()
    for split in ["train", "dev", "test"]:
        rel = f"TM-1-2019/train-dev-test/{split}.csv"
        with Path(files[rel]["local"]).open("r", encoding="utf-8", newline="") as f:
            rows = [row for row in csv.reader(f) if row]
        split_rows[split] = len(rows)
        split_ids.update(str(row[0]) for row in rows)
    for value in files.values():
        value.pop("local", None)
    item = sample[0] if isinstance(sample, list) and sample else sample
    utterance_keys: set[str] = set()
    if isinstance(item, dict) and isinstance(item.get("utterances"), list):
        utterance_keys = {str(k) for u in item["utterances"] if isinstance(u, dict) for k in u}
    return {
        "repository": repo,
        "revision": revision,
        "files": files,
        "sample_shape": top_shape(sample),
        "sample_record_keys": sorted(item.keys()) if isinstance(item, dict) else [],
        "sample_utterance_keys": sorted(utterance_keys),
        "split_row_counts_raw": split_rows,
        "unique_split_first_column_values": len(split_ids),
        "known_full_data_blob_shas": {
            "TM-1-2019/self-dialogs.json": "f1a1a3fd4bfb9cbb62d419f7964fb33291e0b2dd",
            "TM-1-2019/woz-dialogs.json": "c3d5ae919713db351eed531957f8d8893d581a8c",
        },
    }


def probe_sgd(tmp: Path) -> dict[str, Any]:
    repo = "google-research-datasets/dstc8-schema-guided-dialogue"
    revision = "e852981ae34990f4358979625854259302feaa78"
    files: dict[str, dict[str, Any]] = {}
    for rel in ["train/schema.json", "train/dialogues_001.json"]:
        path = tmp / ("sgd-" + rel.replace("/", "__"))
        files[rel] = {**raw_github(repo, revision, rel, path), "local": str(path)}
    schema = json.loads(Path(files["train/schema.json"]["local"]).read_text(encoding="utf-8"))
    dialogues = json.loads(Path(files["train/dialogues_001.json"]["local"]).read_text(encoding="utf-8"))
    for value in files.values():
        value.pop("local", None)
    domains: Counter[str] = Counter()
    for service in schema if isinstance(schema, list) else []:
        if isinstance(service, dict):
            name = str(service.get("service_name", ""))
            if name:
                domains[name.split("_")[0]] += 1
    first = dialogues[0] if isinstance(dialogues, list) and dialogues else {}
    turn_keys: set[str] = set()
    frame_keys: set[str] = set()
    if isinstance(first, dict):
        for turn in first.get("turns") or []:
            if isinstance(turn, dict):
                turn_keys.update(map(str, turn.keys()))
                for frame in turn.get("frames") or []:
                    if isinstance(frame, dict):
                        frame_keys.update(map(str, frame.keys()))
    return {
        "repository": repo,
        "revision": revision,
        "files": files,
        "schema_service_count": len(schema) if isinstance(schema, list) else None,
        "schema_domain_prefix_counts": dict(sorted(domains.items())),
        "probe_dialogue_count": len(dialogues) if isinstance(dialogues, list) else None,
        "dialogue_record_keys": sorted(first.keys()) if isinstance(first, dict) else [],
        "turn_keys": sorted(turn_keys),
        "frame_keys": sorted(frame_keys),
    }


def candidate_import_guard() -> dict[str, Any]:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    modules: list[str] = []
    calls: list[str] = []
    forbidden_calls = {"pse_candidate_v13_rank", "evidence_support_signature_v13"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names if "candidate_v13" in alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "candidate_v13" in module:
                modules.append(module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in forbidden_calls:
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute) and node.func.attr in forbidden_calls:
                calls.append(node.func.attr)
    return {"pass": not modules and not calls, "forbidden_modules": sorted(set(modules)), "forbidden_calls": sorted(set(calls))}


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "schema_version": "candidate-v13-external-source-probe-v2",
        "status": "RUNNING",
        "utc": utc_now(),
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "purpose": "Pin source revisions/hashes and inspect source-native schemas/count metadata before adapter implementation.",
    }
    guard = candidate_import_guard()
    result["candidate_import_guard"] = guard
    if not guard["pass"]:
        result["status"] = "FAIL"
        OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return 2
    try:
        with tempfile.TemporaryDirectory(prefix="pse-ev-source-probe-") as td:
            tmp = Path(td)
            result["sources"] = {
                "personamem-v2": probe_personamem(tmp),
                "longmemeval-cleaned": probe_longmemeval(tmp),
                "perltqa-en-v2": probe_perltqa(tmp),
                "taskmaster-1": probe_taskmaster(tmp),
                "sgd": probe_sgd(tmp),
            }
        result["status"] = "PASS"
    except Exception as exc:
        result["status"] = "FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["completed_utc"] = utc_now()
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
