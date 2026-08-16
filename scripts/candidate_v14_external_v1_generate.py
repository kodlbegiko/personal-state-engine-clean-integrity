from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

DOMAINS = ["education","health-routines","travel","shopping","technology","work-projects","food","social-context","finance","household"]
PEOPLE = ["Avery","Blake","Casey","Drew","Emery","Finley","Gray","Harper","Indigo","Jordan","Kai","Logan","Morgan","Noel","Parker","Quinn","Riley","Sage","Taylor","Winter"]
RELATIONS = {
 "education": ("course", ["marine ecology","ceramic chemistry","urban planning","medieval history","soil physics","linguistics"]),
 "health-routines": ("routine", ["evening stretch","early walk","screen-free hour","breathing practice","meal prep","swim session"]),
 "travel": ("destination", ["Tainan","Hualien","Osaka","Lisbon","Reykjavik","Chiayi"]),
 "shopping": ("purchase", ["linen notebook","mechanical keyboard","walking shoes","steel bottle","desk lamp","canvas bag"]),
 "technology": ("device", ["Framework laptop","Pixel phone","e-ink tablet","mini PC","NAS box","noise-cancelling headset"]),
 "work-projects": ("project", ["migration audit","catalog cleanup","sensor pilot","forecast dashboard","archive index","onboarding redesign"]),
 "food": ("meal", ["mushroom risotto","sesame noodles","tomato soup","grilled mackerel","vegetable curry","oat porridge"]),
 "social-context": ("contact", ["Mina","Owen","Priya","Ren","Sol","Yuki"]),
 "finance": ("budget", ["NT$1200 weekly","NT$3000 monthly","NT$500 transport","NT$800 books","NT$1500 groceries","NT$2000 travel"]),
 "household": ("chore", ["water the herbs","sort recycling","wash bedding","clean the filter","label storage","charge the vacuum"]),
}
REL_WORDS = {
 "course": ["class","subject","module"], "routine":["habit","practice","usual step"], "destination":["place","stop","destination"],
 "purchase":["item","thing bought","purchase"], "device":["machine","device","hardware"], "project":["workstream","assignment","project"],
 "meal":["dish","food","meal"], "contact":["person","contact","friend"], "budget":["spending limit","budget","cap"], "chore":["task","household job","chore"]
}
QUERY_TEMPLATES = [
 "What {rw} is {p} currently associated with?",
 "Do you remember the {rw} {p} settled on?",
 "For {p}, which {rw} is the latest one?",
 "Quick check — what's {p}'s current {rw}?",
 "I lost track: what {rw} did {p} end up with?",
 "About {p}: the {rw} now is what again?",
 "Which {rw} belongs to {p} at the moment?",
 "Remind me, where did we land on {p}'s {rw}?",
]
DISCOURSE_PREFIX = ["Unrelated: the weather changed. Anyway, ","Small tangent aside, ","I was talking about something else earlier; now ","Ignore the previous topic — ",""]


def h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def mem(mid: str, text: str, ts: str | None = None) -> dict:
    return {"id": mid, "text": text, "timestamp": ts}


def support_text(p: str, rel: str, value: str, style: int) -> str:
    if style % 4 == 0:
        return f"{p} currently has {value} recorded for the {rel}."
    if style % 4 == 1:
        return f"Latest note on {p}: the selected {rel} is {value}."
    if style % 4 == 2:
        return f"After reconsidering things, {p} ended up choosing {value} as the {rel}."
    return f"For {p}, the present {rel} entry points to {value}, replacing the earlier option."


def query_text(rng: random.Random, p: str, rel: str, naturalistic: bool) -> str:
    rw = rng.choice(REL_WORDS[rel])
    q = rng.choice(QUERY_TEMPLATES).format(p=p, rw=rw)
    if naturalistic:
        q = rng.choice(DISCOURSE_PREFIX) + q
        if rng.random() < .25:
            q = q.replace("What ", "So, what ").replace("?", " — do you recall?")
    return q


