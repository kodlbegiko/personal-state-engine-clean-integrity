from __future__ import annotations

"""Pre-performance calibrated source/domain/family capacity audit.

No Candidate-v13 import/call. No natural-language payload is persisted. The
script downloads only pinned sources, builds source-native evaluator metadata in
memory, deduplicates normalized queries, and writes aggregate capacity counts.
"""

import ast
import csv
import hashlib
import io
import json
import re
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity/capacity-audit-v2.json"
ADAPTER = json.loads((ROOT / "docs/research/candidate-v13-external-validity/adapter-policy.json").read_text())
ALLOC = json.loads((ROOT / "docs/research/candidate-v13-external-validity/allocation-policy.json").read_text())
EXPECTED = {
    "personamem-v2": "95f2a8a324aab7baf2af937feae12731369e2abf7cad5ab3e170594cb25a3e52",
    "longmemeval-cleaned": "821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c",
    "locomo": "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4",
    "sgd-archive": "19da4aa3159d113a073ae1bce75ae46c290323d73e512df7d58c8e616dc776b9",
}
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_'’-]*")
COREF = {"he","she","they","them","their","his","her","hers","it","its","this","that","these","those","former","latter"}
MODAL = {"may","might","maybe","perhaps","possibly","probably","plan","planned","planning","hope","expect","intend","tentative","could","would","should"}
SGD_DOMAIN = {
    "Calendar":"D3","Events":"D3",
    "Banks":"D4","Media":"D4","Messaging":"D4","Movies":"D4","Music":"D4","Payment":"D4","Services":"D4",
    "Buses":"D5","Flights":"D5","Hotels":"D5","RentalCars":"D5","Ridesharing":"D5","Trains":"D5","Travel":"D5",
}


def norm(x: Any) -> str:
    return " ".join(str(x or "").casefold().replace("’", "'").split())


def toks(x: Any) -> list[str]:
    return [m.group(0).casefold().replace("’", "'") for m in TOKEN_RE.finditer(str(x or ""))]


def tset(x: Any) -> set[str]:
    return set(toks(x))


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent":"pse-capacity-v2/1.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def hf(repo: str, rev: str, rel: str) -> str:
    rel = "/".join(urllib.parse.quote(p, safe="") for p in rel.split("/"))
    return f"https://huggingface.co/datasets/{repo}/resolve/{rev}/{rel}?download=true"


