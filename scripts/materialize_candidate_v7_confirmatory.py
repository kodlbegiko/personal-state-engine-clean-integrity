from __future__ import annotations

import hashlib
import json
import random
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments" / "benchmarks" / "candidate-v7-confirmatory-v1.json"
LOCK = ROOT / "experiments" / "benchmarks" / "candidate-v7-confirmatory-lock-v1.json"
EVALUATOR = ROOT / "scripts" / "evaluate_candidate_v7_confirmatory.py"
PROTOCOL = ROOT / "experiments" / "protocols" / "candidate-v7-confirmatory-v1.json"
SOURCE = ROOT / "src" / "personal_state_engine" / "candidate_v7.py"
CONFIG = ROOT / "experiments" / "configs" / "candidate-v7-v1.json"
EXPECTED_SOURCE = "c9bc8a5cf70cca5e2f97240bb427d1ad1cd8d60d14af922a4e634ec9c870bdae"
EXPECTED_CONFIG = "7acc9a99938efa0d361791191960a60cf8a88b6a2ec022d60f54da3df29b7e62"
SEED = 20260815


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mem(mid: str, text: str, day: int = 14) -> dict:
    return {"id": mid, "text": text, "timestamp": f"2026-09-{day:02d}T11:40:00+00:00"}


def noise(prefix: str) -> list[dict]:
    return [
        mem(prefix + "-n1", "The team penciled in a future discussion about an unrelated administrative item."),
        mem(prefix + "-n2", "No verified value was entered for the unrelated field."),
        mem(prefix + "-n3", "Could someone clarify the separate planning question later?"),
        mem(prefix + "-n4", "A tentative note about another topic is still unresolved."),
        mem(prefix + "-n5", "This unrelated decoy record should not be used as an answer."),
    ]


