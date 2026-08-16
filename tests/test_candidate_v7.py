from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v7 import evidence_support_signature, pse_candidate_v7_rank

ROOT = Path(__file__).resolve().parents[1]
DEV = json.loads((ROOT / "experiments" / "benchmarks" / "candidate-v7-development-v1.json").read_text())
CASES = DEV["cases"]
ANSWERABLE = [case for case in CASES if case["relevant_memory_ids"]]
NO_EVIDENCE = [case for case in CASES if not case["relevant_memory_ids"]]


@pytest.mark.parametrize("case", ANSWERABLE, ids=lambda c: c["id"])
def test_answerable_cases_preserve_candidate_v2_ranking(case):
    assert pse_candidate_v7_rank(case, 5) == pse_candidate_v2_rank(case, 5)
    assert evidence_support_signature(case)["verdict"] == "SUPPORTED"


@pytest.mark.parametrize("case", NO_EVIDENCE, ids=lambda c: c["id"])
def test_no_evidence_cases_abstain(case):
    assert pse_candidate_v7_rank(case, 5) == []
    assert evidence_support_signature(case)["verdict"] == "INSUFFICIENT"


@pytest.mark.parametrize("category", [
    "natural_first_person_fact", "preference", "multi_clause_fact", "implicit_predicate",
    "free_conversational_statement", "temporal_update", "correction", "supersession",
    "multi_session_evidence", "assistant_provided_fact", "user_provided_fact",
    "indirect_but_explicit_fact", "lexical_paraphrase", "low_overlap_evidence",
    "noisy_surrounding_dialogue", "multiple_relevant_evidence_turns", "location",
    "work_role", "possession", "activity_hobby",
])
def test_required_answerable_categories_have_coverage(category):
    matched = [case for case in ANSWERABLE if case["category"] == category]
    assert matched
    assert all(pse_candidate_v7_rank(case, 5) for case in matched)


@pytest.mark.parametrize("category", [
    "wrong_subject", "wrong_relation", "stale_only", "meta_discussion", "agenda",
    "question_repetition", "review_topic", "explicit_no_value", "unresolved",
    "contradiction", "near_duplicate_distractor", "query_copy_distractor",
])
def test_required_negative_categories_reject(category):
    matched = [case for case in NO_EVIDENCE if case["category"] == category]
    assert matched
    assert all(pse_candidate_v7_rank(case, 5) == [] for case in matched)


def test_determinism():
    case = copy.deepcopy(ANSWERABLE[0])
    outputs = [pse_candidate_v7_rank(case, 5) for _ in range(20)]
    assert all(output == outputs[0] for output in outputs)


def test_ground_truth_fields_do_not_change_inference():
    case = copy.deepcopy(ANSWERABLE[1])
    baseline = pse_candidate_v7_rank(case, 5)
    case["has_answer"] = False
    case["answer"] = "FORBIDDEN_SENTINEL"
    case["answer_session_ids"] = ["FORBIDDEN_SENTINEL"]
    case["question_type"] = "FORBIDDEN_SENTINEL"
    case["relevant_memory_ids"] = []
    assert pse_candidate_v7_rank(case, 5) == baseline


def test_case_id_and_abs_suffix_do_not_change_inference():
    case = copy.deepcopy(ANSWERABLE[2])
    baseline = pse_candidate_v7_rank(case, 5)
    case["id"] = "totally-different_abs"
    case["question_id"] = "forbidden_abs"
    assert pse_candidate_v7_rank(case, 5) == baseline


def test_memory_ground_truth_labels_are_ignored():
    case = copy.deepcopy(ANSWERABLE[3])
    baseline = pse_candidate_v7_rank(case, 5)
    for memory in case["memories"]:
        memory["has_answer"] = not memory["id"].endswith("rel")
        memory["answer"] = "FORBIDDEN_SENTINEL"
    assert pse_candidate_v7_rank(case, 5) == baseline


