from __future__ import annotations

import hashlib
import json
import random
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments" / "benchmarks" / "candidate-v7-protected-validation-v1.json"
LOCK = ROOT / "experiments" / "benchmarks" / "candidate-v7-protected-validation-lock-v1.json"
EVALUATOR = ROOT / "scripts" / "evaluate_candidate_v7_protected.py"
PROTOCOL = ROOT / "experiments" / "protocols" / "candidate-v7-protected-validation-v1.json"
SOURCE = ROOT / "src" / "personal_state_engine" / "candidate_v7.py"
CONFIG = ROOT / "experiments" / "configs" / "candidate-v7-v1.json"
SEED = 20260814
EXPECTED_SOURCE = "c9bc8a5cf70cca5e2f97240bb427d1ad1cd8d60d14af922a4e634ec9c870bdae"
EXPECTED_CONFIG = "7acc9a99938efa0d361791191960a60cf8a88b6a2ec022d60f54da3df29b7e62"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mem(mid: str, text: str, day: int = 12) -> dict:
    return {"id": mid, "text": text, "timestamp": f"2026-08-{day:02d}T09:15:00+00:00"}


def decoys(prefix: str) -> list[dict]:
    return [
        mem(prefix + "-d1", "Agenda item: revisit an unrelated planning topic."),
        mem(prefix + "-d2", "No confirmed answer is recorded for the unrelated note."),
        mem(prefix + "-d3", "What should the group discuss at the next session?"),
        mem(prefix + "-d4", "This unrelated matter remains unresolved."),
    ]


