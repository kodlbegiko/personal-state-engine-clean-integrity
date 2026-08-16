from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v10 import certify_memory_v10, semantic_requirements_v10


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--minimum-v2-competitor-rank1-rate", type=float, default=0.20)
    args = parser.parse_args()

    payload = json.loads(args.benchmark.read_text())
    answerable = [case for case in payload["cases"] if case["relevant_memory_ids"]]
    eligible_competitor_count = 0
    v2_competitor_rank1_count = 0
    invalid: list[dict] = []

    for case in answerable:
        competitors = [
            memory for memory in case["memories"]
            if "eligible-lexical-competitor" in str(memory["id"])
        ]
        if len(competitors) != 1:
            invalid.append({"case_id": case["id"], "reason": "missing_or_multiple_competitors"})
            continue
        competitor = competitors[0]
        req = semantic_requirements_v10(case["query"])
        cert = certify_memory_v10(case["query"], competitor, req)
        if cert["supported"]:
            eligible_competitor_count += 1
        else:
            invalid.append({
                "case_id": case["id"],
                "reason": "competitor_not_candidate_v10_eligible",
                "clause_proofs": [
                    {
                        "supported": clause.supported,
                        "subject_ok": clause.subject_ok,
                        "relation_ok": clause.relation_ok,
                        "value_type_ok": clause.value_type_ok,
                        "value_bearing": clause.value_bearing,
                        "assertion_ok": clause.assertion_ok,
                        "temporal_ok": clause.temporal_ok,
                        "blocker": clause.blocker,
                    }
                    for clause in cert["clauses"]
                ],
            })
        v2_rank = pse_candidate_v2_rank(case, 1)
        if v2_rank and v2_rank[0] == str(competitor["id"]):
            v2_competitor_rank1_count += 1

    n = len(answerable)
    eligibility_rate = eligible_competitor_count / n if n else 0.0
    v2_rank1_rate = v2_competitor_rank1_count / n if n else 0.0
    pass_eligibility = eligible_competitor_count == n
    pass_priority_pressure = v2_rank1_rate >= args.minimum_v2_competitor_rank1_rate

    result = {
        "schema_version": "candidate-v11-rank-stressor-validity-v1",
        "benchmark": str(args.benchmark),
        "answerable_count": n,
        "eligible_competitor_count": eligible_competitor_count,
        "eligible_competitor_rate": eligibility_rate,
        "candidate_v2_competitor_rank1_count": v2_competitor_rank1_count,
        "candidate_v2_competitor_rank1_rate": v2_rank1_rate,
        "minimum_v2_competitor_rank1_rate": args.minimum_v2_competitor_rank1_rate,
        "eligibility_pass": pass_eligibility,
        "priority_pressure_pass": pass_priority_pressure,
        "invalid_examples": invalid[:20],
        "verdict": "PASS" if pass_eligibility and pass_priority_pressure else "FAIL",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))
    if result["verdict"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
