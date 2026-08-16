from personal_state_engine.candidate_v14 import pse_candidate_v14_rank

def test_negated_memory_is_penalized():
    c={'query':'What hobby is stated for Mara Vale?','memories':[{'id':'yes','text':"Mara Vale's hobby is cycling."},{'id':'no','text':"Mara Vale's hobby is not painting."}]}
    assert pse_candidate_v14_rank(c,5)[0]=='yes'
