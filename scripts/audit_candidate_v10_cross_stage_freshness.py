from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import combinations
from pathlib import Path

import generate_candidate_v10_benchmark_v2 as gen_v2


def case_exact(case: dict) -> str:
    return json.dumps(
        {"q": case["query"], "m": sorted(m["text"] for m in case["memories"])},
        sort_keys=True,
    )


def case_normalized(case: dict) -> str:
    return json.dumps(
        {
            "q": gen_v2.normalize(case["query"]),
            "m": sorted(gen_v2.normalize(m["text"]) for m in case["memories"]),
        },
        sort_keys=True,
    )


def stage_view(path: Path) -> dict:
    payload = json.loads(path.read_text())
    cases = payload["cases"]
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    relevant_evidence = [
        next(m["text"] for m in c["memories"] if m["id"] in set(c["relevant_memory_ids"]))
        for c in answerable
    ]
    return {
        "path": str(path),
        "stage": payload["designation"].casefold(),
        "case_count": len(cases),
        "exact": {case_exact(c) for c in cases},
        "normalized": {case_normalized(c) for c in cases},
        "question_skeletons": {gen_v2.skeleton(c["query"]) for c in cases},
        "evidence_skeletons": {gen_v2.skeleton(x) for x in relevant_evidence},
        "families": {c["generator_metadata"]["query_grammar_family"] for c in cases},
        "template_provenance": {c["generator_metadata"]["template_provenance"] for c in cases},
        "domains": Counter(c["generator_metadata"]["semantic_domain"] for c in cases),
    }


def audit(paths: list[Path]) -> dict:
    views = [stage_view(p) for p in paths]
    pairs = []
    integrity = True
    for a, b in combinations(views, 2):
        exact = len(a["exact"] & b["exact"])
        normalized = len(a["normalized"] & b["normalized"])
        qsk = len(a["question_skeletons"] & b["question_skeletons"])
        esk = len(a["evidence_skeletons"] & b["evidence_skeletons"])
        fam = sorted(a["families"] & b["families"])
        prov = sorted(a["template_provenance"] & b["template_provenance"])
        pair_ok = exact == 0 and normalized == 0 and not fam and not prov
        integrity = integrity and pair_ok
        pairs.append({
            "stages": [a["stage"], b["stage"]],
            "exact_case_overlap": exact,
            "normalized_case_overlap": normalized,
            "question_skeleton_overlap": qsk,
            "evidence_skeleton_overlap": esk,
            "grammar_family_overlap": fam,
            "template_provenance_overlap": prov,
            "integrity_pass": pair_ok,
        })
    return {
        "schema_version": "candidate-v10-cross-stage-freshness-audit-v1",
        "stages": [
            {
                "stage": v["stage"],
                "path": v["path"],
                "case_count": v["case_count"],
                "families": sorted(v["families"]),
                "question_skeleton_unique": len(v["question_skeletons"]),
                "evidence_skeleton_unique": len(v["evidence_skeletons"]),
                "semantic_domain_distribution": dict(sorted(v["domains"].items())),
                "template_provenance": sorted(v["template_provenance"]),
            }
            for v in views
        ],
        "pairwise": pairs,
        "integrity_policy": {
            "exact_case_overlap_must_be_zero": True,
            "normalized_case_overlap_must_be_zero": True,
            "grammar_family_overlap_must_be_zero": True,
            "template_provenance_overlap_must_be_zero": True,
            "question_and_evidence_skeleton_overlap": "reported for stratified audit; not a post-hoc numeric gate",
        },
        "integrity_pass": integrity,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--benchmarks", type=Path, nargs="+", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = audit(args.benchmarks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not result["integrity_pass"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
