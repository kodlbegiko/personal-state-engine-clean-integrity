from __future__ import annotations
import json,sys
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from personal_state_engine.candidate_v14 import pse_candidate_v14_rank
BASE={'query':'What favorite food is stated for Mara Vale?','memories':[{'id':'gold','text':"Mara Vale's food is ramen.",'timestamp':'2040-01-01T00:00:00+00:00'},{'id':'d1','text':"Niko Voss's food is tacos.",'timestamp':'2040-02-01T00:00:00+00:00'}]}
def first(c):
    r=pse_candidate_v14_rank(c,5);return r[0] if r else None
def main():
    checks={};checks['retrieval_preserving_wording']=first({'query':"According to the record, tell me Mara Vale's preferred cuisine.",'memories':deepcopy(BASE['memories'])})=='gold';checks['punctuation_invariance']=first({'query':'What favorite food, is stated for Mara Vale?!','memories':deepcopy(BASE['memories'])})=='gold';checks['memory_permutation_invariance']=first({'query':BASE['query'],'memories':list(reversed(BASE['memories']))})=='gold';checks['evidence_removal_retrieve_to_abstain']=first({'query':BASE['query'],'memories':[BASE['memories'][1]]}) is None
    lure=deepcopy(BASE);lure['memories'].append({'id':'lure','text':"The phrase 'favorite food' appears here for Niko Voss; Mara Vale is only copied as a tag.",'timestamp':'2041-01-01T00:00:00+00:00'});checks['lexical_lure_resistance']=first(lure)=='gold'
    contra=deepcopy(BASE);contra['memories'].append({'id':'contra','text':"Mara Vale's food is not tacos.",'timestamp':'2041-01-01T00:00:00+00:00'});checks['contradiction_resistance']=first(contra)=='gold'
    temporal={'query':'What meeting day is stated for Mara Vale?','memories':[{'id':'old','text':"Mara Vale's meeting is Monday.",'timestamp':'2039-01-01T00:00:00+00:00'},{'id':'new','text':"Mara Vale's meeting is Friday.",'timestamp':'2041-01-01T00:00:00+00:00'}]};checks['temporal_newer_wins']=first(temporal)=='new';checks['deterministic_output']=len({tuple(pse_candidate_v14_rank(BASE,5)) for _ in range(25)})==1
    out={'schema_version':'candidate-v14-counterfactual-audit-v1','checks':checks,'pass':all(checks.values()),'count':len(checks),'passed':sum(checks.values())};(ROOT/'results/candidate-v14/counterfactual-audit.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');meta_keys=['retrieval_preserving_wording','punctuation_invariance','memory_permutation_invariance','evidence_removal_retrieve_to_abstain','contradiction_resistance','deterministic_output'];meta={'schema_version':'candidate-v14-metamorphic-audit-v1','checks':{k:checks[k] for k in meta_keys},'pass':all(checks[k] for k in meta_keys)};(ROOT/'results/candidate-v14/metamorphic-audit.json').write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n');print(json.dumps({'counterfactual':out,'metamorphic':meta},indent=2));raise SystemExit(0 if out['pass'] and meta['pass'] else 2)
if __name__=='__main__':main()
