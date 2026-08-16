from __future__ import annotations

from copy import deepcopy

from personal_state_engine.candidate_v10 import certify_memory_v10, semantic_requirements_v10
from personal_state_engine.candidate_v11 import (
    candidate_source_invariant_v11,
    evidence_priority_proof_v11,
    pse_candidate_v11_rank,
)


def memory(mid: str, text: str, day: int = 2) -> dict:
    return {
        "id": mid,
        "text": text,
        "timestamp": f"2028-04-{day:02d}T09:00:00+00:00",
    }


def case(query: str, memories: list[dict], **metadata) -> dict:
    payload = {"query": query, "memories": memories}
    payload.update(metadata)
    return payload


# ---------------------------------------------------------------------------
# Eligibility / safety: Candidate-v11 must not weaken Candidate-v10 blockers.
# ---------------------------------------------------------------------------


def test_eligibility_correct_subject_relation_value_is_eligible():
    q = "What is Rowan Hale's work role?"
    m = memory("ok", "Rowan Hale's work role is systems analyst.")
    req = semantic_requirements_v10(q)
    assert certify_memory_v10(q, m, req)["supported"] is True
    assert pse_candidate_v11_rank(case(q, [m]), 5) == ["ok"]


def test_eligibility_wrong_subject_rejected():
    q = "What is Rowan Hale's work role?"
    wrong = memory("wrong", "Mira Quinn's work role is systems analyst.")
    assert pse_candidate_v11_rank(case(q, [wrong]), 5) == []


def test_eligibility_wrong_relation_rejected():
    q = "What is Rowan Hale's work role?"
    wrong = memory("wrong", "Rowan Hale's accommodation is Cedar House Hotel.")
    assert pse_candidate_v11_rank(case(q, [wrong]), 5) == []


def test_eligibility_uncertainty_rejected():
    q = "What is Rowan Hale's work role?"
    uncertain = memory("u", "Rowan Hale's work role is perhaps systems analyst.")
    assert pse_candidate_v11_rank(case(q, [uncertain]), 5) == []


def test_eligibility_hypothetical_rejected():
    q = "What is Rowan Hale's work role?"
    hypothetical = memory("h", "Rowan Hale plans to work as systems analyst.")
    assert pse_candidate_v11_rank(case(q, [hypothetical]), 5) == []


def test_eligibility_no_value_rejected():
    q = "What is Rowan Hale's work role?"
    no_value = memory("n", "No verified value is available for Rowan Hale's work role.")
    assert pse_candidate_v11_rank(case(q, [no_value]), 5) == []


def test_eligibility_stale_for_explicit_current_query_rejected_when_v10_blocks_it():
    q = "What is Rowan Hale's current work role?"
    stale = memory("s", "Rowan Hale previously worked as systems analyst.")
    assert pse_candidate_v11_rank(case(q, [stale]), 5) == []


# ---------------------------------------------------------------------------
# Rank-1 discrimination. All examples are synthetic and not historical copies.
# ---------------------------------------------------------------------------


def test_rank1_case_a_exact_relation_direct_value_beats_broad_assignment():
    q = "What is Nolan Mercer's work role?"
    broad = memory(
        "broad",
        "Earlier profile entry — Nolan Mercer's work role: support technician.",
        4,
    )
    exact = memory("exact", "Nolan Mercer works as a systems analyst.", 2)
    ranking = pse_candidate_v11_rank(case(q, [broad, exact]), 5)
    assert ranking[0] == "exact"


def test_rank1_case_b_semantic_proof_beats_lexical_stuffing():
    q = "What is Priya Lennox's software tool?"
    lexical = memory(
        "lexical",
        "Old profile note about Priya Lennox's software tool, software tool: SlatePad.",
        4,
    )
    semantic = memory("semantic", "Priya Lennox's software tool is ForgeEdit.", 2)
    ranking = pse_candidate_v11_rank(case(q, [lexical, semantic]), 5)
    assert ranking[0] == "semantic"


