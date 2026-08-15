from __future__ import annotations

"""Evaluate four preregistered Candidate-v12 architectures on Development only."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Callable

from personal_state_engine.candidate_v11 import pse_candidate_v11_rank
from personal_state_engine.candidate_v12 import (
    candidate_source_invariant_v12,
    parse_query_frame_v12,
    pse_candidate_v12_arch_b_rank,
    pse_candidate_v12_arch_d_rank,
    pse_candidate_v12_rank,
)

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "experiments/benchmarks/candidate-v12-development-v1.json"
ARCH_OUT = ROOT / "results/candidate-v12/architecture-comparison-development-v1.json"
SUMMARY_OUT = ROOT / "results/candidate-v12/development-summary-v1.json"

Ranker = Callable[[dict, int], list[str]]

THRESHOLDS = {
    "mrr": 0.98,
    "r_at_1": 0.97,
    "r_at_3": 0.99,
    "r_at_5": 0.995,
    "answerable_recall": 0.99,
    "false_abstention_rate_max": 0.01,
    "false_retrieval_rate_max": 0.03,
    "abstention_accuracy": 0.97,
    "eligible_rank1_accuracy": 0.97,
    "subject_mandatory_anchor_precision": 0.99,
    "subject_mandatory_anchor_recall": 0.99,
    "relation_frame_accuracy": 0.98,
    "temporal_scope_accuracy": 0.98,
    "discourse_token_contamination_rate_max": 0.01,
}


def _metrics(cases: list[dict], ranker: Ranker) -> dict:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    no_evidence = [c for c in cases if not c["relevant_memory_ids"]]

    reciprocal = []
    hits1 = hits3 = hits5 = 0
    false_abstentions = 0
    false_retrieval_cases = 0
    eligible_answerable = 0
    eligible_rank1_correct = 0
    no_evidence_abstain = 0
    total_returned = 0
    total_nonrelevant_returned = 0

    for case in answerable:
        ranked = ranker(case, 5)
        relevant = set(case["relevant_memory_ids"])
        total_returned += len(ranked)
        nonrel = [x for x in ranked if x not in relevant]
        total_nonrelevant_returned += len(nonrel)
        false_retrieval_cases += int(bool(nonrel))
        if ranked:
            eligible_answerable += 1
            eligible_rank1_correct += int(ranked[0] in relevant)
        else:
            false_abstentions += 1

        hit_rank = next((i for i, mid in enumerate(ranked, start=1) if mid in relevant), None)
        reciprocal.append(1.0 / hit_rank if hit_rank else 0.0)
        hits1 += int(hit_rank == 1)
        hits3 += int(hit_rank is not None and hit_rank <= 3)
        hits5 += int(hit_rank is not None and hit_rank <= 5)

    for case in no_evidence:
        ranked = ranker(case, 5)
        total_returned += len(ranked)
        total_nonrelevant_returned += len(ranked)
        if ranked:
            false_retrieval_cases += 1
        else:
            no_evidence_abstain += 1

    a = max(1, len(answerable))
    n = max(1, len(no_evidence))
    all_count = max(1, len(cases))
    return {
        "case_count": len(cases),
        "answerable_count": len(answerable),
        "no_evidence_count": len(no_evidence),
        "mrr": sum(reciprocal) / a,
        "r_at_1": hits1 / a,
        "r_at_3": hits3 / a,
        "r_at_5": hits5 / a,
        "answerable_recall": hits5 / a,
        "false_abstention_rate": false_abstentions / a,
        "false_retrieval_rate": false_retrieval_cases / all_count,
        "abstention_accuracy": no_evidence_abstain / n,
        "eligible_answerable_count": eligible_answerable,
        "eligible_rank1_accuracy": eligible_rank1_correct / max(1, eligible_answerable),
        "returned_evidence_count": total_returned,
        "nonrelevant_returned_evidence_count": total_nonrelevant_returned,
    }


def _frame_metrics(cases: list[dict]) -> dict:
    subject_exact = 0
    relation_exact = 0
    temporal_exact = 0
    anchor_tp = anchor_fp = anchor_fn = 0
    contamination_cases = 0
    parse_valid = 0
    discourse_counts: Counter[str] = Counter()

    for case in cases:
        frame = parse_query_frame_v12(case["query"], case["memories"])
        gold = case["generator_metadata"]["gold_frame"]
        parse_valid += int(frame.parse_valid)
        discourse_counts[frame.discourse_intent] += 1

        predicted_subject = frame.subject_entities[0] if len(frame.subject_entities) == 1 else None
        subject_exact += int(predicted_subject == gold["subject_entity"])

        predicted_relation = frame.relation_frame[0] if len(frame.relation_frame) == 1 else None
        relation_exact += int(predicted_relation == gold["relation_frame"])
        temporal_exact += int(frame.temporal_scope == gold["temporal_scope"])

        gold_tokens = {t.casefold().removesuffix("'s") for t in gold["subject_entity"].split()}
        pred_tokens = set()
        if predicted_subject:
            pred_tokens = {t.casefold().removesuffix("'s") for t in predicted_subject.split()}
        tp = len(gold_tokens & pred_tokens)
        fp = len(pred_tokens - gold_tokens)
        fn = len(gold_tokens - pred_tokens)
        anchor_tp += tp
        anchor_fp += fp
        anchor_fn += fn
        contamination_cases += int(bool(fp))

    count = max(1, len(cases))
    return {
        "frame_case_count": len(cases),
        "parse_valid_rate": parse_valid / count,
        "subject_exact_span_accuracy": subject_exact / count,
        "subject_mandatory_anchor_precision": anchor_tp / max(1, anchor_tp + anchor_fp),
        "subject_mandatory_anchor_recall": anchor_tp / max(1, anchor_tp + anchor_fn),
        "relation_frame_accuracy": relation_exact / count,
        "temporal_scope_accuracy": temporal_exact / count,
        "discourse_token_contamination_rate": contamination_cases / count,
        "discourse_intent_counts": dict(discourse_counts),
    }


def _integrity(cases: list[dict]) -> dict:
    source_violations = 0
    metadata_firewall_violations = 0
    determinism_violations = 0

    for case in cases:
        inv = candidate_source_invariant_v12(case, 5)
        source_violations += int(not inv["pass"])

        baseline = pse_candidate_v12_rank(case, 5)
        again = pse_candidate_v12_rank(case, 5)
        determinism_violations += int(baseline != again)

        mutated = deepcopy(case)
        mutated["relevant_memory_ids"] = list(reversed(case["relevant_memory_ids"])) + ["FORBIDDEN-GOLD-MUTATION"]
        mutated["designation"] = "FORBIDDEN-STAGE-MUTATION"
        mutated["generator_metadata"] = {
            "grammar_family": "FORBIDDEN",
            "discourse_family": "FORBIDDEN",
            "semantic_domain": "FORBIDDEN",
            "answer": "FORBIDDEN",
        }
        mutated["case_id"] = "FORBIDDEN"
        metadata_firewall_violations += int(pse_candidate_v12_rank(mutated, 5) != baseline)

    return {
        "candidate_source_violations": source_violations,
        "metadata_firewall_violations": metadata_firewall_violations,
        "determinism_violations": determinism_violations,
        "candidate_source_invariant": "PASS" if source_violations == 0 else "FAIL",
        "metadata_firewall": "PASS" if metadata_firewall_violations == 0 else "FAIL",
        "determinism": "PASS" if determinism_violations == 0 else "FAIL",
    }


def _accept(metrics: dict, frame: dict, integrity: dict) -> tuple[bool, list[str]]:
    failures = []
    minimums = {
        "mrr": THRESHOLDS["mrr"],
        "r_at_1": THRESHOLDS["r_at_1"],
        "r_at_3": THRESHOLDS["r_at_3"],
        "r_at_5": THRESHOLDS["r_at_5"],
        "answerable_recall": THRESHOLDS["answerable_recall"],
        "abstention_accuracy": THRESHOLDS["abstention_accuracy"],
        "eligible_rank1_accuracy": THRESHOLDS["eligible_rank1_accuracy"],
    }
    for key, threshold in minimums.items():
        if metrics[key] < threshold:
            failures.append(f"{key}<{threshold}")
    if metrics["false_abstention_rate"] > THRESHOLDS["false_abstention_rate_max"]:
        failures.append("false_abstention_rate>0.01")
    if metrics["false_retrieval_rate"] > THRESHOLDS["false_retrieval_rate_max"]:
        failures.append("false_retrieval_rate>0.03")

    frame_minimums = {
        "subject_mandatory_anchor_precision": THRESHOLDS["subject_mandatory_anchor_precision"],
        "subject_mandatory_anchor_recall": THRESHOLDS["subject_mandatory_anchor_recall"],
        "relation_frame_accuracy": THRESHOLDS["relation_frame_accuracy"],
        "temporal_scope_accuracy": THRESHOLDS["temporal_scope_accuracy"],
    }
    for key, threshold in frame_minimums.items():
        if frame[key] < threshold:
            failures.append(f"{key}<{threshold}")
    if frame["discourse_token_contamination_rate"] > THRESHOLDS["discourse_token_contamination_rate_max"]:
        failures.append("discourse_token_contamination_rate>0.01")

    for key in ("candidate_source_invariant", "metadata_firewall", "determinism"):
        if integrity[key] != "PASS":
            failures.append(f"{key}=FAIL")
    return not failures, failures


def main() -> None:
    payload = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    cases = payload["cases"]

    architectures: dict[str, Ranker] = {
        "A_frozen_candidate_v11": pse_candidate_v11_rank,
        "B_bounded_discourse_stripping": pse_candidate_v12_arch_b_rank,
        "C_structured_semantic_frame": pse_candidate_v12_rank,
        "D_clause_first_proposition_graph": pse_candidate_v12_arch_d_rank,
    }
    comparison = {
        name: _metrics(cases, ranker)
        for name, ranker in architectures.items()
    }
    frame = _frame_metrics(cases)
    integrity = _integrity(cases)
    accepted, failures = _accept(comparison["C_structured_semantic_frame"], frame, integrity)

    ARCH_OUT.parent.mkdir(parents=True, exist_ok=True)
    ARCH_OUT.write_text(
        json.dumps(
            {
                "schema_version": "candidate-v12-development-architecture-comparison-v1",
                "designation": "DEVELOPMENT",
                "formal_execution": False,
                "benchmark": str(BENCHMARK.relative_to(ROOT)),
                "architectures": comparison,
                "frame_extraction": frame,
                "integrity": integrity,
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    summary = {
        "schema_version": "candidate-v12-development-summary-v1",
        "designation": "DEVELOPMENT",
        "formal_execution": False,
        "candidate": "v12",
        "architecture_selected": "C_structured_semantic_frame" if accepted else None,
        "development_acceptance": "PASS" if accepted else "FAIL",
        "threshold_failures": failures,
        "thresholds": THRESHOLDS,
        "selected_metrics": comparison["C_structured_semantic_frame"],
        "frame_extraction": frame,
        "integrity": integrity,
        "historical_protected_used_for_development_evaluation": False,
        "protected_execution_count": 0,
        "confirmatory_execution_count": 0,
        "final_execution_count": 0,
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
