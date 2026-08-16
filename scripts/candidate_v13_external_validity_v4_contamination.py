from __future__ import annotations

"""Strict v3 contamination audit, including prior v2 infrastructure artifacts.

Adds normalized-substring checks and explicitly checks v2 formal-infrastructure
text in addition to the historical benchmark/development scan. Candidate-v13 is
never imported or invoked.
"""

import csv
import difflib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V2_AUDIT = ROOT / "scripts/candidate_v13_external_validity_v2_strict_contamination.py"


def _load():
    name = "pse_v4_v2_contamination_primitives"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, V2_AUDIT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load v2 contamination primitives")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def prior_v2_strings(v2: Any, root: Path) -> tuple[list[str], dict[str, int]]:
    roots = [
        root / "docs/research/candidate-v13-external-validity-v2",
        root / "results/candidate-v13-external-validity-v2",
    ]
    values: list[str] = []
    stats = Counter()
    for base in roots:
        if not base.exists():
            continue
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            try:
                suffix = path.suffix.casefold()
                raw: list[str] = []
                if suffix == ".json":
                    raw.extend(v2.strings_from_json(json.loads(path.read_text(encoding="utf-8"))))
                elif suffix == ".jsonl":
                    for line in path.read_text(encoding="utf-8").splitlines():
                        if line.strip():
                            raw.extend(v2.strings_from_json(json.loads(line)))
                elif suffix == ".csv":
                    with path.open("r", encoding="utf-8", newline="") as fh:
                        for row in csv.reader(fh):
                            raw.extend(row)
                elif suffix in {".md", ".txt", ".yml", ".yaml", ".py"}:
                    raw.extend(path.read_text(encoding="utf-8").splitlines())
                else:
                    continue
                stats["files_scanned"] += 1
                for item in raw:
                    n = v2.norm(item)
                    if len(n) >= 24 and len(v2.tokens(n)) >= 5:
                        values.append(n)
                        stats["meaningful_strings"] += 1
            except Exception:
                stats["files_unreadable"] += 1
    unique = sorted(set(values))
    stats["unique_meaningful_strings"] = len(unique)
    return unique, dict(sorted(stats.items()))


def supplemental_overlap_audit(v2: Any, root: Path, bases: list[dict[str, Any]]) -> dict[str, Any]:
    historical, historical_stats = v2.project_strings(root)
    prior, prior_stats = prior_v2_strings(v2, root)
    internals = historical + [x for x in prior if x not in set(historical)]
    kinds = ["historical"] * len(historical) + ["prior_v2"] * (len(internals) - len(historical))
    grams = [v2.fivegrams(x) for x in internals]
    skeletons = [v2.skeleton(x) for x in internals]
    gram_index: dict[str, list[int]] = defaultdict(list)
    for i, gs in enumerate(grams):
        for gram in gs:
            gram_index[gram].append(i)

    counts = Counter()
    hashes: list[dict[str, Any]] = []
    checked = 0
    for base in bases:
        payloads = [("query", str(base.get("query") or ""))]
        payloads.extend(("memory", str(x)) for x in (base.get("gold") or []))
        for payload_kind, raw in payloads:
            n = v2.norm(raw)
            if len(n) < 24 or len(v2.tokens(n)) < 5:
                continue
            checked += 1
            g = v2.fivegrams(n)
            candidate_ids: set[int] = set()
            for gram in g:
                candidate_ids.update(gram_index.get(gram, ()))
            digest = v2.sha(n)
            found = False
            for idx in candidate_ids:
                other = internals[idx]
                source_class = kinds[idx]
                if n != other and (n in other or other in n):
                    reason = f"normalized_substring_overlap:{source_class}:{payload_kind}"
                    counts[reason] += 1
                    if len(hashes) < 250:
                        hashes.append({"payload_sha256": digest, "reason": reason, "source": str(base.get("source"))})
                    found = True
                    break
                if source_class == "prior_v2":
                    if n == other:
                        reason = f"normalized_exact_overlap:prior_v2:{payload_kind}"
                        counts[reason] += 1
                        if len(hashes) < 250:
                            hashes.append({"payload_sha256": digest, "reason": reason, "source": str(base.get("source"))})
                        found = True
                        break
                    other_g = grams[idx]
                    union = len(g | other_g)
                    score = len(g & other_g) / union if union else 0.0
                    if score >= 0.85:
                        reason = f"token_5gram_jaccard_prior_v2:{payload_kind}"
                        counts[reason] += 1
                        if len(hashes) < 250:
                            hashes.append({"payload_sha256": digest, "reason": reason, "score": score, "source": str(base.get("source"))})
                        found = True
                        break
                    sk = v2.skeleton(n)
                    other_sk = skeletons[idx]
                    if sk and other_sk:
                        score = difflib.SequenceMatcher(None, sk, other_sk, autojunk=False).ratio()
                        if score >= 0.92:
                            reason = f"{payload_kind}_skeleton_overlap_prior_v2"
                            counts[reason] += 1
                            if len(hashes) < 250:
                                hashes.append({"payload_sha256": digest, "reason": reason, "score": score, "source": str(base.get("source"))})
                            found = True
                            break
            if found:
                continue
    return {
        "historical_scan": historical_stats,
        "prior_v2_scan": prior_stats,
        "external_payloads_checked": checked,
        "counts": dict(sorted(counts.items())),
        "overlap_hash_records": hashes,
        "material_overlap_count": sum(counts.values()),
    }


def audit(root: Path, bases: list[dict[str, Any]]) -> dict[str, Any]:
    v2 = _load()
    baseline = v2.audit(root, bases)
    supplemental = supplemental_overlap_audit(v2, root, bases)
    total = int(baseline.get("material_overlap_count", 0)) + int(supplemental["material_overlap_count"])
    return {
        "schema_version": "candidate-v13-external-validity-v4-contamination-audit-v1",
        "candidate_v13_invoked": False,
        "formal_case_materialized": False,
        "methods": [
            "normalized-exact-overlap",
            "normalized-substring-overlap",
            "token-5gram-jaccard>=0.85",
            "query-skeleton-overlap>=0.92",
            "memory-skeleton-overlap>=0.92",
            "synthetic-namespace-collision",
            "prior-v2-formal-infrastructure-overlap",
        ],
        "historical_candidate_development_audit": baseline,
        "supplemental_v3_audit": supplemental,
        "material_overlap_count": total,
        "status": "PASS" if total == 0 else "FAIL",
    }
