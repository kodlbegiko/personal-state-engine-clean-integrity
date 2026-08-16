from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from personal_state_engine.candidate_v14 import decide_candidate_v14

DOMAINS = {
    "identity": ("language", "language", ["Asterian", "Boreal", "Cyrene"], ["tongue", "speaks"]),
    "preference": ("favorite color", "color", ["teal", "amber", "violet"], ["favourite hue", "preferred colour"]),
    "schedule": ("meeting day", "meeting", ["Monday", "Wednesday", "Friday"], ["appointment day", "scheduled session"]),
    "location": ("city", "city", ["Orion Bay", "Cedar Point", "Nova Vale"], ["town", "location"]),
    "device": ("device model", "device", ["MiraBook 14", "NovaPhone X", "AsterPad 3"], ["computer model", "machine"]),
    "education": ("course", "course", ["chemistry", "history", "calculus"], ["class", "subject"]),
    "food": ("favorite food", "food", ["ramen", "risotto", "tacos"], ["preferred cuisine", "favourite dish"]),
    "activity": ("hobby", "hobby", ["cycling", "painting", "badminton"], ["pastime", "activity"]),
}
FAMILIES = ["exact", "paraphrase", "synonym", "entity_substitution", "temporal_shift", "negation", "contradiction", "irrelevant_distractor", "ambiguous_evidence", "multi_memory", "weak_lexical_strong_semantic", "strong_lexical_wrong_semantic"]
NAMES = ["Aren Aster", "Belen Borel", "Cyra Cinder", "Darin Dune", "Elin Ember", "Faro Frost"]


def _case(seed: int, domain: str, family: str, answerable: bool, idx: int) -> dict:
    rng = random.Random((seed * 1000003) + idx * 97 + len(domain) * 31 + len(family))
    label, relation, values, aliases = DOMAINS[domain]
    name = rng.choice(NAMES) + f" V14{idx:04d}"
    gold_value = rng.choice(values)
    other = rng.choice([v for v in values if v != gold_value])
    alias = rng.choice(aliases)
    q_exact = f"What {label} is stated for {name}?"
    q_para = f"According to the record, tell me {name}'s {alias}."
    query = q_exact if family in {"exact", "entity_substitution", "temporal_shift", "negation", "contradiction", "irrelevant_distractor", "multi_memory"} else q_para
    if family == "weak_lexical_strong_semantic": query = f"For {name}, which {alias} applies?"
    if family == "strong_lexical_wrong_semantic": query = f"What {label} is stated for {name}?"
    gold_text = f"{name}'s {relation} is {gold_value}."
    if family in {"paraphrase", "synonym", "weak_lexical_strong_semantic"}: gold_text = f"For {name}, the recorded {alias} is {gold_value}."
    if family == "temporal_shift":
        old = {"id":"old", "text":f"{name}'s {relation} is {other}.", "timestamp":"2039-01-01T00:00:00+00:00"}; gold_ts = "2040-01-01T00:00:00+00:00"
    else: old = None; gold_ts = "2040-01-01T00:00:00+00:00"
    memories=[]
    if answerable:
        memories.append({"id":"gold", "text":gold_text, "timestamp":gold_ts})
        if old: memories.append(old)
    distractor_name = rng.choice([n for n in NAMES if not name.startswith(n)]) + f" V14X{idx:04d}"
    memories.append({"id":"d1", "text":f"{distractor_name}'s {relation} is {other}.", "timestamp":"2040-02-01T00:00:00+00:00"})
    memories.append({"id":"d2", "text":f"{name}'s unrelated note mentions project {other}.", "timestamp":"2040-02-02T00:00:00+00:00"})
    if family == "negation": memories.append({"id":"neg", "text":f"{name}'s {relation} is not {other}.", "timestamp":"2040-03-01T00:00:00+00:00"})
    elif family == "contradiction": memories.append({"id":"contra", "text":f"A correction says {name}'s {relation} is not {other}.", "timestamp":"2040-03-01T00:00:00+00:00"})
    elif family == "ambiguous_evidence": memories.append({"id":"maybe", "text":f"Perhaps {name}'s {relation} is {other}.", "timestamp":"2040-03-01T00:00:00+00:00"})
    elif family == "multi_memory": memories.append({"id":"related", "text":f"{name}'s {relation} was discussed in a planning note.", "timestamp":"2039-12-01T00:00:00+00:00"})
    elif family == "strong_lexical_wrong_semantic": memories.append({"id":"lure", "text":f"The phrase '{label}' appears here for {distractor_name}; {name} is only copied as a tag.", "timestamp":"2040-03-01T00:00:00+00:00"})
    elif family == "irrelevant_distractor": memories.extend([{"id":"d3", "text":f"{name} attended an unrelated conference in spring.", "timestamp":"2040-02-03T00:00:00+00:00"},{"id":"d4", "text":f"A document contains the word {relation} but refers to another person.", "timestamp":"2040-02-04T00:00:00+00:00"}])
    rng.shuffle(memories)
    return {"case_id":f"{domain}-{family}-{idx}","domain":domain,"family":family,"query":query,"memories":memories,"relevant_memory_ids":["gold"] if answerable else [],"answerable":answerable}


def generate(seed: int, per_family_domain: int) -> list[dict]:
    cases=[]; idx=0
    for domain in DOMAINS:
        for family in FAMILIES:
            for j in range(per_family_domain):
                cases.append(_case(seed,domain,family,(j%4)!=3,idx)); idx += 1
    return cases


