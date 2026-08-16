from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "results/candidate-v11/development-freeze-manifest-v1.json")
    parser.add_argument("--counts", type=Path, default=ROOT / "results/candidate-v11/formal-execution-counts-v1.json")
    parser.add_argument("--require-zero-counts", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    counts = json.loads(args.counts.read_text())
    mismatches = []
    for rel, expected in manifest["frozen_components_sha256"].items():
        path = ROOT / rel
        actual = sha256(path) if path.is_file() else None
        if actual != expected:
            mismatches.append({"path": rel, "expected": expected, "actual": actual})

    zero_counts = all(counts.get(stage) == 0 for stage in ("protected", "confirmatory", "final"))
    count_guard = zero_counts if args.require_zero_counts else True
    dev_sha_ok = sha256(ROOT / manifest["development_surface"]) == manifest["development_surface_sha256"]

    result = {
        "schema_version": "candidate-v11-freeze-verification-v1",
        "frozen_component_count": manifest["frozen_component_count"],
        "hash_mismatch_count": len(mismatches),
        "hash_mismatches": mismatches,
        "development_surface_hash_pass": dev_sha_ok,
        "formal_counts": {stage: counts.get(stage) for stage in ("protected", "confirmatory", "final")},
        "zero_count_guard_required": bool(args.require_zero_counts),
        "zero_count_guard_pass": count_guard,
        "verdict": "PASS" if not mismatches and dev_sha_ok and count_guard else "FAIL",
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["verdict"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