def make_answerable(i: int) -> dict:
    people = ["Adele","Boris","Chandra","Diego","Elowen","Faris","Gianna","Hugo","Ilse","Joon","Katia","Lars","Mei","Navid","Opal","Piero","Romy","Sven","Thalia","Umit","Viola","Wade","Yuna","Zahir","Clio","Damon","Eira","Fynn","Gala","Hector"]
    towns = ["Malmo","Kanazawa","Granada","Aarhus","Lyon","Tainan","Bologna","Graz","Quebec City","Fukuoka"]
    drinks = ["genmaicha","lime seltzer","flat white","hibiscus tea","ginger ale","cold brew","chamomile tea","grape soda","espresso tonic","soy latte"]
    roles = ["urban forester","radiographer","museum registrar","survey technician","speech therapist","lab coordinator","policy researcher","sound engineer","horticulturist","data steward"]
    pets = ["basenji","ragdoll cat","budgerigar","mini rex rabbit","akita","goldfish","dachshund","leopard gecko","maine coon","papillon"]
    hobbies = ["linocut printing","dragon boat paddling","glassblowing","folk dancing","trail cycling","bookbinding","indoor climbing","embroidery","table tennis","astrophotography"]
    langs = ["Norwegian","Japanese","Spanish","Danish","French","Mandarin","Italian","German","French","Japanese"]
    schools = ["Maple Coast University","Redwood Technical College","Juniper Institute","Bluewater University","Silver Hill College","Crescent Polytechnic","Pinecrest University","East Harbor College","Meadow Institute","Granite State College"]
    courses = ["soil microbiology","graph theory","sound design","renewable energy systems","syntax","environmental law","organic spectroscopy","museum studies","hydraulic modeling","visual anthropology"]
    media = ["bebop jazz","Nordic folk","trip-hop","classical guitar","electro swing","dream pop","soul","chamber opera","lo-fi hip-hop","flamenco"]
    devices = ["ThinkPad P14s","MacBook Air","Surface Pro","Framework Laptop 13","Zenbook 14","Latitude 7350","Yoga Slim 7","EliteBook 845","Gram 16","Spectre 14"]
    goals = ["a sprint triathlon","a C1 language exam","a pottery exhibition","a wilderness first-aid certificate","a 100-km cycling event","a piano grade exam","a design portfolio review","a rescue-diver certificate","a half-marathon","a conference talk"]
    transit = ["tram 5","bus 119","metro line C","route 26","express 8","tram 2","bus 615","line M3","route 44","metro line A"]
    partners = ["Rina","Mateo","Lea","Oskar","Nadia","Timo","Sara","Emil","Aya","Ravi"]
    colors = ["ochre","sage green","indigo","rust orange","pearl white","slate gray","crimson","seafoam","mustard","aubergine"]
    clubs = ["geology society","community orchestra","canoe club","language exchange","makers collective","volunteer garden group","photography circle","public-speaking club","historical society","badminton club"]
    statuses = ["approved","active","paused","ready","closed","scheduled","confirmed","archived","open","completed"]
    person, j, mode = people[i % len(people)], i % 10, i % 22
    rid = f"CV7CONF-A-{i:03d}-rel"
    if mode == 0:
        q, text = f"What drink does {person} reach for most often?", f"During breaks, {person} usually chooses {drinks[j]} without hesitation."
    elif mode == 1:
        q, text = f"Where does {person} live now?", f"Since changing apartments, {person} now lives in {towns[j]}."
    elif mode == 2:
        q, text = f"What kind of work does {person} do?", f"{person} works as an {roles[j]} in the regional office."
    elif mode == 3:
        q, text = f"What pet does {person} own?", f"At home, {person} has a {pets[j]} named Moss."
    elif mode == 4:
        q, text = f"What hobby does {person} practice?", f"Most Saturdays, {person} practices {hobbies[j]}."
    elif mode == 5:
        q, text = f"Which language can {person} speak?", f"{person} speaks {langs[j]} comfortably in everyday conversation."
    elif mode == 6:
        q, text = f"Which university or college does {person} attend?", f"{person} studies at {schools[j]} this academic year."
    elif mode == 7:
        q, text = f"What class is {person} enrolled in?", f"This semester {person} is enrolled in {courses[j]}."
    elif mode == 8:
        q, text = f"What music does {person} listen to?", f"On the commute, {person} listens to {media[j]} most days."
    elif mode == 9:
        q, text = f"What computer does {person} use?", f"For daily tasks, {person} uses a {devices[j]}."
    elif mode == 10:
        q, text = f"What goal is {person} preparing for?", f"{person} is training toward {goals[j]} this year."
    elif mode == 11:
        q, text = f"Which public transport does {person} take?", f"{person} rides {transit[j]} to work each weekday."
    elif mode == 12:
        q, text = f"Who is {person} married to?", f"{person} is married to {partners[j]}."
    elif mode == 13:
        q, text = f"What color is {person}'s travel bag?", f"{person}'s travel bag is {colors[j]}."
    elif mode == 14:
        q, text = f"Which club is {person} a member of?", f"Earlier this year, {person} joined the {clubs[j]}."
    elif mode == 15:
        q, text = f"What is {person}'s current application status?", f"A correction was filed: {person}'s application status is now {statuses[j]}."
    elif mode == 16:
        q, text = "What beverage do I tend to order after work?", f"I almost always order {drinks[j]} after work."
    elif mode == 17:
        q, text = f"Where does {person} currently live?", f"The previous address is obsolete; after relocating, {person} now lives in {towns[j]}."
    elif mode == 18:
        q, text = f"What version is {person}'s tablet using?", f"{person}'s tablet is running NovaOS {4 + j % 4}.{j}."
    elif mode == 19:
        q, text = f"What is {person}'s favorite drink these days?", f"The preference changed recently, and {person} now prefers {drinks[j]}."
    elif mode == 20:
        q, text = f"What activity does {person} enjoy?", f"Although the week is busy, {person} makes time for {hobbies[j]} and really enjoys it."
    else:
        q, text = f"When is {person}'s recurring check-in?", f"The check-in was rescheduled; {person} now meets on {['Monday','Tuesday','Wednesday','Thursday','Friday'][j%5]} morning."
    memories = [mem(rid, text, 15)] + noise(f"CV7CONF-A-{i:03d}")
    random.Random(SEED + i).shuffle(memories)
    return {"id": f"CV7CONF-A-{i:03d}", "query": q, "memories": memories, "relevant_memory_ids": [rid], "designation": "CONFIRMATORY"}


