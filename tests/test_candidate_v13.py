from __future__ import annotations

from copy import deepcopy

from personal_state_engine.candidate_v13 import (
    candidate_source_invariant_v13,
    parse_query_frame_v13,
    pse_candidate_v13_rank,
)


def _answerable_case() -> dict:
    return {
        "query": "Which language is stated for Aren Aster V13TEST?",
        "memories": [
            {"id": "gold", "text": "Aren Aster V13TEST's language is Lingua-Test-G.", "timestamp": "2037-03-20T09:00:00+00:00"},
            {"id": "uncertain", "text": "Aren Aster V13TEST's language is perhaps Lingua-Test-U.", "timestamp": "2037-03-22T09:00:00+00:00"},
            {"id": "wrong", "text": "Belen Borel V13OTHER's language is Lingua-Test-W.", "timestamp": "2037-03-23T09:00:00+00:00"},
            {"id": "contradiction", "text": "Aren Aster V13TEST's language is not Lingua-Test-U.", "timestamp": "2037-03-24T09:00:00+00:00"},
        ],
        "relevant_memory_ids": ["gold"],
        "generator_metadata": {"grammar_family": "DO_NOT_READ"},
    }


def test_candidate_v13_selects_direct_supported_evidence() -> None:
    assert pse_candidate_v13_rank(_answerable_case(), 5) == ["gold"]


def test_candidate_v13_metadata_firewall() -> None:
    case = _answerable_case()
    baseline = pse_candidate_v13_rank(case, 5)
    mutated = deepcopy(case)
    mutated["relevant_memory_ids"] = ["contradiction"]
    mutated["designation"] = "FINAL"
    mutated["case_id"] = "LEAK"
    mutated["generator_metadata"] = {
        "grammar_family": "LEAK", "discourse_family": "LEAK",
        "structural_family": "LEAK", "answer": "LEAK",
    }
    assert pse_candidate_v13_rank(mutated, 5) == baseline


def test_candidate_v13_candidate_v2_source_invariant() -> None:
    assert candidate_source_invariant_v13(_answerable_case(), 5)["pass"]


def test_candidate_v13_frame_is_explicit_and_deterministic() -> None:
    case = _answerable_case()
    first = parse_query_frame_v13(case["query"], case["memories"])
    second = parse_query_frame_v13(case["query"], case["memories"])
    assert first == second
    assert first.target_subject == ("Aren Aster V13TEST",)
    assert first.target_relation == ("language",)
    assert first.requested_answer_type == "RELATION_VALUE"
    assert first.parse_valid


def test_candidate_v13_abstains_when_only_ineligible_evidence_exists() -> None:
    case = _answerable_case()
    case["memories"] = [
        {"id": "uncertain", "text": "Aren Aster V13TEST's language is perhaps Lingua-Test-U.", "timestamp": "2037-03-22T09:00:00+00:00"},
        {"id": "contradiction", "text": "Aren Aster V13TEST's language is not Lingua-Test-U.", "timestamp": "2037-03-24T09:00:00+00:00"},
    ]
    assert pse_candidate_v13_rank(case, 5) == []
