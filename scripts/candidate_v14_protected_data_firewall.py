from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Scope is intentionally limited to Candidate-v14 development/qualification assets.
# Historical Candidate-v7..v13 and External Validity v2/v3/v4 infrastructure are
# immutable lineage evidence, not inputs to Candidate-v14 development. Scanning
# the entire inherited repository would therefore create false positives merely
# because those historical files legitimately contain protected-evaluation terms.
SCAN_GLOBS = [
    "src/personal_state_engine/candidate_v14.py",
    "scripts/candidate_v14_*.py",
    "tests/test_candidate_v14*.py",
    ".github/workflows/candidate-v14-*.yml",
    "data/candidate-v14-development/*.json",
]

FORBIDDEN = [
    re.compile(r"ev[-_]?a[-_]?v4.*(?:case|query|memory|assignment|seed)", re.I),
    re.compile(r"ev[-_]?[bc][-_]?v4.*(?:assignment|case|seed)", re.I),
    re.compile(r"protected.*(?:case[_ -]?id|query[_ -]?text|memory[_ -]?text|assignment|seed)", re.I),
    re.compile(r"formal[_ -]?assignment", re.I),
]

# The scanner necessarily contains the forbidden patterns as data.
ALLOW_CONTENT_SCAN = {"scripts/candidate_v14_protected_data_firewall.py": False}
HOLDOUT = "data/candidate-v14-development/untouched-internal-holdout.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_files() -> list[Path]:
    found: dict[str, Path] = {}
    for pattern in SCAN_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file() and "__pycache__" not in path.parts:
                found[path.relative_to(ROOT).as_posix()] = path
    return [found[key] for key in sorted(found)]


def main() -> int:
    violations: list[dict[str, str]] = []
    scanned: list[dict[str, str | bool]] = []

    for path in candidate_files():
        rel = path.relative_to(ROOT).as_posix()
        content_inspected = rel != HOLDOUT and ALLOW_CONTENT_SCAN.get(rel, True)
        scanned.append(
            {
                "path": rel,
                "sha256": sha256(path),
                "content_inspected": content_inspected,
            }
        )
        if not content_inspected:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for regex in FORBIDDEN:
            for match in regex.finditer(text):
                violations.append(
                    {
                        "path": rel,
                        "pattern": regex.pattern,
                        "match": match.group(0)[:160],
                    }
                )

    out = {
        "schema_version": "candidate-v14-protected-firewall-v2",
        "scope": "Candidate-v14 executable, development, test, workflow, and generated-data assets only; inherited historical v7-v13/evaluation infrastructure excluded; untouched holdout hash-only pre-freeze",
        "scan_globs": SCAN_GLOBS,
        "scanned_file_count": len(scanned),
        "violations": violations,
        "protected_case_level_data_used": False if not violations else None,
        "protected_assignment_reconstruction": False if not violations else None,
        "holdout_content_inspected": False,
        "status": "PASS" if not violations else "FAIL",
        "files": scanned,
    }
    output = ROOT / "results/candidate-v14/protected-data-firewall.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0 if not violations else 2


if __name__ == "__main__":
    raise SystemExit(main())
