from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from personal_state_engine.candidate_v10 import evidence_support_signature_v10, pse_candidate_v10_rank

BENCH = ROOT / "experiments/benchmarks/candidate-v10-development-v1.json"
OUT = ROOT / "results/candidate-v10/development-failure-taxonomy-v1.json"


def main() -> None:
    payload = json.loads(BENCH.read_text())
    misses = []
    domains = Counter()
    families = Counter()
    relations = Counter()
    failure_flags = Counter()
    domain_family = Counter()

    for c in payload["cases"]:
        relevant = set(c["relevant_memory_ids"])
        if not relevant:
            continue
        ranking = pse_candidate_v10_rank(c, 5)
        if relevant & set(ranking):
            continue
        meta = c.get("generator_metadata", {})
        domain = meta.get("semantic_domain", "unknown")
        family = meta.get("query_grammar_family", "unknown")
        domains[domain] += 1
        families[family] += 1
        domain_family[f"{domain}::{family}"] += 1
        sig = evidence_support_signature_v10(c)
        for rel in sig["requirements"]["relations"]:
            relations[rel] += 1
        certs = {row["memory_id"]: row for row in sig["certifications"]}
        relevant_rows = []
        for rid in relevant:
            row = certs.get(rid)
            if not row:
                failure_flags["relevant_not_in_candidate_v2_full_ranking"] += 1
                continue
            clauses = row["clauses"]
            flags = {
                "subject": any(x.subject_ok for x in clauses),
                "relation": any(x.relation_ok for x in clauses),
                "value_type": any(x.value_type_ok for x in clauses),
                "value_bearing": any(x.value_bearing for x in clauses),
                "assertion": any(x.assertion_ok for x in clauses),
                "temporal": any(x.temporal_ok for x in clauses),
                "blocker_free": any(x.blocker is None for x in clauses),
            }
            for key, ok in flags.items():
                if not ok:
                    failure_flags[key] += 1
            relevant_rows.append({
                "memory_id": rid,
                "flags": flags,
                "clauses": [asdict(x) for x in clauses],
            })
        misses.append({
            "case_id": c["id"],
            "semantic_domain": domain,
            "grammar_family": family,
            "query": c["query"],
            "relevant_texts": [m["text"] for m in c["memories"] if m["id"] in relevant],
            "requirements": sig["requirements"],
            "candidate_v10_rank": ranking,
            "relevant_certifications": relevant_rows,
        })

    result = {
        "schema_version": "candidate-v10-development-failure-taxonomy-v1",
        "stage": "development",
        "formal_stage": False,
        "miss_count": len(misses),
        "by_semantic_domain": dict(sorted(domains.items())),
        "by_grammar_family": dict(sorted(families.items())),
        "by_relation": dict(sorted(relations.items())),
        "failed_constraint_counts": dict(sorted(failure_flags.items())),
        "by_domain_family": dict(sorted(domain_family.items())),
        "misses": misses,
        "monetary_cost_usd": 0,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ["miss_count", "by_semantic_domain", "by_grammar_family", "by_relation", "failed_constraint_counts", "by_domain_family"]}, indent=2))


if __name__ == "__main__":
    main()
