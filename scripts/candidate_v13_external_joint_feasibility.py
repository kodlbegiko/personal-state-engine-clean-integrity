from __future__ import annotations

"""Joint pre-performance feasibility proof for Candidate-v13 external validity.

This script MUST NOT import or invoke Candidate-v13. It materializes source
records only ephemerally in the GitHub Actions workspace, solves exact source,
domain, and structural-family allocation constraints for EV-A/B/C, and persists
only aggregate matrices, stress proportions, and SHA256 digests of selected base
IDs. No formal natural-language payload or individual EV-B/EV-C IDs are saved.
"""

import ast
import csv
import hashlib
import importlib.util
import io
import json
import re
import sys
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/candidate-v13-external-validity/joint-feasibility.json"
BASE_PATH = ROOT / "scripts/candidate_v13_external_capacity_audit_v2.py"
ADAPTER_PATH = ROOT / "docs/research/candidate-v13-external-validity/adapter-policy-v3.json"
ALLOC_PATH = ROOT / "docs/research/candidate-v13-external-validity/allocation-policy-v4.json"
ALGO_PATH = ROOT / "docs/research/candidate-v13-external-validity/feasibility-algorithm-v1.json"
STRESS_PATH = ROOT / "docs/research/candidate-v13-external-validity/stress-policy-v1.json"
QUAL_PATH = ROOT / "results/candidate-v13-external-validity/evermembench-dynamic-qualification.json"

ADAPTER = json.loads(ADAPTER_PATH.read_text())
ALLOC = json.loads(ALLOC_PATH.read_text())
ALGO = json.loads(ALGO_PATH.read_text())
STRESS = json.loads(STRESS_PATH.read_text())
QUAL = json.loads(QUAL_PATH.read_text())

spec = importlib.util.spec_from_file_location("capacity_base", BASE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("capacity base module unavailable")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)

FAMILIES = [f"N{i}" for i in range(1, 13)]
DOMAINS = [f"D{i}" for i in range(1, 9)]
SOURCES = ["personamem-v2", "locomo", "sgd-carryover", "longmemeval-cleaned", "evermembench-dynamic"]
COREF = {"he","she","they","them","their","his","her","hers","it","its","this","that","these","those","former","latter"}
MODAL = {"may","might","maybe","perhaps","possibly","probably","plan","planned","planning","hope","expect","intend","tentative","could","would","should"}


def h(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(str(x) for x in parts).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    q = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            q.update(block)
    return q.hexdigest()


def norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().replace("’", "'").split())


def tokens(value: Any) -> list[str]:
    return base.toks(value)


def tset(value: Any) -> set[str]:
    return set(tokens(value))


def candidate_guard() -> dict[str, Any]:
    tree = ast.parse(Path(__file__).read_text())
    modules: list[str] = []
    calls: list[str] = []
    forbidden = {"pse_candidate_v13_rank", "evidence_support_signature_v13"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names if "candidate_v13" in alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "candidate_v13" in module:
                modules.append(module)
        elif isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            if name in forbidden:
                calls.append(name)
    return {"pass": not modules and not calls, "forbidden_modules": sorted(set(modules)), "forbidden_calls": sorted(set(calls))}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "pse-joint-feasibility/1.0"})
    with urllib.request.urlopen(req, timeout=300) as response:
        return response.read()


def hf_url(repo: str, revision: str, rel: str) -> str:
    quoted = "/".join(urllib.parse.quote(part, safe="") for part in rel.split("/"))
    return f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{quoted}?download=true"


def strict_phrase(hay: str, phrase: str) -> bool:
    hn, pn = norm(hay), norm(phrase)
    if not pn:
        return False
    if " " in pn:
        return pn in hn
    return re.search(rf"(?<![a-z0-9_]){re.escape(pn)}(?![a-z0-9_])", hn) is not None


def strict_domain(hay: str, fallback: str) -> str:
    rules = ADAPTER["strict_text_domain_rules"]
    for domain in ["D3","D4","D5","D6","D7","D2","D8","D1"]:
        if any(strict_phrase(hay, p) for p in rules.get(domain, [])):
            return domain
    return fallback


