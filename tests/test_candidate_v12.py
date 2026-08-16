from __future__ import annotations

from copy import deepcopy

from personal_state_engine.candidate_v11 import pse_candidate_v11_rank
from personal_state_engine.candidate_v12 import (
    candidate_source_invariant_v12,
    parse_query_frame_v12,
    pse_candidate_v12_arch_b_rank,
    pse_candidate_v12_arch_d_rank,
    pse_candidate_v12_rank,
)


def _abstracted_case() -> dict:
    # Abstracted historical regression: wording, structure, entities, values,
    # identifiers and evidence text are intentionally distinct from historical
    # Candidate-v11 Protected examples.
    return {
        "id": "CV12-UNIT-ABSTRACT-001",
        "query": "Administrative context concerns Mira Solen. Which language is stated for her?",
        "memories": [
            {
                "id": "gold",
                "text": "Mira Solen speaks Icelandic.",
                "timestamp": "2031-01-04T10:00:00+00:00",
            },
            {
                "id": "uncertain",
                "text": "Mira Solen perhaps speaks Latvian.",
                "timestamp": "2031-01-05T10:00:00+00:00",
            },
            {
                "id": "wrong-subject",
                "text": "Tarin Solen speaks Latvian.",
                "timestamp": "2031-01-06T10:00:00+00:00",
            },
            {
                "id": "wrong-relation",
                "text": "Mira Solen's accommodation is Northbank House.",
                "timestamp": "2031-01-06T10:00:00+00:00",
            },
        ],
        "relevant_memory_ids": ["gold"],
        "designation": "DEVELOPMENT_ONLY_TEST_METADATA",
        "generator_metadata": {"hidden": "must-not-affect-inference"},
    }


def test_structured_frame_separates_discourse_from_subject() -> None:
    case = _abstracted_case()
    frame = parse_query_frame_v12(case["query"], case["memories"])
    assert frame.parse_valid
    assert frame.subject_entities == ("Mira Solen",)
    assert "Administrative" not in frame.subject_entities
    assert frame.relation_frame == ("language",)
    assert frame.discourse_intent == "CONTEXT_PLUS_PROPOSITION"


def test_abstracted_historical_regression_recovers_upstream_subject_failure() -> None:
    case = _abstracted_case()
    assert pse_candidate_v11_rank(case, 1) == []
    assert pse_candidate_v12_rank(case, 1) == ["gold"]


def test_architecture_b_and_d_are_independent_comparison_paths() -> None:
    case = _abstracted_case()
    assert pse_candidate_v12_arch_b_rank(case, 1) == ["gold"]
    assert pse_candidate_v12_arch_d_rank(case, 1) == ["gold"]


def test_ambiguous_subject_binding_fails_closed() -> None:
    case = {
        "query": "Avery Cole and Rowan Pike are in scope. Which language is stated?",
        "memories": [
            {"id": "a", "text": "Avery Cole speaks Danish.", "timestamp": None},
            {"id": "b", "text": "Rowan Pike speaks Swedish.", "timestamp": None},
        ],
    }
    frame = parse_query_frame_v12(case["query"], case["memories"])
    assert frame.subject_ambiguous
    assert not frame.parse_valid
    assert pse_candidate_v12_rank(case, 5) == []


def test_relation_lexeme_in_discourse_does_not_become_requested_relation() -> None:
    # Abstracted Development regression: a discourse clause contains lexemes
    # that are valid semantic relations in other contexts. The requested relation
    # is selected by bound-subject evidence support, not a token blacklist.
    case = {
        "query": "The status of this request is routine. Which work role is documented for Mira Solen?",
        "memories": [
            {"id": "gold", "text": "Mira Solen's work role is CartographyLead-X1.", "timestamp": None},
            {"id": "support", "text": "Mira Solen's work role is perhaps CartographyLead-X2.", "timestamp": None},
            {"id": "wrong-rel", "text": "Mira Solen's status is StateMarker-X3.", "timestamp": None},
            {"id": "wrong-subject", "text": "Tarin Solen's work role is StateMarker-X4.", "timestamp": None},
        ],
    }
    frame = parse_query_frame_v12(case["query"], case["memories"])
    assert set(frame.relation_candidates) >= {"status", "routine", "work_role"}
    assert frame.relation_frame == ("work_role",)
    assert not frame.relation_ambiguous
    assert pse_candidate_v12_rank(case, 5) == ["gold"]


def test_relation_support_tie_fails_closed() -> None:
    case = {
        "query": "The status and language fields for Mira Solen are both in scope.",
        "memories": [
            {"id": "status", "text": "Mira Solen's status is Marker-A.", "timestamp": None},
            {"id": "language", "text": "Mira Solen speaks Marker-B.", "timestamp": None},
        ],
    }
    frame = parse_query_frame_v12(case["query"], case["memories"])
    assert frame.relation_ambiguous
    assert not frame.parse_valid
    assert pse_candidate_v12_rank(case, 5) == []


def test_first_person_query_remains_supported_without_named_entity() -> None:
    case = {
        "query": "Which language do I speak?",
        "memories": [
            {"id": "self", "text": "I speak Korean.", "timestamp": None},
            {"id": "uncertain", "text": "I perhaps speak Polish.", "timestamp": None},
        ],
    }
    frame = parse_query_frame_v12(case["query"], case["memories"])
    assert frame.parse_valid
    assert "FIRST_PERSON_SELF" in frame.subject_coreference
    assert pse_candidate_v12_rank(case, 1) == ["self"]


def test_no_evidence_safety_is_not_replaced_by_permissive_fallback() -> None:
    case = {
        "query": "A briefing concerns Nela Corin. Which language is stated for her?",
        "memories": [
            {"id": "uncertain", "text": "Nela Corin perhaps speaks Polish.", "timestamp": None},
            {"id": "agenda", "text": "Agenda item: discuss Nela Corin's language later.", "timestamp": None},
            {"id": "wrong", "text": "Darin Corin speaks Polish.", "timestamp": None},
        ],
    }
    assert pse_candidate_v12_rank(case, 5) == []


def test_metadata_firewall_is_byte_stable_for_rank_output() -> None:
    case = _abstracted_case()
    baseline = pse_candidate_v12_rank(case, 5)
    mutated = deepcopy(case)
    mutated["relevant_memory_ids"] = ["wrong-subject"]
    mutated["designation"] = "FINAL"
    mutated["generator_metadata"] = {
        "semantic_domain": "secret",
        "grammar_family": "secret",
        "answer": "secret",
    }
    mutated["case_id"] = "LEAK-ME"
    assert pse_candidate_v12_rank(mutated, 5) == baseline


def test_candidate_v2_remains_exclusive_candidate_source() -> None:
    result = candidate_source_invariant_v12(_abstracted_case(), 5)
    assert result["pass"]
    assert result["no_injection"]
    assert result["only_eligible"]
    assert result["unique"]
