from __future__ import annotations

"""Candidate-blind normalization of v4 artifact filenames after deterministic v3->v4 code generation."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    "prequalification",
    "core",
    "materializer",
    "contamination",
    "qualification_runner",
    "evaluator",
    "formal_runner",
    "formal_sequence",
    "freeze",
    "infrastructure_qualification",
]


def main() -> int:
    if "personal_state_engine.candidate_v13" in sys.modules:
        raise RuntimeError("Candidate imported before v4 filename normalization")
    changed = []
    for stem in TARGETS:
        path = ROOT / "scripts" / f"candidate_v13_external_validity_v4_{stem}.py"
        text = path.read_text(encoding="utf-8")
        normalized = text.replace("-v3.json", "-v4.json").replace("-v3.md", "-v4.md")
        normalized = normalized.replace("-v3-summary.json", "-v4-summary.json")
        normalized = normalized.replace("-v3-materialization-summary.json", "-v4-materialization-summary.json")
        if normalized != text:
            path.write_text(normalized, encoding="utf-8")
            changed.append(str(path.relative_to(ROOT)))
    # Fail closed if any generated v4 implementation still references a v3 artifact filename
    # inside the v4 namespace. Historical v3 paths are allowed only in the bootstrap audit script,
    # which is intentionally excluded from TARGETS.
    remaining = []
    for stem in TARGETS:
        path = ROOT / "scripts" / f"candidate_v13_external_validity_v4_{stem}.py"
        text = path.read_text(encoding="utf-8")
        for needle in (
            "runtime-memory-policy-v3.json",
            "allocation-policy-v3.json",
            "evaluation-policy-v3.json",
            "source-contract-v3.json",
            "source-manifest-v3.json",
            "adapter-policy-v3.json",
            "materializer-contract-v3.json",
            "preregistration-lock-v3.json",
            "preregistration-v3.md",
            "formal-authorization-lock-v3.json",
            "infrastructure-freeze-manifest-v3.json",
            "ev-a-v3-summary.json",
            "ev-b-v3-summary.json",
            "ev-c-v3-summary.json",
        ):
            if needle in text:
                remaining.append(f"{path.name}:{needle}")
    if remaining:
        raise RuntimeError("v4 artifact filename normalization incomplete: " + ", ".join(remaining))
    print(json.dumps({"status": "PASS", "changed": changed, "candidate_v13_imported": False, "candidate_v13_invoked": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
