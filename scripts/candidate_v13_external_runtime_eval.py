from __future__ import annotations

"""Deterministic runtime evaluator for Candidate-v13 naturalistic external validity.

The module reconstructs the locked source pool, reproduces joint-feasibility
stage selections, materializes only the requested stage in memory, routes every
case through Candidate-v2 before Candidate-v13, and emits aggregate evidence.
No raw external case payload is committed.
"""

import argparse
import csv
import dataclasses
import hashlib
import importlib
import importlib.util
import inspect
import io
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"src"; sys.path.insert(0,str(SRC))
JOINT_PATH=ROOT/"scripts/candidate_v13_external_joint_feasibility.py"
CONTRACT_PATH=ROOT/"results/candidate-v13-external-validity/runtime-contract.json"
FEAS_PATH=ROOT/"results/candidate-v13-external-validity/joint-feasibility.json"
OUT_DIR=ROOT/"results/candidate-v13-external-validity"
UNKNOWN_TS="2000-01-01T00:00:00Z"

spec=importlib.util.spec_from_file_location("joint_runtime",JOINT_PATH)
if spec is None or spec.loader is None: raise RuntimeError("joint module unavailable")
joint=importlib.util.module_from_spec(spec); sys.modules[spec.name]=joint; spec.loader.exec_module(joint)
CONTRACT=json.loads(CONTRACT_PATH.read_text()); FEAS=json.loads(FEAS_PATH.read_text())


def h(*parts:Any)->str: return hashlib.sha256("\x1f".join(str(x) for x in parts).encode()).hexdigest()
def norm(x:Any)->str: return " ".join(str(x or "").casefold().replace("’","'").split())
def tset(x:Any)->set[str]: return set(joint.tokens(x))


def jsonable(v:Any)->Any:
    if v is None or isinstance(v,(str,int,float,bool)): return v
    if isinstance(v,dict): return {str(k):jsonable(v[k]) for k in sorted(v,key=lambda x:str(x))}
    if isinstance(v,(list,tuple)): return [jsonable(x) for x in v]
    if dataclasses.is_dataclass(v): return jsonable(dataclasses.asdict(v))
    if hasattr(v,"__dict__"): return jsonable(vars(v))
    return repr(v)


def canonical(v:Any)->str: return json.dumps(jsonable(v),ensure_ascii=False,sort_keys=True,separators=(",",":"))


def invoke(fn:Callable[...,Any],query:str,records:list[Any])->Any:
    sig=inspect.signature(fn); args=[]; kwargs={}
    for p in sig.parameters.values():
        n=p.name.casefold()
        if n in {"query","user_query","question","original_query","runtime_query"} or "query" in n: value=query
        elif any(tok in n for tok in ["candidate","record","memory","memories","items"]): value=records
        elif n in {"k","top_k","limit","n"}: value=len(records)
        elif any(tok in n for tok in ["now","current_time","reference_time"]): value="2026-01-04T12:00:00Z"
        elif p.default is not inspect._empty: continue
        else: raise TypeError(f"unmapped required parameter: {p.name}")
        if p.kind in {p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD}: args.append(value)
        elif p.kind==p.KEYWORD_ONLY: kwargs[p.name]=value
        else: raise TypeError(f"unsupported parameter kind: {p.name}")
    return fn(*args,**kwargs)


def list_like(v:Any)->list[Any]|None:
    if isinstance(v,list): return v
    if isinstance(v,tuple):
        for x in v:
            if isinstance(x,list): return x
    if isinstance(v,dict):
        for k in ["candidates","ranked_candidates","results","items","records"]:
            if isinstance(v.get(k),list): return v[k]
    for k in ["candidates","ranked_candidates","results","items","records"]:
        x=getattr(v,k,None)
        if isinstance(x,list): return x
    return None


def extract_id(item:Any,id_key:str)->str|None:
    if isinstance(item,str): return item
    if isinstance(item,(list,tuple)) and item: return extract_id(item[0],id_key)
    keys=[id_key,"id","memory_id","candidate_id","record_id","doc_id","key"]
    if isinstance(item,dict):
        for k in keys:
            if k in item and isinstance(item[k],(str,int)): return str(item[k])
    for k in keys:
        x=getattr(item,k,None)
        if isinstance(x,(str,int)): return str(x)
    return None


