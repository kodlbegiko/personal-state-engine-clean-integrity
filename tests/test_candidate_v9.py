from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v9 import pse_candidate_v9_rank, semantic_requirements


def m(mid, text, day=20):
    return {"id":mid,"text":text,"timestamp":f"2027-02-{day:02d}T08:30:00+00:00","speaker":"user"}


def case(query, memories, **extra):
    return {"query":query,"memories":memories,**extra}


def test_preference_relation_canonicalization():
    c=case("Which beverage does Noor favor routinely?",[m("rel","Noor normally selects jasmine tea during breaks."),m("d","Agenda item: discuss Noor's drink later.")])
    assert pse_candidate_v9_rank(c,5)==["rel"]


def test_education_institution_canonicalization():
    c=case("Where is Noor studying this year?",[m("rel","Noor is enrolled at Harbor Institute for the current academic year."),m("d","Noor works near Harbor Institute as a technician.")])
    assert pse_candidate_v9_rank(c,5)==["rel"]


def test_value_type_prevents_nearby_false_support():
    c=case("Which beverage does Noor normally prefer?",[m("x","Noor's favorite pastime is pottery."),m("d","No verified information about Noor's drink is available.")])
    assert pse_candidate_v9_rank(c,5)==[]


def test_wrong_subject_rejected():
    c=case("Which laptop does Noor use?",[m("x","Mina's main laptop is a ThinkPad T14.")])
    assert pse_candidate_v9_rank(c,5)==[]


def test_question_only_rejected():
    c=case("Which laptop does Noor use?",[m("x","Which laptop does Noor use?")])
    assert pse_candidate_v9_rank(c,5)==[]


def test_uncertain_rejected():
    c=case("Where does Noor live now?",[m("x","It is uncertain whether Noor lives in Oslo.")])
    assert pse_candidate_v9_rank(c,5)==[]


def test_hypothetical_rejected():
    c=case("Which transit does Noor use?",[m("x","If the weather changed, Noor might take tram 7.")])
    assert pse_candidate_v9_rank(c,5)==[]


def test_future_intent_rejected():
    c=case("What hobby does Noor practice?",[m("x","Noor plans to start woodworking next year.")])
    assert pse_candidate_v9_rank(c,5)==[]


def test_assistant_suggestion_rejected():
    c=case("What goal is Noor preparing for?",[m("x","The assistant suggested that Noor train for a half marathon.")])
    assert pse_candidate_v9_rank(c,5)==[]


def test_stale_only_rejected_for_current_query():
    c=case("Where does Noor live now?",[m("x","Previously, Noor lived in Oslo, but that address is no longer current.")])
    assert pse_candidate_v9_rank(c,5)==[]


def test_bounded_coreference_same_memory():
    c=case("Where does Noor reside currently?",[m("rel","Noor updated the address. They now reside in Utrecht."),m("d","A tentative note about another person remains unresolved.")])
    assert "rel" in pse_candidate_v9_rank(c,5)


def test_first_person_support():
    c=case("Which beverage do I normally favor after class?",[m("rel","My regular after-class pick is cocoa."),m("d","No verified value is available.")])
    assert pse_candidate_v9_rank(c,5)==["rel"]


def test_candidate_v2_is_sole_ranker_and_output_is_subsequence():
    c=case("Which language does Noor speak?",[m("d","Agenda item: discuss Noor's language."),m("rel","Noor speaks Swedish fluently."),m("x","Mina speaks Swedish fluently.")])
    full=pse_candidate_v2_rank(c,5); out=pse_candidate_v9_rank(c,5)
    assert out == [mid for mid in full if mid in set(out)]
    assert out == ["rel"]


def test_one_supported_memory_does_not_unlock_invalid_memory():
    c=case("Which language does Noor speak?",[m("rel","Noor speaks Swedish fluently."),m("bad","An unverified claim says Noor speaks Dutch."),m("d","Agenda item: discuss language.")])
    assert pse_candidate_v9_rank(c,5)==["rel"]


def test_benchmark_metadata_cannot_change_inference():
    base=case("Which language does Noor speak?",[m("rel","Noor speaks Swedish fluently.")])
    poisoned={**base,"id":"SPECIAL","relevant_memory_ids":["not-rel"],"answer":"wrong","designation":"PROTECTED","provenance":"secret"}
    assert pse_candidate_v9_rank(base,5)==pse_candidate_v9_rank(poisoned,5)==["rel"]


def test_query_intent_is_typed():
    req=semantic_requirements("At which institution is Noor pursuing studies?")
    assert "education_institution" in req.relations
    assert "institution" in req.value_types


def test_open_class_role_is_licensed_by_typed_relation():
    c=case("What profession does Noor hold?",[m("rel","Noor serves as a quantum archivist.")])
    assert pse_candidate_v9_rank(c,5)==["rel"]


def test_open_class_course_is_licensed_by_typed_relation():
    c=case("Which course is Noor taking this term?",[m("rel","Noor is enrolled in comparative hydrology this term.")])
    assert pse_candidate_v9_rank(c,5)==["rel"]


def test_polymorphic_preference_rejects_explicit_conflicting_type():
    c=case("Which beverage does Noor normally prefer?",[m("x","Noor's favorite pastime is origami.")])
    assert pse_candidate_v9_rank(c,5)==[]


def test_polymorphic_preference_accepts_open_value_without_conflicting_type():
    c=case("Which beverage does Noor normally prefer?",[m("rel","Noor normally orders saffron tonic during breaks.")])
    assert pse_candidate_v9_rank(c,5)==["rel"]