def density_count(rng: random.Random, bucket: str) -> int:
    if bucket == "low": return rng.randint(4,8)
    if bucket == "medium": return rng.randint(9,20)
    if bucket == "high": return rng.randint(21,50)
    return rng.randint(51,70)


def distractor(rng: random.Random, idx: int, target_p: str, rel: str, value: str, lure: bool=False) -> dict:
    other_p = rng.choice([x for x in PEOPLE if x != target_p])
    other_rel = rng.choice([x for x in REL_WORDS if x != rel])
    other_val = rng.choice(sum((vals for _, vals in RELATIONS.values()), []))
    if lure:
        text = f"{other_p}'s {rel} is {value}; this note is not about {target_p}."
    elif idx % 3 == 0:
        text = f"{target_p} mentioned {other_val}, but it was only background and not the {rel}."
    elif idx % 3 == 1:
        text = f"{other_p} currently has {other_val} recorded for the {rel}."
    else:
        text = f"A separate note says {target_p} discussed {other_rel}: {other_val}."
    return mem(f"m{idx:03d}", text, f"2026-0{1+(idx%8)}-{1+(idx%27):02d}T09:00:00+00:00")


def build_answerable(rng: random.Random, cid: str, domain: str, family: str, density: str, naturalistic: bool, variant: int=0) -> dict:
    rel, vals = RELATIONS[domain]
    p = rng.choice(PEOPLE)
    value = rng.choice(vals)
    q = query_text(rng, p, rel, naturalistic)
    memories = []
    relevant = []
    requires_all = False
    if family == "temporal_supersession":
        old = rng.choice([v for v in vals if v != value])
        memories += [mem("m001", f"Earlier, {p}'s {rel} was {old}.", "2026-01-03T09:00:00+00:00"), mem("m002", f"Update: {p}'s {rel} is now {value}; {old} was superseded.", "2026-07-03T09:00:00+00:00")]
        relevant=["m002"]
    elif family == "negation":
        q = f"Which {rng.choice(REL_WORDS[rel])} is explicitly ruled out for {p}?"
        memories += [mem("m001", f"{p} explicitly does not want {value} as the {rel}.", "2026-06-03T09:00:00+00:00")]
        relevant=["m001"]
    elif family == "compositional":
        bridge = rng.choice([x for x in PEOPLE if x != p])
        memories += [mem("m001", f"{p}'s current collaborator is {bridge}.", "2026-05-01T09:00:00+00:00"), mem("m002", f"{bridge}'s current {rel} is {value}.", "2026-05-02T09:00:00+00:00")]
        q = f"What {rng.choice(REL_WORDS[rel])} belongs to {p}'s current collaborator?"
        relevant=["m001","m002"]; requires_all=True
    elif family == "entity_ambiguity":
        same = p + " Lee"
        other = p + " Chen"
        memories += [mem("m001", f"{same}'s current {rel} is {value}."), mem("m002", f"{other}'s current {rel} is {rng.choice([v for v in vals if v != value])}.")]
        q = f"For {same}, what is the current {rng.choice(REL_WORDS[rel])}?"; relevant=["m001"]
    elif family == "strong_lexical_wrong_semantic":
        memories += [mem("m001", f"{rng.choice([x for x in PEOPLE if x != p])}'s {rel} is {value}. This sentence repeats {p} and {rel} but is not about {p}."), mem("m002", support_text(p, rel, value, 3))]
        relevant=["m002"]
    elif family == "relation_ambiguity":
        other_rel = rng.choice([x for x in REL_WORDS if x != rel])
        memories += [mem("m001", f"{p}'s {other_rel} entry mentions {value}."), mem("m002", support_text(p, rel, value, 2))]
        relevant=["m002"]
    elif family == "discourse_contamination":
        memories += [mem("m001", f"We talked about weather and errands. Correction: for {p}, the current {rel} is {value}. The rest is unrelated.")]
        relevant=["m001"]
    else:
        style = 2 if family in {"weak_lexical_correct_semantic","lexical_divergence","natural_variation"} else variant
        memories += [mem("m001", support_text(p, rel, value, style), "2026-06-15T09:00:00+00:00")]
        relevant=["m001"]
    target_n = density_count(rng, density)
    while len(memories) < target_n:
        i=len(memories)+1
        memories.append(distractor(rng,i,p,rel,value,lure=(family=="strong_lexical_wrong_semantic" and i%4==0)))
    rng.shuffle(memories)
    return {"id":cid,"query":q,"memories":memories,"answerable":True,"relevant_ids":relevant,"requires_all":requires_all,"domain":domain,"families":[family],"density":density,"naturalistic":naturalistic,"generation_family":["structured","conversational","adversarial","elliptical"][variant%4]}