def add_base(bases: list[dict[str, Any]], *, source: str, base_id: str, query: str, subject: str, relation: str, gold: list[str], domain: str, temporal: bool=False, contradiction: bool=False, force_n11: bool=False, force_n4: bool=False) -> None:
    if source not in SOURCES or domain not in DOMAINS or not norm(query) or not gold or not all(norm(x) for x in gold):
        return
    q = tokens(query)
    qs = set(q)
    qn = norm(query)
    joined = norm(" ".join([query, *gold]))
    coref = bool(qs & COREF) and (not subject or norm(subject) not in qn)
    modality = bool((qs | tset(joined)) & MODAL)
    boundaries = sum(query.count(ch) for ch in [",", ";", "(", ")"])
    discourse = len(q) >= 18 or boundaries >= 2 or any(norm(m) in qn for m in ADAPTER.get("generic_discourse_markers", ["by the way","actually","anyway","for context","i mean","one more thing","quick question"]))
    terminal_q = query.rstrip().endswith("?")
    fragment = force_n11 or (len(q) <= 12 and (not terminal_q or bool(q and q[0] in COREF) or "..." in query or "…" in query))
    flags = {
        "N1": source != "sgd-carryover" and len(gold) == 1 and 3 <= len(q) <= 30 and terminal_q and not discourse and not coref and not temporal and not contradiction and not modality and not fragment,
        "N2": discourse,
        "N4": force_n4,
        "N5": coref,
        "N6": temporal,
        "N7": contradiction,
        "N8": modality,
        "N10": True,
        "N11": fragment,
    }
    bases.append({
        "source": source,
        "id": base_id,
        "query": query,
        "query_norm": norm(query),
        "subject": subject,
        "relation": relation or "unknown",
        "gold": gold,
        "domain": domain,
        "flags": flags,
        "multi_clause": boundaries >= 2,
        "implicit_relation": source == "sgd-carryover",
    })


def load_personamem(raw: bytes, bases: list[dict[str, Any]], stats: Counter[str]) -> None:
    rules = {
      "D3": ["schedule","calendar","appointment","meeting","reservation","booking","deadline"],
      "D4": ["subscription","banking","bank","insurance","billing","payment","streaming","internet service","utility","phone plan","financial service"],
      "D5": ["travel","trip","flight","airline","airport","hotel","vacation","destination","transportation","rental car"],
      "D6": ["technology","tech","device","computer","laptop","phone","smartphone","tablet","software","app","camera","browser"],
      "D7": ["project","membership","club","organization","community","research","certification","volunteer","initiative"],
      "D2": ["work","job","career","employer","occupation","professional","education","school","college","university","study"],
      "D8": ["routine","exercise","fitness","workout","sleep","daily habit","weekly habit","practice","wellness"],
      "D1": ["preference","favorite","favourite","food","music","hobby","hobbies","sport","sports","style","taste"]
    }
    def topic_domain(text: str) -> str:
        for d in ["D3","D4","D5","D6","D7","D2","D8","D1"]:
            if any(strict_phrase(text,p) for p in rules[d]): return d
        return "D1"
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    for i, row in enumerate(reader):
        stats["personamem_rows"] += 1
        subject = str(row.get("persona_id", "")) or f"persona:{i}"
        relation = str(row.get("topic_preference", "")).strip() or str(row.get("topic_query", "")).strip() or "preference"
        topic_text = " ".join([str(row.get("topic_preference", "")), str(row.get("topic_query", ""))])
        prev, cur = str(row.get("prev_pref", "")).strip(), str(row.get("preference", "")).strip()
        temporal = bool(prev) or norm(row.get("updated")) in {"true","1","yes","y"}
        contradiction = bool(prev and cur and norm(prev) != norm(cur))
        add_base(bases, source="personamem-v2", base_id=f"pm:{i}", query=str(row.get("user_query", "")), subject=subject, relation=relation, gold=[str(row.get("related_conversation_snippet", ""))], domain=topic_domain(topic_text), temporal=temporal, contradiction=contradiction)


def session_text(session: Any) -> str:
    if not isinstance(session, list): return ""
    parts = []
    for message in session:
        if isinstance(message, dict):
            content = str(message.get("content", "")).strip()
            if content:
                parts.append(f"{message.get('role','')}: {content}")
    return "\n".join(parts)