def architecture_rank(case: dict, arch: str, k: int=5) -> list[str]:
    d=decide_candidate_v14(case,k)
    if arch=="B": return list(d.ranking)
    scores=list(d.scores)
    if not scores:return []
    top=scores[0]; second=scores[1] if len(scores)>1 else None; margin=top.total-(second.total if second else 0.0)
    if arch=="A": return [s.memory_id for s in scores[:k]] if top.total>=0.52 else []
    if arch=="C": return [s.memory_id for s in scores[:k]] if top.total>=0.38 and margin>=0.10 and top.contradiction_penalty==0 else []
    if arch=="D":
        suff=0.35*top.lexical+0.30*top.entity+0.25*top.semantic+0.10*max(0.0,margin)
        return [s.memory_id for s in scores[:k]] if suff>=0.34 and top.contradiction_penalty==0 else []
    raise ValueError(arch)


def metrics(cases: list[dict], arch: str="B") -> dict:
    rr=[];r1=[];r3=[];r5=[];answerable_total=0;answerable_retrieved=0;noev_total=0;noev_abstain=0;false_abstain=0;false_retrieve=0;eligible_rank1=[];fam=defaultdict(lambda:[0,0]);dom=defaultdict(lambda:{"ans":0,"retr":0,"noev":0,"false_ret":0});actions=[]
    for c in cases:
        ranking=architecture_rank(c,arch,5);gold=c["relevant_memory_ids"];actions.append("retrieve" if ranking else "abstain");ok=False
        if c["answerable"]:
            answerable_total+=1;answerable_retrieved+=int(bool(ranking));false_abstain+=int(not ranking);pos=next((i for i,m in enumerate(ranking,1) if m in gold),None)
            rr.append(1/pos if pos else 0);r1.append(int(pos==1));r3.append(int(pos is not None and pos<=3));r5.append(int(pos is not None and pos<=5));
            if ranking:eligible_rank1.append(int(ranking[0] in gold))
            ok=bool(pos==1)
        else:
            noev_total+=1;noev_abstain+=int(not ranking);false_retrieve+=int(bool(ranking));ok=not ranking
        fam[c["family"]][0]+=int(ok);fam[c["family"]][1]+=1;ds=dom[c["domain"]]
        if c["answerable"]:ds["ans"]+=1;ds["retr"]+=int(bool(ranking))
        else:ds["noev"]+=1;ds["false_ret"]+=int(bool(ranking))
    avg=lambda xs:sum(xs)/len(xs) if xs else 0.0
    dm={}
    for d,s in dom.items():
        subset=[c for c in cases if c["domain"]==d and c["answerable"]];subr=[architecture_rank(c,arch,5) for c in subset]
        dr1=sum(int(bool(r) and r[0] in c["relevant_memory_ids"]) for c,r in zip(subset,subr))/max(1,len(subset));dm[d]={"r1":dr1,"answerable_recall":s["retr"]/max(1,s["ans"]),"false_retrieval":s["false_ret"]/max(1,s["noev"])}
    retrieve_rate=actions.count("retrieve")/len(actions)
    return {"case_count":len(cases),"mrr":avg(rr),"r1":avg(r1),"r3":avg(r3),"r5":avg(r5),"answerable_recall":answerable_retrieved/max(1,answerable_total),"eligible_rank1_accuracy":avg(eligible_rank1),"abstention_accuracy":noev_abstain/max(1,noev_total),"false_abstention":false_abstain/max(1,answerable_total),"false_retrieval":false_retrieve/max(1,noev_total),"retrieve_rate":retrieve_rate,"abstain_rate":1-retrieve_rate,"family_accuracy":{k:v[0]/v[1] for k,v in fam.items()},"domain_metrics":dm}


def sha(path: Path) -> str:return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path: Path,obj)->None:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser();ap.add_argument("mode",choices=["generate","compare","holdout"]);ap.add_argument("--root",default=str(ROOT));args=ap.parse_args();root=Path(args.root);data=root/"data/candidate-v14-development";results=root/"results/candidate-v14"
    if args.mode=="generate":
        splits={"architecture-development":(14001,4),"internal-validation":(14002,4),"adversarial-validation":(14003,4),"untouched-internal-holdout":(14999,4)};manifest={"generator":"candidate_v14_development.py","splits":{}}
        for name,(seed,n) in splits.items():
            cases=generate(seed,n);path=data/f"{name}.json";dump(path,cases);manifest["splits"][name]={"seed":seed,"count":len(cases),"sha256":sha(path)}
        dump(data/"manifest.json",manifest);print(json.dumps(manifest,indent=2))
    elif args.mode=="compare":
        combined=[]
        for name in ["architecture-development","internal-validation","adversarial-validation"]:combined+=json.loads((data/f"{name}.json").read_text())
        for arch in "ABCD":dump(results/f"architecture-{arch.lower()}-results.json",metrics(combined,arch))
        print(json.dumps({a:metrics(combined,a) for a in "ABCD"},indent=2))
    else:
        holdout_path=data/"untouched-internal-holdout.json";cases=json.loads(holdout_path.read_text());out=metrics(cases,"B");out["holdout_sha256"]=sha(holdout_path);out["invocation_count"]=1;out["rerun_count"]=0;dump(results/"internal-holdout-results.json",out);print(json.dumps(out,indent=2))
if __name__=="__main__":main()