def ranked_ids(output:Any,id_key:str)->list[str]:
    lst=list_like(output)
    if lst is None:
        if output in (None,False,""): return []
        one=extract_id(output,id_key); return [one] if one else []
    out=[]
    for item in lst:
        mid=extract_id(item,id_key)
        if mid is not None and mid not in out: out.append(mid)
    return out


def make_raw(mem:dict[str,Any],schema:dict[str,str])->dict[str,Any]:
    return {schema["id"]:mem["id"],schema["text"]:mem["text"],schema["timestamp"]:mem.get("timestamp") or UNKNOWN_TS}


def mem(mid:str,text:str,subject:str,relation:str,source:str,timestamp:str|None=None,kind:str="context")->dict[str,Any]:
    return {"id":str(mid),"text":str(text),"timestamp":timestamp or UNKNOWN_TS,"subject":str(subject),"relation":str(relation),"source":source,"kind":kind}


def source_raws()->dict[str,bytes]:
    erev=str(joint.QUAL["revision"])
    return {
      "pm":joint.fetch(joint.hf_url("bowen-upenn/PersonaMem-v2","b7b42b78917157afed063527a1c959e98f6109f2","benchmark/text/benchmark.csv")),
      "lme":joint.fetch(joint.hf_url("xiaowu0162/longmemeval-cleaned","98d7416c24c778c2fee6e6f3006e7a073259d48f","longmemeval_oracle.json")),
      "loc":joint.fetch("https://raw.githubusercontent.com/snap-research/locomo/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/data/locomo10.json"),
      "sgd":joint.fetch("https://github.com/google-research-datasets/dstc8-schema-guided-dialogue/archive/e852981ae34990f4358979625854259302feaa78.zip"),
      "everq":joint.fetch(joint.hf_url("EverMind-AI/EverMemBench-Dynamic",erev,"EverMemBench_QAR.json")),
      "everd":joint.fetch(joint.hf_url("EverMind-AI/EverMemBench-Dynamic",erev,"EverMemBench_Dialogues.json")),
    }


def rebuild_bases(raws:dict[str,bytes])->tuple[list[dict[str,Any]],Counter[str]]:
    stats=Counter(); bases=[]; joint.load_personamem(raws["pm"],bases,stats); joint.load_lme(raws["lme"],bases,stats); joint.load_locomo(raws["loc"],bases,stats); joint.load_sgd(raws["sgd"],bases,stats); joint.load_evermem(raws["everq"],raws["everd"],bases,stats); bases=joint.global_dedup(bases,stats); joint.dynamic_families(bases); return bases,stats


def select_through(stage:str,bases:list[dict[str,Any]])->dict[str,Any]:
    used=set(); selected={}; stages=[]
    for st in joint.ALLOC["stage_order"]:
        remaining=[i for i in range(len(bases)) if i not in used]; solved=False
        for variant in range(int(joint.ALGO["transport_variants"]["count"])):
            ok,matrix=joint.transport(st,remaining,bases,variant)
            if not ok: continue
            fm,assignments=joint.family_match(st,remaining,bases,matrix)
            if not fm: continue
            noev=joint.no_evidence(st,assignments,bases); digest=hashlib.sha256("\n".join(sorted(bases[i]["id"] for i,_ in assignments)).encode()).hexdigest()
            expected=FEAS["stages"][st]["selected_base_id_digest"]
            if digest!=expected: raise RuntimeError(f"selection digest mismatch {st}: {digest} != {expected}")
            selected[st]={"assignments":assignments,"no_evidence":noev,"matrix":matrix,"variant":variant,"digest":digest}; used.update(i for i,_ in assignments); solved=True; break
        if not solved: raise RuntimeError(f"unable to reproduce locked selection for {st}")
        stages.append(st)
        if st==stage: break
    return selected[stage]


def detail_persona(raw:bytes)->dict[str,dict[str,Any]]:
    out={}
    for i,row in enumerate(csv.DictReader(io.StringIO(raw.decode("utf-8")))):
        bid=f"pm:{i}"; subject=str(row.get("persona_id", "")) or f"persona:{i}"; relation=str(row.get("topic_preference", "")).strip() or str(row.get("topic_query", "")).strip() or "preference"
        gold=[mem(f"persona::{i}::related",str(row.get("related_conversation_snippet", "")),subject,relation,"personamem-v2",kind="gold")]
        pool=list(gold); prev=str(row.get("prev_pref", "")).strip()
        if prev: pool.append(mem(f"persona::{i}::prev_pref",prev,subject,relation,"personamem-v2",kind="stale"))
        out[bid]={"gold":gold,"pool":pool}
    return out