def load_lme(raw: bytes, bases: list[dict[str, Any]], stats: Counter[str]) -> None:
    for i, row in enumerate(json.loads(raw)):
        stats["lme_rows"] += 1
        ids = [str(x) for x in row.get("haystack_session_ids", [])]
        sessions = row.get("haystack_sessions", [])
        if len(ids) != len(sessions):
            stats["lme_alignment_failure"] += 1; continue
        byid = {sid: session_text(s) for sid, s in zip(ids, sessions)}
        gold_ids = [str(x) for x in row.get("answer_session_ids", [])]
        if not gold_ids or any(g not in byid for g in gold_ids):
            stats["lme_gold_failure"] += 1; continue
        gold = [byid[g] for g in gold_ids]
        q = str(row.get("question", "")); typ = str(row.get("question_type", "unknown")); qid = str(row.get("question_id", i))
        add_base(bases, source="longmemeval-cleaned", base_id=f"lme:{qid}", query=q, subject=f"lme:{qid}", relation=typ, gold=gold, domain=strict_domain(" ".join([q,*gold]), "D8"), temporal=typ in {"knowledge-update","temporal-reasoning"})


def locomo_session_keys(c: dict[str, Any]) -> list[str]:
    return sorted([k for k,v in c.items() if k.startswith("session_") and not k.endswith("_date_time") and isinstance(v,list) and k.removeprefix("session_").isdigit()], key=lambda k:int(k.removeprefix("session_")))


def load_locomo(raw: bytes, bases: list[dict[str, Any]], stats: Counter[str]) -> None:
    for si, sample in enumerate(json.loads(raw)):
        stats["locomo_samples"] += 1
        if not isinstance(sample, dict): continue
        c, qa = sample.get("conversation"), sample.get("qa")
        if not isinstance(c, dict) or not isinstance(qa, list): continue
        sid = str(sample.get("sample_id", si)); turns = {}
        for key in locomo_session_keys(c):
            for turn in c.get(key, []):
                if isinstance(turn, dict) and turn.get("dia_id") is not None:
                    turns[str(turn["dia_id"])] = turn
        for qi, item in enumerate(qa):
            stats["locomo_qa"] += 1
            if not isinstance(item, dict): continue
            q = str(item.get("question", "")).strip(); a = str(item.get("answer", "")).strip() if item.get("answer") is not None else ""
            ev = item.get("evidence"); eids = [str(x) for x in ev] if isinstance(ev, list) else ([str(ev)] if isinstance(ev, str) and ev.strip() else [])
            if not q or not a or not eids or any(e not in turns for e in eids):
                stats["locomo_excluded"] += 1; continue
            gt = [turns[e] for e in eids]
            gold = [f"{t.get('speaker','')}: {t.get('text','')}" for t in gt]
            speakers = "|".join(sorted({str(t.get("speaker", "")) for t in gt if str(t.get("speaker", ""))})) or f"sample:{sid}"
            add_base(bases, source="locomo", base_id=f"locomo:{sid}:{qi}", query=q, subject=f"{sid}:{speakers}", relation=f"category-{item.get('category','unknown')}", gold=gold, domain=strict_domain(" ".join([q,*gold]), "D8"))


def state_values(frame: dict[str, Any]) -> dict[str, set[str]]:
    state = frame.get("state"); sv = state.get("slot_values") if isinstance(state, dict) else None; out = {}
    if isinstance(sv, dict):
        for slot, vals in sv.items():
            if isinstance(vals, list):
                vv = {norm(v) for v in vals if norm(v)}
                if vv: out[str(slot)] = vv
    return out


def explicit_slots(frame: dict[str, Any]) -> set[str]:
    slots = frame.get("slots")
    return {str(x.get("slot")) for x in slots if isinstance(x, dict) and x.get("slot")} if isinstance(slots, list) else set()