def build_no_evidence(rng: random.Random, cid: str, domain: str, family: str, density: str, naturalistic: bool, variant: int=0) -> dict:
    rel, vals = RELATIONS[domain]; p=rng.choice(PEOPLE); value=rng.choice(vals)
    q=query_text(rng,p,rel,naturalistic); memories=[]
    if family == "contradictory_unresolved":
        memories=[mem("m001",f"One unverified note says {p}'s {rel} may be {value}."),mem("m002",f"Another note disputes that {p}'s {rel} is {value}.")]
    elif family == "wrong_relation_only":
        other_rel=rng.choice([x for x in REL_WORDS if x!=rel]); memories=[mem("m001",f"{p}'s {other_rel} entry is {value}; no {rel} is recorded.")]
    elif family == "partial_evidence":
        memories=[mem("m001",f"{p} discussed {value}, but the note does not say it was selected as the {rel}.")]
    elif family == "underspecified":
        q=f"What is the current one for {p}?"; memories=[mem("m001",f"{p} has several unrelated records and no uniquely specified relation.")]
    elif family == "out_of_memory":
        q=f"What passport number is recorded for {p}?"; memories=[mem("m001",f"{p} has routine notes, but no passport identifier is stored.")]
    else:
        memories=[mem("m001",f"{rng.choice([x for x in PEOPLE if x != p])}'s {rel} is {value}.")]
    target_n=density_count(rng,density)
    while len(memories)<target_n:
        i=len(memories)+1; memories.append(distractor(rng,i,p,rel,value,lure=(i%5==0)))
    rng.shuffle(memories)
    return {"id":cid,"query":q,"memories":memories,"answerable":False,"relevant_ids":[],"requires_all":False,"domain":domain,"families":["no_evidence",family],"density":density,"naturalistic":naturalistic,"generation_family":["structured","conversational","adversarial","elliptical"][variant%4]}


def transform_case(base: dict, kind: str, new_id: str, rng: random.Random) -> dict:
    c=json.loads(json.dumps(base)); c["id"]=new_id; c["metamorphic_kind"]=kind
    if kind=="memory_order_permutation": rng.shuffle(c["memories"])
    elif kind=="punctuation": c["query"]=c["query"].replace("?"," ?!")
    elif kind=="equivalent_framing": c["query"]="Briefly, and ignoring unrelated context: "+c["query"]
    return c


