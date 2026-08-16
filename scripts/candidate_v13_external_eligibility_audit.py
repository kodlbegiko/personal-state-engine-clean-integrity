from __future__ import annotations

"""Pre-performance eligibility audit for Candidate-v13 external validity.

This script downloads only the pinned core source files, reconstructs evaluator
metadata in memory, and emits aggregate capacities. It never imports or invokes
Candidate-v13 and never writes natural-language queries/memories to the repo.
"""

import ast
import csv
import hashlib
import json
import re
import tempfile
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity/eligibility-audit.json"
ADAPTER_POLICY = ROOT / "docs/research/candidate-v13-external-validity/adapter-policy.json"
ALLOCATION_POLICY = ROOT / "docs/research/candidate-v13-external-validity/allocation-policy.json"

EXPECTED_HASHES = {
    "personamem-v2": "95f2a8a324aab7baf2af937feae12731369e2abf7cad5ab3e170594cb25a3e52",
    "longmemeval-cleaned": "821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c",
    "perltqa-mem": "fb3011d78babdc9c5323a8d303ca7d4cdb9e2e08992c9890f9ccb2362ff8be94",
    "perltqa-qa": "ca9f29cbb23eb8f7dbfb792359d9ff90eec066e6d927c83f6c0b7d0bf7baff23",
}

TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_'’-]*")
MODALITY = {"may", "might", "maybe", "perhaps", "possibly", "probably", "plan", "planned", "planning", "hope", "expect", "intend", "tentative", "could", "would", "should"}
COREf = {"he", "she", "they", "them", "their", "his", "her", "hers", "it", "its", "this", "that", "these", "those", "former", "latter"}
CONTRACTION_RE = re.compile(r"\b(?:i'm|i've|i'd|i'll|you're|you've|you'd|you'll|he's|she's|it's|we're|they're|can't|won't|don't|doesn't|didn't|isn't|aren't|wasn't|weren't|couldn't|wouldn't|shouldn't)\b", re.I)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, path: Path) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "pse-external-eligibility-audit/1.0"})
    with urllib.request.urlopen(req, timeout=300) as src, path.open("wb") as out:
        while True:
            block = src.read(1024 * 1024)
            if not block:
                break
            out.write(block)
    return sha256(path)


def hf_url(repo: str, revision: str, rel: str) -> str:
    quoted = "/".join(urllib.parse.quote(part, safe="") for part in rel.split("/"))
    return f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{quoted}?download=true"


