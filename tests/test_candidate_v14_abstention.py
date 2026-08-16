from personal_state_engine.candidate_v14 import pse_candidate_v14_rank

def test_uncertain_only_evidence_abstains():
    c={'query':'What hobby is stated for Mara Vale?','memories':[{'id':'m','text':"Perhaps Mara Vale's hobby is cycling."}]}
    assert pse_candidate_v14_rank(c,5)==[]
def test_unrelated_same_entity_abstains():
    c={'query':'What hobby is stated for Mara Vale?','memories':[{'id':'m','text':'Mara Vale attended a conference.'}]}
    assert pse_candidate_v14_rank(c,5)==[]