def generate(seed: str) -> tuple[list[dict], dict]:
    rng=random.Random(seed)
    cases=[]
    densities=["low","medium","high","low","medium","high","low","medium","high","extreme"]
    answer_families=["weak_lexical_correct_semantic","strong_lexical_wrong_semantic","temporal_supersession","negation","compositional","entity_ambiguity","relation_ambiguity","discourse_contamination","lexical_divergence","natural_variation"]
    no_families=["truly_absent","wrong_relation_only","partial_evidence","contradictory_unresolved","underspecified","out_of_memory"]
    # 120 counterfactual pairs / 240 answerable members.
    for pair in range(120):
        domain=DOMAINS[pair%len(DOMAINS)]; fam=answer_families[pair%len(answer_families)]; den=densities[pair%len(densities)]
        a=build_answerable(rng,f"cf-{pair:03d}-a",domain,fam,den,True,pair)
        b=json.loads(json.dumps(a)); b["id"]=f"cf-{pair:03d}-b"
        # change subject and add a true support for the new subject; old support becomes a lure
        newp=rng.choice([x for x in PEOPLE if x not in b["query"]])
        oldq=b["query"]
        oldp=next((p for p in PEOPLE if p in oldq),None)
        if oldp: b["query"]=oldq.replace(oldp,newp)
        rel,_=RELATIONS[domain]; newmid="m999"; b["memories"].append(mem(newmid,f"{newp}'s current {rel} is independently recorded in this note."))
        b["relevant_ids"]=[newmid]; b["requires_all"]=False
        for c,role in ((a,"a"),(b,"b")):
            c["counterfactual_pair_id"]=f"cf-{pair:03d}"; c["counterfactual_role"]=role; c["families"].append("counterfactual")
            cases.append(c)
    # 100 metamorphic groups / 400 members; 25 groups are no-evidence.
    for g in range(100):
        domain=DOMAINS[(240+g)%len(DOMAINS)]; den=densities[g%len(densities)]; nat=True
        if g<25: base=build_no_evidence(rng,f"mm-{g:03d}-0",domain,no_families[g%len(no_families)],den,nat,g)
        else: base=build_answerable(rng,f"mm-{g:03d}-0",domain,answer_families[g%len(answer_families)],den,nat,g)
        base["metamorphic_group_id"]=f"mm-{g:03d}"; base["metamorphic_kind"]="base"; base["families"].append("metamorphic")
        cases.append(base)
        for j,kind in enumerate(["memory_order_permutation","punctuation","equivalent_framing"],1):
            d=transform_case(base,kind,f"mm-{g:03d}-{j}",rng); d["metamorphic_group_id"]=f"mm-{g:03d}"; cases.append(d)
    # 580 standalone answerable.
    for i in range(580):
        domain=DOMAINS[(640+i)%len(DOMAINS)]; fam=answer_families[i%len(answer_families)]; den=densities[i%len(densities)]; nat=(i%4!=0)
        cases.append(build_answerable(rng,f"ans-{i:04d}",domain,fam,den,nat,i))
    # 380 standalone no-evidence.
    for i in range(380):
        domain=DOMAINS[(1220+i)%len(DOMAINS)]; fam=no_families[i%len(no_families)]; den=densities[i%len(densities)]; nat=(i%4!=0)
        cases.append(build_no_evidence(rng,f"abs-{i:04d}",domain,fam,den,nat,i))
    assert len(cases)==1600
    answer_key={c["id"]:{"answerable":c["answerable"],"relevant_ids":c["relevant_ids"],"requires_all":c["requires_all"],"domain":c["domain"],"families":c["families"],"counterfactual_pair_id":c.get("counterfactual_pair_id"),"metamorphic_group_id":c.get("metamorphic_group_id")} for c in cases}
    public=[{k:v for k,v in c.items() if k not in ("answerable","relevant_ids","requires_all")} for c in cases]
    return public,answer_key


def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--seed",required=True); ap.add_argument("--out",required=True); ns=ap.parse_args()
    out=Path(ns.out); out.mkdir(parents=True,exist_ok=True)
    public,key=generate(ns.seed)
    for shard in range(8):
        chunk=public[shard*200:(shard+1)*200]
        (out/f"protected-{shard:02d}.json").write_text(json.dumps(chunk,separators=(",",":"),ensure_ascii=False)+"\n",encoding="utf-8")
    (out/"answer-key.json").write_text(json.dumps(key,separators=(",",":"),sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"case_count":len(public),"answerable":sum(v["answerable"] for v in key.values()),"no_evidence":sum(not v["answerable"] for v in key.values())},sort_keys=True))

if __name__=="__main__": main()