def test_empty_memories_fail_closed():
    case = {"query": "What is Maya's favorite drink?", "memories": []}
    assert pse_candidate_v7_rank(case, 5) == []


def test_question_only_fails_closed():
    case = {
        "query": "What is Maya's favorite drink?",
        "memories": [{"id": "m1", "text": "What is Maya's favorite drink?", "timestamp": None}],
    }
    assert pse_candidate_v7_rank(case, 5) == []


def test_explicit_no_value_fails_closed():
    case = {
        "query": "What is Maya's favorite drink?",
        "memories": [{"id": "m1", "text": "No confirmed value for Maya's favorite drink is available.", "timestamp": None}],
    }
    assert pse_candidate_v7_rank(case, 5) == []


def test_wrong_subject_fails_closed():
    case = {
        "query": "What is Maya's favorite drink?",
        "memories": [{"id": "m1", "text": "Nora loves jasmine tea.", "timestamp": None}],
    }
    assert pse_candidate_v7_rank(case, 5) == []


def test_wrong_relation_fails_closed():
    case = {
        "query": "Where does Maya currently live?",
        "memories": [{"id": "m1", "text": "Maya works as a designer.", "timestamp": None}],
    }
    assert pse_candidate_v7_rank(case, 5) == []


def test_stale_only_current_query_fails_closed():
    case = {
        "query": "Where does Maya currently live?",
        "memories": [{"id": "m1", "text": "Maya's old home was Lisbon before it was superseded.", "timestamp": "2026-01-01T00:00:00+00:00"}],
    }
    assert pse_candidate_v7_rank(case, 5) == []


def test_current_update_can_supersede_stale_language():
    case = {
        "query": "Where does Maya currently live?",
        "memories": [{"id": "m1", "text": "Maya used to live in Lisbon, but now lives in Kyoto.", "timestamp": "2026-08-10T00:00:00+00:00"}],
    }
    assert pse_candidate_v7_rank(case, 5) == ["m1"]


def test_correction_supported():
    case = {
        "query": "What is Maya's current project status?",
        "memories": [{"id": "m1", "text": "Correction: Maya's project status is now approved.", "timestamp": "2026-08-10T00:00:00+00:00"}],
    }
    assert pse_candidate_v7_rank(case, 5) == ["m1"]


def test_preference_paraphrase_supported():
    case = {
        "query": "What is Maya's favorite snack?",
        "memories": [{"id": "m1", "text": "Maya is obsessed with seaweed crackers and picks them every time.", "timestamp": None}],
    }
    assert pse_candidate_v7_rank(case, 5) == ["m1"]


def test_implicit_activity_supported():
    case = {
        "query": "What instrument does Maya practice?",
        "memories": [{"id": "m1", "text": "Every evening Maya practices the cello before dinner.", "timestamp": None}],
    }
    assert pse_candidate_v7_rank(case, 5) == ["m1"]


def test_first_person_fact_supported():
    case = {
        "query": "What drink do I usually order?",
        "memories": [{"id": "m1", "text": "I always get jasmine tea after class.", "timestamp": None}],
    }
    assert pse_candidate_v7_rank(case, 5) == ["m1"]


def test_meta_only_fails_closed():
    case = {
        "query": "What is Maya's favorite drink?",
        "memories": [{"id": "m1", "text": "We discussed the query about Maya's favorite drink.", "timestamp": None}],
    }
    assert pse_candidate_v7_rank(case, 5) == []


def test_unresolved_inference_fails_closed():
    case = {
        "query": "What is Maya's favorite drink?",
        "memories": [{"id": "m1", "text": "Maya probably likes tea, but this remains uncertain.", "timestamp": None}],
    }
    assert pse_candidate_v7_rank(case, 5) == []


def test_explicit_conflict_fails_closed():
    case = {
        "query": "What is Maya's favorite drink?",
        "memories": [{"id": "m1", "text": "Records conflict about Maya's favorite drink; the values cannot be reconciled.", "timestamp": None}],
    }
    assert pse_candidate_v7_rank(case, 5) == []