def gh_raw(repo: str, revision: str, rel: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{revision}/{rel}"


def norm(text: Any) -> str:
    return " ".join(str(text or "").casefold().split())


def tokens(text: Any) -> set[str]:
    return {m.group(0).casefold().replace("’", "'") for m in TOKEN_RE.finditer(str(text or ""))}


def token_list(text: Any) -> list[str]:
    return [m.group(0).casefold().replace("’", "'") for m in TOKEN_RE.finditer(str(text or ""))]


def stable_id(*parts: Any) -> str:
    raw = "\x1f".join(str(x) for x in parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def candidate_guard() -> dict[str, Any]:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    modules: list[str] = []
    calls: list[str] = []
    forbidden_calls = {"pse_candidate_v13_rank", "evidence_support_signature_v13"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(a.name for a in node.names if "candidate_v13" in a.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "candidate_v13" in module:
                modules.append(module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in forbidden_calls:
                calls.append(node.func.id)
            if isinstance(node.func, ast.Attribute) and node.func.attr in forbidden_calls:
                calls.append(node.func.attr)
    return {"pass": not modules and not calls, "forbidden_modules": sorted(set(modules)), "forbidden_calls": sorted(set(calls))}


def classify_domain(policy: dict[str, Any], source: str, query: str, relation: str, gold_texts: list[str], meta: dict[str, Any]) -> str | None:
    if source == "perltqa-en-v2" and meta.get("section") == "profile":
        ref = meta.get("profile_ref")
        overrides = policy["domain_classifier"]["structured_overrides"]["perltqa_profile"]
        for domain, fields in overrides.items():
            if ref in fields:
                return domain
    hay = norm(" ".join([query, relation, *gold_texts]))
    rules = policy["domain_classifier"]["lexical_rules"]
    for domain in policy["domain_classifier"]["priority"]:
        for phrase in rules[domain]:
            p = norm(phrase)
            if " " in p:
                if p in hay:
                    return domain
            elif re.search(rf"(?<![a-z0-9_]){re.escape(p)}(?![a-z0-9_])", hay):
                return domain
    if source == "personamem-v2":
        return "D1"
    if source == "perltqa-en-v2" and meta.get("section") in {"events", "dialogues"}:
        return "D8"
    if source == "longmemeval-cleaned":
        return "D8"
    return None


def query_natural_flags(query: str, subject: str, gold_texts: list[str], temporal: bool, contradiction: bool, discourse_markers: Iterable[str]) -> dict[str, bool]:
    qtokens = token_list(query)
    qset = set(qtokens)
    qn = norm(query)
    joined = norm(" ".join([query, *gold_texts]))
    subject_present = bool(subject) and norm(subject) in qn
    coref = bool(qset & COREf) and not subject_present
    modality = bool((qset | tokens(joined)) & MODALITY)
    punctuation_boundaries = sum(query.count(ch) for ch in [",", ";", "(", ")"])
    discourse = len(qtokens) >= 18 or punctuation_boundaries >= 2 or any(norm(m) in qn for m in discourse_markers)
    terminal_q = query.rstrip().endswith("?")
    n1 = 5 <= len(qtokens) <= 18 and terminal_q and not coref and not modality
    starts_coref = bool(qtokens and qtokens[0] in COREf)
    fragment = len(qtokens) <= 12 and (
        not terminal_q
        or starts_coref
        or "..." in query
        or "…" in query
        or bool(CONTRACTION_RE.search(query))
        or bool(query[:1] and query[:1].islower())
    )
    return {"N1": n1, "N2": discourse, "N5": coref, "N6": temporal, "N7": contradiction, "N8": modality, "N11": fragment}


def add_base(bases: list[dict[str, Any]], policy: dict[str, Any], *, source: str, base_id: str, query: str, subject: str, relation: str, gold_texts: list[str], temporal: bool = False, contradiction: bool = False, meta: dict[str, Any] | None = None) -> None:
    meta = meta or {}
    if not norm(query) or not gold_texts or not all(norm(x) for x in gold_texts):
        return
    domain = classify_domain(policy, source, query, relation, gold_texts, meta)
    if domain is None:
        return
    flags = query_natural_flags(query, subject, gold_texts, temporal, contradiction, policy["generic_discourse_markers"])
    bases.append({
        "source": source,
        "base_id": base_id,
        "query": query,
        "subject": subject,
        "relation": relation or "unknown",
        "gold_texts": gold_texts,
        "domain": domain,
        "flags": flags,
    })


def load_personamem(path: Path, policy: dict[str, Any], bases: list[dict[str, Any]], stats: Counter[str]) -> None:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            stats["personamem_rows"] += 1
            query = str(row.get("user_query", ""))
            gold = str(row.get("related_conversation_snippet", ""))
            subject = str(row.get("persona_id", "")) or f"persona-row-{idx}"
            relation = str(row.get("topic_preference", "")).strip() or str(row.get("topic_query", "")).strip() or "preference"
            prev = str(row.get("prev_pref", "")).strip()
            current = str(row.get("preference", "")).strip()
            updated = norm(row.get("updated")) in {"true", "1", "yes", "y"} or bool(prev)
            contradiction = bool(prev and current and norm(prev) != norm(current))
            before = len(bases)
            add_base(bases, policy, source="personamem-v2", base_id=f"pm:{idx}:{stable_id(subject, idx)}", query=query, subject=subject, relation=relation, gold_texts=[gold], temporal=updated, contradiction=contradiction, meta={"pref_type": row.get("pref_type", "")})
            stats["personamem_eligible"] += len(bases) - before


def session_text(session: Any) -> str:
    if not isinstance(session, list):
        return ""
    parts = []
    for message in session:
        if isinstance(message, dict):
            content = str(message.get("content", "")).strip()
            if content:
                parts.append(content)
    return "\n".join(parts)


def load_longmemeval(path: Path, policy: dict[str, Any], bases: list[dict[str, Any]], stats: Counter[str]) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    for idx, row in enumerate(data if isinstance(data, list) else []):
        stats["longmemeval_rows"] += 1
        qid = str(row.get("question_id", idx))
        ids = [str(x) for x in (row.get("haystack_session_ids") or [])]
        sessions = row.get("haystack_sessions") or []
        if len(ids) != len(sessions):
            stats["longmemeval_alignment_fail"] += 1
            continue
        text_by_id = {sid: session_text(session) for sid, session in zip(ids, sessions)}
        gold_ids = [str(x) for x in (row.get("answer_session_ids") or [])]
        if not gold_ids or any(gid not in text_by_id for gid in gold_ids):
            stats["longmemeval_gold_mapping_fail"] += 1
            continue
        gold_texts = [text_by_id[gid] for gid in gold_ids]
        qtype = str(row.get("question_type", "unknown"))
        temporal = qtype in {"knowledge-update", "temporal-reasoning"}
        before = len(bases)
        add_base(bases, policy, source="longmemeval-cleaned", base_id=f"lme:{qid}", query=str(row.get("question", "")), subject=qid, relation=qtype, gold_texts=gold_texts, temporal=temporal, contradiction=False, meta={"question_type": qtype})
        stats["longmemeval_eligible"] += len(bases) - before


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


def ref_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str):
        return [value]
    return []


def perlt_memory_text(section: str, record: Any) -> str:
    if section == "profile":
        return str(record or "").strip()
    if not isinstance(record, dict):
        return ""
    if section == "events":
        return str(record.get("content") or record.get("summary") or "").strip()
    if section == "social_relationship":
        return str(record.get("Description") or "").strip()
    if section == "dialogues":
        return str(record.get("contents") or "").strip()
    return ""


def perlt_relation(section: str, refs: list[str], records: list[Any]) -> str:
    if section == "profile":
        return refs[0] if refs else "profile"
    first = records[0] if records else None
    if isinstance(first, dict):
        if section == "events":
            return str(first.get("Theme") or "events")
        if section == "social_relationship":
            return str(first.get("Relationship") or "social_relationship")
    return section


def load_perltqa(mem_path: Path, qa_path: Path, policy: dict[str, Any], bases: list[dict[str, Any]], stats: Counter[str]) -> None:
    mem = json.loads(mem_path.read_text(encoding="utf-8"))
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    for path, row in walk_qa(qa):
        stats["perltqa_canonical_rows"] += 1
        char = next((x for x in path if isinstance(x, str) and isinstance(mem, dict) and x in mem), None)
        section = next((str(x) for x in path if str(x) in {"profile", "events", "social_relationship", "dialogues"}), None)
        if not char or not section or not isinstance(mem.get(char), dict):
            stats["perltqa_character_or_section_unresolved"] += 1
            continue
        refs = ref_list(row.get("Reference Memory"))
        if not refs:
            stats["perltqa_empty_reference"] += 1
            continue
        container = mem[char].get(section)
        records: list[Any] = []
        ok = True
        if section == "profile":
            if not isinstance(container, dict):
                ok = False
            else:
                for ref in refs:
                    if ref not in container:
                        ok = False
                        break
                    records.append(container[ref])
        else:
            if not isinstance(container, dict):
                ok = False
            else:
                for ref in refs:
                    if ref not in container:
                        ok = False
                        break
                    records.append(container[ref])
        if not ok:
            stats["perltqa_reference_unresolved"] += 1
            continue
        gold_texts = [perlt_memory_text(section, r) for r in records]
        if not all(norm(x) for x in gold_texts):
            stats["perltqa_empty_memory_text"] += 1
            continue
        relation = perlt_relation(section, refs, records)
        meta = {"section": section, "profile_ref": refs[0] if section == "profile" and refs else None}
        before = len(bases)
        add_base(bases, policy, source="perltqa-en-v2", base_id=f"plt:{stable_id(*path)}", query=str(row.get("Question", "")), subject=str(char), relation=relation, gold_texts=gold_texts, temporal=False, contradiction=False, meta=meta)
        stats["perltqa_eligible"] += len(bases) - before


def mark_dynamic_families(bases: list[dict[str, Any]]) -> None:
    by_subject: dict[str, list[int]] = defaultdict(list)
    by_subject_relation: dict[tuple[str, str], list[int]] = defaultdict(list)
    by_domain: dict[str, list[int]] = defaultdict(list)
    inverted: dict[tuple[str, str], set[int]] = defaultdict(set)
    gold_token_sets: list[list[set[str]]] = []
    query_sets: list[set[str]] = []
    for i, base in enumerate(bases):
        by_subject[norm(base["subject"])].append(i)
        by_subject_relation[(norm(base["subject"]), norm(base["relation"]))].append(i)
        by_domain[base["domain"]].append(i)
        qset = tokens(base["query"])
        query_sets.append(qset)
        gsets = [tokens(x) for x in base["gold_texts"]]
        gold_token_sets.append(gsets)
        for gset in gsets:
            for tok in gset:
                inverted[(base["domain"], tok)].add(i)
    for i, base in enumerate(bases):
        flags = base["flags"]
        subject_key = norm(base["subject"])
        relation_key = norm(base["relation"])
        flags["N3"] = any(norm(bases[j]["subject"]) != subject_key for j in by_domain[base["domain"]])
        flags["N4"] = any(norm(bases[j]["relation"]) != relation_key for j in by_subject[subject_key])
        flags["N12"] = len(by_subject_relation[(subject_key, relation_key)]) >= 2
        flags["N10"] = True
        qset = query_sets[i]
        best_gold = max((len(qset & g) / max(1, len(qset)) for g in gold_token_sets[i]), default=0.0)
        candidate_ids: set[int] = set()
        for tok in qset:
            candidate_ids.update(inverted.get((base["domain"], tok), set()))
        found = False
        for j in candidate_ids:
            if j == i:
                continue
            score = max((len(qset & g) / max(1, len(qset)) for g in gold_token_sets[j]), default=0.0)
            if score > best_gold:
                found = True
                break
        flags["N9"] = found


def aggregate(bases: list[dict[str, Any]], allocation: dict[str, Any]) -> dict[str, Any]:
    source_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    source_domain: Counter[tuple[str, str]] = Counter()
    family_counts: Counter[str] = Counter()
    family_by_source: dict[str, Counter[str]] = defaultdict(Counter)
    for base in bases:
        source_counts[base["source"]] += 1
        domain_counts[base["domain"]] += 1
        source_domain[(base["source"], base["domain"])] += 1
        for family, eligible in base["flags"].items():
            if eligible:
                family_counts[family] += 1
                family_by_source[base["source"]][family] += 1
    required_source_domain: Counter[tuple[str, str]] = Counter()
    required_family: Counter[str] = Counter()
    for stage, domains in allocation["source_domain_targets"].items():
        for domain, sources in domains.items():
            for source, count in sources.items():
                required_source_domain[(source, domain)] += int(count)
    for stage, families in allocation["structural_family_targets"].items():
        for family, count in families.items():
            required_family[family] += int(count)
    sd_shortfalls = []
    for key, required in sorted(required_source_domain.items()):
        available = source_domain[key]
        if available < required:
            sd_shortfalls.append({"source": key[0], "domain": key[1], "required_all_stages": required, "available_unique_base_items": available, "shortfall": required - available})
    family_shortfalls = []
    for family, required in sorted(required_family.items()):
        available = family_counts[family]
        if available < required:
            family_shortfalls.append({"family": family, "required_all_stages": required, "available_unique_base_items": available, "shortfall": required - available})
    return {
        "eligible_base_count": len(bases),
        "source_counts": dict(sorted(source_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
        "source_domain_counts": {f"{s}:{d}": source_domain[(s, d)] for s, d in sorted(source_domain)},
        "family_eligibility_counts": dict(sorted(family_counts.items())),
        "family_eligibility_by_source": {s: dict(sorted(c.items())) for s, c in sorted(family_by_source.items())},
        "required_source_domain_all_stages": {f"{s}:{d}": required_source_domain[(s, d)] for s, d in sorted(required_source_domain)},
        "required_family_all_stages": dict(sorted(required_family.items())),
        "source_domain_shortfalls": sd_shortfalls,
        "family_capacity_shortfalls": family_shortfalls,
        "basic_capacity_pass": not sd_shortfalls and not family_shortfalls,
    }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    adapter = json.loads(ADAPTER_POLICY.read_text(encoding="utf-8"))
    allocation = json.loads(ALLOCATION_POLICY.read_text(encoding="utf-8"))
    result: dict[str, Any] = {
        "schema_version": "candidate-v13-external-eligibility-audit-v1",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "guard": candidate_guard(),
        "adapter_policy_sha256": sha256(ADAPTER_POLICY),
        "allocation_policy_sha256": sha256(ALLOCATION_POLICY),
    }
    if not result["guard"]["pass"]:
        result["status"] = "FAIL_GUARD"
        OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return 2
    stats: Counter[str] = Counter()
    bases: list[dict[str, Any]] = []
    try:
        with tempfile.TemporaryDirectory(prefix="pse-ev-elig-") as td_raw:
            td = Path(td_raw)
            pm = td / "personamem.csv"
            lme = td / "longmemeval.json"
            plt_mem = td / "perltmem.json"
            plt_qa = td / "perltqa.json"
            hashes = {
                "personamem-v2": download(hf_url("bowen-upenn/PersonaMem-v2", "b7b42b78917157afed063527a1c959e98f6109f2", "benchmark/text/benchmark.csv"), pm),
                "longmemeval-cleaned": download(hf_url("xiaowu0162/longmemeval-cleaned", "98d7416c24c778c2fee6e6f3006e7a073259d48f", "longmemeval_oracle.json"), lme),
                "perltqa-mem": download(gh_raw("Elvin-Yiming-Du/PerLTQA", "8d9e19868e239740ef701e603ec205cd581f221b", "Dataset/en_v2/perltmem_en_v2.json"), plt_mem),
                "perltqa-qa": download(gh_raw("Elvin-Yiming-Du/PerLTQA", "8d9e19868e239740ef701e603ec205cd581f221b", "Dataset/en_v2/perltqa_en_v2.json"), plt_qa),
            }
            result["source_hashes"] = hashes
            bad = {k: {"expected": EXPECTED_HASHES[k], "actual": v} for k, v in hashes.items() if EXPECTED_HASHES[k] != v}
            if bad:
                result["status"] = "FAIL_SOURCE_HASH"
                result["source_hash_mismatches"] = bad
                OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
                return 3
            load_personamem(pm, adapter, bases, stats)
            load_longmemeval(lme, adapter, bases, stats)
            load_perltqa(plt_mem, plt_qa, adapter, bases, stats)
        mark_dynamic_families(bases)
        result["loader_stats"] = dict(sorted(stats.items()))
        result["capacity"] = aggregate(bases, allocation)
        result["status"] = "PASS_BASIC_CAPACITY" if result["capacity"]["basic_capacity_pass"] else "CAPACITY_SHORTFALL"
    except Exception as exc:
        result["status"] = "FAIL_EXCEPTION"
        result["error"] = f"{type(exc).__name__}: {exc}"
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if result["status"] in {"PASS_BASIC_CAPACITY", "CAPACITY_SHORTFALL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
