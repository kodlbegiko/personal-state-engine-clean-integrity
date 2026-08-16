from __future__ import annotations

"""Conservative fast wrapper around calibrated capacity audit v2.

The original v2 audit performs an unnecessarily expensive full-corpus N9 search.
This wrapper keeps the same source/gold/domain logic, deterministically caps SGD
at a reservoir vastly larger than formal requirements, and evaluates N9 only on
a deterministic per-domain reservoir. This can only under-count capacity.
Candidate-v13 remains unimported/uninvoked and no formal payload is persisted.
"""

import hashlib
import importlib.util
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "scripts/candidate_v13_external_capacity_audit_v2.py"
FAST_OUT = ROOT / "results/candidate-v13-external-validity/capacity-audit-fast.json"

spec = importlib.util.spec_from_file_location("capacity_v2", BASE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load capacity v2 audit")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

_original_load_sgd = mod.load_sgd


def hkey(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(map(str, parts)).encode("utf-8")).hexdigest()


def capped_load_sgd(raw: bytes, bases: list[dict[str, Any]], stats: Any) -> None:
    before = len(bases)
    _original_load_sgd(raw, bases, stats)
    prefix = bases[:before]
    sgd = bases[before:]
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for base in sgd:
        by_domain[base["domain"]].append(base)
    kept: list[dict[str, Any]] = []
    for domain in sorted(by_domain):
        items = by_domain[domain]
        items.sort(key=lambda b: hkey("sgd-capacity-reservoir", domain, b["id"]))
        kept.extend(items[:6000])
        stats[f"sgd_{domain}_full_eligible"] = len(items)
        stats[f"sgd_{domain}_capacity_reservoir"] = min(len(items), 6000)
    stats["sgd_capacity_reservoir_dropped"] += max(0, len(sgd) - len(kept))
    bases[:] = prefix + kept


def fast_dynamic(bases: list[dict[str, Any]]) -> None:
    bydom: dict[str, list[int]] = defaultdict(list)
    psub: dict[str, list[int]] = defaultdict(list)
    psr: dict[tuple[str, str], list[int]] = defaultdict(list)
    qsets: list[set[str]] = []
    gsets: list[list[set[str]]] = []
    for i, base in enumerate(bases):
        bydom[base["domain"]].append(i)
        if base["source"] == "personamem-v2":
            psub[mod.norm(base["subject"])].append(i)
            psr[(mod.norm(base["subject"]), mod.norm(base["relation"]))].append(i)
        qsets.append(mod.tset(base["query"]))
        gsets.append([mod.tset(x) for x in base["gold"]])

    for i, base in enumerate(bases):
        base["flags"]["N3"] = any(bases[j]["subject"] != base["subject"] for j in bydom[base["domain"]] if j != i)
        if base["source"] == "personamem-v2":
            sub, rel = mod.norm(base["subject"]), mod.norm(base["relation"])
            base["flags"]["N4"] = base["flags"].get("N4", False) or any(mod.norm(bases[j]["relation"]) != rel for j in psub[sub] if j != i)
            base["flags"]["N12"] = len(psr[(sub, rel)]) >= 2
        else:
            base["flags"]["N12"] = False
        base["flags"]["N9"] = False

    # Conservative N9 reservoir: at most 1200 bases/domain. Only discovered
    # decoys count as eligible; undiscovered full-corpus decoys remain false.
    for domain in sorted(bydom):
        ids = list(bydom[domain])
        ids.sort(key=lambda i: hkey("n9-reservoir", domain, bases[i]["source"], bases[i]["id"]))
        reservoir = ids[:1200]
        for i in reservoir:
            qs = qsets[i]
            denom = max(1, len(qs))
            best_gold = max((len(qs & g) / denom for g in gsets[i]), default=0.0)
            for j in reservoir:
                if j == i:
                    continue
                score = max((len(qs & g) / denom for g in gsets[j]), default=0.0)
                if score > best_gold:
                    bases[i]["flags"]["N9"] = True
                    break


mod.load_sgd = capped_load_sgd
mod.dynamic = fast_dynamic
mod.OUT = FAST_OUT

if __name__ == "__main__":
    raise SystemExit(mod.main())
