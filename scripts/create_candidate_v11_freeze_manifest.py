from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FROZEN_COMPONENTS = [
    "src/personal_state_engine/candidate_v2.py",
    "src/personal_state_engine/candidate_v10.py",
    "src/personal_state_engine/candidate_v11.py",
    "scripts/generate_candidate_v11_benchmark.py",
    "scripts/generate_candidate_v11_benchmark_v2.py",
    "scripts/generate_candidate_v11_benchmark_v5.py",
    "scripts/validate_candidate_v11_rank_stressor.py",
    "scripts/evaluate_candidate_v11.py",
    "scripts/audit_candidate_v11_freshness.py",
    "scripts/run_candidate_v11_formal.py",
    "scripts/verify_candidate_v11_freeze.py",
    "config/candidate-v11.json",
    "tests/test_candidate_v11.py",
    "docs/research/candidate-v11/preregistration.md",
    "docs/research/candidate-v11/architecture-decision.md",
    "docs/research/candidate-v11/development-report.md",
    ".github/workflows/candidate-v11-formal-mission.yml",
]

FORMAL_BENCHMARKS = [
    "experiments/benchmarks/candidate-v11-protected-v1.json",
    "experiments/benchmarks/candidate-v11-confirmatory-v1.json",
    "experiments/benchmarks/candidate-v11-final-v1.json",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: str):
    return json.loads((ROOT / path).read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--counts", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args()

    dev = load("results/candidate-v11/development-summary-v5.json")
    stress = load("results/candidate-v11/development-rank-stressor-validity-v5.json")
    freshness = load("results/candidate-v11/development-freshness-audit-v5.json")
    comparison = load("results/candidate-v11/architecture-comparison-v1.json")

    if dev["verdict"] != "PASS":
        raise SystemExit("Development-v5 is not PASS")
    if stress["verdict"] != "PASS":
        raise SystemExit("Development rank-stressor validity is not PASS")
    if freshness["verdict"] != "PASS":
        raise SystemExit("Development freshness is not PASS")
    if comparison["architectures"]["C_lexicographic_semantic_proof_ordering"]["R@1"] < 0.97:
        raise SystemExit("Selected architecture C does not satisfy Development rank target")

    preexisting_formal = [path for path in FORMAL_BENCHMARKS if (ROOT / path).exists()]
    if preexisting_formal:
        raise SystemExit(f"formal payload existed before freeze: {preexisting_formal}")

    missing = [path for path in FROZEN_COMPONENTS if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit(f"missing frozen components: {missing}")

    hashes = {path: sha256(ROOT / path) for path in FROZEN_COMPONENTS}
    manifest = {
        "schema_version": "candidate-v11-development-freeze-manifest-v1",
        "status": "DEVELOPMENT_FROZEN",
        "freeze_source_commit_sha": os.environ.get("GITHUB_SHA", "LOCAL"),
        "development_surface": "experiments/benchmarks/candidate-v11-development-v5.json",
        "development_surface_sha256": sha256(ROOT / "experiments/benchmarks/candidate-v11-development-v5.json"),
        "development_summary_sha256": sha256(ROOT / "results/candidate-v11/development-summary-v5.json"),
        "stressor_validity_sha256": sha256(ROOT / "results/candidate-v11/development-rank-stressor-validity-v5.json"),
        "architecture_comparison_sha256": sha256(ROOT / "results/candidate-v11/architecture-comparison-v1.json"),
        "preregistration_commit_sha": "bf6c0d2b1435a9af868f1c6c3faf8f2853a5078b",
        "candidate_v10_terminal_commit": "f909c0da144ada1268145b2f42cf26571231818e",
        "formal_execution_counts_at_freeze": {"protected": 0, "confirmatory": 0, "final": 0},
        "formal_payloads_generated_before_freeze": [],
        "frozen_components_sha256": hashes,
        "frozen_component_count": len(hashes),
        "thresholds_locked": True,
        "seeds_locked": True,
        "bootstrap_locked": True,
        "monetary_cost_usd": 0,
    }

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    args.counts.write_text(json.dumps({
        "schema_version": "candidate-v11-formal-execution-counts-v1",
        "protected": 0,
        "confirmatory": 0,
        "final": 0,
        "terminal_state": None,
    }, indent=2, sort_keys=True) + "\n")
    # Empty JSONL is intentional: formal STARTED/COMPLETED events are appended
    # only by the one-shot formal runner.
    args.ledger.write_text("")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
