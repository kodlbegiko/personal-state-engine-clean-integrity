from personal_state_engine.candidate_v14 import pse_candidate_v14_rank, pse_candidate_v14_decide

def test_basic_retrieve():
    c={'query':'What favorite food is stated for Mara Vale?','memories':[{'id':'g','text':"Mara Vale's food is ramen."},{'id':'d','text':"Niko Voss's food is tacos."}]}
    assert pse_candidate_v14_rank(c,5)[0]=='g'
    assert pse_candidate_v14_decide(c,5)['verdict']=='SUPPORTED'

def test_no_evidence_abstains():
    c={'query':'What favorite food is stated for Mara Vale?','memories':[{'id':'d','text':"Niko Voss's food is tacos."}]}
    assert pse_candidate_v14_rank(c,5)==[]
