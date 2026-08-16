from __future__ import annotations

"""Strict candidate-blind contamination audit for External Validity v2.

Implements the historical preregistration's overlap classes without consulting
Candidate-v13 output: exact, normalized, token 5-gram Jaccard, project synthetic
namespace tokens, and normalized skeleton similarity.
"""

import csv
import difflib
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_'’-]*")
SYNTHETIC_TOKEN_RE = re.compile(
    r"^(?:subject|entity|memory|mem|person|user|case|fixture|synthetic|candidate|benchmark)[-_]?[a-z]*\d{1,8}$",
    re.I,
)
UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b", re.I)
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
EMAIL_RE = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
QUOTED_RE = re.compile(r"(['\"]).*?\1")


def norm(x: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(x or "")).casefold().replace("’", "'").split())


def tokens(x: Any) -> list[str]:
    return [m.group(0).casefold().replace("’", "'") for m in TOKEN_RE.finditer(norm(x))]


def fivegrams(x: Any) -> set[str]:
    ts = tokens(x)
    if len(ts) < 5:
        return set()
    return {"\x1f".join(ts[i:i + 5]) for i in range(len(ts) - 4)}


def skeleton(x: Any) -> str:
    s = norm(x)
    s = EMAIL_RE.sub("<email>", s)
    s = UUID_RE.sub("<uuid>", s)
    s = QUOTED_RE.sub("<quoted>", s)
    s = NUMBER_RE.sub("<num>", s)
    out = []
    for t in tokens(s):
        if SYNTHETIC_TOKEN_RE.match(t):
            out.append("<entity>")
        elif len(t) >= 16 and any(c.isdigit() for c in t) and any(c.isalpha() for c in t):
            out.append("<id>")
        else:
            out.append(t)
    return " ".join(out)


def sha(x: str) -> str:
    return hashlib.sha256(x.encode("utf-8")).hexdigest()


def strings_from_json(node: Any) -> Iterable[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for item in node:
            yield from strings_from_json(item)
    elif isinstance(node, dict):
        for value in node.values():
            yield from strings_from_json(value)


def project_strings(root: Path) -> tuple[list[str], dict[str, int]]:
    roots = [
        root / "experiments/benchmarks",
        root / "tests/fixtures",
        root / "docs/research/candidate-v13",
        root / "results/candidate-v13",
        root / "docs/research/candidate-v12",
        root / "results/candidate-v12",
    ]
    out: list[str] = []
    stats = Counter()
    for base in roots:
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            if "candidate-v13-external-validity-v2" in str(path):
                continue
            try:
                values: list[str] = []
                suffix = path.suffix.casefold()
                if suffix == ".json":
                    values.extend(strings_from_json(json.loads(path.read_text(encoding="utf-8"))))
                elif suffix == ".jsonl":
                    for line in path.read_text(encoding="utf-8").splitlines():
                        if line.strip():
                            values.extend(strings_from_json(json.loads(line)))
                elif suffix == ".csv":
                    with path.open("r", encoding="utf-8", newline="") as f:
                        for row in csv.reader(f):
                            values.extend(row)
                elif suffix in {".txt", ".md"}:
                    values.extend(path.read_text(encoding="utf-8").splitlines())
                else:
                    continue
                stats["files_scanned"] += 1
                for value in values:
                    n = norm(value)
                    if len(n) >= 24 and len(tokens(n)) >= 5:
                        out.append(n)
                        stats["meaningful_strings"] += 1
            except Exception:
                stats["files_unreadable"] += 1
    # Deduplicate to reduce candidate comparisons.
    unique = sorted(set(out))
    stats["unique_meaningful_strings"] = len(unique)
    return unique, dict(sorted(stats.items()))


def audit(root: Path, bases: list[dict[str, Any]]) -> dict[str, Any]:
    internal, scan_stats = project_strings(root)
    internal_norm = {sha(s): i for i, s in enumerate(internal)}
    internal_grams: list[set[str]] = [fivegrams(s) for s in internal]
    internal_skeletons: list[str] = [skeleton(s) for s in internal]
    gram_index: dict[str, list[int]] = defaultdict(list)
    for i, grams in enumerate(internal_grams):
        for gram in grams:
            gram_index[gram].append(i)

    synthetic_vocab: set[str] = set()
    for s in internal:
        for t in tokens(s):
            if SYNTHETIC_TOKEN_RE.match(t):
                synthetic_vocab.add(t)

    counts = Counter()
    overlaps: list[dict[str, Any]] = []
    checked = 0

    def record(base: dict[str, Any], kind: str, reason: str, digest: str, score: float | None = None) -> None:
        counts[reason] += 1
        if len(overlaps) < 250:
            item = {
                "source": str(base.get("source")),
                "kind": kind,
                "reason": reason,
                "payload_sha256": digest,
            }
            if score is not None:
                item["score"] = score
            overlaps.append(item)

    for base in bases:
        payloads: list[tuple[str, str]] = [("query", str(base.get("query") or ""))]
        payloads.extend(("memory", str(x)) for x in (base.get("gold") or []))
        for kind, raw in payloads:
            n = norm(raw)
            ts = tokens(n)
            if len(n) < 24 or len(ts) < 5:
                continue
            checked += 1
            digest = sha(n)

            if digest in internal_norm:
                record(base, kind, "normalized_exact_duplicate", digest, 1.0)
                continue

            role_tokens = set(ts)
            synth_hit = sorted(role_tokens & synthetic_vocab)
            if synth_hit:
                record(base, kind, "synthetic_namespace_overlap", digest, 1.0)
                continue

            grams = fivegrams(n)
            candidate_ids: set[int] = set()
            for gram in grams:
                candidate_ids.update(gram_index.get(gram, ()))

            contaminated = False
            if grams:
                for idx in candidate_ids:
                    other = internal_grams[idx]
                    if not other:
                        continue
                    inter = len(grams & other)
                    union = len(grams | other)
                    score = inter / union if union else 0.0
                    if score >= 0.85:
                        record(base, kind, "token_5gram_jaccard", digest, score)
                        contaminated = True
                        break
            if contaminated:
                continue

            sk = skeleton(n)
            if sk and candidate_ids:
                for idx in candidate_ids:
                    other_sk = internal_skeletons[idx]
                    if not other_sk:
                        continue
                    # SequenceMatcher is deterministic; candidate restriction comes only
                    # from shared natural-language 5-grams, avoiding quadratic scans.
                    score = difflib.SequenceMatcher(None, sk, other_sk, autojunk=False).ratio()
                    if score >= 0.92:
                        record(base, kind, "skeleton_similarity", digest, score)
                        contaminated = True
                        break

    total = sum(counts.values())
    return {
        "schema_version": "candidate-v13-external-validity-v2-contamination-audit-v2",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "methods": [
            "exact-normalized-overlap",
            "token-5gram-jaccard>=0.85",
            "project-synthetic-namespace-token-overlap",
            "normalized-skeleton-similarity>=0.92",
        ],
        "historical_scan": scan_stats,
        "external_payloads_checked": checked,
        "contamination_counts": dict(sorted(counts.items())),
        "material_overlap_count": total,
        "overlap_hash_records": overlaps,
        "status": "PASS" if total == 0 else "FAIL",
    }
