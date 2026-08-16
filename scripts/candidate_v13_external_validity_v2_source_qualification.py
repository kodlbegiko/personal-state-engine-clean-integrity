from __future__ import annotations

"""Candidate-blind source/schema/capacity qualification for External Validity v2.

This script MUST NOT import or call Candidate-v13. It requalifies the historical
four-source pool from pinned bytes, then inspects supplemental sources under
fresh schema-first contracts. It persists only aggregate metadata/hashes.
"""

import ast
import fnmatch
import hashlib
import importlib.util
import json
import math
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from datasets import load_dataset
from huggingface_hub import HfApi, snapshot_download

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "results/candidate-v13-external-validity-v2"
DOCDIR = ROOT / "docs/research/candidate-v13-external-validity-v2"
SOURCE_CONTRACT = json.loads((DOCDIR / "source-contract-v2.json").read_text(encoding="utf-8"))
LEGACY_ADAPTER = ROOT / "docs/research/candidate-v13-external-validity/adapter-policy.json"
LEGACY_ALLOC = ROOT / "docs/research/candidate-v13-external-validity/allocation-policy.json"
LEGACY_SCRIPT = ROOT / "scripts/candidate_v13_external_capacity_audit_v2.py"
CANDIDATE = ROOT / "src/personal_state_engine/candidate_v13.py"
EXPECTED_CANDIDATE_SHA256 = "b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838"

D6_WORDS = {
    "device", "devices", "computer", "computers", "laptop", "laptops", "phone", "phones",
    "smartphone", "smartphones", "tablet", "tablets", "software", "application", "applications",
    "browser", "camera", "technology", "technologies", "macbook", "iphone", "android",
    "server", "servers", "database", "databases", "api", "apis", "programming", "code",
    "coding", "tool", "tools", "platform", "platforms", "system", "systems", "hardware",
}
D7_WORDS = {
    "project", "projects", "membership", "member", "members", "club", "clubs",
    "organization", "organizations", "community", "communities", "research",
    "certification", "certificate", "volunteer", "initiative", "initiatives",
    "team", "teams", "committee", "committees", "collaboration", "program", "programs",
}
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_'’-]*")
DATE_REF_RE = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})(?::(?P<idx>\d+))?")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().replace("’", "'").split())


def tokens(value: Any) -> set[str]:
    return {m.group(0).casefold().replace("’", "'") for m in TOKEN_RE.finditer(str(value or ""))}


def json_shape(value: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"top_level_type": type(value).__name__}
    if isinstance(value, dict):
        result["top_level_keys"] = sorted(str(k) for k in value.keys())
        first_container = None
        for key, item in value.items():
            if isinstance(item, list) and item:
                first_container = (str(key), item)
                break
        if first_container:
            key, rows = first_container
            result["first_list_container"] = key
            result["first_list_length"] = len(rows)
            first = rows[0]
            result["record_type"] = type(first).__name__
            if isinstance(first, dict):
                result["record_keys"] = sorted(str(k) for k in first.keys())
    elif isinstance(value, list):
        result["top_level_length"] = len(value)
        if value:
            first = value[0]
            result["record_type"] = type(first).__name__
            if isinstance(first, dict):
                result["record_keys"] = sorted(str(k) for k in first.keys())
    return result


def firewall() -> dict[str, Any]:
    candidate_hash = sha256_file(CANDIDATE)
    violations: list[str] = []
    checked: list[str] = []
    for path in sorted((ROOT / "scripts").glob("*external_validity_v2*.py")):
        checked.append(str(path.relative_to(ROOT)))
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "personal_state_engine.candidate_v13" or alias.name.endswith(".candidate_v13"):
                        violations.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "personal_state_engine.candidate_v13" or mod.endswith(".candidate_v13"):
                    violations.append(f"{path.name}: from {mod}")
            elif isinstance(node, ast.Call):
                name = ""
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name in {"pse_candidate_v13_rank", "evidence_support_signature_v13"}:
                    violations.append(f"{path.name}: call {name}")
    return {
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
        "candidate_v13_external_predictions_exist": False,
        "formal_case_materialized": False,
        "candidate_sha256_expected": EXPECTED_CANDIDATE_SHA256,
        "candidate_sha256_actual": candidate_hash,
        "candidate_hash_match": candidate_hash == EXPECTED_CANDIDATE_SHA256,
        "checked_scripts": checked,
        "violations": violations,
        "pass": candidate_hash == EXPECTED_CANDIDATE_SHA256 and not violations,
    }