def answerable_case(i: int) -> dict:
    names = ["Asha","Benicio","Celeste","Dae","Emina","Felix","Greta","Haruto","Ines","Jamil","Keiko","Lior","Maren","Nabil","Oona","Petra","Rafi","Selene","Tomas","Uma","Veda","Wren","Xenia","Yusuf","Zora"]
    cities = ["Reykjavik","Busan","Porto","Edinburgh","Sapporo","Ljubljana","Valencia","Brno","Kaohsiung","Ghent"]
    drinks = ["oolong tea","sparkling water","chicory coffee","pear soda","mint tea","barley tea","cocoa","lemon tonic","rooibos","apple cider"]
    jobs = ["cartographer","paramedic","translator","geologist","curator","auditor","physiotherapist","planner","technician","ecologist"]
    pets = ["whippet","calico cat","cockatiel","ferret","shiba inu","lop rabbit","canary","border collie","iguana","samoyed"]
    activities = ["rowing","woodcarving","salsa dancing","archery","calligraphy","kayaking","origami","fencing","stargazing","weaving"]
    languages = ["Finnish","Korean","Catalan","Estonian","Welsh","Slovene","Turkish","Czech","Tagalog","Dutch"]
    universities = ["Northbridge University","Seaside Institute","Orchid University","Riverton College","Cedar State University","Harbor Polytechnic","Summit University","Westgate College","Aurora Institute","Stonefield University"]
    courses = ["marine ecology","discrete mathematics","ceramic design","urban hydrology","phonetics","planetary science","bioethics","materials chemistry","digital cartography","comparative literature"]
    devices = ["Framework Laptop 16","Surface Laptop 7","ThinkPad T14","MacBook Pro","Zenbook S","EliteBook 1040","Yoga Pro 9","Gram Pro","Spectre x360","Latitude 7450"]
    goals = ["a 10K road race","a B2 language exam","a public recital","a climbing certification","a first-aid qualification","a portfolio review","a cycling brevet","a cooking assessment","a diving certificate","a research poster"]
    buses = ["41A","208","Blue 6","73X","N12","502","Green 9","311","K4","88"]
    colors = ["saffron yellow","forest green","midnight blue","brick red","lavender","charcoal gray","coral orange","ivory","teal","plum"]
    clubs = ["robotics club","birding society","debate team","film club","astronomy society","rowing club","chess circle","makers guild","history society","choir"]
    music = ["modal jazz","baroque chamber music","synthwave","Afrobeat","ambient folk","bossa nova","post-rock","minimal piano","bluegrass","city pop"]
    meds = ["cetirizine","melatonin","iron tablets","vitamin D","magnesium","loratadine","ibuprofen","electrolyte tablets","calcium","B12"]
    names2 = ["Noor","Mateo","Elif","Sora","Anika","Ruben","Mina","Theo","Lena","Omar"]
    name = names[i % len(names)]
    j = i % 10
    mode = i % 24
    rid = f"CV7PROT-A-{i:03d}-rel"
    if mode == 0:
        q, text = f"Which beverage does {name} consistently choose?", f"{name} consistently prefers {drinks[j]} during afternoon breaks."
    elif mode == 1:
        q, text = f"Where does {name} currently live?", f"Following a relocation, {name} now lives in {cities[j]}."
    elif mode == 2:
        q, text = f"What job does {name} have?", f"{name} works as a {jobs[j]} for the municipal service."
    elif mode == 3:
        q, text = f"When is {name}'s planning meeting?", f"The meeting was rescheduled and is now on {['Monday','Tuesday','Wednesday','Thursday','Friday'][j%5]} afternoon for {name}."
    elif mode == 4:
        q, text = f"What pet does {name} have?", f"{name} adopted a {pets[j]} last spring."
    elif mode == 5:
        q, text = f"What activity does {name} practice?", f"{name} practices {activities[j]} every weekend."
    elif mode == 6:
        q, text = f"Which city will {name} visit?", f"For the upcoming trip, {name} will visit {cities[j]} in October."
    elif mode == 7:
        q, text = f"What is {name}'s current project status?", f"Correction: {name}'s project status is now confirmed."
    elif mode == 8:
        q, text = f"What language does {name} speak?", f"{name} speaks {languages[j]} fluently with family."
    elif mode == 9:
        q, text = f"Which university does {name} attend?", f"{name} studies at {universities[j]}."
    elif mode == 10:
        q, text = f"What course is {name} taking?", f"{name} is enrolled in {courses[j]} this term."
    elif mode == 11:
        q, text = f"What music does {name} listen to?", f"{name} listens to {music[j]} while commuting."
    elif mode == 12:
        q, text = f"What medication does {name} take?", f"{name} takes {meds[j]} after breakfast."
    elif mode == 13:
        q, text = f"What laptop does {name} use?", f"{name} uses a {devices[j]} for daily work."
    elif mode == 14:
        q, text = f"What goal is {name} training toward?", f"{name} is training toward {goals[j]} this season."
    elif mode == 15:
        q, text = f"Which bus does {name} ride?", f"{name} rides bus {buses[j]} to the office."
    elif mode == 16:
        q, text = f"Who is {name} married to?", f"{name} is married to {names2[j]}."
    elif mode == 17:
        q, text = f"What color is {name}'s backpack?", f"{name}'s backpack is {colors[j]}."
    elif mode == 18:
        q, text = f"Which club did {name} join?", f"{name} joined the {clubs[j]} this year."
    elif mode == 19:
        q, text = "What drink do I usually choose?", f"I always choose {drinks[j]} after training."
    elif mode == 20:
        q, text = f"Where does {name} currently live?", f"After finishing a lease and moving north, {name} now lives in {cities[j]} and commutes by rail."
    elif mode == 21:
        q, text = f"What version is {name}'s notebook running?", f"{name}'s notebook is running OrionOS {7 + (j%3)}.{j}."
    elif mode == 22:
        q, text = f"What is {name}'s current project status?", f"The older note is superseded; {name}'s project status is now active."
    else:
        q, text = f"Which beverage does {name} currently prefer?", f"{name} switched preferences and now prefers {drinks[j]}."
    memories = [mem(rid, text, 13)] + decoys(f"CV7PROT-A-{i:03d}")
    random.Random(SEED + i).shuffle(memories)
    return {"id": f"CV7PROT-A-{i:03d}", "query": q, "memories": memories, "relevant_memory_ids": [rid], "designation": "PROTECTED_VALIDATION"}


