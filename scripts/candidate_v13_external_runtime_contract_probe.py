from __future__ import annotations

"""Synthetic-only runtime contract probe for Candidate-v2 -> Candidate-v13.

This probe may invoke the frozen algorithms ONLY on a fixed, project-independent
synthetic fixture used to determine callable signatures and record schema. It
must never load an external-validity corpus and must never score performance.
"""

import ast
import hashlib
import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
OUT = ROOT / "results/candidate-v13-external-validity/runtime-contract.json"
V13_PATH = SRC / "personal_state_engine/candidate_v13.py"
EXPECTED_V13_SHA256 = "b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838"

FIXTURE_QUERY = "What beverage does Rowan prefer?"
FIXTURE_TEXTS = [
    ("synthetic-m1", "Rowan prefers green tea.", "2026-01-02T12:00:00Z"),
    ("synthetic-m2", "Morgan prefers coffee.", "2026-01-01T12:00:00Z"),
    ("synthetic-m3", "Rowan owns a blue notebook.", "2026-01-03T12:00:00Z"),
]

SCHEMAS = [
    {"name":"id_text_timestamp","id":"id","text":"text","timestamp":"timestamp"},
    {"name":"memory_id_text_timestamp","id":"memory_id","text":"text","timestamp":"timestamp"},
    {"name":"id_content_timestamp","id":"id","text":"content","timestamp":"timestamp"},
    {"name":"memory_id_content_timestamp","id":"memory_id","text":"content","timestamp":"timestamp"},
    {"name":"id_text_created_at","id":"id","text":"text","timestamp":"created_at"},
    {"name":"memory_id_text_created_at","id":"memory_id","text":"text","timestamp":"created_at"},
    {"name":"id_text_updated_at","id":"id","text":"text","timestamp":"updated_at"},
    {"name":"memory_id_text_updated_at","id":"memory_id","text":"text","timestamp":"updated_at"},
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_v2() -> tuple[str, str]:
    candidates=[]
    for path in sorted((SRC / "personal_state_engine").glob("*.py")):
        try: tree=ast.parse(path.read_text(encoding="utf-8"))
        except Exception: continue
        for node in tree.body:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and "candidate_v2" in node.name.casefold():
                candidates.append((path,node.name))
    exact=[x for x in candidates if x[1]=="pse_candidate_v2_rank"]
    path,name=(exact or candidates)[0]
    return f"personal_state_engine.{path.stem}",name


def get_v13() -> tuple[str,str]:
    module="personal_state_engine.candidate_v13"; mod=importlib.import_module(module)
    if hasattr(mod,"pse_candidate_v13_rank"): return module,"pse_candidate_v13_rank"
    names=[n for n,v in vars(mod).items() if callable(v) and "candidate_v13" in n.casefold()]
    if not names: raise RuntimeError("Candidate-v13 callable not found")
    return module,sorted(names)[0]


def invoke(fn: Callable[...,Any], query: str, records: list[dict[str,Any]]) -> Any:
    sig=inspect.signature(fn); kwargs={}; args=[]
    for p in sig.parameters.values():
        n=p.name.casefold()
        if n in {"query","user_query","question","original_query","runtime_query"} or "query" in n:
            value=query
        elif any(tok in n for tok in ["candidate","record","memory","memories","items"]):
            value=records
        elif n in {"k","top_k","limit","n"}:
            value=len(records)
        elif any(tok in n for tok in ["now","current_time","reference_time"]):
            value="2026-01-04T12:00:00Z"
        elif p.default is not inspect._empty:
            continue
        else:
            raise TypeError(f"unmapped required parameter: {p.name}")
        if p.kind in {p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD}:
            args.append(value)
        elif p.kind==p.KEYWORD_ONLY:
            kwargs[p.name]=value
        else:
            raise TypeError(f"unsupported parameter kind for {p.name}: {p.kind}")
    return fn(*args,**kwargs)


def list_like(value: Any) -> list[Any] | None:
    if isinstance(value,list): return value
    if isinstance(value,tuple):
        for item in value:
            if isinstance(item,list): return item
    if isinstance(value,dict):
        for key in ["candidates","ranked_candidates","results","items","records"]:
            if isinstance(value.get(key),list): return value[key]
    for key in ["candidates","ranked_candidates","results","items","records"]:
        item=getattr(value,key,None)
        if isinstance(item,list): return item
    return None


def shape(value: Any) -> dict[str,Any]:
    out={"type":type(value).__name__}
    lst=list_like(value)
    if lst is not None:
        out["list_length"]=len(lst)
        if lst:
            item=lst[0]
            out["item_type"]=type(item).__name__
            if isinstance(item,dict): out["item_keys"]=sorted(map(str,item.keys()))
            elif hasattr(item,"__dict__"): out["item_attributes"]=sorted(map(str,vars(item).keys()))
    elif isinstance(value,dict): out["keys"]=sorted(map(str,value.keys()))
    elif hasattr(value,"__dict__"): out["attributes"]=sorted(map(str,vars(value).keys()))
    return out


def make_records(schema: dict[str,str]) -> list[dict[str,Any]]:
    records=[]
    for mid,text,ts in FIXTURE_TEXTS:
        records.append({schema["id"]:mid,schema["text"]:text,schema["timestamp"]:ts})
    return records


def main() -> int:
    OUT.parent.mkdir(parents=True,exist_ok=True)
    actual=sha256(V13_PATH)
    result={
        "schema_version":"candidate-v13-external-runtime-contract-v1",
        "fixture_only":True,
        "external_corpus_loaded":False,
        "candidate_v13_external_performance_observed":False,
        "candidate_v13_synthetic_contract_probe_invoked":False,
        "candidate_v13_source_sha256":actual,
        "candidate_v13_source_hash_match":actual==EXPECTED_V13_SHA256,
        "attempts":[],
    }
    if actual!=EXPECTED_V13_SHA256:
        result["status"]="FAIL_FROZEN_HASH"; OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); return 2
    try:
        v2_module,v2_name=find_v2(); v13_module,v13_name=get_v13(); v2= getattr(importlib.import_module(v2_module),v2_name); v13=getattr(importlib.import_module(v13_module),v13_name)
        result["v2"]={"module":v2_module,"callable":v2_name,"signature":str(inspect.signature(v2))}
        result["v13"]={"module":v13_module,"callable":v13_name,"signature":str(inspect.signature(v13))}
        success=None
        for schema in SCHEMAS:
            attempt={"schema":schema["name"]}
            try:
                raw=make_records(schema); v2out=invoke(v2,FIXTURE_QUERY,raw); attempt["v2_output_shape"]=shape(v2out); candidates=list_like(v2out)
                if candidates is None: raise TypeError("Candidate-v2 output contains no list-like candidate set")
                v13out=invoke(v13,FIXTURE_QUERY,candidates); result["candidate_v13_synthetic_contract_probe_invoked"]=True; attempt["v13_output_shape"]=shape(v13out); attempt["status"]="PASS"; success={"schema":schema,"v2_output_shape":shape(v2out),"v13_output_shape":shape(v13out)}; result["attempts"].append(attempt); break
            except Exception as exc:
                attempt["status"]="FAIL"; attempt["error_type"]=type(exc).__name__; attempt["error_message_prefix"]=str(exc)[:300]; result["attempts"].append(attempt)
        if success is None:
            result["status"]="FAIL_NO_COMPATIBLE_SCHEMA"
        else:
            result["status"]="PASS"; result["selected_contract"]=success
    except Exception as exc:
        result["status"]="FAIL_EXCEPTION"; result["error_type"]=type(exc).__name__; result["error_message_prefix"]=str(exc)[:500]
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return 0 if result["status"]=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