def test_rank1_case_c_direct_predicate_value_beats_narrative_assignment():
    q = "What is Omar Bell's accommodation?"
    narrative = memory(
        "narrative",
        "Profile note about Omar Bell's accommodation: East Quay Hostel.",
        4,
    )
    direct = memory("direct", "Omar Bell's accommodation is North Garden Hotel.", 2)
    ranking = pse_candidate_v11_rank(case(q, [narrative, direct]), 5)
    assert ranking[0] == "direct"


def test_rank1_case_d_current_specificity_beats_temporally_vague_when_both_eligible():
    q = "Which work role is current for Leila Moss?"
    vague = memory("vague", "Leila Moss's work role is data technician.", 4)
    current = memory("current", "Leila Moss currently works as a research analyst.", 2)
    ranking = pse_candidate_v11_rank(case(q, [vague, current]), 5)
    assert ranking[0] == "current"


def test_rank1_case_e_object_compatible_evidence_beats_relation_only_evidence():
    q = "What is Hector Vale's passport status?"
    relation_only = memory("relation", "Hector Vale's status is approved.", 4)
    object_specific = memory("object", "Hector Vale's passport status is approved.", 2)
    ranking = pse_candidate_v11_rank(case(q, [relation_only, object_specific]), 5)
    assert ranking[0] == "object"


# ---------------------------------------------------------------------------
# Abstracted historical regression: failure classes, never historical payloads.
# ---------------------------------------------------------------------------


def test_abstracted_historical_regression_directness_class():
    q = "What is Keira Dalton's dietary restriction?"
    older_assignment = memory(
        "older",
        "Earlier profile snapshot — Keira Dalton's dietary restriction: sesame-free.",
        4,
    )
    direct_record = memory(
        "direct",
        "Keira Dalton's dietary restriction is nut-free.",
        2,
    )
    assert pse_candidate_v11_rank(case(q, [older_assignment, direct_record]), 5)[0] == "direct"


def test_abstracted_historical_regression_relation_specificity_class():
    q = "What is Theo Marin's appointment?"
    broad = memory("broad", "Profile note about Theo Marin's appointment: clinic visit.", 4)
    direct = memory("direct", "Theo Marin's appointment is dental checkup.", 2)
    assert pse_candidate_v11_rank(case(q, [broad, direct]), 5)[0] == "direct"


def test_abstracted_historical_regression_temporal_competition_class():
    q = "What is Amara Frost's subscription?"
    old = memory("old", "Last year, Amara Frost's subscription: Standard tier.", 4)
    direct = memory("direct", "Amara Frost's subscription is Research tier.", 2)
    assert pse_candidate_v11_rank(case(q, [old, direct]), 5)[0] == "direct"


# ---------------------------------------------------------------------------
# Safety adversarial competition.
# ---------------------------------------------------------------------------


def test_strong_lexical_distractor_cannot_rescue_blocked_uncertainty():
    q = "What is Mina Cole's sports team?"
    blocked = memory(
        "blocked",
        "Mina Cole's sports team sports team is perhaps Harbor Falcons.",
        5,
    )
    direct = memory("direct", "Mina Cole's sports team is Valley Comets.", 2)
    ranking = pse_candidate_v11_rank(case(q, [blocked, direct]), 5)
    assert ranking == ["direct"]


def test_same_subject_wrong_predicate_cannot_outrank():
    q = "What is Mina Cole's sports team?"
    wrong = memory("wrong", "Mina Cole's accommodation is Valley Comets Hotel.", 5)
    direct = memory("direct", "Mina Cole's sports team is Harbor Falcons.", 2)
    assert pse_candidate_v11_rank(case(q, [wrong, direct]), 5) == ["direct"]


def test_same_predicate_wrong_subject_cannot_outrank():
    q = "What is Mina Cole's sports team?"
    wrong = memory("wrong", "Ravi Cole's sports team is Harbor Falcons.", 5)
    direct = memory("direct", "Mina Cole's sports team is Valley Comets.", 2)
    assert pse_candidate_v11_rank(case(q, [wrong, direct]), 5) == ["direct"]