def load_sgd(raw: bytes, bases: list[dict[str, Any]], stats: Counter[str]) -> None:
    domain_map = {}
    for d, prefixes in ADAPTER["sources"]["sgd-carryover"]["domain_map"].items():
        for p in prefixes: domain_map[p] = d
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = sorted(n for n in zf.namelist() if re.search(r"/(train|dev|test)/dialogues_\d+\.json$", n))
        for name in names:
            split = next(x for x in ["train","dev","test"] if f"/{x}/" in name)
            for di, dialog in enumerate(json.loads(zf.read(name))):
                stats["sgd_dialogues"] += 1
                if not isinstance(dialog, dict): continue
                did = str(dialog.get("dialogue_id", di)); turns = dialog.get("turns", []); prior = defaultdict(list)
                if not isinstance(turns, list): continue
                for ti, turn in enumerate(turns):
                    if not isinstance(turn, dict) or turn.get("speaker") != "USER": continue
                    frames = turn.get("frames", []); utt = str(turn.get("utterance", "")); by_domain = defaultdict(list)
                    for fr in frames if isinstance(frames, list) else []:
                        if not isinstance(fr, dict): continue
                        service = str(fr.get("service", "")); domain = domain_map.get(service.split("_",1)[0])
                        if not domain: continue
                        sv, ex = state_values(fr), explicit_slots(fr)
                        for slot, vals in sv.items():
                            if slot in ex: continue
                            for val in vals:
                                if prior[(service,slot,val)]: by_domain[domain].append((service,slot,prior[(service,slot,val)][-1]))
                    active = [d for d, rels in by_domain.items() if rels]
                    if len(active) == 1:
                        domain = active[0]
                        relmap = {(s,slot):(s,slot,g) for s,slot,g in by_domain[domain]}
                        gold_idx = sorted({g for _,_,g in relmap.values()})
                        gold = [str(turns[g].get("utterance", "")) for g in gold_idx if 0 <= g < len(turns) and isinstance(turns[g], dict)]
                        if gold:
                            holder: list[dict[str, Any]] = []
                            add_base(holder, source="sgd-carryover", base_id=f"sgd:{split}:{did}:{ti}", query=utt, subject=f"sgd:{split}:{did}", relation="|".join(sorted(f"{s}:{slot}" for s,slot,_ in relmap.values())), gold=gold, domain=domain, force_n11=True, force_n4=len(relmap)>=2)
                            if holder: buckets[domain].append(holder[0])
                    for fr in frames if isinstance(frames, list) else []:
                        if not isinstance(fr, dict): continue
                        service = str(fr.get("service", "")); domain = domain_map.get(service.split("_",1)[0])
                        if not domain: continue
                        sv = state_values(fr)
                        for slot in explicit_slots(fr):
                            for val in sv.get(slot, set()): prior[(service,slot,val)].append(ti)
    for domain, items in sorted(buckets.items()):
        items.sort(key=lambda b:h("sgd-feasibility-reservoir",domain,b["id"]))
        stats[f"sgd_{domain}_full"] = len(items)
        bases.extend(items[:6000])
        stats[f"sgd_{domain}_kept"] = min(len(items),6000)


def ever_message_text(msg: dict[str, Any]) -> str:
    speaker = ""
    for k in ["sender_name","sender","speaker","name","role","author"]:
        if isinstance(msg.get(k), str) and msg.get(k).strip(): speaker = msg[k].strip(); break
    text = ""
    for k in ["content","text","message","body","msg","utterance"]:
        if isinstance(msg.get(k), str) and msg.get(k).strip(): text = msg[k].strip(); break
    return f"{speaker}: {text}" if speaker and text else text


def expand_indices(value: Any) -> set[str]:
    out=set()
    if value is None: return out
    for chunk in str(value).split(","):
        chunk=chunk.strip()
        if re.fullmatch(r"\d+",chunk): out.add(str(int(chunk))); continue
        m=re.fullmatch(r"(\d+)\s*-\s*(\d+)",chunk)
        if m:
            lo,hi=int(m.group(1)),int(m.group(2))
            if hi>=lo and hi-lo<=1000: out.update(str(x) for x in range(lo,hi+1))
    return out


def iter_qars(raw: Any) -> Iterable[tuple[str, dict[str, Any]]]:
    if isinstance(raw, dict):
        for t, value in raw.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict): yield str(t).upper(), item
            elif isinstance(value, dict):
                for child in value.values():
                    if isinstance(child, list):
                        for item in child:
                            if isinstance(item, dict): yield str(t).upper(), item
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict): yield str(item.get("topic_id", "")).upper(), item