def load_legacy_module():
    spec = importlib.util.spec_from_file_location("pse_legacy_capacity_requalifier", LEGACY_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load historical capacity module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ADAPTER = json.loads(LEGACY_ADAPTER.read_text(encoding="utf-8"))
    module.ALLOC = json.loads(LEGACY_ALLOC.read_text(encoding="utf-8"))
    return module


def fresh_baseline(legacy) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raws = {
        "personamem-v2": legacy.fetch(legacy.hf(
            "bowen-upenn/PersonaMem-v2", "b7b42b78917157afed063527a1c959e98f6109f2",
            "benchmark/text/benchmark.csv")),
        "longmemeval-cleaned": legacy.fetch(legacy.hf(
            "xiaowu0162/longmemeval-cleaned", "98d7416c24c778c2fee6e6f3006e7a073259d48f",
            "longmemeval_oracle.json")),
        "locomo": legacy.fetch(legacy.gh(
            "snap-research/locomo", "3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376",
            "data/locomo10.json")),
        "sgd-archive": legacy.fetch(
            "https://github.com/google-research-datasets/dstc8-schema-guided-dialogue/archive/"
            "e852981ae34990f4358979625854259302feaa78.zip"),
    }
    hashes = {k: sha256_bytes(v) for k, v in raws.items()}
    mismatch = {
        k: {"expected": legacy.EXPECTED[k], "actual": h}
        for k, h in hashes.items() if h != legacy.EXPECTED[k]
    }
    if mismatch:
        raise RuntimeError(f"baseline source hash mismatch: {mismatch}")
    stats = Counter()
    bases: list[dict[str, Any]] = []
    legacy.load_persona(raws["personamem-v2"], bases, stats)
    legacy.load_lme(raws["longmemeval-cleaned"], bases, stats)
    legacy.load_locomo(raws["locomo"], bases, stats)
    legacy.load_sgd(raws["sgd-archive"], bases, stats)
    return bases, {
        "source_hashes": hashes,
        "loader_stats": dict(sorted(stats.items())),
        "pre_dedup_base_count": len(bases),
        "legacy_loader_git_blob_sha": SOURCE_CONTRACT["baseline_requalification"]["legacy_capacity_script_git_blob_sha"],
    }


def choose_index_field(messages: list[dict[str, Any]]) -> str:
    seen = set()
    for msg in messages[:50]:
        if isinstance(msg, dict):
            for candidate in ("message_index", "msg_index"):
                if candidate in msg:
                    seen.add(candidate)
    if len(seen) != 1:
        raise RuntimeError(f"EverMem dialogue message index field ambiguous/missing: {sorted(seen)}")
    return next(iter(seen))


def extract_message_text(msg: dict[str, Any]) -> str:
    for key in ("text", "content", "message", "utterance"):
        value = msg.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    candidates = [v.strip() for k, v in msg.items()
                  if isinstance(v, str) and v.strip() and k not in {"speaker", "role", "name"}]
    if len(candidates) == 1:
        return candidates[0]
    raise RuntimeError("EverMem message text field is missing/ambiguous")


def expand_indices(value: Any) -> set[str]:
    out: set[str] = set()
    if value is None:
        return out
    if isinstance(value, list):
        for item in value:
            out |= expand_indices(item)
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
            if hi < lo or hi - lo > 1000:
                raise RuntimeError(f"invalid message index range: {chunk}")
            out.update(str(x) for x in range(lo, hi + 1))
            continue
        raise RuntimeError(f"unparseable message index: {chunk}")
    return out


def normalize_topic(value: Any) -> str:
    s = str(value or "").strip()
    if s.upper().startswith("T") and s[1:].isdigit():
        return str(int(s[1:]))
    if s.isdigit():
        return str(int(s))
    return s


def evermem(legacy, bases: list[dict[str, Any]], schema_manifest: dict[str, Any]) -> dict[str, Any]:
    api = HfApi()
    repo = SOURCE_CONTRACT["supplemental_sources"]["evermembench-dynamic"]["dataset"]
    info = api.dataset_info(repo)
    rev = info.sha
    if not rev:
        raise RuntimeError("EverMemBench revision missing")
    license_value = str((info.card_data or {}).get("license") or "").casefold()

    with tempfile.TemporaryDirectory(prefix="pse-evermem-root-") as td:
        snap = Path(snapshot_download(
            repo_id=repo, repo_type="dataset", revision=rev, local_dir=td,
            allow_patterns=["EverMemBench_QAR.json", "EverMemBench_Dialogues.json"],
        ))
        qroot = json.loads((snap / "EverMemBench_QAR.json").read_text(encoding="utf-8"))
        droot = json.loads((snap / "EverMemBench_Dialogues.json").read_text(encoding="utf-8"))
        schema_manifest["evermembench-dynamic:legacy-root-qar"] = json_shape(qroot)
        schema_manifest["evermembench-dynamic:legacy-root-dialogues"] = json_shape(droot)

    qds = load_dataset(repo, "qars", split="train", revision=rev)
    dds = load_dataset(repo, "dialogues", split="train", revision=rev)
    schema_manifest["evermembench-dynamic:qars-config"] = {
        "top_level_type": "Dataset",
        "record_keys": sorted(qds.column_names),
        "row_count": len(qds),
        "features": str(qds.features),
    }
    schema_manifest["evermembench-dynamic:dialogues-config"] = {
        "top_level_type": "Dataset",
        "record_keys": sorted(dds.column_names),
        "row_count": len(dds),
        "features": str(dds.features),
    }
    for required in ("topic_id", "Q", "A", "R"):
        if required not in qds.column_names:
            raise RuntimeError(f"EverMem qars config missing required field {required}")
    for required in ("topic_id", "date", "dialogues"):
        if required not in dds.column_names:
            raise RuntimeError(f"EverMem dialogues config missing required field {required}")

    index: dict[tuple[str, str, str, str], str] = {}
    id_field: str | None = None
    for row in dds:
        topic = normalize_topic(row["topic_id"])
        date = str(row["date"])[:10]
        groups = row["dialogues"]
        if not isinstance(groups, dict):
            raise RuntimeError(f"EverMem dialogues container must be dict, got {type(groups).__name__}")
        for group, messages in groups.items():
            if not isinstance(messages, list) or not messages:
                raise RuntimeError("EverMem dialogue group must be non-empty list")
            dict_messages = [m for m in messages if isinstance(m, dict)]
            if len(dict_messages) != len(messages):
                raise RuntimeError("EverMem dialogue message must be dict")
            detected = choose_index_field(dict_messages)
            if id_field is None:
                id_field = detected
            elif id_field != detected:
                raise RuntimeError(f"EverMem message id field changed: {id_field} -> {detected}")
            for msg in dict_messages:
                idx = str(msg[id_field])
                text = extract_message_text(msg)
                key = (topic, date, str(group), idx)
                if key in index and index[key] != text:
                    raise RuntimeError(f"EverMem duplicate message key with different text: {key}")
                index[key] = text
    if not index:
        raise RuntimeError("EverMem parsed zero messages")

    eligible = Counter()
    unresolved = Counter()
    duplicate_queries: set[str] = set()
    for row in qds:
        q = str(row["Q"] or "").strip()
        a = str(row["A"] or "").strip()
        topic = normalize_topic(row["topic_id"])
        refs = row["R"]
        if not q or not a or not isinstance(refs, list) or not refs:
            unresolved["missing_q_a_or_refs"] += 1
            continue
        gold: list[str] = []
        ok = True
        for ref in refs:
            if not isinstance(ref, dict):
                unresolved["reference_not_dict"] += 1
                ok = False
                break
            date = str(ref.get("date") or "")[:10]
            group = str(ref.get("group") or "")
            ref_idx = ref.get("message_index", ref.get("msg_index"))
            ids = expand_indices(ref_idx)
            if not date or not group or not ids:
                unresolved["malformed_reference"] += 1
                ok = False
                break
            for idx in sorted(ids, key=lambda x: int(x) if x.isdigit() else x):
                text = index.get((topic, date, group, idx))
                if text is None:
                    unresolved["unresolved_message_id"] += 1
                    ok = False
                    break
                gold.append(text)
            if not ok:
                break
        if not ok or not gold:
            continue
        nq = norm(q)
        if nq in duplicate_queries:
            unresolved["normalized_query_duplicate_within_source"] += 1
            continue
        duplicate_queries.add(nq)
        if topic == "1":
            domain = "D6"
        elif topic in {"2", "3", "4", "5"}:
            domain = "D7"
        else:
            unresolved["unsupported_topic"] += 1
            continue
        legacy.add(
            bases, "evermembench-dynamic", f"evermem:{topic}:{row.get('id', len(bases))}",
            q, f"evermem-topic-{topic}", "source-native-QAR-reference", gold, domain
        )
        eligible[domain] += 1

    return {
        "dataset": repo,
        "revision": rev,
        "license": license_value,
        "message_index_field": id_field,
        "indexed_messages": len(index),
        "qars_rows": len(qds),
        "dialogue_rows": len(dds),
        "eligible_by_domain_pre_global_dedup": dict(sorted(eligible.items())),
        "unresolved": dict(sorted(unresolved.items())),
        "gold_rule": "source-native R exact resolution against topic/date/group/message index",
        "candidate_blind": True,
    }


def read_text_loose(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def generic_conversation_turns(path: Path) -> tuple[str | None, list[str]]:
    obj = json.loads(read_text_loose(path))
    date: str | None = None
    messages: Any = None
    if isinstance(obj, dict):
        for key in ("date", "session_date", "datetime", "timestamp"):
            if key in obj and obj[key]:
                date = str(obj[key])[:10]
                break
        for key in ("messages", "dialogue", "dialogues", "conversation", "turns"):
            if isinstance(obj.get(key), list):
                messages = obj[key]
                break
    elif isinstance(obj, list):
        messages = obj
    if messages is None:
        return date, []
    out = []
    for msg in messages:
        if isinstance(msg, str) and msg.strip():
            out.append(msg.strip())
        elif isinstance(msg, dict):
            parts = []
            for key in ("speaker", "role", "name"):
                if msg.get(key):
                    parts.append(str(msg[key]))
                    break
            text = ""
            for key in ("text", "content", "message", "utterance"):
                if isinstance(msg.get(key), str) and msg[key].strip():
                    text = msg[key].strip()
                    break
            if text:
                out.append((parts[0] + ": " if parts else "") + text)
    return date, out


def classify_rhelm_domain(q: str, a: str, evidence: Any) -> str | None:
    ts = tokens(q) | tokens(a) | tokens(evidence)
    d6 = len(ts & D6_WORDS)
    d7 = len(ts & D7_WORDS)
    if d6 == 0 and d7 == 0:
        return None
    if d6 > d7:
        return "D6"
    if d7 > d6:
        return "D7"
    return None


def rhelm(legacy, bases: list[dict[str, Any]], schema_manifest: dict[str, Any]) -> dict[str, Any]:
    api = HfApi()
    repo = SOURCE_CONTRACT["reserve_sources"]["rhelm"]["dataset"]
    info = api.dataset_info(repo)
    rev = info.sha
    if not rev:
        raise RuntimeError("RHELM revision missing")
    license_value = str((info.card_data or {}).get("license") or "").casefold()

    with tempfile.TemporaryDirectory(prefix="pse-rhelm-") as td:
        snap = Path(snapshot_download(
            repo_id=repo, repo_type="dataset", revision=rev, local_dir=td,
            allow_patterns=["QA_final/*.jsonl", "conversations/**", "emails/**", "attachments/**"],
        ))
        qa_files = sorted((snap / "QA_final").glob("*.jsonl"))
        if not qa_files:
            raise RuntimeError("RHELM QA files missing")
        first_row = None
        for line in qa_files[0].read_text(encoding="utf-8").splitlines():
            if line.strip():
                first_row = json.loads(line)
                break
        if not isinstance(first_row, dict):
            raise RuntimeError("RHELM first QA row must be object")
        schema_manifest["rhelm:qa-jsonl"] = {
            "top_level_type": "JSONL",
            "record_type": "dict",
            "record_keys": sorted(first_row.keys()),
            "qa_file_count": len(qa_files),
        }
        required = {"id", "question", "answer", "question_date", "question_type", "supporting_evidence", "characteristics"}
        missing = required - set(first_row)
        if missing:
            raise RuntimeError(f"RHELM QA schema missing fields: {sorted(missing)}")

        eligible = Counter()
        unresolved = Counter()
        total = 0
        resolved = 0
        seen_queries: set[str] = set()
        source_cache: dict[str, dict[str, Any]] = {}
        for qafile in qa_files:
            persona = qafile.stem
            persona = re.sub(r"^low_score_qa_", "", persona)
            persona = re.sub(r"_all_validated$", "", persona)
            if persona not in source_cache:
                files = []
                for root_name in ("conversations", "emails", "attachments"):
                    p = snap / root_name / persona
                    if p.exists():
                        files.extend(x for x in p.rglob("*") if x.is_file())
                by_basename = defaultdict(list)
                by_date = defaultdict(list)
                conversation_turns: dict[Path, list[str]] = {}
                for f in files:
                    by_basename[f.name].append(f)
                    if f.suffix.lower() == ".json":
                        try:
                            date, turns = generic_conversation_turns(f)
                        except Exception:
                            date, turns = None, []
                        if date:
                            by_date[date].append(f)
                        if turns:
                            conversation_turns[f] = turns
                    m = re.search(r"\d{4}-\d{2}-\d{2}", f.name)
                    if m:
                        by_date[m.group(0)].append(f)
                source_cache[persona] = {
                    "files": files,
                    "by_basename": by_basename,
                    "by_date": by_date,
                    "conversation_turns": conversation_turns,
                }
            src = source_cache[persona]

            for line in qafile.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                total += 1
                row = json.loads(line)
                q = str(row.get("question") or "").strip()
                a = str(row.get("answer") or "").strip()
                refs = row.get("supporting_evidence")
                if isinstance(refs, str):
                    refs = [refs] if refs.strip() else []
                if not q or not a or not isinstance(refs, list) or not refs:
                    unresolved["missing_q_a_or_evidence"] += 1
                    continue
                nq = norm(q)
                if nq in seen_queries:
                    unresolved["normalized_query_duplicate_within_source"] += 1
                    continue
                domain = classify_rhelm_domain(q, a, refs)
                if domain not in {"D6", "D7"}:
                    unresolved["not_d6_d7"] += 1
                    continue
                gold: list[str] = []
                ok = True
                for rawref in refs:
                    ref = str(rawref).strip()
                    if not ref:
                        ok = False
                        unresolved["empty_reference"] += 1
                        break
                    matched_text: str | None = None
                    file_token = ref.split(":", 1)[0]
                    candidates = []
                    if any(ext in file_token.lower() for ext in (".md", ".html", ".txt", ".json")):
                        for f in src["files"]:
                            if fnmatch.fnmatch(f.name, file_token) or fnmatch.fnmatch(str(f.relative_to(snap)), file_token):
                                candidates.append(f)
                        if len(candidates) == 1:
                            matched_text = read_text_loose(candidates[0])
                    if matched_text is None:
                        dm = DATE_REF_RE.search(ref)
                        if dm:
                            date = dm.group("date")
                            idx = dm.group("idx")
                            candidates = list(dict.fromkeys(src["by_date"].get(date, [])))
                            if len(candidates) == 1:
                                f = candidates[0]
                                turns = src["conversation_turns"].get(f, [])
                                if idx is not None and turns:
                                    i = int(idx)
                                    options = []
                                    if 0 <= i < len(turns):
                                        options.append(turns[i])
                                    if 1 <= i <= len(turns):
                                        options.append(turns[i - 1])
                                    options = list(dict.fromkeys(options))
                                    if len(options) == 1:
                                        matched_text = options[0]
                                elif idx is None:
                                    matched_text = read_text_loose(f)
                    if matched_text is None:
                        unresolved["unresolved_reference"] += 1
                        ok = False
                        break
                    gold.append(matched_text)
                if not ok or not gold:
                    continue
                seen_queries.add(nq)
                resolved += 1
                legacy.add(
                    bases, "rhelm", f"rhelm:{persona}:{row.get('id', total)}", q, persona,
                    str(row.get("question_type") or "memory"), gold, domain,
                    temporal=str(row.get("question_type") or "").casefold() == "temporal"
                )
                eligible[domain] += 1

        return {
            "dataset": repo,
            "revision": rev,
            "license": license_value,
            "qa_rows": total,
            "gold_resolved_d6_d7_rows": resolved,
            "eligible_by_domain_pre_global_dedup": dict(sorted(eligible.items())),
            "unresolved": dict(sorted(unresolved.items())),
            "gold_rule": "supporting_evidence must resolve mechanically to exactly one source item/turn",
            "candidate_blind": True,
        }


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    firewall_result = firewall()
    (OUTDIR / "candidate-firewall.json").write_text(
        json.dumps(firewall_result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not firewall_result["pass"]:
        (OUTDIR / "infrastructure-qualification.json").write_text(json.dumps({
            "schema_version": "candidate-v13-external-validity-v2-infrastructure-qualification-v1",
            "status": "INFRASTRUCTURE_DEVELOPMENT_CONTAMINATED",
            "candidate_firewall": "FAIL",
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 20

    schema_manifest: dict[str, Any] = {}
    qualification: dict[str, Any] = {
        "schema_version": "candidate-v13-external-validity-v2-source-qualification-v1",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "sources": {},
        "errors": {},
    }
    legacy = load_legacy_module()
    stats = Counter()
    bases: list[dict[str, Any]] = []

    try:
        baseline, baseline_meta = fresh_baseline(legacy)
        bases.extend(baseline)
        qualification["sources"]["baseline-four-source-pool"] = {
            "status": "PASS",
            **baseline_meta,
        }
    except Exception as exc:
        qualification["errors"]["baseline-four-source-pool"] = f"{type(exc).__name__}: {exc}"

    if "baseline-four-source-pool" not in qualification["errors"]:
        try:
            qualification["sources"]["evermembench-dynamic"] = {
                "status": "PASS",
                **evermem(legacy, bases, schema_manifest),
            }
        except Exception as exc:
            qualification["errors"]["evermembench-dynamic"] = f"{type(exc).__name__}: {exc}"

        try:
            qualification["sources"]["rhelm"] = {
                "status": "PASS",
                **rhelm(legacy, bases, schema_manifest),
            }
        except Exception as exc:
            qualification["errors"]["rhelm"] = f"{type(exc).__name__}: {exc}"

    pre_dedup = len(bases)
    bases = legacy.dedup(bases, stats)
    legacy.dynamic(bases)
    source_counts = Counter(b["source"] for b in bases)
    domain_counts = Counter(b["domain"] for b in bases)
    source_domain_counts = Counter((b["source"], b["domain"]) for b in bases)
    family_counts = Counter()
    for b in bases:
        for family, ok in b["flags"].items():
            if ok:
                family_counts[family] += 1

    required_source, required_domain, required_family = legacy.required()
    min_safety_ratio = float(SOURCE_CONTRACT["capacity_policy"]["minimum_safety_ratio"])
    preferred_safety_ratio = float(SOURCE_CONTRACT["capacity_policy"]["preferred_safety_ratio"])
    domain_audit = {}
    hard_shortfalls = []
    safety_warnings = []
    for domain, required in sorted(required_domain.items()):
        eligible = domain_counts[domain]
        ratio = eligible / required if required else math.inf
        status = "PASS_PREFERRED" if ratio >= preferred_safety_ratio else (
            "PASS_MINIMUM_SAFETY" if ratio >= min_safety_ratio else (
                "PASS_REQUIRED_ONLY" if eligible >= required else "FAIL_REQUIRED_CAPACITY"
            )
        )
        domain_audit[domain] = {
            "required": required,
            "eligible": eligible,
            "safety_ratio": ratio,
            "minimum_safety_target": math.ceil(required * min_safety_ratio),
            "preferred_safety_target": math.ceil(required * preferred_safety_ratio),
            "status": status,
        }
        if eligible < required:
            hard_shortfalls.append(domain)
        elif ratio < min_safety_ratio:
            safety_warnings.append(domain)

    family_shortfalls = [
        family for family, required in sorted(required_family.items())
        if family_counts[family] < required
    ]
    source_qualification_ok = not qualification["errors"]
    capacity_status = "PASS" if not hard_shortfalls and not family_shortfalls else "FAIL"

    capacity = {
        "schema_version": "candidate-v13-external-validity-v2-source-capacity-audit-v1",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "pre_dedup_base_count": pre_dedup,
        "deduplicated_base_count": len(bases),
        "normalized_duplicates_removed": stats["normalized_query_duplicates_removed"],
        "source_counts": dict(sorted(source_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
        "source_domain_counts": {f"{s}:{d}": n for (s, d), n in sorted(source_domain_counts.items())},
        "family_counts": dict(sorted(family_counts.items())),
        "domain_capacity": domain_audit,
        "hard_domain_shortfalls": hard_shortfalls,
        "family_shortfalls": family_shortfalls,
        "safety_margin_warnings": safety_warnings,
        "status": capacity_status,
    }

    qualification["status"] = "PASS" if source_qualification_ok else "FAIL"
    (OUTDIR / "source-schema-manifest.json").write_text(
        json.dumps(schema_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUTDIR / "source-qualification.json").write_text(
        json.dumps(qualification, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (OUTDIR / "source-capacity-audit.json").write_text(
        json.dumps(capacity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    gates = {
        "SOURCE_ACCESS_PASS": source_qualification_ok,
        "LICENSE_PASS": source_qualification_ok and all(
            str(v.get("license", "")).lower() in {"apache-2.0", "cc-by-4.0"}
            for k, v in qualification["sources"].items() if k != "baseline-four-source-pool"
        ),
        "SCHEMA_PASS": source_qualification_ok and bool(schema_manifest),
        "PARSER_PASS": source_qualification_ok,
        "GOLD_RESOLUTION_PASS": source_qualification_ok,
        "DOMAIN_MAPPING_PASS": source_qualification_ok,
        "CAPACITY_PASS": capacity_status == "PASS",
        "DEDUP_PASS": True,
        "CONTAMINATION_PASS": False,
        "DETERMINISM_PASS": False,
        "MATERIALIZATION_DRY_RUN_PASS": False,
        "CANDIDATE_FIREWALL_PASS": firewall_result["pass"],
    }
    all_pass = all(gates.values())
    infra = {
        "schema_version": "candidate-v13-external-validity-v2-infrastructure-qualification-v1",
        "status": "PASS" if all_pass else "IN_PROGRESS",
        "gates": gates,
        "formal_authorized": all_pass,
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "note": "Contamination, full determinism, and synthetic materialization dry-run are separate pre-freeze gates.",
    }
    (OUTDIR / "infrastructure-qualification.json").write_text(
        json.dumps(infra, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0 if source_qualification_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