def detail_lme(raw:bytes)->dict[str,dict[str,Any]]:
    out={}
    for i,row in enumerate(json.loads(raw)):
        qid=str(row.get("question_id",i)); bid=f"lme:{qid}"; ids=[str(x) for x in row.get("haystack_session_ids",[])]; sessions=row.get("haystack_sessions",[]); dates=row.get("haystack_dates",[]); typ=str(row.get("question_type","unknown")); subject=f"lme:{qid}"
        if len(ids)!=len(sessions): continue
        pool=[]; byid={}
        for j,(sid,sess) in enumerate(zip(ids,sessions)):
            text=joint.session_text(sess); ts=str(dates[j]) if isinstance(dates,list) and j<len(dates) and dates[j] else UNKNOWN_TS; m=mem(sid,text,subject,typ,"longmemeval-cleaned",ts); pool.append(m); byid[sid]=m
        gids=[str(x) for x in row.get("answer_session_ids",[])]; gold=[dict(byid[g],kind="gold") for g in gids if g in byid]
        if gold: out[bid]={"gold":gold,"pool":pool}
    return out


def detail_locomo(raw:bytes)->dict[str,dict[str,Any]]:
    out={}
    for si,sample in enumerate(json.loads(raw)):
        if not isinstance(sample,dict): continue
        c,qa=sample.get("conversation"),sample.get("qa"); sid=str(sample.get("sample_id",si))
        if not isinstance(c,dict) or not isinstance(qa,list): continue
        turns={}; pool=[]
        for key in joint.locomo_session_keys(c):
            date=str(c.get(f"{key}_date_time",UNKNOWN_TS) or UNKNOWN_TS)
            for t in c.get(key,[]):
                if not isinstance(t,dict) or t.get("dia_id") is None: continue
                did=str(t["dia_id"]); subject=f"{sid}:{t.get('speaker','')}"; m=mem(f"{sid}::{did}",f"{t.get('speaker','')}: {t.get('text','')}",subject,"conversation","locomo",date); turns[did]=m; pool.append(m)
        for qi,item in enumerate(qa):
            if not isinstance(item,dict): continue
            ev=item.get("evidence"); eids=[str(x) for x in ev] if isinstance(ev,list) else ([str(ev)] if isinstance(ev,str) and ev.strip() else [])
            gold=[dict(turns[e],kind="gold") for e in eids if e in turns]
            if eids and len(gold)==len(eids): out[f"locomo:{sid}:{qi}"]={"gold":gold,"pool":pool}
    return out


def detail_sgd(raw:bytes)->dict[str,dict[str,Any]]:
    import zipfile
    out={}; domain_map={}
    for d,prefixes in joint.ADAPTER["sources"]["sgd-carryover"]["domain_map"].items():
        for p in prefixes: domain_map[p]=d
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names=sorted(n for n in zf.namelist() if re.search(r"/(train|dev|test)/dialogues_\d+\.json$",n))
        for name in names:
            split=next(x for x in ["train","dev","test"] if f"/{x}/" in name)
            for di,dialog in enumerate(json.loads(zf.read(name))):
                if not isinstance(dialog,dict): continue
                did=str(dialog.get("dialogue_id",di)); turns=dialog.get("turns",[]); prior=defaultdict(list); user_pool=[]
                for ti,turn in enumerate(turns if isinstance(turns,list) else []):
                    if isinstance(turn,dict) and turn.get("speaker")=="USER": user_pool.append(mem(f"sgd::{split}::{did}::{ti}",str(turn.get("utterance","")),f"sgd:{split}:{did}","dialogue","sgd-carryover"))
                by_index={int(m["id"].rsplit("::",1)[1]):m for m in user_pool}
                for ti,turn in enumerate(turns if isinstance(turns,list) else []):
                    if not isinstance(turn,dict) or turn.get("speaker")!="USER": continue
                    frames=turn.get("frames",[]); bydom=defaultdict(list)
                    for fr in frames if isinstance(frames,list) else []:
                        if not isinstance(fr,dict): continue
                        service=str(fr.get("service","")); dom=domain_map.get(service.split("_",1)[0]); sv=joint.state_values(fr); ex=joint.explicit_slots(fr)
                        if not dom: continue
                        for slot,vals in sv.items():
                            if slot in ex: continue
                            for val in vals:
                                if prior[(service,slot,val)]: bydom[dom].append((service,slot,prior[(service,slot,val)][-1]))
                    active=[d for d,r in bydom.items() if r]
                    if len(active)==1:
                        relmap={(s,slot):(s,slot,g) for s,slot,g in bydom[active[0]]}; gids=sorted({g for _,_,g in relmap.values()}); gold=[dict(by_index[g],kind="gold") for g in gids if g in by_index]
                        if gold: out[f"sgd:{split}:{did}:{ti}"]={"gold":gold,"pool":user_pool}
                    for fr in frames if isinstance(frames,list) else []:
                        if not isinstance(fr,dict): continue
                        service=str(fr.get("service","")); dom=domain_map.get(service.split("_",1)[0]); sv=joint.state_values(fr)
                        if not dom: continue
                        for slot in joint.explicit_slots(fr):
                            for val in sv.get(slot,set()): prior[(service,slot,val)].append(ti)
    return out


