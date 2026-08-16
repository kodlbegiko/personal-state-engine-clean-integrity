from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v9 import evidence_support_signature_v9, pse_candidate_v9_rank

BENCH = ROOT / "experiments/benchmarks/candidate-v9-confirmatory-v1.json"
OUT = ROOT / "results/candidate-v10/candidate-v9-confirmatory-failure-taxonomy-v1.json"
REPORT = ROOT / "docs/research/candidate-v10/candidate-v9-confirmatory-failure-taxonomy.md"


def classify_relevant_cert(cert: dict) -> list[str]:
    clauses = cert["clauses"]
    causes: list[str] = []
    if not any(c.subject_ok for c in clauses):
        causes.append("subject_resolution")
    if not any(c.relation_ok for c in clauses):
        causes.append("relation_abstraction")
    if not any(c.value_type_ok for c in clauses):
        causes.append("typed_value_inference")
    if not any(c.value_bearing for c in clauses):
        causes.append("argument_value_binding")
    if not any(c.temporal_ok for c in clauses):
        causes.append("temporal_interpretation")
    if any(c.blocker is not None for c in clauses) and not any(c.blocker is None for c in clauses):
        causes.append("safety_blocker")
    if not causes:
        # The clause may satisfy individual predicates on different clauses while
        # no single clause forms a complete proof.
        causes.append("cross_clause_proof_composition")
    return causes


def main() -> None:
    payload = json.loads(BENCH.read_text())
    failures = []
    cause_counts: Counter[str] = Counter()
    by_relation: dict[str, int] = defaultdict(int)
    by_value_type: dict[str, int] = defaultdict(int)

    for case in payload["cases"]:
        relevant = set(case["relevant_memory_ids"])
        if not relevant:
            continue
        v2 = pse_candidate_v2_rank(case, 5)
        v9 = pse_candidate_v9_rank(case, 5)
        if relevant & set(v9):
            continue

        sig = evidence_support_signature_v9(case)
        cert_map = {row["memory_id"]: row for row in sig["certifications"]}
        relevant_certs = []
        case_causes: set[str] = set()
        for rid in relevant:
            cert = cert_map.get(rid)
            if cert is None:
                continue
            causes = classify_relevant_cert(cert)
            case_causes.update(causes)
            relevant_certs.append({
                "memory_id": rid,
                "causes": causes,
                "clauses": [asdict(c) for c in cert["clauses"]],
            })

        for cause in case_causes:
            cause_counts[cause] += 1
        for r in sig["requirements"]["relations"]:
            by_relation[r] += 1
        for t in sig["requirements"]["value_types"]:
            by_value_type[t] += 1

        memories = {m["id"]: m for m in case["memories"]}
        failures.append({
            "case_id": case["id"],
            "query": case["query"],
            "relevant_memory_ids": sorted(relevant),
            "relevant_memories": [memories[r] for r in sorted(relevant) if r in memories],
            "candidate_v2_rank": v2,
            "candidate_v9_rank": v9,
            "requirements": sig["requirements"],
            "root_causes": sorted(case_causes),
            "relevant_certifications": relevant_certs,
        })

    result = {
        "schema_version": "candidate-v10-historical-diagnostic-v1",
        "classification": "HISTORICAL_DIAGNOSTIC_ONLY",
        "historical_candidate": "Candidate-v9",
        "historical_stage": "confirmatory",
        "historical_terminal_commit": "a5f627248064ab98fed9e23a1f5eb24707a74c22",
        "preregistration_commit": "d31881019a3df1befbd7faa23df0f009e76485a9",
        "formal_reuse_prohibited": True,
        "case_specific_hardcoding_prohibited": True,
        "failure_count": len(failures),
        "cause_counts": dict(sorted(cause_counts.items())),
        "failure_relation_distribution": dict(sorted(by_relation.items())),
        "failure_value_type_distribution": dict(sorted(by_value_type.items())),
        "failures": failures,
        "monetary_cost_usd": 0,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")

    lines = [
        "# Candidate-v9 Confirmatory Failure Taxonomy for Candidate-v10",
        "",
        "Classification: `HISTORICAL_DIAGNOSTIC_ONLY`",
        "",
        f"Observed false-abstention cases: **{len(failures)}**.",
        "",
        "## Root-cause counts",
        "",
    ]
    for k, v in sorted(cause_counts.items()):
        lines.append(f"- `{k}`: {v}")
    lines += ["", "## Failure cases", ""]
    for row in failures:
        lines += [
            f"### {row['case_id']}",
            f"- query: {row['query']}",
            f"- root causes: {', '.join(row['root_causes'])}",
            f"- relations: {row['requirements']['relations']}",
            f"- value types: {row['requirements']['value_types']}",
            f"- relevant evidence: {' | '.join(m['text'] for m in row['relevant_memories'])}",
            "",
        ]
    lines += [
        "## Interpretation rule",
        "",
        "These cases are historical diagnosis only. Their literal strings, answers, case IDs, and exact constructions are forbidden from Candidate-v10 protected/confirmatory/final generation and inference hardcoding.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n")
    print(json.dumps({"failure_count": len(failures), "cause_counts": result["cause_counts"]}, indent=2))


if __name__ == "__main__":
    main()
