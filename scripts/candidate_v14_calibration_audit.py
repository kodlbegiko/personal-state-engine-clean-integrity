from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from personal_state_engine.candidate_v14 import decide_candidate_v14

def ece(points,bins=10):
    total=len(points);out=0.0;details=[]
    for b in range(bins):
        lo=b/bins;hi=(b+1)/bins;selected=[p for p in points if lo<=p[0]<hi or (b==bins-1 and p[0]==1.0)]
        if not selected:continue
        conf=sum(p[0] for p in selected)/len(selected);acc=sum(p[1] for p in selected)/len(selected);out+=len(selected)/max(1,total)*abs(conf-acc);details.append({'bin':[lo,hi],'n':len(selected),'mean_confidence':conf,'accuracy':acc})
    return out,details

def quantiles(xs):
    xs=sorted(xs)
    if not xs:return {}
    def q(p):return xs[min(len(xs)-1,round(p*(len(xs)-1)))]
    return {'min':xs[0],'p10':q(.1),'p25':q(.25),'median':q(.5),'p75':q(.75),'p90':q(.9),'max':xs[-1],'mean':sum(xs)/len(xs)}

def main():
    cases=json.loads((ROOT/'data/candidate-v14-development/internal-validation.json').read_text());retrieval=[];abstain=[];margins=[];top_scores=[];answerable_scores=[];noev_scores=[];points=[]
    for c in cases:
        d=decide_candidate_v14(c,5);margins.append(d.top_margin);top=d.scores[0].total if d.scores else 0.0;top_scores.append(top);correct=(bool(d.ranking) and c['answerable'] and d.ranking[0] in c['relevant_memory_ids']) or (not d.ranking and not c['answerable']);points.append((d.confidence,int(correct)));(retrieval if d.ranking else abstain).append(d.confidence);(answerable_scores if c['answerable'] else noev_scores).append(top)
    ec,curve=ece(points);sens=[]
    for floor in [0.10,0.14,0.18,0.22,0.26,0.30]:
        ans=fa=noev=fr=0
        for c in cases:
            d=decide_candidate_v14(c,5);top=d.scores[0] if d.scores else None;predicted=bool(d.ranking) and bool(top) and top.total>floor
            if c['answerable']:ans+=1;fa+=int(not predicted)
            else:noev+=1;fr+=int(predicted)
        sens.append({'diagnostic_floor':floor,'false_abstention':fa/max(1,ans),'false_retrieval':fr/max(1,noev)})
    out={'schema_version':'candidate-v14-calibration-audit-v1','split':'internal-validation','case_count':len(cases),'retrieval_confidence':quantiles(retrieval),'abstention_confidence':quantiles(abstain),'top_score':quantiles(top_scores),'answerable_top_score':quantiles(answerable_scores),'no_evidence_top_score':quantiles(noev_scores),'top1_top2_margin':quantiles(margins),'expected_calibration_error':ec,'reliability_curve':curve,'threshold_sensitivity_diagnostic':sens,'interpretation':'Threshold sensitivity is diagnostic only and does not alter the frozen policy.'}
    p=ROOT/'results/candidate-v14/calibration-audit.json';p.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
