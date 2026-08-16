from personal_state_engine.candidate_v14 import pse_candidate_v14_rank

def test_newer_equivalent_support_ranks_first():
    c={'query':'What meeting day is stated for Mara Vale?','memories':[{'id':'old','text':"Mara Vale's meeting is Monday.",'timestamp':'2039-01-01T00:00:00+00:00'},{'id':'new','text':"Mara Vale's meeting is Friday.",'timestamp':'2041-01-01T00:00:00+00:00'}]}
    assert pse_candidate_v14_rank(c,5)[0]=='new'
