from personal_state_engine.candidate_v14 import pse_candidate_v14_rank

def rank(mem): return pse_candidate_v14_rank({'query':'What favorite food is stated for Mara Vale?','memories':mem},5)
def test_evidence_deletion_causes_abstention(): assert rank([{'id':'d','text':"Niko Voss's food is tacos."}])==[]
def test_lexical_lure_does_not_win():
    m=[{'id':'g','text':"Mara Vale's food is ramen."},{'id':'l','text':"The phrase 'favorite food' appears here for Niko Voss; Mara Vale is only copied as a tag."}]
    assert rank(m)[0]=='g'
def test_contradiction_does_not_win():
    m=[{'id':'g','text':"Mara Vale's food is ramen."},{'id':'c','text':"Mara Vale's food is not tacos."}]
    assert rank(m)[0]=='g'