def load_evermem(qraw: bytes, draw: bytes, bases: list[dict[str, Any]], stats: Counter[str]) -> None:
    qars, dialogues = json.loads(qraw), json.loads(draw)
    index: dict[tuple[str,str,str,str], str] = {}
    for row in dialogues if isinstance(dialogues, list) else []:
        if not isinstance(row, dict): continue
        t=str(row.get("topic_id","")).upper(); date=str(row.get("date", ""))[:10]; groups=row.get("dialogues")
        if not t or not date or not isinstance(groups, dict): continue
        for group, messages in groups.items():
            if not isinstance(messages,list): continue
            for msg in messages:
                if not isinstance(msg,dict): continue
                idx=msg.get("msg_index",msg.get("message_index"))
                if idx is None: continue
                text=ever_message_text(msg)
                if text: index[(t,date,str(group),str(int(idx)) if str(idx).isdigit() else str(idx))]=text
    for qi,(t,item) in enumerate(iter_qars(qars)):
        stats["ever_qars"] += 1
        q=str(item.get("Q", "")).strip(); a=str(item.get("A", "")).strip(); refs=item.get("R") if isinstance(item.get("R"),list) else []
        if not q or not a or not refs or t not in {"T1","T2","T3","T4","T5"}: stats["ever_excluded"]+=1; continue
        keys=[]; ok=True
        for ref in refs:
            if not isinstance(ref,dict): ok=False; break
            rt=str(ref.get("topic_id",t)).upper() or t; date=str(ref.get("date", ""))[:10]; group=str(ref.get("group", "")); requested=expand_indices(ref.get("message_index",ref.get("msg_index")))
            if not date or not group or not requested: ok=False; break
            for idx in sorted(requested,key=lambda x:int(x) if x.isdigit() else x):
                key=(rt,date,group,idx)
                if key not in index: ok=False; break
                keys.append(key)
            if not ok: break
        if not ok or not keys: stats["ever_unresolved"]+=1; continue
        gold=[index[k] for k in keys]
        domain="D6" if t=="T1" else "D7"
        group_subject="|".join(sorted({k[2] for k in keys}))
        add_base(bases, source="evermembench-dynamic", base_id=f"ever:{t}:{qi}", query=q, subject=f"ever:{t}:{group_subject}", relation=t, gold=gold, domain=domain)
        stats[f"ever_{domain}_eligible"]+=1


def global_dedup(bases: list[dict[str, Any]], stats: Counter[str]) -> list[dict[str, Any]]:
    grouped=defaultdict(list)
    for b in bases: grouped[b["query_norm"]].append(b)
    out=[]
    for q,items in grouped.items():
        if not q: continue
        items.sort(key=lambda b:h(b["source"],b["id"]))
        out.append(items[0]); stats["normalized_query_duplicates_removed"]+=max(0,len(items)-1)
    return out


def dynamic_families(bases: list[dict[str, Any]]) -> None:
    by_domain=defaultdict(list); persona_subject=defaultdict(list); persona_sr=defaultdict(list); qsets=[]; gsets=[]
    for i,b in enumerate(bases):
        by_domain[b["domain"]].append(i)
        if b["source"]=="personamem-v2":
            persona_subject[norm(b["subject"])].append(i); persona_sr[(norm(b["subject"]),norm(b["relation"]))].append(i)
        qsets.append(tset(b["query"])); gsets.append([tset(x) for x in b["gold"]])
    for i,b in enumerate(bases):
        b["flags"]["N3"]=any(bases[j]["subject"]!=b["subject"] for j in by_domain[b["domain"]] if j!=i)
        if b["source"]=="personamem-v2":
            s,r=norm(b["subject"]),norm(b["relation"])
            b["flags"]["N4"]=b["flags"].get("N4",False) or any(norm(bases[j]["relation"])!=r for j in persona_subject[s] if j!=i)
            b["flags"]["N12"]=len(persona_sr[(s,r)])>=2
        else:
            b["flags"]["N12"]=False
        b["flags"]["N9"]=False
    for domain in DOMAINS:
        ids=list(by_domain[domain]); ids.sort(key=lambda i:h("n9-feasibility-reservoir",domain,bases[i]["source"],bases[i]["id"])); ids=ids[:1600]
        for i in ids:
            qs=qsets[i]; denom=max(1,len(qs)); best=max((len(qs&g)/denom for g in gsets[i]),default=0.0)
            for j in ids:
                if j==i: continue
                score=max((len(qs&g)/denom for g in gsets[j]),default=0.0)
                if score>best: b=bases[i]; b["flags"]["N9"]=True; break


def stress_count(b: dict[str, Any]) -> int:
    return sum(1 for key in ["N3","N4","N5","N6","N7","N9","N11"] if b["flags"].get(key)) + int(b.get("multi_clause",False)) + int(b.get("implicit_relation",False))


@dataclass
class Edge:
    to: int
    rev: int
    cap: int
    orig: int


