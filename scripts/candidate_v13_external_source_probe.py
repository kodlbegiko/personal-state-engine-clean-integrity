from __future__ import annotations

"""Pre-performance source probe for Candidate-v13 external validity.

This script is intentionally forbidden from importing or invoking Candidate-v13.
It pins public source revisions, hashes only the minimum probe files, and records
schema/count metadata needed to implement deterministic adapters. It does not
materialize EV-A/EV-B/EV-C cases and does not inspect Candidate-v13 outputs.
"""

import csv
import hashlib
import json
import tempfile
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity/source-probe.json"
USER_AGENT = "personal-state-engine-external-validity-source-probe/1.0"


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
    siblings = [x.get("rfilename") for x in data.get("siblings", []) if x.get("rfilename")]
    return {
        "sha": data.get("sha"),
        "last_modified": data.get("lastModified"),
        "private": data.get("private"),
        "gated": data.get("gated"),
        "siblings": sorted(siblings),
    }


def hf_download(repo: str, revision: str, rel: str, path: Path) -> dict[str, Any]:
    quoted_rel = "/".join(urllib.parse.quote(part, safe="") for part in rel.split("/"))
    url = f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{quoted_rel}?download=true"
    return download(url, path)


def probe_personamem(tmp: Path) -> dict[str, Any]:
    repo = "bowen-upenn/PersonaMem-v2"
    meta = hf_metadata(repo)
    revision = meta.get("sha")
    if not revision:
        raise RuntimeError("PersonaMem-v2 Hugging Face revision missing")
    rel = "benchmark/text/benchmark.csv"
    path = tmp / "personamem-v2-benchmark.csv"
    file_info = hf_download(repo, revision, rel, path)
    rows = 0
    headers: list[str] = []
    nonempty: Counter[str] = Counter()
    distinct: dict[str, set[str]] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        distinct = {h: set() for h in headers if h in {"question_type", "topic", "scenario", "category", "task", "domain"}}
        for row in reader:
            rows += 1
            for h in headers:
                value = row.get(h)
                if value is not None and str(value).strip():
                    nonempty[h] += 1
            for h in distinct:
                value = str(row.get(h, "")).strip()
                if value and len(distinct[h]) < 2000:
                    distinct[h].add(value)
    return {
        "dataset_repo": repo,
        "dataset_revision": revision,
        "hf_metadata": {k: v for k, v in meta.items() if k != "siblings"},
        "required_file_present": rel in meta["siblings"],
        "file": {"path": rel, **file_info},
        "row_count": rows,
        "headers": headers,
        "nonempty_counts": dict(sorted(nonempty.items())),
        "distinct_probe_fields": {k: sorted(v) for k, v in distinct.items()},
    }


def _top_level_shape(data: Any) -> dict[str, Any]:
    if isinstance(data, list):
        keys = sorted({str(k) for item in data[:100] if isinstance(item, dict) for k in item})
        return {"type": "list", "length": len(data), "sample_union_keys": keys}
    if isinstance(data, dict):
        return {"type": "dict", "length": len(data), "keys": sorted(map(str, data.keys()))[:500]}
    return {"type": type(data).__name__}