def detail_ever(qraw:bytes,draw:bytes)->dict[str,dict[str,Any]]:
    qars,dialogues=json.loads(qraw),json.loads(draw); index={}; pools=defaultdict(list)
    for row in dialogues if isinstance(dialogues,list) else []:
        if not isinstance(row,dict): continue
        t=str(row.get("topic_id","")).upper(); date=str(row.get("date", ""))[:10]; groups=row.get("dialogues")
        if not t or not date or not isinstance(groups,dict): continue
        for group,messages in groups.items():
            if not isinstance(messages,list): continue
            for msg in messages:
                if not isinstance(msg,dict): continue
                idx=msg.get("msg_index",msg.get("message_index")); text=joint.ever_message_text(msg)
                if idx is None or not text: continue
                sid=str(int(idx)) if str(idx).isdigit() else str(idx); mid=f"evermem::{t}::{date}::{group}::{sid}"; m=mem(mid,text,f"ever:{t}:{group}",t,"evermembench-dynamic",f"{date}T00:00:00Z"); index[(t,date,str(group),sid)]=m; pools[(t,str(group))].append(m)
    out={}
    for qi,(t,item) in enumerate(joint.iter_qars(qars)):
        refs=item.get("R") if isinstance(item.get("R"),list) else []; keys=[]; ok=True
        for ref in refs:
            if not isinstance(ref,dict): ok=False; break
            rt=str(ref.get("topic_id",t)).upper() or t; date=str(ref.get("date", ""))[:10]; group=str(ref.get("group", "")); req=joint.expand_indices(ref.get("message_index",ref.get("msg_index")))
            for idx in sorted(req,key=lambda x:int(x) if x.isdigit() else x):
                key=(rt,date,group,idx)
                if key not in index: ok=False; break
                keys.append(key)
            if not ok: break
        if not ok or not keys: continue
        gold=[dict(index[k],kind="gold") for k in keys]; pool=[]
        for k in keys: pool.extend(pools[(k[0],k[2])])
        seen=set(); pool=[x for x in pool if not (x["id"] in seen or seen.add(x["id"]))]
        out[f"ever:{t}:{qi}"]={"gold":gold,"pool":pool}
    return out


def details(raws:dict[str,bytes])->dict[str,dict[str,Any]]:
    out={};
    for d in [detail_persona(raws["pm"]),detail_lme(raws["lme"]),detail_locomo(raws["loc"]),detail_sgd(raws["sgd"]),detail_ever(raws["everq"],raws["everd"])]: out.update(d)
    return out


def memory_overlap(query:str,text:str)->float:
    q=tset(query); return len(q&tset(text))/max(1,len(q))


def choose_other(base:dict[str,Any],bases:list[dict[str,Any]],detail:dict[str,dict[str,Any]],predicate:Callable[[dict[str,Any]],bool],tag:str)->dict[str,Any]|None:
    candidates=[b for b in bases if b["id"]!=base["id"] and b["id"] in detail and predicate(b) and detail[b["id"]]["gold"]]
    if not candidates: return None
    candidates.sort(key=lambda b:h("decoy",tag,base["id"],b["source"],b["id"])); b=candidates[0]; m=dict(detail[b["id"]]["gold"][0]); m["kind"]="decoy"; return m