class Dinic:
    def __init__(self,n:int): self.g=[[] for _ in range(n)]
    def add(self,u:int,v:int,c:int)->Edge:
        a=Edge(v,len(self.g[v]),c,c); b=Edge(u,len(self.g[u]),0,0); self.g[u].append(a); self.g[v].append(b); return a
    def flow(self,s:int,t:int)->int:
        total=0; n=len(self.g)
        while True:
            level=[-1]*n; level[s]=0; q=deque([s])
            while q:
                u=q.popleft()
                for e in self.g[u]:
                    if e.cap>0 and level[e.to]<0: level[e.to]=level[u]+1; q.append(e.to)
            if level[t]<0: return total
            it=[0]*n
            def dfs(u:int,f:int)->int:
                if u==t: return f
                while it[u]<len(self.g[u]):
                    e=self.g[u][it[u]]
                    if e.cap>0 and level[u]+1==level[e.to]:
                        got=dfs(e.to,min(f,e.cap))
                        if got: e.cap-=got; self.g[e.to][e.rev].cap+=got; return got
                    it[u]+=1
                return 0
            while True:
                f=dfs(s,10**9)
                if not f: break
                total+=f


def transport(stage:str, remaining:list[int], bases:list[dict[str,Any]], variant:int) -> tuple[bool,dict[tuple[str,str],int]]:
    avail=Counter((bases[i]["source"],bases[i]["domain"]) for i in remaining)
    source_targets={k:int(v) for k,v in ALLOC["stage_source_targets"][stage].items() if k!="total"}
    domain_targets={k:int(v) for k,v in ALLOC["domain_targets"][stage].items()}
    src_nodes={s:i+1 for i,s in enumerate(SOURCES)}; dom_nodes={d:1+len(SOURCES)+i for i,d in enumerate(DOMAINS)}; sink=1+len(SOURCES)+len(DOMAINS); din=Dinic(sink+1); root=0
    for s in SOURCES: din.add(root,src_nodes[s],source_targets[s])
    for d in DOMAINS: din.add(dom_nodes[d],sink,domain_targets[d])
    refs={}
    pairs=[(s,d) for s in SOURCES for d in DOMAINS if avail[(s,d)]>0]
    pairs.sort(key=lambda sd:h("transport",stage,variant,sd[0],sd[1]))
    for s,d in pairs: refs[(s,d)]=din.add(src_nodes[s],dom_nodes[d],avail[(s,d)])
    got=din.flow(root,sink); total=int(ALLOC["stage_source_targets"][stage]["total"])
    matrix={(s,d):e.orig-e.cap for (s,d),e in refs.items() if e.orig-e.cap>0}
    return got==total,matrix


def family_match(stage:str, remaining:list[int], bases:list[dict[str,Any]], matrix:dict[tuple[str,str],int]) -> tuple[bool,list[tuple[int,str]]]:
    cells=[cell for cell,q in sorted(matrix.items()) if q>0]
    fam_targets={f:int(ALLOC["structural_family_targets"][stage][f]) for f in FAMILIES}
    cell_cases=defaultdict(list)
    for i in remaining:
        cell=(bases[i]["source"],bases[i]["domain"])
        if cell in matrix: cell_cases[cell].append(i)
    for cell,ids in cell_cases.items():
        if stage=="ev_b": ids.sort(key=lambda i:(stress_count(bases[i]),h("family",stage,bases[i]["id"])))
        elif stage=="ev_c": ids.sort(key=lambda i:(-stress_count(bases[i]),h("family",stage,bases[i]["id"])))
        else: ids.sort(key=lambda i:h("family",stage,bases[i]["id"]))
    root=0; next_node=1; cell_nodes={}
    for c in cells: cell_nodes[c]=next_node; next_node+=1
    case_nodes={}
    candidate_ids=sorted({i for c in cells for i in cell_cases[c]},key=lambda i:h("case-node",stage,bases[i]["id"]))
    for i in candidate_ids: case_nodes[i]=next_node; next_node+=1
    fam_nodes={}
    for f in FAMILIES: fam_nodes[f]=next_node; next_node+=1
    sink=next_node; din=Dinic(sink+1)
    for c in cells: din.add(root,cell_nodes[c],matrix[c])
    for c in cells:
        for i in cell_cases[c]: din.add(cell_nodes[c],case_nodes[i],1)
    assignment_edges={}
    for i in candidate_ids:
        eligible=[f for f in FAMILIES if bases[i]["flags"].get(f,False)]
        for f in eligible: assignment_edges[(i,f)]=din.add(case_nodes[i],fam_nodes[f],1)
    for f in FAMILIES: din.add(fam_nodes[f],sink,fam_targets[f])
    total=int(ALLOC["stage_source_targets"][stage]["total"]); got=din.flow(root,sink)
    if got!=total: return False,[]
    assignments=[]
    for (i,f),e in assignment_edges.items():
        if e.orig-e.cap==1: assignments.append((i,f))
    if len(assignments)!=total: return False,[]
    return True,assignments