def negative_case(i: int) -> dict:
    names = ["Asha","Benicio","Celeste","Dae","Emina","Felix","Greta","Haruto","Ines","Jamil","Keiko","Lior","Maren","Nabil","Oona","Petra","Rafi","Selene","Tomas","Uma","Veda","Wren","Xenia","Yusuf","Zora"]
    other = ["Ivo","Maya","Nora","Pia","Rex","Sana","Uri","Vera","Yara","Zane"]
    name = names[i % len(names)]
    j = i % 10
    mode = i % 12
    if mode == 0:
        q, texts = f"Which beverage does {name} consistently choose?", [f"{other[j]} consistently prefers mint tea."]
    elif mode == 1:
        q, texts = f"What course is {name} taking?", [f"{name} lives near Northbridge University."]
    elif mode == 2:
        q, texts = f"What laptop does {name} use?", [f"What laptop does {name} use?"]
    elif mode == 3:
        q, texts = f"Who is {name} married to?", [f"Agenda item: discuss whether {name} is married."]
    elif mode == 4:
        q, texts = f"What music does {name} listen to?", [f"We discussed the query about {name}'s music preference."]
    elif mode == 5:
        q, texts = f"What medication does {name} take?", [f"No confirmed information about {name}'s medication is available."]
    elif mode == 6:
        q, texts = f"What goal is {name} training toward?", [f"{name} might train for a qualification, but the target remains unresolved."]
    elif mode == 7:
        q, texts = f"What is {name}'s current project status?", [f"Records conflict about {name}'s project status; the values cannot be reconciled."]
    elif mode == 8:
        q, texts = f"Where does {name} currently live?", [f"{name} used to live in Porto but no longer lives there."]
    elif mode == 9:
        q, texts = f"What color is {name}'s backpack?", [f"Wrong answer record: {name}'s backpack is teal."]
    elif mode == 10:
        q, texts = f"Which club did {name} join?", [f"Query copy decoy: which club did {name} join? Ignore this record."]
    else:
        q, texts = f"Which bus does {name} ride?", [f"{name}'s bus route is unknown."]
    memories = [mem(f"CV7PROT-N-{i:03d}-x", texts[0])] + decoys(f"CV7PROT-N-{i:03d}")
    random.Random(SEED + 1000 + i).shuffle(memories)
    return {"id": f"CV7PROT-N-{i:03d}", "query": q, "memories": memories, "relevant_memory_ids": [], "designation": "PROTECTED_VALIDATION"}


def main() -> None:
    if OUT.exists() or LOCK.exists():
        raise SystemExit("protected materialization refused: benchmark/lock already exists")
    if sha(SOURCE) != EXPECTED_SOURCE or sha(CONFIG) != EXPECTED_CONFIG:
        raise SystemExit("protected materialization refused: frozen candidate identity changed")
    protocol = json.loads(PROTOCOL.read_text())
    if protocol.get("status") != "PREREGISTERED_AFTER_CANDIDATE_FREEZE_BEFORE_PROTECTED_MATERIALIZATION":
        raise SystemExit("protected materialization refused: protocol not preregistered")

    cases = [answerable_case(i) for i in range(70)] + [negative_case(i) for i in range(50)]
    payload = {
        "schema_version": "candidate-v7-protected-validation-v1",
        "name": "candidate-v7-protected-validation-v1",
        "designation": "PROTECTED_VALIDATION",
        "seed": SEED,
        "namespace": "CV7PROT-",
        "case_count": 120,
        "answerable_count": 70,
        "no_evidence_count": 50,
        "candidate_frozen_before_materialization": True,
        "candidate_source_sha256": EXPECTED_SOURCE,
        "cases": cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    generator_sha = sha(Path(__file__))
    evaluator_sha = sha(EVALUATOR)
    dataset_sha = sha(OUT)
    lock = {
        "schema_version": "candidate-v7-protected-validation-lock-v1",
        "status": "FROZEN_BEFORE_FORMAL_EXECUTION",
        "materialization_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "seed": SEED,
        "case_count": 120,
        "answerable_count": 70,
        "no_evidence_count": 50,
        "schema": "candidate-v7-protected-validation-v1",
        "dataset_sha256": dataset_sha,
        "generator_path": "scripts/materialize_candidate_v7_protected.py",
        "generator_sha256": generator_sha,
        "evaluator_path": "scripts/evaluate_candidate_v7_protected.py",
        "evaluator_sha256": evaluator_sha,
        "candidate_source_sha256": EXPECTED_SOURCE,
        "config_sha256": EXPECTED_CONFIG,
        "formal_execution_count_before_run": 0,
        "formal_execution_allowed_count": 1,
        "post_result_editing": False,
        "rerun": False,
    }
    LOCK.write_text(json.dumps(lock, indent=2) + "\n")
    print(json.dumps({"dataset_sha256": dataset_sha, "generator_sha256": generator_sha, "evaluator_sha256": evaluator_sha, "status": lock["status"]}, indent=2))


if __name__ == "__main__":
    main()