def materialize_case(base:dict[str,Any],primary_family:str,is_noev:bool,bases:list[dict[str,Any]],detail:dict[str,dict[str,Any]])->dict[str,Any]:
    d=detail.get(base["id"])
    if not d or not d.get("gold"): raise RuntimeError(f"missing source detail for {base['id']}")
    gold=[dict(x) for x in d["gold"]]; gold_ids={x["id"] for x in gold}; gold_norm={norm(x["text"]) for x in gold}; pool=[dict(x) for x in d.get("pool",[]) if x.get("id")]
    required=[]
    if primary_family=="N3":
        x=choose_other(base,bases,detail,lambda b:b["domain"]==base["domain"] and b["subject"]!=base["subject"],"N3"); required += [x] if x else []
    if primary_family=="N4" and not base.get("implicit_relation"):
        x=choose_other(base,bases,detail,lambda b:b["subject"]==base["subject"] and b["relation"]!=base["relation"],"N4"); required += [x] if x else []
    if primary_family=="N12":
        x=choose_other(base,bases,detail,lambda b:b["subject"]==base["subject"] and b["relation"]==base["relation"],"N12"); required += [x] if x else []
    if primary_family=="N9":
        best=max(memory_overlap(base["query"],x["text"]) for x in gold)
        candidates=[]
        for b in bases:
            if b["id"]==base["id"] or b["domain"]!=base["domain"] or b["id"] not in detail: continue
            for m in detail[b["id"]]["gold"][:1]:
                if memory_overlap(base["query"],m["text"])>best: candidates.append((b,m))
        if candidates:
            candidates.sort(key=lambda bm:h("decoy","N9",base["id"],bm[0]["id"])); x=dict(candidates[0][1]); x["kind"]="decoy"; required.append(x)
    # Add source-native pool, required family decoys, then same-domain fillers.
    memories=[]; seen=set()
    def push(m:dict[str,Any]):
        if not m or m["id"] in seen: return
        if is_noev and (m["id"] in gold_ids or norm(m["text"]) in gold_norm): return
        seen.add(m["id"]); memories.append(m)
    if not is_noev:
        for m in gold: push(m)
    for m in required: push(m)
    native=sorted(pool,key=lambda m:h("native-pool",base["id"],m["id"]))
    for m in native: push(m)
    fillers=[b for b in bases if b["id"]!=base["id"] and b["domain"]==base["domain"] and b["id"] in detail]
    fillers.sort(key=lambda b:h("filler",base["id"],b["source"],b["id"]))
    for b in fillers:
        if len(memories)>=20: break
        if detail[b["id"]]["gold"]:
            m=dict(detail[b["id"]]["gold"][0]); m["kind"]="decoy"; push(m)
    if len(memories)<2: raise RuntimeError(f"insufficient runtime memories {base['id']}")
    memories=memories[:20]
    if not is_noev and not gold_ids.issubset({m["id"] for m in memories}): raise RuntimeError(f"gold dropped by budget {base['id']}")
    return {"query":base["query"],"gold_ids":sorted(gold_ids),"memories":memories,"metadata":{"base_id":base["id"],"source":base["source"],"domain":base["domain"],"primary_family":primary_family,"subject":base["subject"],"relation":base["relation"],"answerable":not is_noev}}


def load_functions()->tuple[Callable[...,Any],Callable[...,Any],dict[str,str]]:
    v2=CONTRACT["v2"]; v13=CONTRACT["v13"]; fn2=getattr(importlib.import_module(v2["module"]),v2["callable"]); fn13=getattr(importlib.import_module(v13["module"]),v13["callable"]); return fn2,fn13,CONTRACT["selected_contract"]["schema"]


def run_runtime(case:dict[str,Any],fn2:Callable[...,Any],fn13:Callable[...,Any],schema:dict[str,str])->dict[str,Any]:
    raws=[make_raw(m,schema) for m in case["memories"]]
    # No evaluator metadata may enter runtime records.
    allowed={schema["id"],schema["text"],schema["timestamp"]}
    if any(set(r)!=allowed for r in raws): raise RuntimeError("metadata firewall raw-record shape failure")
    v2out=invoke(fn2,case["query"],raws); candidates=list_like(v2out)
    if candidates is None: raise RuntimeError("Candidate-v2 output lacks candidate list")
    v2ids=ranked_ids(v2out,schema["id"]); v13out=invoke(fn13,case["query"],candidates); v13ids=ranked_ids(v13out,schema["id"])
    violations=[x for x in v13ids if x not in set(v2ids)]
    return {"v2_ids":v2ids,"v13_ids":v13ids,"candidate_source_violations":violations,"v13_canonical":canonical(v13out)}


