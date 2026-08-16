from __future__ import annotations

import hashlib, json, math, random, statistics, sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from personal_state_engine.candidate_v14 import pse_candidate_v14_decide

RES=ROOT/"results/candidate-v14-external-v1"
DATA=ROOT/"data/candidate-v14-external-v1"
PREREG=json.loads((ROOT/"docs/research/candidate-v14-external-v1/preregistration.json").read_text())


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def mean(xs): return sum(xs)/len(xs) if xs else 0.0

def load():
    cases=[]
    for p in sorted(DATA.glob("protected-*.json")): cases.extend(json.loads(p.read_text()))
    key=json.loads((DATA/"answer-key.json").read_text())
    return cases,key

def correctness(pred,k):
    if not k["answerable"]: return pred["verdict"]=="INSUFFICIENT" and len(pred["ranking"])==0
    if pred["verdict"]!="SUPPORTED": return False
    if k.get("requires_all"): return all(x in pred["ranking"] for x in k["relevant_ids"])
    return bool(pred["ranking"]) and pred["ranking"][0] in k["relevant_ids"]

def score(cases,key,preds):
    byid={p["id"]:p for p in preds}; ans=[]; no=[]; rr=[]; r1=[]; r3=[]; r5=[]; fam=defaultdict(list); dom=defaultdict(list); case_correct={}
    for c in cases:
        k=key[c["id"]]; p=byid[c["id"]]; ok=correctness(p,k); case_correct[c["id"]]=ok
        for f in k["families"]: fam[f].append(ok)
        dom[k["domain"]].append((k,p,ok))
        if k["answerable"]:
            ans.append((k,p,ok)); ranks=[p["ranking"].index(x)+1 for x in k["relevant_ids"] if x in p["ranking"]]; rank=min(ranks) if ranks else None
            rr.append(1/rank if rank else 0); r1.append(1 if rank==1 else 0); r3.append(1 if rank and rank<=3 else 0); r5.append(1 if rank and rank<=5 else 0)
        else: no.append((k,p,ok))
    overall={"case_count":len(cases),"answerable_count":len(ans),"no_evidence_count":len(no),"mrr":mean(rr),"r1":mean(r1),"r3":mean(r3),"r5":mean(r5),"answerable_recall":mean([1 if p["verdict"]=="SUPPORTED" and any(x in p["ranking"] for x in k["relevant_ids"]) else 0 for k,p,_ in ans]),"eligible_rank1_accuracy":mean([1 if p["verdict"]=="SUPPORTED" and p["ranking"] and p["ranking"][0] in k["relevant_ids"] else 0 for k,p,_ in ans]),"abstention_accuracy":mean([1 if ok else 0 for _,_,ok in no]),"false_abstention_rate":mean([1 if p["verdict"]=="INSUFFICIENT" else 0 for _,p,_ in ans]),"false_retrieval_rate":mean([1 if p["verdict"]=="SUPPORTED" else 0 for _,p,_ in no]),"retrieve_rate":mean([1 if byid[c["id"]]["verdict"]=="SUPPORTED" else 0 for c in cases])}
    family={f:{"n":len(v),"accuracy":mean([1 if x else 0 for x in v])} for f,v in sorted(fam.items())}
    domain={}
    for d,rows in sorted(dom.items()):
        a=[r for r in rows if r[0]["answerable"]]; z=[r for r in rows if not r[0]["answerable"]]
        domain[d]={"n":len(rows),"r1":mean([1 if p["verdict"]=="SUPPORTED" and p["ranking"] and p["ranking"][0] in k["relevant_ids"] else 0 for k,p,_ in a]),"answerable_recall":mean([1 if p["verdict"]=="SUPPORTED" and any(x in p["ranking"] for x in k["relevant_ids"]) else 0 for k,p,_ in a]),"false_retrieval":mean([1 if p["verdict"]=="SUPPORTED" else 0 for k,p,_ in z])}
    pairs=defaultdict(list); groups=defaultdict(list)
    for c in cases:
        k=key[c["id"]]
        if k.get("counterfactual_pair_id"): pairs[k["counterfactual_pair_id"]].append(c["id"])
        if k.get("metamorphic_group_id"): groups[k["metamorphic_group_id"]].append(c["id"])
    pair_ok=[]
    for ids in pairs.values():
        if len(ids)==2:
            a,b=ids; pa,pb=byid[a],byid[b]; pair_ok.append(case_correct[a] and case_correct[b] and (pa["verdict"],pa["ranking"][:1])!=(pb["verdict"],pb["ranking"][:1]))
    mm_ok=[]
    for ids in groups.values():
        if len(ids)>=2:
            base=byid[sorted(ids)[0]]; mm_ok.append(all((byid[i]["verdict"],byid[i]["ranking"][:1])==(base["verdict"],base["ranking"][:1]) for i in ids[1:]))
    return overall,family,domain,{"pair_count":len(pair_ok),"exact_pair_consistency":mean(pair_ok)},{"group_count":len(mm_ok),"invariance_consistency":mean(mm_ok)},case_correct

