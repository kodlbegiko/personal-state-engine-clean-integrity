from __future__ import annotations

"""Pre-performance contamination firewall for Candidate-v13 external validity.

No Candidate-v13 import/call. External text and historical benchmark strings are
held in memory only. Output is aggregate counts plus a digest of any contaminated
base IDs; no natural-language payload or individual IDs are persisted.
"""

import ast
import csv
import hashlib
import importlib.util
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"results/candidate-v13-external-validity/contamination-audit.json"
JOINT=ROOT/"scripts/candidate_v13_external_joint_feasibility.py"
POLICY=ROOT/"docs/research/candidate-v13-external-validity/contamination-policy-v1.json"

spec=importlib.util.spec_from_file_location("joint_for_contamination",JOINT)
if spec is None or spec.loader is None: raise RuntimeError("joint feasibility module unavailable")
joint=importlib.util.module_from_spec(spec); sys.modules[spec.name]=joint; spec.loader.exec_module(joint)

FUNCTION_WORDS={"a","an","the","is","are","was","were","be","been","being","do","does","did","have","has","had","can","could","will","would","shall","should","may","might","must","to","of","in","on","at","for","from","with","about","by","as","and","or","but","if","then","than","that","this","these","those","what","which","who","whom","whose","where","when","why","how","i","you","he","she","it","we","they","me","him","her","us","them","my","your","his","its","our","their"}
NS_RE=re.compile(r"(?:candidate[-_ ]?v\d+|gate[-_ ]?[a-z]|protected(?:[-_ ]?(?:set|case|benchmark))?|confirmatory(?:[-_ ]?(?:set|case|benchmark))?|final[-_ ]?(?:gate|set|case|benchmark)|(?:entity|value|subject|relation)[-_]?\d+)",re.I)
TOKEN_RE=re.compile(r"[A-Za-z0-9][A-Za-z0-9_'’-]*")


def norm(x:Any)->str: return " ".join(str(x or "").casefold().replace("’","'").split())
def toks(x:Any)->list[str]: return [m.group(0).casefold().replace("’","'") for m in TOKEN_RE.finditer(str(x or ""))]
def ngrams(x:Any,n:int=12)->list[tuple[str,...]]:
    t=toks(x); return [tuple(t[i:i+n]) for i in range(max(0,len(t)-n+1))]
def skeleton(x:Any)->str:
    out=[]
    for t in toks(x):
        if t.isdigit(): out.append("<NUM>")
        elif t in FUNCTION_WORDS: out.append(t)
        else: out.append("<CONTENT>")
    return " ".join(out)


def strings_from_json(v:Any)->Iterable[str]:
    if isinstance(v,str):
        if v.strip(): yield v
    elif isinstance(v,dict):
        for k,val in v.items():
            if isinstance(k,str) and k.strip(): yield k
            yield from strings_from_json(val)
    elif isinstance(v,list):
        for item in v: yield from strings_from_json(item)


