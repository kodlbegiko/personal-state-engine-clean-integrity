from __future__ import annotations

import copy
import importlib.util
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INTEGRITY = ROOT / "scripts/candidate_v13_external_validity_v2_integrity_qualification.py"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    integrity = load("pse_v2_integrity", INTEGRITY)

    def fixed_build_pool():
        mod = integrity.load_module("pse_v2_source_qualifier_for_integrity", integrity.SRC)
        runner = integrity.load_module("pse_v2_source_runner_for_integrity", integrity.RUNNER)
        runner.bind_schema_verified_evermem(mod)
        mod.rhelm = lambda legacy, bases, schema_manifest: runner.fast_rhelm(mod, legacy, bases, schema_manifest)
        legacy = mod.load_legacy_module()
        bases, baseline_meta = mod.fresh_baseline(legacy)
        manifest: dict[str, Any] = {}
        ever = mod.evermem(legacy, bases, manifest)
        rhelm = mod.rhelm(legacy, bases, manifest)
        pre = len(bases)
        stats = Counter()
        exact_seen: set[str] = set()
        exact_dups = 0
        for b in bases:
            sig = integrity.h(integrity.json.dumps({
                "source": b.get("source"), "id": b.get("id"), "query": integrity.norm(b.get("query")),
                "gold": [integrity.norm(x) for x in b.get("gold", [])], "domain": b.get("domain")
            }, sort_keys=True, separators=(",", ":")))
            if sig in exact_seen:
                exact_dups += 1
            exact_seen.add(sig)
        deduped = legacy.dedup(copy.deepcopy(bases), stats)
        legacy.dynamic(deduped)
        return mod, legacy, deduped, {
            "baseline": baseline_meta,
            "evermembench": ever,
            "rhelm": rhelm,
            "pre_dedup": pre,
            "post_dedup": len(deduped),
            "exact_duplicate_count": exact_dups,
            "normalized_query_duplicates_removed": stats["normalized_query_duplicates_removed"],
        }

    integrity.build_pool = fixed_build_pool
    return int(integrity.main())


if __name__ == "__main__":
    raise SystemExit(main())
