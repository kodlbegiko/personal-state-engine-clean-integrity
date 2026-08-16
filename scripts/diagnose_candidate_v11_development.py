from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from personal_state_engine.candidate_v10 import pse_candidate_v10_rank
from personal_state_engine.candidate_v11 import evidence_support_signature_v11, pse_candidate_v11_rank


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark", type=Path)
    parser.add_argument("evaluation", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--iteration", type=int, required=True)
    args = parser.parse_args()

    payload = json.loads(args.benchmark.read_text())
    evaluation = json.loads(args.evaluation.read_text())
    failures: list[dict[str, Any]] = []
    categories: Counter[str] = Counter()
    families: Counter[str] = Counter()
    domains: Counter[str] = Counter()

    for case in payload["cases"]:
        relevant = set(case["relevant_memory_ids"])
        v11 = pse_candidate_v11_rank(case, 5)
        if relevant:
            if relevant & set(v11[:1]):
                continue
            if not v11:
                category = "false_abstention"
            elif relevant & set(v11):
                category = "rank1_preference_failure"
            else:
                category = "eligible_recall_failure"
        else:
            if not v11:
                continue
            category = "false_retrieval"

        signature = evidence_support_signature_v11(case)
        metadata = case.get("generator_metadata", {})
        row = {
            "case_id": case["id"],
            "category": category,
            "grammar_family": metadata.get("query_grammar_family"),
            "semantic_domain": metadata.get("semantic_domain"),
            "relevant_memory_ids": list(case["relevant_memory_ids"]),
            "candidate_v10_ranking": pse_candidate_v10_rank(case, 5),
            "candidate_v11_ranking": v11,
            "v11_proofs": signature["proofs"],
        }
        failures.append(row)
        categories.update([category])
        families.update([str(row["grammar_family"])])
        domains.update([str(row["semantic_domain"])])

    result = {
        "schema_version": "candidate-v11-development-failure-taxonomy-v1",
        "iteration": args.iteration,
        "benchmark": str(args.benchmark),
        "evaluation_verdict": evaluation["verdict"],
        "candidate_v11_metrics": evaluation["candidate_v11"],
        "failure_count": len(failures),
        "category_counts": dict(categories.most_common()),
        "grammar_family_counts": dict(families.most_common()),
        "semantic_domain_counts": dict(domains.most_common()),
        "failures": failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "iteration": args.iteration,
        "failure_count": len(failures),
        "category_counts": result["category_counts"],
        "grammar_family_counts": result["grammar_family_counts"],
    }, indent=2))


if __name__ == "__main__":
    main()