def wilson(k:int,n:int,z:float=1.959963984540054)->tuple[float,float]:
    if n<=0: return (0.0,0.0)
    p=k/n; den=1+z*z/n; center=(p+z*z/(2*n))/den; half=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den; return max(0,center-half),min(1,center+half)


def evaluate(stage:str,execute:bool=True)->dict[str,Any]:
    raws=source_raws(); bases,loader_stats=rebuild_bases(raws); sel=select_through(stage,bases); d=details(raws); assignment=sel["assignments"]; noev=sel["no_evidence"]
    cases=[]
    for i,fam in assignment: cases.append(materialize_case(bases[i],fam,i in noev,bases,d))
    counts={"source":Counter(c["metadata"]["source"] for c in cases),"domain":Counter(c["metadata"]["domain"] for c in cases),"family":Counter(c["metadata"]["primary_family"] for c in cases),"answerable":sum(c["metadata"]["answerable"] for c in cases),"no_evidence":sum(not c["metadata"]["answerable"] for c in cases)}
    output={"schema_version":"candidate-v13-external-runtime-evaluation-v1","stage":stage,"candidate_v13_source_sha256":hashlib.sha256((SRC/"personal_state_engine/candidate_v13.py").read_bytes()).hexdigest(),"selection_digest":sel["digest"],"loader_stats":dict(sorted(loader_stats.items())),"case_counts":{"total":len(cases),"source":dict(sorted(counts["source"].items())),"domain":dict(sorted(counts["domain"].items())),"family":dict(sorted(counts["family"].items())),"answerable":counts["answerable"],"no_evidence":counts["no_evidence"]},"raw_case_payload_persisted":False}
    if not execute: output["status"]="MATERIALIZATION_VALIDATED_NO_EXECUTION"; return output
    fn2,fn13,schema=load_functions(); results=[]; source_viol=0; rank_hist=Counter(); rr_sum=0.0; answerable_n=0; recall_hits=Counter(); false_abst=0; false_retr=0; abst_correct=0; rank1=0; subject_ok=subject_n=relation_ok=relation_n=temporal_ok=temporal_n=contrad_ok=contrad_n=0; discourse_bad=discourse_n=0
    id_meta=[]
    for idx,case in enumerate(cases):
        r=run_runtime(case,fn2,fn13,schema); source_viol+=len(r["candidate_source_violations"]); ids=r["v13_ids"]; gold=set(case["gold_ids"]); meta=case["metadata"]; answerable=bool(meta["answerable"]); memory_by_id={m["id"]:m for m in case["memories"]}; rank=None
        if answerable:
            answerable_n+=1
            for pos,mid in enumerate(ids,1):
                if mid in gold: rank=pos; break
            if rank is not None: rr_sum+=1/rank; rank_hist[str(rank)]+=1
            for k in [1,3,5]: recall_hits[k]+=int(rank is not None and rank<=k)
            false_abst+=int(len(ids)==0); abst_correct+=int(len(ids)>0); rank1+=int(rank==1)
            if ids:
                top=memory_by_id.get(ids[0]); subject_n+=1; relation_n+=1; subject_ok+=int(bool(top) and top.get("subject")==meta["subject"]); relation_ok+=int(bool(top) and top.get("relation")==meta["relation"])
            if meta["primary_family"]=="N6": temporal_n+=1; temporal_ok+=int(rank==1)
            if meta["primary_family"]=="N7": contrad_n+=1; contrad_ok+=int(rank==1)
            if meta["primary_family"]=="N2": discourse_n+=1; discourse_bad+=int(rank!=1)
        else:
            false_retr+=int(len(ids)>0); abst_correct+=int(len(ids)==0)
        results.append({"rank":rank,"answerable":answerable,"ids_nonempty":bool(ids),"source":meta["source"],"domain":meta["domain"],"family":meta["primary_family"],"top1_gold":rank==1})
        id_meta.append((idx,case,r))
    total=len(cases); noev_n=total-answerable_n
    metrics={"MRR":rr_sum/max(1,answerable_n),"R@1":recall_hits[1]/max(1,answerable_n),"R@3":recall_hits[3]/max(1,answerable_n),"R@5":recall_hits[5]/max(1,answerable_n),"answerable_recall":sum(1 for x in results if x["answerable"] and x["rank"] is not None)/max(1,answerable_n),"false_abstention_rate":false_abst/max(1,answerable_n),"false_retrieval_rate":false_retr/max(1,noev_n),"abstention_accuracy":abst_correct/max(1,total),"eligible_rank1_accuracy":rank1/max(1,answerable_n),"subject_binding_accuracy":subject_ok/max(1,subject_n),"relation_binding_accuracy":relation_ok/max(1,relation_n),"temporal_scope_accuracy":temporal_ok/max(1,temporal_n),"contradiction_handling_accuracy":contrad_ok/max(1,contrad_n),"discourse_contamination_rate":discourse_bad/max(1,discourse_n)}
    ci={}
    for key,k,n in [("R@1",recall_hits[1],answerable_n),("answerable_recall",sum(1 for x in results if x["answerable"] and x["rank"] is not None),answerable_n),("abstention_accuracy",abst_correct,total),("false_retrieval_rate",false_retr,noev_n),("false_abstention_rate",false_abst,answerable_n)]: ci[key]={"low":wilson(k,n)[0],"high":wilson(k,n)[1],"method":"Wilson 95%"}
    breakdown={}
    for axis in ["source","domain","family"]:
        vals=defaultdict(list)
        for x in results: vals[x[axis]].append(x)
        breakdown[axis]={}
        for key,arr in sorted(vals.items()):
            a=[x for x in arr if x["answerable"]]; n0=[x for x in arr if not x["answerable"]]; breakdown[axis][key]={"count":len(arr),"answerable":len(a),"no_evidence":len(n0),"R@1":sum(x["rank"]==1 for x in a)/max(1,len(a)),"answerable_recall":sum(x["rank"] is not None for x in a)/max(1,len(a)),"false_retrieval_rate":sum(x["ids_nonempty"] for x in n0)/max(1,len(n0)),"false_abstention_rate":sum(not x["ids_nonempty"] for x in a)/max(1,len(a))}
    # Determinism and metadata firewall on fixed subsets. Metadata is evaluator-only;
    # mutate it while preserving query/runtime records byte-for-byte.
    det_fail=0; meta_fail=0
    for idx,case,r1 in id_meta[:64]:
        r2=run_runtime(case,fn2,fn13,schema); det_fail+=int(r1["v13_canonical"]!=r2["v13_canonical"])
    for idx,case,r1 in id_meta[:32]:
        mutated={"query":case["query"],"gold_ids":list(reversed(case["gold_ids"])),"memories":case["memories"],"metadata":{"base_id":"MUTATED","source":"MUTATED","domain":"D8","primary_family":"N12","subject":"MUTATED","relation":"MUTATED","answerable":not case["metadata"]["answerable"]}}
        r2=run_runtime(mutated,fn2,fn13,schema); meta_fail+=int(r1["v13_canonical"]!=r2["v13_canonical"])
    output.update({"status":"EXECUTED","candidate_v13_external_performance_observed":True,"metrics":metrics,"confidence_intervals":ci,"breakdown":breakdown,"integrity":{"candidate_source_violations":source_viol,"determinism_violations":det_fail,"metadata_firewall_violations":meta_fail,"determinism_cases_repeated":min(64,total),"metadata_mutation_cases":min(32,total),"candidate_source_invariant_pass":source_viol==0,"determinism_pass":det_fail==0,"metadata_firewall_pass":meta_fail==0},"rank_histogram":dict(sorted(rank_hist.items(),key=lambda kv:int(kv[0]))),"runtime_contract_schema":schema})
    return output


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--stage",choices=["ev_a","ev_b","ev_c"],required=True); ap.add_argument("--materialize-only",action="store_true"); args=ap.parse_args(); r=evaluate(args.stage,execute=not args.materialize_only); path=OUT_DIR/(f"{args.stage.replace('_','-')}-runtime.json"); path.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(path); return 0

if __name__=="__main__": raise SystemExit(main())