def test_direct_looking_hypothetical_cannot_be_promoted():
    q = "What is Tessa Ward's travel plan?"
    hypothetical = memory("hyp", "Tessa Ward plans to travel to Northport.", 5)
    direct = memory("direct", "Tessa Ward's travel plan is Southbay.", 2)
    assert pse_candidate_v11_rank(case(q, [hypothetical, direct]), 5) == ["direct"]


def test_multiple_entities_require_correct_subject_binding():
    q = "What is Ezra Pike's language?"
    mixed = memory("mixed", "Ezra Pike met Lina Pike; Lina Pike speaks Icelandic.", 5)
    direct = memory("direct", "Ezra Pike speaks Finnish.", 2)
    ranking = pse_candidate_v11_rank(case(q, [mixed, direct]), 5)
    assert ranking[0] == "direct"


# ---------------------------------------------------------------------------
# Metadata firewall and deterministic behavior.
# ---------------------------------------------------------------------------


def test_metadata_firewall_all_forbidden_metadata_changes_do_not_change_output():
    q = "What is Yuna Park's work role?"
    memories = [
        memory("m1", "Earlier profile entry — Yuna Park's work role: support engineer.", 4),
        memory("m2", "Yuna Park works as a systems engineer.", 2),
    ]
    baseline = case(
        q,
        deepcopy(memories),
        id="CASE-ORIGINAL",
        relevant_memory_ids=["m1"],
        answer="support engineer",
        labels={"gold": "m1"},
        designation="development",
        generator_metadata={
            "query_grammar_family": "SECRET-A",
            "semantic_domain": "secret-domain",
            "template_provenance": "secret-template",
            "stage": "development",
        },
    )
    mutated = deepcopy(baseline)
    mutated["id"] = "CASE-MUTATED"
    mutated["relevant_memory_ids"] = ["m2"]
    mutated["answer"] = "systems engineer"
    mutated["labels"] = {"gold": "m2", "hidden": True}
    mutated["designation"] = "FINAL"
    mutated["generator_metadata"] = {
        "query_grammar_family": "SECRET-Z",
        "semantic_domain": "other-domain",
        "template_provenance": "other-template",
        "stage": "final",
        "relevant_ids": ["m1"],
    }
    assert pse_candidate_v11_rank(baseline, 5) == pse_candidate_v11_rank(mutated, 5)


def test_determinism_100_repeated_executions():
    c = case(
        "What is Sora Kent's volunteering?",
        [
            memory("m1", "Old profile note about Sora Kent's volunteering: trail maintenance.", 4),
            memory("m2", "Sora Kent's volunteering is food-bank sorting.", 2),
            memory("m3", "Sora Kent's volunteering is perhaps library shelving.", 5),
        ],
    )
    expected = pse_candidate_v11_rank(c, 5)
    for _ in range(100):
        assert pse_candidate_v11_rank(c, 5) == expected


def test_candidate_source_and_eligibility_invariant():
    c = case(
        "What is Sora Kent's volunteering?",
        [
            memory("m1", "Old profile note about Sora Kent's volunteering: trail maintenance.", 4),
            memory("m2", "Sora Kent's volunteering is food-bank sorting.", 2),
            memory("m3", "Sora Kent's volunteering is perhaps library shelving.", 5),
            memory("m4", "Luca Kent's volunteering is park cleanup.", 5),
        ],
    )
    invariant = candidate_source_invariant_v11(c, 5)
    assert invariant["pass"] is True
    assert invariant["no_injection"] is True
    assert invariant["only_eligible"] is True


def test_priority_proof_is_explainable_and_uses_original_rank_only_as_last_tiebreak():
    q = "What is Rowan Hale's work role?"
    m = memory("m", "Rowan Hale works as a systems analyst.")
    proof = evidence_priority_proof_v11(q, m, 7)
    assert proof is not None
    assert proof.memory_id == "m"
    assert proof.subject_binding_quality >= 2
    assert proof.relation_specificity >= 2
    assert proof.assertion_directness >= 3
    assert proof.semantic_completeness == 6
    assert proof.priority_tuple[-1] == -7