def bootstrap(cases,key,preds,n=2000,seed=20260816):
    rng=random.Random(seed); byid={p["id"]:p for p in preds}; ids=[c["id"] for c in cases]
    metrics={k:[] for k in ["r1","answerable_recall","false_abstention_rate","false_retrieval_rate"]}
    for _ in range(n):
        sample=[rng.choice(ids) for _ in ids]; ans=[i for i in sample if key[i]["answerable"]]; no=[i for i in sample if not key[i]["answerable"]]
        metrics["r1"].append(mean([1 if byid[i]["verdict"]=="SUPPORTED" and byid[i]["ranking"] and byid[i]["ranking"][0] in key[i]["relevant_ids"] else 0 for i in ans]))
        metrics["answerable_recall"].append(mean([1 if byid[i]["verdict"]=="SUPPORTED" and any(x in byid[i]["ranking"] for x in key[i]["relevant_ids"]) else 0 for i in ans]))
        metrics["false_abstention_rate"].append(mean([1 if byid[i]["verdict"]=="INSUFFICIENT" else 0 for i in ans]))
        metrics["false_retrieval_rate"].append(mean([1 if byid[i]["verdict"]=="SUPPORTED" else 0 for i in no]))
    out={}
    for k,vals in metrics.items():
        vals=sorted(vals); out[k]=[vals[int(.025*(len(vals)-1))],vals[int(.975*(len(vals)-1))]]
    return out

def calibration(cases,key,preds):
    rows=[]
    for p in preds:
        y=1.0 if key[p["id"]]["answerable"] else 0.0; prob=p["confidence"] if p["verdict"]=="SUPPORTED" else 1-p["confidence"]; rows.append((max(0,min(1,prob)),y))
    brier=mean([(p-y)**2 for p,y in rows]); ece=0.0
    for b in range(10):
        bucket=[r for r in rows if (b/10)<=r[0]<(b+1)/10 or (b==9 and r[0]==1.0)]
        if bucket: ece+=len(bucket)/len(rows)*abs(mean([x for x,_ in bucket])-mean([y for _,y in bucket]))
    return {"brier":brier,"ece_10bin":ece,"count":len(rows)}

def main():
    RES.mkdir(parents=True,exist_ok=True); cases,key=load(); preds=[]
    for c in cases:
        runtime={"query":c["query"],"memories":c["memories"]}; p=pse_candidate_v14_decide(runtime,5); p["id"]=c["id"]; preds.append(p)
    pred_path=RES/"predictions.json"; pred_path.write_text(json.dumps(preds,separators=(",",":"),sort_keys=True)+"\n")
    (RES/"predictions.sha256").write_text(sha(pred_path)+"\n")
    overall,family,domain,cf,mm,case_correct=score(cases,key,preds)
    ci=bootstrap(cases,key,preds,PREREG["bootstrap_resamples"],PREREG["bootstrap_seed"]); cal=calibration(cases,key,preds)
    for name,obj in [("aggregate-results.json",overall),("family-results.json",family),("domain-results.json",domain),("counterfactual-results.json",cf),("metamorphic-results.json",mm),("calibration-results.json",cal),("bootstrap-confidence-intervals.json",ci)]: (RES/name).write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n")

if __name__=="__main__": main()