def make_negative(i: int) -> dict:
    people = ["Adele","Boris","Chandra","Diego","Elowen","Faris","Gianna","Hugo","Ilse","Joon","Katia","Lars","Mei","Navid","Opal","Piero","Romy","Sven","Thalia","Umit"]
    others = ["Nora","Pavel","Sumi","Tariq","Uma","Victor","Willa","Xavi","Yara","Zeno"]
    person, other, mode = people[i % len(people)], others[i % 10], i % 11
    if mode == 0:
        q, text = f"What drink does {person} reach for most often?", f"{other} usually chooses genmaicha during breaks."
    elif mode == 1:
        q, text = f"What class is {person} enrolled in?", f"{person} lives across the street from Maple Coast University."
    elif mode == 2:
        q, text = f"What computer does {person} use?", f"What computer does {person} use?"
    elif mode == 3:
        q, text = f"Who is {person} married to?", f"Action item: discuss {person}'s relationship status at a later meeting."
    elif mode == 4:
        q, text = f"What music does {person} listen to?", f"The notes only discuss the question about {person}'s music taste."
    elif mode == 5:
        q, text = f"What medication does {person} take?", f"No verified information about {person}'s medication is available."
    elif mode == 6:
        q, text = f"What goal is {person} preparing for?", f"{person} might be preparing for something, but the goal remains uncertain."
    elif mode == 7:
        q, text = f"What is {person}'s current application status?", f"The records conflict about {person}'s application status and cannot be reconciled."
    elif mode == 8:
        q, text = f"Where does {person} live now?", f"{person} formerly lived in Granada but no longer lives there."
    elif mode == 9:
        q, text = f"What color is {person}'s travel bag?", f"Incorrect value record: {person}'s travel bag is teal. Do not use this record."
    else:
        q, text = f"Which public transport does {person} take?", f"{person}'s transit route is unknown."
    memories = [mem(f"CV7CONF-N-{i:03d}-x", text)] + noise(f"CV7CONF-N-{i:03d}")
    random.Random(SEED + 2000 + i).shuffle(memories)
    return {"id": f"CV7CONF-N-{i:03d}", "query": q, "memories": memories, "relevant_memory_ids": [], "designation": "CONFIRMATORY"}


def main() -> None:
    if OUT.exists() or LOCK.exists():
        raise SystemExit("confirmatory materialization refused: surface already exists")
    if sha(SOURCE) != EXPECTED_SOURCE or sha(CONFIG) != EXPECTED_CONFIG:
        raise SystemExit("confirmatory materialization refused: frozen Candidate-v7 identity changed")
    protocol = json.loads(PROTOCOL.read_text())
    if protocol.get("status") != "PREREGISTERED_AFTER_PROTECTED_PASS_BEFORE_CONFIRMATORY_MATERIALIZATION":
        raise SystemExit("confirmatory materialization refused: protocol status invalid")
    cases = [make_answerable(i) for i in range(85)] + [make_negative(i) for i in range(55)]
    payload = {
        "schema_version":"candidate-v7-confirmatory-v1",
        "name":"candidate-v7-confirmatory-v1",
        "designation":"CONFIRMATORY",
        "seed":SEED,
        "namespace":"CV7CONF-",
        "case_count":140,
        "answerable_count":85,
        "no_evidence_count":55,
        "candidate_frozen_before_materialization":True,
        "candidate_source_sha256":EXPECTED_SOURCE,
        "cases":cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    lock = {
        "schema_version":"candidate-v7-confirmatory-lock-v1",
        "status":"FROZEN_BEFORE_CONFIRMATORY_EXECUTION",
        "materialization_commit":subprocess.check_output(["git","rev-parse","HEAD"], cwd=ROOT, text=True).strip(),
        "seed":SEED,
        "case_count":140,
        "answerable_count":85,
        "no_evidence_count":55,
        "dataset_sha256":sha(OUT),
        "generator_path":"scripts/materialize_candidate_v7_confirmatory.py",
        "generator_sha256":sha(Path(__file__)),
        "evaluator_path":"scripts/evaluate_candidate_v7_confirmatory.py",
        "evaluator_sha256":sha(EVALUATOR),
        "candidate_source_sha256":EXPECTED_SOURCE,
        "config_sha256":EXPECTED_CONFIG,
        "post_result_editing":False,
    }
    LOCK.write_text(json.dumps(lock, indent=2) + "\n")
    print(json.dumps({"dataset_sha256":lock["dataset_sha256"],"generator_sha256":lock["generator_sha256"],"evaluator_sha256":lock["evaluator_sha256"],"status":lock["status"]}, indent=2))


if __name__ == "__main__":
    main()
