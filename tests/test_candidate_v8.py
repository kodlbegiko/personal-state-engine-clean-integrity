from __future__ import annotations

import pytest

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v8 import (
    VERDICT_INSUFFICIENT,
    VERDICT_SUPPORTED,
    evidence_support_signature,
    pse_candidate_v8_rank,
)

def m(mid: str, text: str, day: int = 15) -> dict:
    return {"id": mid, "text": text, "timestamp": f"2026-10-{day:02d}T09:20:00+00:00"}

def case(query: str, relevant: str, negatives: list[str] | None = None) -> dict:
    memories = [m("rel", relevant)]
    for i, text in enumerate(negatives or []):
        memories.append(m(f"n{i}", text, 14))
    return {"query": query, "memories": memories}

@pytest.mark.parametrize("query,text", [
    ("What beverage does Amina normally pick?", "Amina usually chooses barley tea."),
    ("Which public transport does Benoit take?", "Benoit rides tram 5 each weekday."),
    ("What class is Celine enrolled in?", "Celine studies graph theory this semester."),
    ("What beverage do I tend to order after work?", "My usual after-work choice is cold brew."),
    ("Where does Dario live now?", "After relocating, Dario now lives in Turin."),
    ("What kind of work does Esme do?", "Esme works as a museum registrar."),
    ("What pet does Felix own?", "Felix has a basenji at home."),
    ("What hobby does Greta practice?", "Greta practices bookbinding on weekends."),
    ("Which language can Hana speak?", "Hana speaks Japanese comfortably."),
    ("Which university does Ivo attend?", "Ivo studies at Juniper Institute."),
    ("What music does Jia listen to?", "Jia listens to chamber opera most days."),
    ("What computer does Kiran use?", "Kiran uses a ThinkPad P14s."),
    ("What goal is Lena preparing for?", "Lena is training toward a sprint triathlon."),
    ("Who is Marek married to?", "Marek is married to Rina."),
    ("What color is Nia's travel bag?", "Nia's travel bag is indigo."),
    ("Which club is Oren a member of?", "Oren joined the geology society."),
    ("What is Priya's current application status?", "Priya's application is currently approved."),
    ("What version is Quinn's tablet using?", "Quinn's tablet is running NovaOS 7.2."),
    ("When is Rhea's recurring check-in?", "Rhea now meets on Thursday morning."),
])
def test_answerable_forms(query: str, text: str) -> None:
    c = case(query, text, [
        "Agenda item: discuss an unrelated supply request.",
        "No confirmed information is available for the unrelated field.",
        "Could someone answer a separate question later?",
    ])
    assert "rel" in pse_candidate_v8_rank(c, 5)

@pytest.mark.parametrize("query,text", [
    ("What beverage does Amina usually choose?", "Nora usually chooses barley tea."),
    ("What class is Benoit enrolled in?", "Benoit lives near Maple Coast University."),
    ("What computer does Celine use?", "What computer does Celine use?"),
    ("Who is Dario married to?", "Agenda item: discuss Dario's relationship next week."),
    ("What music does Esme listen to?", "The notes only discuss the question about Esme's music taste."),
    ("What medication does Felix take?", "Information about Felix's medication remains unavailable."),
    ("What goal is Greta preparing for?", "Greta might be preparing for something; the goal remains uncertain."),
    ("What is Hana's current application status?", "The records conflict about Hana's application status and cannot be reconciled."),
    ("Where does Ivo live now?", "Ivo formerly lived in Porto but no longer lives there."),
    ("What color is Jia's travel bag?", "Incorrect value record: Jia's travel bag is teal. Do not use this record."),
    ("Which public transport does Kiran take?", "Kiran's transit route is unknown."),
    ("What pet does Lena own?", "If Lena adopted a pet, a dachshund would be the first choice."),
    ("What course is Marek enrolled in?", "Marek plans to study graph theory next year."),
    ("What laptop does Nia use?", "The assistant suggested that Nia buy a Framework Laptop 13."),
    ("What job does Oren have?", "An unverified claim says Oren works as an urban planner."),
    ("What version is Priya's tablet using?", "Priya's phone is running NovaOS 9.4."),
    ("What goal is Quinn preparing for?", "Quinn's application status is active."),
])
def test_no_evidence_controls(query: str, text: str) -> None:
    c = case(query, text)
    assert pse_candidate_v8_rank(c, 5) == []

def test_clause_local_blocker_does_not_poison_fact() -> None:
    c = case(
        "Where does Rhea live now?",
        "Could someone answer a separate budgeting question later?; after relocating, Rhea now lives in Ghent.",
    )
    assert pse_candidate_v8_rank(c, 5) == ["rel"]

def test_stale_clause_is_filtered_but_current_clause_passes() -> None:
    c = case(
        "Where does Samir live now?",
        "Samir previously lived in Brno; after relocating, Samir now lives in Leuven.",
    )
    assert pse_candidate_v8_rank(c, 5) == ["rel"]

def test_per_memory_filtering_does_not_unlock_full_candidate_v2_list() -> None:
    c = {
        "query": "What music does Tova listen to?",
        "memories": [
            m("good", "Tova listens to Nordic folk.", 15),
            m("meta", "The notes only discuss the question about Tova's music taste.", 15),
            m("other", "Uma listens to bebop jazz.", 15),
        ],
    }
    out = pse_candidate_v8_rank(c, 5)
    assert out == ["good"]
    assert len(pse_candidate_v2_rank(c, 5)) > len(out)

def test_candidate_v2_relative_order_is_preserved() -> None:
    c = {
        "query": "What pet does Uri own?",
        "memories": [
            m("a", "Uri has a papillon at home.", 15),
            m("b", "Uri owns a goldfish.", 14),
            m("c", "Agenda item: discuss Uri's pet later.", 15),
        ],
    }
    v2 = pse_candidate_v2_rank(c, 10)
    v8 = pse_candidate_v8_rank(c, 10)
    assert v8 == [mid for mid in v2 if mid in set(v8)]

def test_signature_is_explainable() -> None:
    c = case("Which public transport does Vera take?", "Vera rides metro line C to work.")
    sig = evidence_support_signature(c)
    assert sig["verdict"] == VERDICT_SUPPORTED
    assert sig["supporting_memory_ids"] == ["rel"]
    cert = next(x for x in sig["certifications"] if x["memory_id"] == "rel")
    assert any(clause.supported and "transport" in " ".join(clause.support_signals) for clause in cert["clauses"])

def test_signature_abstains_when_requirements_not_met() -> None:
    c = case("What version is Wren's tablet using?", "Wren's phone is running NovaOS 8.1.")
    sig = evidence_support_signature(c)
    assert sig["verdict"] == VERDICT_INSUFFICIENT
