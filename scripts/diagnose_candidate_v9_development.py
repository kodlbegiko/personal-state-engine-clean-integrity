from __future__ import annotations
import json
from collections import Counter, defaultdict
from pathlib import Path
from personal_state_engine.candidate_v9 import evidence_support_signature_v9, pse_candidate_v9_rank

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'experiments/benchmarks/candidate-v9-development-v1.json'
OUT=ROOT/'results/candidate-v9/development-failure-taxonomy-iteration-0.json'

def main():
    payload=json.loads(DATA.read_text()); failures=[]; counts=Counter(); relation_counts=Counter(); type_counts=Counter()
    for c in payload['cases']:
        rel=set(c['relevant_memory_ids'])
        if not rel: continue
        out=pse_candidate_v9_rank(c,5)
        if rel & set(out): continue
        sig=evidence_support_signature_v9(c)
        cert={x['memory_id']:x for x in sig['certifications']}
        rows=[]; cats=[]
        for mid in rel:
            cr=cert.get(mid,{'clauses':[]})
            for clause in cr.get('clauses',[]):
                if clause.supported: cat='UNEXPECTED'
                elif clause.blocker: cat='BLOCKER:'+str(clause.blocker)
                elif not clause.subject_ok: cat='SUBJECT'
                elif not clause.relation_ok: cat='RELATION'
                elif not clause.value_type_ok: cat='VALUE_TYPE'
                elif not clause.value_bearing: cat='VALUE_BEARING'
                elif not clause.temporal_ok: cat='TEMPORAL'
                else: cat='SCORE_OR_SEGMENTATION'
                cats.append(cat); counts[cat]+=1
                rows.append({'memory_id':mid,'clause':clause.text,'category':cat,'subject_ok':clause.subject_ok,'relation_ok':clause.relation_ok,'value_type_ok':clause.value_type_ok,'value_bearing':clause.value_bearing,'direct_assertion':clause.direct_assertion,'temporal_ok':clause.temporal_ok,'blocker':clause.blocker,'score':clause.score,'relation_signals':list(clause.relation_signals),'value_type_signals':list(clause.value_type_signals)})
        for r in sig['requirements']['relations']: relation_counts[r]+=1
        for t in sig['requirements']['value_types']: type_counts[t]+=1
        failures.append({'case_id':c['id'],'query':c['query'],'requirements':sig['requirements'],'relevant_rows':rows,'categories':sorted(set(cats))})
    result={'failure_count':len(failures),'category_counts':dict(counts),'query_relation_counts':dict(relation_counts),'query_value_type_counts':dict(type_counts),'failures':failures,'formal_counts':{'protected':0,'confirmatory':0,'final':0}}
    OUT.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps({k:result[k] for k in ['failure_count','category_counts','query_relation_counts','query_value_type_counts']},indent=2))

if __name__=='__main__': main()