def no_evidence(stage:str, assignments:list[tuple[int,str]], bases:list[dict[str,Any]]) -> set[int]:
    target=int(ALLOC["answerability_targets"][stage]["no_evidence"]); chosen={i for i,f in assignments if f=="N10"}
    extra=[i for i,f in assignments if f!="N10"]; extra.sort(key=lambda i:h("no-evidence",stage,bases[i]["id"]))
    chosen.update(extra[:max(0,target-len(chosen))]); return chosen


def stage_metrics(stage:str, assignments:list[tuple[int,str]], noev:set[int], bases:list[dict[str,Any]]) -> dict[str,Any]:
    ids=[i for i,_ in assignments]; source=Counter(bases[i]["source"] for i in ids); domain=Counter(bases[i]["domain"] for i in ids); family=Counter(f for _,f in assignments)
    dims={}; n=len(ids)
    for dim in STRESS["dimensions"]:
        count=0
        for i in ids:
            b=bases[i]
            if dim in b["flags"]: ok=bool(b["flags"].get(dim))
            elif dim=="multi_clause": ok=bool(b.get("multi_clause"))
            elif dim=="implicit_relation": ok=bool(b.get("implicit_relation"))
            elif dim=="no_evidence_ambiguity": ok=i in noev and any(b["flags"].get(x,False) for x in ["N3","N9","N11"])
            else: ok=False
            count+=int(ok)
        dims[dim]={"count":count,"proportion":count/n if n else 0.0}
    digest=hashlib.sha256("\n".join(sorted(bases[i]["id"] for i in ids)).encode()).hexdigest()
    return {"selected":n,"source_counts":dict(sorted(source.items())),"domain_counts":dict(sorted(domain.items())),"primary_family_counts":dict(sorted(family.items())),"answerable":n-len(noev),"no_evidence":len(noev),"stress":dims,"selected_base_id_digest":digest}