def probe_longmemeval(tmp: Path) -> dict[str, Any]:
    repo = "xiaowu0162/longmemeval-cleaned"
    meta = hf_metadata(repo)
    revision = meta.get("sha")
    if not revision:
        raise RuntimeError("LongMemEval-cleaned Hugging Face revision missing")
    rel = "longmemeval_oracle.json"
    path = tmp / "longmemeval-oracle.json"
    file_info = hf_download(repo, revision, rel, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data if isinstance(data, list) else []
    qtypes: Counter[str] = Counter()
    key_counts: Counter[str] = Counter()
    for item in records:
        if not isinstance(item, dict):
            continue
        for key in item:
            key_counts[str(key)] += 1
        qtype = item.get("question_type") or item.get("type")
        if qtype is not None:
            qtypes[str(qtype)] += 1
    return {
        "dataset_repo": repo,
        "dataset_revision": revision,
        "hf_metadata": {k: v for k, v in meta.items() if k != "siblings"},
        "required_file_present": rel in meta["siblings"],
        "file": {"path": rel, **file_info},
        "shape": _top_level_shape(data),
        "record_key_counts": dict(sorted(key_counts.items())),
        "question_type_counts": dict(sorted(qtypes.items())),
    }


def raw_github(repo: str, revision: str, rel: str, path: Path) -> dict[str, Any]:
    url = f"https://raw.githubusercontent.com/{repo}/{revision}/{rel}"
    return download(url, path)


def probe_taskmaster(tmp: Path) -> dict[str, Any]:
    repo = "google-research-datasets/Taskmaster"
    revision = "d92cb6af3005f1dc09c39e75e7daf4a04905e00b"
    files = {}
    for rel in ["TM-1-2019/sample.json", "TM-1-2019/ontology.json", "TM-1-2019/train-dev-test/train.csv", "TM-1-2019/train-dev-test/dev.csv", "TM-1-2019/train-dev-test/test.csv"]:
        path = tmp / ("taskmaster-" + rel.replace("/", "__"))
        files[rel] = {**raw_github(repo, revision, rel, path), "local": str(path)}
    sample_path = Path(files["TM-1-2019/sample.json"]["local"])
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    split_rows = {}
    split_ids: set[str] = set()
    for split in ["train", "dev", "test"]:
        rel = f"TM-1-2019/train-dev-test/{split}.csv"
        path = Path(files[rel]["local"])
        count = 0
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                count += 1
                split_ids.add(str(row[0]))
        split_rows[split] = count
    for value in files.values():
        value.pop("local", None)
    sample_item = sample[0] if isinstance(sample, list) and sample else sample
    utterance_keys: list[str] = []
    if isinstance(sample_item, dict):
        utterances = sample_item.get("utterances")
        if isinstance(utterances, list):
            utterance_keys = sorted({str(k) for u in utterances if isinstance(u, dict) for k in u})
    return {
        "repository": repo,
        "revision": revision,
        "files": files,
        "sample_shape": _top_level_shape(sample),
        "sample_record_keys": sorted(sample_item.keys()) if isinstance(sample_item, dict) else [],
        "sample_utterance_keys": utterance_keys,
        "split_row_counts_raw": split_rows,
        "unique_split_first_column_values": len(split_ids),
        "known_full_data_blob_shas": {
            "TM-1-2019/self-dialogs.json": "f1a1a3fd4bfb9cbb62d419f7964fb33291e0b2dd",
            "TM-1-2019/woz-dialogs.json": "c3d5ae919713db351eed531957f8d8893d581a8c"
        }
    }


def probe_sgd(tmp: Path) -> dict[str, Any]:
    repo = "google-research-datasets/dstc8-schema-guided-dialogue"
    revision = "e852981ae34990f4358979625854259302feaa78"
    files = {}
    for rel in ["train/schema.json", "train/dialogues_001.json"]:
        path = tmp / ("sgd-" + rel.replace("/", "__"))
        files[rel] = {**raw_github(repo, revision, rel, path), "local": str(path)}
    schema = json.loads(Path(files["train/schema.json"]["local"]).read_text(encoding="utf-8"))
    dialogues = json.loads(Path(files["train/dialogues_001.json"]["local"]).read_text(encoding="utf-8"))
    for value in files.values():
        value.pop("local", None)
    service_domains: Counter[str] = Counter()
    for service in schema if isinstance(schema, list) else []:
        if isinstance(service, dict):
            name = str(service.get("service_name", ""))
            domain = name.split("_")[0] if name else ""
            if domain:
                service_domains[domain] += 1
    first = dialogues[0] if isinstance(dialogues, list) and dialogues else {}
    turn_keys: list[str] = []
    frame_keys: list[str] = []
    if isinstance(first, dict):
        turns = first.get("turns") or []
        turn_keys = sorted({str(k) for t in turns if isinstance(t, dict) for k in t})
        frame_keys = sorted({str(k) for t in turns if isinstance(t, dict) for fr in (t.get("frames") or []) if isinstance(fr, dict) for k in fr})
    return {
        "repository": repo,
        "revision": revision,
        "files": files,
        "schema_service_count": len(schema) if isinstance(schema, list) else None,
        "schema_domain_prefix_counts": dict(sorted(service_domains.items())),
        "probe_dialogue_count": len(dialogues) if isinstance(dialogues, list) else None,
        "dialogue_record_keys": sorted(first.keys()) if isinstance(first, dict) else [],
        "turn_keys": turn_keys,
        "frame_keys": frame_keys,
    }


def static_candidate_import_guard() -> dict[str, Any]:
    text = Path(__file__).read_text(encoding="utf-8")
    forbidden = [
        "from personal_state_engine.candidate_v13",
        "import personal_state_engine.candidate_v13",
        "from candidate_v13",
        "import candidate_v13",
        "pse_candidate_v13_rank" + "(",
        "evidence_support_signature_v13" + "("
    ]
    hits = [needle for needle in forbidden if needle in text]
    return {"pass": not hits, "forbidden_hits": hits}


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "schema_version": "candidate-v13-external-source-probe-v1",
        "status": "RUNNING",
        "utc": utc_now(),
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "purpose": "Pin source revisions and inspect source-native schemas/count metadata before adapter implementation."
    }
    guard = static_candidate_import_guard()
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
                "taskmaster-1": probe_taskmaster(tmp),
                "sgd": probe_sgd(tmp)
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
