from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from personal_state_engine.candidate_v12 import parse_query_frame_v12, pse_candidate_v12_rank

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "experiments/benchmarks/candidate-v12-development-v1.json"
OUT = ROOT / "results/candidate-v12/development-failure-taxonomy-v1.json"


def _bucket_memory_id(memory_id: str) -> str:
    for suffix in ("gold", "uncertain", "wrong-subject", "wrong-relation", "novalue", "agenda"):
        if memory_id.endswith(suffix):
            return suffix
    return "other"


def main() -> None:
    payload = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    relation_confusion: dict[str, Counter[str]] = defaultdict(Counter)
    relation_mismatch_by_grammar: Counter[str] = Counter()
    relation_mismatch_by_discourse: Counter[str] = Counter()
    false_retrieval_by_relation: Counter[str] = Counter()
    false_retrieval_by_grammar: Counter[str] = Counter()
    false_retrieval_by_discourse: Counter[str] = Counter()
    false_retrieval_memory_bucket: Counter[str] = Counter()
    false_retrieval_answerability: Counter[str] = Counter()
    parse_invalid_by_relation: Counter[str] = Counter()

    relation_mismatch_count = 0
    false_retrieval_case_count = 0

    for case in payload["cases"]:
        meta = case["generator_metadata"]
        gold = meta["gold_frame"]
        gold_relation = gold["relation_frame"]
        grammar = meta["grammar_family"]
        discourse = meta["discourse_family"]
        frame = parse_query_frame_v12(case["query"], case["memories"])
        predicted = "+".join(frame.relation_frame) if frame.relation_frame else "<NONE>"
        relation_confusion[gold_relation][predicted] += 1
        if not frame.parse_valid:
            parse_invalid_by_relation[gold_relation] += 1
        if frame.relation_frame != (gold_relation,):
            relation_mismatch_count += 1
            relation_mismatch_by_grammar[grammar] += 1
            relation_mismatch_by_discourse[discourse] += 1

        ranked = pse_candidate_v12_rank(case, 5)
        relevant = set(case["relevant_memory_ids"])
        nonrelevant = [mid for mid in ranked if mid not in relevant]
        if nonrelevant:
            false_retrieval_case_count += 1
            false_retrieval_by_relation[gold_relation] += 1
            false_retrieval_by_grammar[grammar] += 1
            false_retrieval_by_discourse[discourse] += 1
            false_retrieval_answerability["answerable" if relevant else "no-evidence"] += 1
            false_retrieval_memory_bucket.update(_bucket_memory_id(mid) for mid in nonrelevant)

    result = {
        "schema_version": "candidate-v12-development-failure-taxonomy-v1",
        "designation": "DEVELOPMENT",
        "formal_execution": False,
        "case_count": payload["case_count"],
        "relation_mismatch_count": relation_mismatch_count,
        "relation_confusion": {k: dict(v) for k, v in sorted(relation_confusion.items())},
        "relation_mismatch_by_grammar": dict(relation_mismatch_by_grammar),
        "relation_mismatch_by_discourse": dict(relation_mismatch_by_discourse),
        "parse_invalid_by_relation": dict(parse_invalid_by_relation),
        "false_retrieval_case_count": false_retrieval_case_count,
        "false_retrieval_by_relation": dict(false_retrieval_by_relation),
        "false_retrieval_by_grammar": dict(false_retrieval_by_grammar),
        "false_retrieval_by_discourse": dict(false_retrieval_by_discourse),
        "false_retrieval_answerability": dict(false_retrieval_answerability),
        "false_retrieval_memory_bucket": dict(false_retrieval_memory_bucket),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
