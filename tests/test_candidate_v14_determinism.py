from personal_state_engine.candidate_v14 import pse_candidate_v14_rank

def test_deterministic_and_stable_tie_break():
    c={'query':'What hobby is stated for Mara Vale?','memories':[{'id':'b','text':"Mara Vale's hobby is cycling."},{'id':'a','text':"Mara Vale's hobby is cycling."}]}
    outs=[pse_candidate_v14_rank(c,5) for _ in range(25)]
    assert all(x==outs[0] for x in outs)
    assert outs[0][0]=='a'
