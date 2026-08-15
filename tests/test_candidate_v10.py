from __future__ import annotations

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v10 import (
    evidence_support_signature_v10,
    pse_candidate_v10_rank,
    semantic_requirements_v10,
)


def case(query: str, texts: list[str], relevant: list[str] | None = None, **extra):
    memories = [
        {"id": f"m{i}", "text": text, "timestamp": "2027-03-20T08:30:00+00:00"}
        for i, text in enumerate(texts)
    ]
    return {"query": query, "memories": memories, "relevant_memory_ids": relevant or [], **extra}


def test_nominalized_preference_relation_generalizes_without_answer_lexicon():
    c = case(
        "Which morning meal is Rina Bell's usual choice?",
        ["Rina Bell's regular breakfast is spiced millet."],
        ["m0"],
    )
    sig = evidence_support_signature_v10(c)
    assert sig["requirements"]["relations"] == ["preference"]
    assert sig["supporting_memory_ids"] == ["m0"]


def test_open_class_status_is_licensed_by_same_possessed_object_slot():
    c = case(
        "What is Mina Roe's current permit status?",
        ["Mina Roe's permit is awaiting external review."],
        ["m0"],
    )
    req = semantic_requirements_v10(c["query"])
    assert "permit" in req.object_terms
    sig = evidence_support_signature_v10(c)
    assert sig["supporting_memory_ids"] == ["m0"]
    assert any("object-slot:permit" in clause.proof for clause in sig["certifications"][0]["clauses"])


def test_open_class_color_is_licensed_by_same_object_slot():
    c = case(
        "What color is Noa Kim's backpack?",
        ["Noa Kim's backpack is storm-cloud gray."],
        ["m0"],
    )
    assert pse_candidate_v10_rank(c, 5) == ["m0"]


def test_wrong_relation_same_subject_is_rejected():
    c = case(
        "What is Tariq Moss's professional role?",
        ["Tariq Moss's home location is Sendai."],
        [],
    )
    assert pse_candidate_v10_rank(c, 5) == []


def test_wrong_subject_same_relation_is_rejected():
    c = case(
        "What is Tariq Moss's professional role?",
        ["Lea Moss's work role is field ecologist."],
        [],
    )
    assert pse_candidate_v10_rank(c, 5) == []


def test_uncertain_same_relation_is_rejected_by_hard_blocker():
    c = case(
        "What is Tariq Moss's professional role?",
        ["Tariq Moss's work role is perhaps field ecologist."],
        [],
    )
    assert pse_candidate_v10_rank(c, 5) == []


def test_stale_same_relation_is_rejected_for_current_query():
    c = case(
        "What is Tariq Moss's current professional role?",
        ["Previously, Tariq Moss's work role was field ecologist."],
        [],
    )
    assert pse_candidate_v10_rank(c, 5) == []


def test_no_value_statement_is_rejected():
    c = case(
        "What is Tariq Moss's professional role?",
        ["No verified value is available for Tariq Moss's work role."],
        [],
    )
    assert pse_candidate_v10_rank(c, 5) == []


def test_bounded_same_memory_pronoun_coreference():
    c = case(
        "What is Tariq Moss's professional role?",
        ["Tariq Moss updated the profile. Their work role is field ecologist."],
        ["m0"],
    )
    assert pse_candidate_v10_rank(c, 5) == ["m0"]


def test_new_domain_subscription_is_supported_with_open_value():
    c = case(
        "What is Elia North's software subscription?",
        ["Elia North's service plan is Research Ultra."],
        ["m0"],
    )
    assert pse_candidate_v10_rank(c, 5) == ["m0"]


def test_new_domain_dietary_restriction_is_supported():
    c = case(
        "What is Elia North's dietary restriction?",
        ["Elia North's food restriction is no tree nuts."],
        ["m0"],
    )
    assert pse_candidate_v10_rank(c, 5) == ["m0"]


def test_generator_metadata_and_labels_cannot_change_inference():
    base = case(
        "What is Elia North's software subscription?",
        ["Elia North's service plan is Research Ultra."],
        ["m0"],
    )
    poisoned = dict(base)
    poisoned.update({
        "id": "CASE-SHOULD-NOT-MATTER",
        "designation": "FINAL",
        "answer": "WRONG",
        "generator_metadata": {"semantic_domain": "wrong", "query_grammar_family": "Z"},
        "provenance": "hidden-answer=wrong",
    })
    assert pse_candidate_v10_rank(base, 5) == pse_candidate_v10_rank(poisoned, 5)


def test_output_is_order_preserving_subsequence_of_candidate_v2():
    c = case(
        "What is Tariq Moss's professional role?",
        [
            "Tariq Moss's home location is Sendai.",
            "Tariq Moss's work role is field ecologist.",
            "Tariq Moss's professional role is conservation analyst.",
            "Another person's work role is curator.",
        ],
        ["m1", "m2"],
    )
    full = pse_candidate_v2_rank(c, max(5, len(c["memories"])))
    out = pse_candidate_v10_rank(c, 5)
    assert out == [mid for mid in full if mid in set(out)][: len(out)]


def test_hypothetical_future_intent_does_not_become_current_fact():
    c = case(
        "What is Tariq Moss's current professional role?",
        ["Tariq Moss plans to work as a field ecologist next year."],
        [],
    )
    assert pse_candidate_v10_rank(c, 5) == []