def main()->int:
    OUT.parent.mkdir(parents=True,exist_ok=True); result={"schema_version":"candidate-v13-external-joint-feasibility-v1","candidate_v13_invoked":False,"formal_case_materialized":False,"individual_formal_ids_persisted":False,"guard":candidate_guard(),"policy_sha256":{"adapter":sha256_file(ADAPTER_PATH),"allocation":sha256_file(ALLOC_PATH),"algorithm":sha256_file(ALGO_PATH),"stress":sha256_file(STRESS_PATH),"qualification":sha256_file(QUAL_PATH)}}
    if not result["guard"]["pass"]: result["status"]="FAIL_GUARD"; OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); return 2
    try:
        pm=fetch(hf_url("bowen-upenn/PersonaMem-v2","b7b42b78917157afed063527a1c959e98f6109f2","benchmark/text/benchmark.csv")); lme=fetch(hf_url("xiaowu0162/longmemeval-cleaned","98d7416c24c778c2fee6e6f3006e7a073259d48f","longmemeval_oracle.json")); loc=fetch("https://raw.githubusercontent.com/snap-research/locomo/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/data/locomo10.json"); sgd=fetch("https://github.com/google-research-datasets/dstc8-schema-guided-dialogue/archive/e852981ae34990f4358979625854259302feaa78.zip")
        erev=str(QUAL["revision"]); qraw=fetch(hf_url("EverMind-AI/EverMemBench-Dynamic",erev,"EverMemBench_QAR.json")); draw=fetch(hf_url("EverMind-AI/EverMemBench-Dynamic",erev,"EverMemBench_Dialogues.json"))
        stats=Counter(); bases=[]; load_personamem(pm,bases,stats); load_lme(lme,bases,stats); load_locomo(loc,bases,stats); load_sgd(sgd,bases,stats); load_evermem(qraw,draw,bases,stats)
        result["pre_dedup_base_count"]=len(bases); bases=global_dedup(bases,stats); dynamic_families(bases); result["unique_base_count"]=len(bases); result["loader_stats"]=dict(sorted(stats.items()))
        result["capacity"]={"source":dict(sorted(Counter(b["source"] for b in bases).items())),"domain":dict(sorted(Counter(b["domain"] for b in bases).items())),"family":dict(sorted(Counter(f for b in bases for f in FAMILIES if b["flags"].get(f,False)).items()))}
        used=set(); stage_results={}; assignments_by_stage={}; noev_by_stage={}; reserve_before_ev_c=None
        all_indices=list(range(len(bases)))
        for stage in ALLOC["stage_order"]:
            remaining=[i for i in all_indices if i not in used]
            if stage=="ev_c": reserve_before_ev_c=remaining[:]
            solved=False
            for variant in range(int(ALGO["transport_variants"]["count"])):
                ok,matrix=transport(stage,remaining,bases,variant)
                if not ok: continue
                fm,assignments=family_match(stage,remaining,bases,matrix)
                if not fm: continue
                noev=no_evidence(stage,assignments,bases)
                metrics=stage_metrics(stage,assignments,noev,bases); metrics["transport_variant"]=variant; metrics["source_domain_matrix"]={f"{s}:{d}":n for (s,d),n in sorted(matrix.items()) if n>0}
                stage_results[stage]=metrics; assignments_by_stage[stage]=assignments; noev_by_stage[stage]=noev; used.update(i for i,_ in assignments); solved=True; break
            if not solved:
                result["status"]="JOINT_FEASIBILITY_FAIL"; result["failed_stage"]=stage; result["stages"]=stage_results; OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); return 0
        # Stress gate after all three ephemeral selections.
        bstress=stage_results["ev_b"]["stress"]; cstress=stage_results["ev_c"]["stress"]; reserve=reserve_before_ev_c or []
        stress_gate={}; testable_pass=0; testable_total=0; saturated_fail=[]; testable_fail=[]
        for dim in STRESS["dimensions"]:
            bp=float(bstress[dim]["proportion"]); cp=float(cstress[dim]["proportion"])
            eligible_reserve=0
            for i in reserve:
                b=bases[i]
                if dim in b["flags"]: ok=bool(b["flags"].get(dim))
                elif dim=="multi_clause": ok=bool(b.get("multi_clause"))
                elif dim=="implicit_relation": ok=bool(b.get("implicit_relation"))
                elif dim=="no_evidence_ambiguity": ok=any(b["flags"].get(x,False) for x in ["N3","N9","N11"])
                else: ok=False
                eligible_reserve+=int(ok)
            if eligible_reserve<100: cls="insufficient_reserve_not_testable"; passed=True
            elif bp>0.98: cls="saturated_not_testable"; passed=cp+1e-12>=bp; saturated_fail += ([] if passed else [dim])
            else: cls="testable"; testable_total+=1; passed=cp-bp>=0.01-1e-12; testable_pass+=int(passed); testable_fail += ([] if passed else [dim])
            stress_gate[dim]={"classification":cls,"eligible_ev_c_reserve":eligible_reserve,"ev_b_proportion":bp,"ev_c_proportion":cp,"delta":cp-bp,"pass":passed}
        stress_success=testable_total>=int(STRESS["minimum_testable_dimensions"]) and not testable_fail and not saturated_fail
        result["stages"]=stage_results; result["stress_gate"]={"minimum_testable_dimensions":int(STRESS["minimum_testable_dimensions"]),"testable_dimensions":testable_total,"testable_passed":testable_pass,"testable_failures":testable_fail,"saturated_failures":saturated_fail,"dimensions":stress_gate,"pass":stress_success}
        result["global_selected_base_id_digest"]=hashlib.sha256("\n".join(sorted(bases[i]["id"] for i in used)).encode()).hexdigest(); result["all_stage_selected_count"]=len(used)
        result["status"]="JOINT_FEASIBILITY_PASS" if stress_success else "JOINT_FEASIBILITY_STRESS_FAIL"
    except Exception as exc:
        result["status"]="FAIL_EXCEPTION"; result["error"]=f"{type(exc).__name__}: {exc}"
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return 0 if result["status"] in {"JOINT_FEASIBILITY_PASS","JOINT_FEASIBILITY_FAIL","JOINT_FEASIBILITY_STRESS_FAIL"} else 1

if __name__=="__main__": raise SystemExit(main())
