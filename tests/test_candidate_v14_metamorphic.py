from personal_state_engine.candidate_v14 import pse_candidate_v14_rank
MEM=[{'id':'g','text':"Mara Vale's food is ramen."},{'id':'d','text':"Niko Voss's food is tacos."}]
def first(q,m=MEM):
    r=pse_candidate_v14_rank({'query':q,'memories':m},5);return r[0] if r else None
def test_query_paraphrase_invariance(): assert first("According to the record, tell me Mara Vale's preferred cuisine.")=='g'
def test_irrelevant_distractor_invariance(): assert first('What favorite food is stated for Mara Vale?',MEM+[{'id':'x','text':'A weather report discusses rain.'}])=='g'
def test_memory_permutation_invariance(): assert first('What favorite food is stated for Mara Vale?',list(reversed(MEM)))=='g'
def test_case_normalization_invariance(): assert first('WHAT FAVORITE FOOD IS STATED FOR MARA VALE?')=='g'