def gh(repo: str, rev: str, rel: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{rev}/{rel}"


def guard() -> dict[str, Any]:
    tree = ast.parse(Path(__file__).read_text())
    bad_modules, bad_calls = [], []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            bad_modules += [a.name for a in n.names if "candidate_v13" in a.name]
        if isinstance(n, ast.ImportFrom) and "candidate_v13" in (n.module or ""):
            bad_modules.append(n.module or "")
        if isinstance(n, ast.Call):
            name = n.func.id if isinstance(n.func, ast.Name) else n.func.attr if isinstance(n.func, ast.Attribute) else ""
            if name in {"pse_candidate_v13_rank","evidence_support_signature_v13"}:
                bad_calls.append(name)
    return {"pass": not bad_modules and not bad_calls, "modules":sorted(set(bad_modules)), "calls":sorted(set(bad_calls))}


def phrase(hay: str, p: str) -> bool:
    h, p = norm(hay), norm(p)
    if not p: return False
    if " " in p: return p in h
    return re.search(rf"(?<![a-z0-9_]){re.escape(p)}(?![a-z0-9_])", h) is not None


def classify(hay: str, rules: dict[str,list[str]], fallback: str) -> str:
    for d in ADAPTER["domain_classifier"]["priority"]:
        if any(phrase(hay, p) for p in rules.get(d, [])):
            return d
    return fallback


def flags(query: str, subject: str, gold: list[str], temporal=False, contradiction=False, force_n11=False, force_n4=False) -> dict[str,bool]:
    q = toks(query); qs=set(q); qn=norm(query); joined=norm(" ".join([query,*gold]))
    coref = bool(qs & COREF) and (not subject or norm(subject) not in qn)
    modal = bool((qs | tset(joined)) & MODAL)
    boundaries = sum(query.count(ch) for ch in [",",";","(",")"])
    discourse = len(q) >= 18 or boundaries >= 2 or any(norm(m) in qn for m in ADAPTER["generic_discourse_markers"])
    terminal = query.rstrip().endswith("?")
    fragment = force_n11 or (len(q) <= 12 and (not terminal or bool(q and q[0] in COREF) or "..." in query or "…" in query))
    return {
        "N1": 3 <= len(q) <= 30 and terminal and not discourse and not coref and not temporal and not contradiction and not modal and not fragment,
        "N2": discourse,"N4":force_n4,"N5":coref,"N6":temporal,"N7":contradiction,"N8":modal,"N10":True,"N11":fragment,
    }


def add(bases: list[dict[str,Any]], source: str, bid: str, query: str, subject: str, relation: str, gold: list[str], domain: str, **kw: Any) -> None:
    if not norm(query) or not gold or not all(norm(x) for x in gold): return
    bases.append({"source":source,"id":bid,"query":query,"subject":subject,"relation":relation,"gold":gold,"domain":domain,"flags":flags(query,subject,gold,**kw)})


def load_persona(raw: bytes, bases: list[dict[str,Any]], stats: Counter[str]) -> None:
    rules=ADAPTER["domain_classifier"]["personamem_topic_rules"]
    for i,row in enumerate(csv.DictReader(io.StringIO(raw.decode("utf-8")))):
        stats["persona_rows"]+=1
        subject=str(row.get("persona_id", "")) or f"p{i}"
        relation=str(row.get("topic_preference","")).strip() or str(row.get("topic_query","")).strip() or "preference"
        topic=" ".join([str(row.get("topic_preference","")),str(row.get("topic_query",""))])
        prev=str(row.get("prev_pref","")).strip(); cur=str(row.get("preference","")).strip()
        temporal=bool(prev) or norm(row.get("updated")) in {"true","1","yes","y"}
        contradiction=bool(prev and cur and norm(prev)!=norm(cur))
        add(bases,"personamem-v2",f"pm:{i}",str(row.get("user_query","")),subject,relation,[str(row.get("related_conversation_snippet",""))],classify(topic,rules,"D1"),temporal=temporal,contradiction=contradiction)


def session_text(session: Any) -> str:
    if not isinstance(session,list): return ""
    out=[]
    for m in session:
        if isinstance(m,dict) and str(m.get("content","")).strip():
            out.append(f"{m.get('role','')}: {m.get('content','')}")
    return "\n".join(out)


def load_lme(raw: bytes, bases: list[dict[str,Any]], stats: Counter[str]) -> None:
    rules=ADAPTER["domain_classifier"]["strict_text_rules"]
    for i,row in enumerate(json.loads(raw)):
        stats["lme_rows"]+=1
        ids=[str(x) for x in row.get("haystack_session_ids",[])]; sessions=row.get("haystack_sessions",[])
        if len(ids)!=len(sessions): stats["lme_align_fail"]+=1; continue
        byid={sid:session_text(s) for sid,s in zip(ids,sessions)}; gids=[str(x) for x in row.get("answer_session_ids",[])]
        if not gids or any(g not in byid for g in gids): stats["lme_gold_fail"]+=1; continue
        gold=[byid[g] for g in gids]; q=str(row.get("question","")); typ=str(row.get("question_type","unknown")); qid=str(row.get("question_id",i))
        add(bases,"longmemeval-cleaned",f"lme:{qid}",q,f"lme:{qid}",typ,gold,classify(" ".join([q,*gold]),rules,"D8"),temporal=typ in {"knowledge-update","temporal-reasoning"})


def locomo_session_keys(c: dict[str,Any]) -> list[str]:
    return sorted([k for k,v in c.items() if k.startswith("session_") and not k.endswith("_date_time") and isinstance(v,list) and k.removeprefix("session_").isdigit()],key=lambda k:int(k.removeprefix("session_")))


def load_locomo(raw: bytes, bases: list[dict[str,Any]], stats: Counter[str]) -> None:
    rules=ADAPTER["domain_classifier"]["strict_text_rules"]
    for si,sample in enumerate(json.loads(raw)):
        stats["locomo_samples"]+=1
        c=sample.get("conversation",{}); qa=sample.get("qa",[]); sample_id=str(sample.get("sample_id",si)); turns={}
        if not isinstance(c,dict) or not isinstance(qa,list): continue
        for key in locomo_session_keys(c):
            for t in c[key]:
                if isinstance(t,dict) and t.get("dia_id") is not None: turns[str(t["dia_id"])]=t
        for qi,item in enumerate(qa):
            stats["locomo_qa"]+=1
            if not isinstance(item,dict): continue
            q=str(item.get("question","")).strip(); ans=str(item.get("answer","")).strip() if item.get("answer") is not None else ""
            ev=item.get("evidence"); eids=[str(x) for x in ev] if isinstance(ev,list) else ([str(ev)] if isinstance(ev,str) and ev.strip() else [])
            if not q or not ans or not eids: stats["locomo_groundtruth_missing"]+=1; continue
            if any(e not in turns for e in eids): stats["locomo_evidence_fail"]+=1; continue
            gt=[turns[e] for e in eids]; gold=[f"{t.get('speaker','')}: {t.get('text','')}" for t in gt]
            speakers="|".join(sorted({str(t.get("speaker","")) for t in gt if str(t.get("speaker",""))})) or "history"
            add(bases,"locomo",f"locomo:{sample_id}:{qi}",q,f"{sample_id}:{speakers}",f"category-{item.get('category','unknown')}",gold,classify(" ".join([q,*gold]),rules,"D8"))


def state_values(frame: dict[str,Any]) -> dict[str,set[str]]:
    state=frame.get("state"); sv=state.get("slot_values") if isinstance(state,dict) else None; out={}
    if isinstance(sv,dict):
        for slot,vals in sv.items():
            if isinstance(vals,list):
                vv={norm(v) for v in vals if norm(v)}
                if vv: out[str(slot)]=vv
    return out


def explicit_slots(frame: dict[str,Any]) -> set[str]:
    slots=frame.get("slots")
    return {str(x.get("slot")) for x in slots if isinstance(x,dict) and x.get("slot")} if isinstance(slots,list) else set()


def load_sgd(raw: bytes, bases: list[dict[str,Any]], stats: Counter[str]) -> None:
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=sorted(n for n in z.namelist() if re.search(r"/(train|dev|test)/dialogues_\d+\.json$",n))
        for name in names:
            split=next(x for x in ["train","dev","test"] if f"/{x}/" in name)
            for di,dialog in enumerate(json.loads(z.read(name))):
                stats["sgd_dialogues"]+=1
                turns=dialog.get("turns",[]) if isinstance(dialog,dict) else []; did=str(dialog.get("dialogue_id",di)) if isinstance(dialog,dict) else str(di)
                prior=defaultdict(list)
                for ti,turn in enumerate(turns):
                    if not isinstance(turn,dict) or turn.get("speaker")!="USER": continue
                    frames=turn.get("frames",[]); utt=str(turn.get("utterance","")); bydom=defaultdict(list)
                    for fr in frames if isinstance(frames,list) else []:
                        if not isinstance(fr,dict): continue
                        service=str(fr.get("service","")); dom=SGD_DOMAIN.get(service.split("_",1)[0])
                        if not dom: continue
                        sv=state_values(fr); ex=explicit_slots(fr)
                        for slot,vals in sv.items():
                            if slot in ex: continue
                            for val in vals:
                                if prior[(service,slot,val)]: bydom[dom].append((service,slot,prior[(service,slot,val)][-1]))
                    nonempty=[d for d,r in bydom.items() if r]
                    if len(nonempty)==1:
                        dom=nonempty[0]; rels={ (s,slot):(s,slot,g) for s,slot,g in bydom[dom] }; goldidx=sorted({g for _,_,g in rels.values()})
                        gold=[str(turns[g].get("utterance","")) for g in goldidx if 0<=g<len(turns) and isinstance(turns[g],dict)]
                        if gold:
                            add(bases,"sgd-carryover",f"sgd:{split}:{did}:{ti}",utt,f"sgd:{split}:{did}","|".join(sorted(f"{s}:{slot}" for s,slot,_ in rels.values())),gold,dom,force_n11=True,force_n4=len(rels)>=2)
                            stats["sgd_eligible"]+=1
                    elif len(nonempty)>1: stats["sgd_multidomain_excluded"]+=1
                    for fr in frames if isinstance(frames,list) else []:
                        if not isinstance(fr,dict): continue
                        service=str(fr.get("service","")); dom=SGD_DOMAIN.get(service.split("_",1)[0])
                        if not dom: continue
                        sv=state_values(fr)
                        for slot in explicit_slots(fr):
                            for val in sv.get(slot,set()): prior[(service,slot,val)].append(ti)


def dedup(bases: list[dict[str,Any]], stats: Counter[str]) -> list[dict[str,Any]]:
    bucket=defaultdict(list)
    for b in bases: bucket[norm(b["query"])].append(b)
    out=[]
    for q,items in bucket.items():
        if not q: continue
        items.sort(key=lambda b:hashlib.sha256(f"{b['source']}\x1f{b['id']}".encode()).hexdigest())
        out.append(items[0]); stats["normalized_query_duplicates_removed"]+=max(0,len(items)-1)
    return out


def dynamic(bases: list[dict[str,Any]]) -> None:
    bydom=defaultdict(list); psub=defaultdict(list); psr=defaultdict(list); inv=defaultdict(set); qsets=[]; gsets=[]
    for i,b in enumerate(bases):
        bydom[b["domain"]].append(i)
        if b["source"]=="personamem-v2": psub[norm(b["subject"])].append(i); psr[(norm(b["subject"]),norm(b["relation"]))].append(i)
        qs=tset(b["query"]); gs=[tset(x) for x in b["gold"]]; qsets.append(qs); gsets.append(gs)
        for g in gs:
            for tok in g:
                if len(tok)>=3: inv[(b["domain"],tok)].add(i)
    for i,b in enumerate(bases):
        b["flags"]["N3"]=any(bases[j]["subject"]!=b["subject"] for j in bydom[b["domain"]] if j!=i)
        if b["source"]=="personamem-v2":
            sub,rel=norm(b["subject"]),norm(b["relation"]); b["flags"]["N4"]=b["flags"].get("N4",False) or any(norm(bases[j]["relation"])!=rel for j in psub[sub] if j!=i); b["flags"]["N12"]=len(psr[(sub,rel)])>=2
        else: b["flags"]["N12"]=False
        qs=qsets[i]; denom=max(1,len(qs)); best=max((len(qs&g)/denom for g in gsets[i]),default=0.0); cand=set()
        for tok in qs:
            if len(tok)>=3: cand.update(inv.get((b["domain"],tok),set()))
        b["flags"]["N9"]=any(j!=i and max((len(qs&g)/denom for g in gsets[j]),default=0.0)>best for j in cand)


def required() -> tuple[Counter[str],Counter[str],Counter[str]]:
    rs,rd,rf=Counter(),Counter(),Counter()
    for st in ALLOC["allocation_order"]:
        for s,n in ALLOC["stage_source_targets"][st].items():
            if s!="total": rs[s]+=int(n)
        for d,n in ALLOC["domain_targets"][st].items(): rd[d]+=int(n)
        for f,n in ALLOC["structural_family_targets"][st].items(): rf[f]+=int(n)
    return rs,rd,rf


def main() -> int:
    OUT.parent.mkdir(parents=True,exist_ok=True); g=guard(); result={"schema_version":"capacity-audit-v2","candidate_v13_invoked":False,"formal_case_materialized":False,"individual_formal_ids_persisted":False,"guard":g}
    if not g["pass"]: result["status"]="FAIL_GUARD"; OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); return 2
    try:
        raws={
            "personamem-v2":fetch(hf("bowen-upenn/PersonaMem-v2","b7b42b78917157afed063527a1c959e98f6109f2","benchmark/text/benchmark.csv")),
            "longmemeval-cleaned":fetch(hf("xiaowu0162/longmemeval-cleaned","98d7416c24c778c2fee6e6f3006e7a073259d48f","longmemeval_oracle.json")),
            "locomo":fetch(gh("snap-research/locomo","3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376","data/locomo10.json")),
            "sgd-archive":fetch("https://github.com/google-research-datasets/dstc8-schema-guided-dialogue/archive/e852981ae34990f4358979625854259302feaa78.zip"),
        }
        hashes={k:hashlib.sha256(v).hexdigest() for k,v in raws.items()}; result["source_hashes"]=hashes
        bad={k:{"expected":EXPECTED[k],"actual":v} for k,v in hashes.items() if v!=EXPECTED[k]}
        if bad: result["status"]="FAIL_SOURCE_HASH"; result["source_hash_mismatches"]=bad; OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); return 3
        stats=Counter(); bases=[]
        load_persona(raws["personamem-v2"],bases,stats); load_lme(raws["longmemeval-cleaned"],bases,stats); load_locomo(raws["locomo"],bases,stats); load_sgd(raws["sgd-archive"],bases,stats)
        result["pre_dedup_base_count"]=len(bases); bases=dedup(bases,stats); dynamic(bases)
        sc=Counter(b["source"] for b in bases); dc=Counter(b["domain"] for b in bases); sdc=Counter((b["source"],b["domain"]) for b in bases); fc=Counter()
        for b in bases:
            for f,ok in b["flags"].items():
                if ok: fc[f]+=1
        rs,rd,rf=required(); result["loader_stats"]=dict(sorted(stats.items())); result["unique_base_count"]=len(bases)
        result["source_counts"]=dict(sorted(sc.items())); result["domain_counts"]=dict(sorted(dc.items())); result["source_domain_counts"]={f"{s}:{d}":n for (s,d),n in sorted(sdc.items())}; result["family_counts"]=dict(sorted(fc.items()))
        result["required_all_stages"]={"source":dict(sorted(rs.items())),"domain":dict(sorted(rd.items())),"family":dict(sorted(rf.items()))}
        result["shortfalls"]={
            "source":[{"source":k,"available":sc[k],"required":v,"shortfall":v-sc[k]} for k,v in sorted(rs.items()) if sc[k]<v],
            "domain":[{"domain":k,"available":dc[k],"required":v,"shortfall":v-dc[k]} for k,v in sorted(rd.items()) if dc[k]<v],
            "family":[{"family":k,"available":fc[k],"required":v,"shortfall":v-fc[k]} for k,v in sorted(rf.items()) if fc[k]<v],
        }
        result["status"]="PASS_SIMPLE_CAPACITY" if not any(result["shortfalls"].values()) else "CAPACITY_SHORTFALL"
    except Exception as e:
        result["status"]="FAIL_EXCEPTION"; result["error"]=f"{type(e).__name__}: {e}"
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return 0 if result["status"] in {"PASS_SIMPLE_CAPACITY","CAPACITY_SHORTFALL"} else 1

if __name__=="__main__": raise SystemExit(main())
