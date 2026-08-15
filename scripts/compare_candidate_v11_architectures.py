from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v10 import pse_candidate_v10_rank, semantic_requirements_v10
from personal_state_engine.candidate_v11 import evidence_priority_proof_v11, pse_candidate_v11_rank

Ranker = Callable[[dict[str, Any], int], list[str]]


def _eligible_proofs(case: dict[str, Any]):
    full_v2 = pse_candidate_v2_rank(case, max(5, len(case["memories"])))
    by_id = {str(memory["id"]): memory for memory in case["memories"]}
    req = semantic_requirements_v10(case["query"])
    rows = []
    for rank, memory_id in enumerate(full_v2, start=1):
        memory = by_id[memory_id]
        proof = evidence_priority_proof_v11(case["query"], memory, rank, req)
        if proof is not None:
            rows.append(proof)
    return rows


def architecture_b_weighted_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Structured weighted quality score after the same hard eligibility layer."""
    proofs = _eligible_proofs(case)

    # Explicit fixed weights for development comparison only. The point of this
    # architecture is to demonstrate the compensatory-score alternative, not to
    # tune the production candidate. All features are runtime semantic proofs.
    def score(p):
        object_quality = (
            p.object_slot_matches / p.object_slot_total if p.object_slot_total else 0.0
        )
        return (
            3.0 * p.subject_binding_quality
            + 2.5 * p.relation_specificity
            + 2.0 * object_quality
            + 2.0 * p.assertion_directness
            + 1.0 * p.temporal_specificity
            + 0.5 * p.semantic_completeness
            - 1.0 * p.ambiguity_penalty
            - 0.0001 * p.candidate_v2_original_rank
        )

    proofs.sort(key=score, reverse=True)
    return [p.memory_id for p in proofs[:k]]


def _dominates(a, b) -> bool:
    a_obj = a.object_slot_matches / a.object_slot_total if a.object_slot_total else 0.0
    b_obj = b.object_slot_matches / b.object_slot_total if b.object_slot_total else 0.0
    av = (
        a.subject_binding_quality,
        a.relation_specificity,
        a_obj,
        a.assertion_directness,
        a.temporal_specificity,
        a.semantic_completeness,
        -a.ambiguity_penalty,
    )
    bv = (
        b.subject_binding_quality,
        b.relation_specificity,
        b_obj,
        b.assertion_directness,
        b.temporal_specificity,
        b.semantic_completeness,
        -b.ambiguity_penalty,
    )
    return all(x >= y for x, y in zip(av, bv)) and any(x > y for x, y in zip(av, bv))


def architecture_d_dominance_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    """Conservative Pareto/dominance ordering; v2 order resolves incomparability."""
    proofs = _eligible_proofs(case)
    remaining = list(proofs)
    output = []
    while remaining:
        nondominated = [
            candidate
            for candidate in remaining
            if not any(_dominates(other, candidate) for other in remaining if other is not candidate)
        ]
        nondominated.sort(key=lambda p: p.candidate_v2_original_rank)
        output.extend(nondominated)
        ids = {id(p) for p in nondominated}
        remaining = [p for p in remaining if id(p) not in ids]
    return [p.memory_id for p in output[:k]]


def metrics(cases: list[dict[str, Any]], ranker: Ranker) -> dict[str, Any]:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    negatives = [c for c in cases if not c["relevant_memory_ids"]]
    rr = []
    hits = {1: 0, 3: 0, 5: 0}
    recall = 0
    false_retrieval = 0
    for case in answerable:
        ranking = ranker(case, 5)
        relevant = set(case["relevant_memory_ids"])
        positions = [i + 1 for i, mid in enumerate(ranking) if mid in relevant]
        rr.append(1.0 / positions[0] if positions else 0.0)
        recall += int(bool(positions))
        for cutoff in hits:
            hits[cutoff] += int(bool(relevant & set(ranking[:cutoff])))
    for case in negatives:
        false_retrieval += int(bool(ranker(case, 5)))
    return {
        "MRR": sum(rr) / len(answerable),
        "R@1": hits[1] / len(answerable),
        "R@3": hits[3] / len(answerable),
        "R@5": hits[5] / len(answerable),
        "answerable_recall": recall / len(answerable),
        "false_retrieval": false_retrieval / len(negatives),
        "abstention_accuracy": 1.0 - false_retrieval / len(negatives),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.benchmark.read_text())
    cases = payload["cases"]

    architectures = {
        "A_binary_certification_plus_candidate_v2_order": pse_candidate_v10_rank,
        "B_structured_weighted_quality_ranking": architecture_b_weighted_rank,
        "C_lexicographic_semantic_proof_ordering": pse_candidate_v11_rank,
        "D_pareto_dominance_plus_candidate_v2_tiebreak": architecture_d_dominance_rank,
    }
    results = {name: metrics(cases, ranker) for name, ranker in architectures.items()}

    result = {
        "schema_version": "candidate-v11-architecture-comparison-v1",
        "surface": payload["name"],
        "development_only": True,
        "architectures": results,
        "interpretation": {
            "A": "Frozen Candidate-v10 concept; establishes the no-second-stage baseline.",
            "B": "Shows whether a compensatory weighted proof score can recover rank-1 while preserving the same Layer-1 safety surface.",
            "C": "Selected Candidate-v11 architecture; fixed lexicographic semantic proof ordering with Candidate-v2 rank last.",
            "D": "Conservative non-compensatory dominance alternative; incomparable candidates fall back to Candidate-v2 order.",
        },
        "selection_rule": (
            "Prefer C when it meets all safety/ranking requirements and is at least as effective as B/D, "
            "because it is deterministic, non-compensatory, explainable, and has a smaller tuning surface."
        ),
        "monetary_cost_usd": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