def historical_strings()->list[str]:
    out=[]; exts={".json",".jsonl",".csv",".py",".md",".txt",".yaml",".yml"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in exts: continue
        rel=path.relative_to(ROOT).as_posix()
        if rel.startswith(".git/") or "candidate-v13-external-validity" in rel: continue
        if path.stat().st_size>8_000_000: continue
        try:
            text=path.read_text(encoding="utf-8",errors="ignore")
            if path.suffix.casefold()==".json":
                out.extend(strings_from_json(json.loads(text)))
            elif path.suffix.casefold()==".jsonl":
                for line in text.splitlines():
                    try: out.extend(strings_from_json(json.loads(line)))
                    except Exception: pass
            elif path.suffix.casefold()==".csv":
                for row in csv.reader(io.StringIO(text)):
                    out.extend(cell for cell in row if cell.strip())
            elif path.suffix.casefold()==".py":
                try:
                    tree=ast.parse(text)
                    out.extend(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.strip())
                except Exception: pass
            else:
                out.extend(line.strip() for line in text.splitlines() if line.strip())
        except Exception:
            continue
    return out


def build_bases()->tuple[list[dict[str,Any]],Counter[str]]:
    pm=joint.fetch(joint.hf_url("bowen-upenn/PersonaMem-v2","b7b42b78917157afed063527a1c959e98f6109f2","benchmark/text/benchmark.csv")); lme=joint.fetch(joint.hf_url("xiaowu0162/longmemeval-cleaned","98d7416c24c778c2fee6e6f3006e7a073259d48f","longmemeval_oracle.json")); loc=joint.fetch("https://raw.githubusercontent.com/snap-research/locomo/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/data/locomo10.json"); sgd=joint.fetch("https://github.com/google-research-datasets/dstc8-schema-guided-dialogue/archive/e852981ae34990f4358979625854259302feaa78.zip"); erev=str(joint.QUAL["revision"]); qraw=joint.fetch(joint.hf_url("EverMind-AI/EverMemBench-Dynamic",erev,"EverMemBench_QAR.json")); draw=joint.fetch(joint.hf_url("EverMind-AI/EverMemBench-Dynamic",erev,"EverMemBench_Dialogues.json"))
    stats=Counter(); bases=[]; joint.load_personamem(pm,bases,stats); joint.load_lme(lme,bases,stats); joint.load_locomo(loc,bases,stats); joint.load_sgd(sgd,bases,stats); joint.load_evermem(qraw,draw,bases,stats); bases=joint.global_dedup(bases,stats); return bases,stats


def main()->int:
    OUT.parent.mkdir(parents=True,exist_ok=True)
    result={"schema_version":"candidate-v13-external-contamination-audit-v1","candidate_v13_invoked":False,"formal_case_materialized":False,"policy_sha256":hashlib.sha256(POLICY.read_bytes()).hexdigest()}
    try:
        hist=historical_strings(); exact=set(s.strip() for s in hist if s.strip()); normalized=set(norm(s) for s in hist if norm(s)); gramset=set(); skset=set()
        for s in hist:
            gs=ngrams(s)
            if gs: gramset.update(gs)
            sk=skeleton(s)
            if sk: skset.add(sk)
        bases,stats=build_bases(); overlap=Counter(); source=Counter(); domain=Counter(); contaminated=[]; qsk=0; msk=0
        for b in bases:
            material=False
            texts=[("query",b["query"]),*(("memory",g) for g in b["gold"])]
            for kind,text in texts:
                stripped=str(text).strip(); nn=norm(text); gs=ngrams(text); cov=(sum(1 for g in gs if g in gramset)/len(gs)) if gs else 0.0
                if stripped in exact: overlap[f"{kind}_exact"]+=1; material=True
                if nn and nn in normalized: overlap[f"{kind}_normalized"]+=1; material=True
                if len(gs)>=2 and cov>=0.80: overlap[f"{kind}_ngram_material"]+=1; material=True
                if NS_RE.search(str(text)): overlap[f"{kind}_synthetic_namespace"]+=1; material=True
                sk=skeleton(text)
                if sk and sk in skset:
                    if kind=="query": qsk+=1
                    else: msk+=1
            if material:
                contaminated.append(b["id"]); source[b["source"]]+=1; domain[b["domain"]]+=1
        digest=hashlib.sha256("\n".join(sorted(contaminated)).encode()).hexdigest()
        result.update({"status":"PASS_NO_MATERIAL_CONTAMINATION" if not contaminated else "MATERIAL_CONTAMINATION_FOUND","historical_string_fingerprint_count":len(hist),"historical_normalized_unique_count":len(normalized),"historical_12gram_unique_count":len(gramset),"eligible_external_base_count":len(bases),"loader_stats":dict(sorted(stats.items())),"material_contaminated_base_count":len(contaminated),"material_contaminated_base_id_digest":digest,"material_overlap_type_counts":dict(sorted(overlap.items())),"contaminated_source_counts":dict(sorted(source.items())),"contaminated_domain_counts":dict(sorted(domain.items())),"diagnostic_query_skeleton_overlap_count":qsk,"diagnostic_memory_skeleton_overlap_count":msk})
    except Exception as exc:
        result["status"]="FAIL_EXCEPTION"; result["error"]=f"{type(exc).__name__}: {exc}"
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return 0 if result["status"] in {"PASS_NO_MATERIAL_CONTAMINATION","MATERIAL_CONTAMINATION_FOUND"} else 1

if __name__=="__main__": raise SystemExit(main())
