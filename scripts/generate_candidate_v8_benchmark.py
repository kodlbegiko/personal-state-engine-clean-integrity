from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

SEEDS = {"development": 2026081500, "protected": 2026081511, "confirmatory": 2026081522}
COUNTS = {"development": (140, 100), "protected": (95, 65), "confirmatory": (120, 80)}

PEOPLE = ["Amina","Benoit","Celine","Dario","Esme","Felix","Greta","Hana","Ivo","Jia","Kiran","Lena","Marek","Nia","Oren","Priya","Quinn","Rhea","Samir","Tova","Uri","Vera","Wren","Xena","Yuki","Zane"]
OTHER = ["Milo","Nora","Omar","Pia","Ravi","Sora","Tari","Uma","Vik","Willa"]
TOWNS = ["Tainan","Ghent","Sapporo","Limerick","Turin","Daegu","Porto","Brno","Leuven","Sendai"]
DRINKS = ["oolong tea","tonic water","flat white","barley tea","ginger soda","cold brew","rooibos","grape soda","espresso","soy latte"]
ROLES = ["urban planner","radiographer","museum registrar","survey technician","speech therapist","lab coordinator","policy researcher","sound engineer","horticulturist","data steward"]
PETS = ["basenji","ragdoll cat","budgerigar","mini rex rabbit","akita","goldfish","dachshund","leopard gecko","maine coon","papillon"]
HOBBIES = ["linocut printing","dragon boat paddling","glassblowing","folk dancing","trail cycling","bookbinding","indoor climbing","embroidery","table tennis","astrophotography"]
LANGS = ["Norwegian","Japanese","Spanish","Danish","French","Mandarin","Italian","German","Korean","Portuguese"]
SCHOOLS = ["Maple Coast University","Redwood Technical College","Juniper Institute","Bluewater University","Silver Hill College","Crescent Polytechnic","Pinecrest University","East Harbor College","Meadow Institute","Granite State College"]
COURSES = ["soil microbiology","graph theory","sound design","renewable energy systems","syntax","environmental law","organic spectroscopy","museum studies","hydraulic modeling","visual anthropology"]
MEDIA = ["bebop jazz","Nordic folk","trip-hop","classical guitar","electro swing","dream pop","soul","chamber opera","lo-fi hip-hop","flamenco"]
DEVICES = ["ThinkPad P14s","MacBook Air","Surface Pro","Framework Laptop 13","Zenbook 14","Latitude 7350","Yoga Slim 7","EliteBook 845","Gram 16","Spectre 14"]
GOALS = ["a sprint triathlon","a C1 language exam","a pottery exhibition","a wilderness first-aid certificate","a 100-km cycling event","a piano grade exam","a design portfolio review","a rescue-diver certificate","a half-marathon","a conference talk"]
TRANSIT = ["tram 5","bus 119","metro line C","route 26","express 8","tram 2","bus 615","line M3","route 44","metro line A"]
PARTNERS = ["Rina","Mateo","Lea","Oskar","Nadia","Timo","Sara","Emil","Aya","Ravi"]
COLORS = ["ochre","sage green","indigo","rust orange","pearl white","slate gray","crimson","seafoam","mustard","aubergine"]
CLUBS = ["geology society","community orchestra","canoe club","language exchange","makers collective","volunteer garden group","photography circle","public-speaking club","historical society","badminton club"]
STATUSES = ["approved","active","paused","ready","closed","scheduled","confirmed","archived","open","completed"]
DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday"]

def memory(mid: str, text: str, day: int = 14, speaker: str = "user") -> dict:
    return {"id": mid, "text": text, "timestamp": f"2026-10-{day:02d}T09:20:00+00:00", "speaker": speaker}

def benign_noise(prefix: str) -> list[dict]:
    return [
        memory(prefix+"-n1", "Agenda item for next month: discuss an unrelated office supply request."),
        memory(prefix+"-n2", "No confirmed information is available for the unrelated field."),
        memory(prefix+"-n3", "Could someone answer the separate planning question later?"),
        memory(prefix+"-n4", "A tentative note on another subject remains unresolved."),
        memory(prefix+"-n5", "This is an unrelated decoy record; do not use it as an answer."),
    ]

def render_answerable(i: int, split: str) -> tuple[str, str, list[dict]]:
    p = PEOPLE[i % len(PEOPLE)]
    j = (i * 7 + SEEDS[split]) % 10
    mode = i % 21
    variant = {"development": i % 3, "protected": 3 + i % 2, "confirmatory": 5 + i % 2}[split]

    if mode == 0:
        q = [f"What beverage does {p} reach for most often?", f"What drink is {p}'s usual choice?", f"Which beverage does {p} normally pick?"][variant % 3]
        text = [f"During breaks, {p} usually chooses {DRINKS[j]}.", f"{p} tends to order {DRINKS[j]} when taking a break.", f"{p}'s go-to after lunch is {DRINKS[j]}."][variant % 3]
    elif mode == 1:
        q = [f"Where does {p} live now?", f"What city is {p} currently based in?", f"Where is {p}'s home these days?"][variant % 3]
        text = [f"After relocating, {p} now lives in {TOWNS[j]}.", f"{p} is currently based in {TOWNS[j]}.", f"{p}'s home is in {TOWNS[j]} now."][variant % 3]
    elif mode == 2:
        q = [f"What kind of work does {p} do?", f"What is {p}'s job?", f"Which role does {p} work in?"][variant % 3]
        text = [f"{p} works as a {ROLES[j]}.", f"{p}'s current job is {ROLES[j]}.", f"At the regional office, {p} works as a {ROLES[j]}."][variant % 3]
    elif mode == 3:
        q = [f"What pet does {p} own?", f"Which animal does {p} have at home?", f"What kind of pet does {p} keep?"][variant % 3]
        text = [f"{p} has a {PETS[j]} at home.", f"At home, {p} owns a {PETS[j]}.", f"{p}'s pet is a {PETS[j]}."][variant % 3]
    elif mode == 4:
        q = [f"What hobby does {p} practice?", f"Which activity does {p} enjoy?", f"What does {p} do for fun?"][variant % 3]
        text = [f"{p} practices {HOBBIES[j]} on weekends.", f"{p} really enjoys {HOBBIES[j]}.", f"For fun, {p} plays at {HOBBIES[j]} regularly."][variant % 3]
    elif mode == 5:
        q = [f"Which language can {p} speak?", f"What language is {p} fluent in?", f"Which language does {p} use comfortably?"][variant % 3]
        text = [f"{p} speaks {LANGS[j]} comfortably.", f"{p} is fluent in {LANGS[j]}.", f"In everyday conversation, {p} speaks {LANGS[j]}."][variant % 3]
    elif mode == 6:
        q = [f"Which university or college does {p} attend?", f"Where does {p} study?", f"Which school is {p} enrolled at?"][variant % 3]
        text = [f"{p} studies at {SCHOOLS[j]}.", f"{p} attends {SCHOOLS[j]} this year.", f"{p}'s campus is {SCHOOLS[j]}."][variant % 3]
    elif mode == 7:
        q = [f"What class is {p} enrolled in?", f"Which course is {p} taking?", f"What subject is {p} studying this semester?"][variant % 3]
        text = [f"{p} is enrolled in {COURSES[j]}.", f"This semester {p} studies {COURSES[j]}.", f"{p}'s current course is {COURSES[j]}."][variant % 3]
    elif mode == 8:
        q = [f"What music does {p} listen to?", f"Which kind of music does {p} usually play?", f"What is {p} listening to lately?"][variant % 3]
        text = [f"{p} listens to {MEDIA[j]} most days.", f"{p} usually plays {MEDIA[j]} on the commute.", f"Lately, {p} listens to {MEDIA[j]}."][variant % 3]
    elif mode == 9:
        q = [f"What computer does {p} use?", f"Which laptop does {p} use for daily work?", f"What device is {p}'s main computer?"][variant % 3]
        text = [f"{p} uses a {DEVICES[j]}.", f"For daily tasks, {p} uses a {DEVICES[j]}.", f"{p}'s main computer is a {DEVICES[j]}."][variant % 3]
    elif mode == 10:
        q = [f"What goal is {p} preparing for?", f"What target is {p} training toward?", f"What is {p} working toward this year?"][variant % 3]
        text = [f"{p} is training toward {GOALS[j]}.", f"{p} is preparing for {GOALS[j]}.", f"This year {p} is working toward {GOALS[j]}."][variant % 3]
    elif mode == 11:
        q = [f"Which public transport does {p} take?", f"What transit route does {p} use?", f"How does {p} commute by public transport?"][variant % 3]
        text = [f"{p} rides {TRANSIT[j]} each weekday.", f"{p} takes {TRANSIT[j]} to work.", f"For the commute, {p} rides {TRANSIT[j]}."][variant % 3]
    elif mode == 12:
        q = [f"Who is {p} married to?", f"Who is {p}'s spouse?", f"Which person is {p}'s partner?"][variant % 3]
        text = [f"{p} is married to {PARTNERS[j]}.", f"{p}'s spouse is {PARTNERS[j]}.", f"{p}'s partner is {PARTNERS[j]}."][variant % 3]
    elif mode == 13:
        q = [f"What color is {p}'s travel bag?", f"Which colour is {p}'s travel bag?", f"What is the color of {p}'s travel bag?"][variant % 3]
        text = [f"{p}'s travel bag is {COLORS[j]}.", f"The color of {p}'s travel bag is {COLORS[j]}.", f"{p} has a {COLORS[j]} travel bag."][variant % 3]
    elif mode == 14:
        q = [f"Which club is {p} a member of?", f"What club did {p} join?", f"Which group is {p} a member of?"][variant % 3]
        text = [f"{p} joined the {CLUBS[j]}.", f"{p} is a member of the {CLUBS[j]}.", f"Earlier this year, {p} joined the {CLUBS[j]}."][variant % 3]
    elif mode == 15:
        q = [f"What is {p}'s current application status?", f"Which status does {p}'s application have now?", f"What state is {p}'s application in currently?"][variant % 3]
        text = [f"A correction was filed: {p}'s application status is now {STATUSES[j]}.", f"{p}'s application is currently {STATUSES[j]}.", f"The updated application status for {p} is {STATUSES[j]}."][variant % 3]
    elif mode == 16:
        q = "What beverage do I tend to order after work?"
        text = [f"I usually order {DRINKS[j]} after work.", f"My usual after-work choice is {DRINKS[j]}.", f"After work, I tend to order {DRINKS[j]}."][variant % 3]
    elif mode == 17:
        q = f"Where does {p} currently live?"
        text = f"The prior address is obsolete; after relocating, {p} now lives in {TOWNS[j]}."
    elif mode == 18:
        q = f"What version is {p}'s tablet using?"
        text = [f"{p}'s tablet is running NovaOS {4+j%4}.{j}.", f"The version on {p}'s tablet is NovaOS {4+j%4}.{j}.", f"{p} uses NovaOS {4+j%4}.{j} on the tablet."][variant % 3]
    elif mode == 19:
        q = f"What is {p}'s favorite drink these days?"
        text = f"The preference changed recently, and {p} now prefers {DRINKS[j]}."
    else:
        q = f"When is {p}'s recurring check-in?"
        text = f"The check-in was rescheduled; {p} now meets on {DAYS[j%5]} morning."

    extras = []
    # Mixed-clause positives: a benign question/meta clause must not poison a factual clause.
    if i % 9 == 0:
        text = f"Someone asked a separate planning question earlier; {text}"
    # Current facts can have a stale distractor that must not be returned.
    if mode in {1,15,17,19,20}:
        extras.append(memory(f"stale-{i}", f"Previously, {p}'s old value was recorded differently, but it is no longer current.", 11))

    return q, text, extras

NEGATIVE_MODES = [
    "wrong_subject", "wrong_relation", "question_only", "agenda", "meta_paraphrase",
    "no_value_variant", "uncertain", "contradiction", "stale_only", "negative_decoy",
    "unknown_value", "hypothetical", "future_intent", "assistant_suggestion", "unverified_quote",
    "entity_collision", "same_subject_nearby_relation",
]

def render_negative(i: int, split: str) -> tuple[str, str]:
    p = PEOPLE[i % len(PEOPLE)]
    o = OTHER[(i * 3) % len(OTHER)]
    mode = NEGATIVE_MODES[i % len(NEGATIVE_MODES)]
    if mode == "wrong_subject":
        return f"What beverage does {p} usually choose?", f"{o} usually chooses oolong tea."
    if mode == "wrong_relation":
        return f"What class is {p} enrolled in?", f"{p} lives near Maple Coast University."
    if mode == "question_only":
        return f"What computer does {p} use?", f"What computer does {p} use?"
    if mode == "agenda":
        return f"Who is {p} married to?", f"Agenda item: discuss {p}'s relationship at the next meeting."
    if mode == "meta_paraphrase":
        return f"What music does {p} listen to?", f"The notes only discuss the question about {p}'s music taste."
    if mode == "no_value_variant":
        text = [
            f"No verified information about {p}'s medication is available.",
            f"There is no confirmed answer recorded for {p}'s medication.",
            f"Information about {p}'s medication remains unavailable.",
        ][{"development":0,"protected":1,"confirmatory":2}[split]]
        return f"What medication does {p} take?", text
    if mode == "uncertain":
        return f"What goal is {p} preparing for?", f"{p} might be preparing for something; the goal remains uncertain."
    if mode == "contradiction":
        return f"What is {p}'s current application status?", f"The records conflict about {p}'s application status and cannot be reconciled."
    if mode == "stale_only":
        return f"Where does {p} live now?", f"{p} formerly lived in Turin but no longer lives there."
    if mode == "negative_decoy":
        return f"What color is {p}'s travel bag?", f"Incorrect value record: {p}'s travel bag is teal. Do not use this record."
    if mode == "unknown_value":
        return f"Which public transport does {p} take?", f"{p}'s transit route is unknown."
    if mode == "hypothetical":
        return f"What pet does {p} own?", f"If {p} adopted a pet, a dachshund would be the first choice."
    if mode == "future_intent":
        return f"What course is {p} enrolled in?", f"{p} plans to study graph theory next year."
    if mode == "assistant_suggestion":
        return f"What laptop does {p} use?", f"The assistant suggested that {p} buy a Framework Laptop 13."
    if mode == "unverified_quote":
        return f"What job does {p} have?", f"An unverified claim says {p} works as an urban planner."
    if mode == "entity_collision":
        return f"What version is {p}'s tablet using?", f"{p}'s phone is running NovaOS 9.4."
    return f"What goal is {p} preparing for?", f"{p}'s application status is active."

def canonical_surface_hash(case: dict) -> str:
    normalized = {
        "query": " ".join(case["query"].split()),
        "memories": sorted(
            [{"id": m["id"], "text": " ".join(m["text"].split()), "timestamp": m.get("timestamp")} for m in case["memories"]],
            key=lambda x: x["id"],
        ),
    }
    return hashlib.sha256(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def generate(split: str) -> dict:
    if split not in SEEDS:
        raise ValueError(split)
    seed = SEEDS[split]
    answerable_count, negative_count = COUNTS[split]
    cases = []
    for i in range(answerable_count):
        cid = f"CV8-{split.upper()}-A-{i:03d}"
        q, text, extras = render_answerable(i, split)
        rid = cid+"-rel"
        memories = [memory(rid, text, 15)] + extras + benign_noise(cid)
        random.Random(seed + i).shuffle(memories)
        case = {
            "id": cid,
            "query": q,
            "memories": memories,
            "relevant_memory_ids": [rid],
            "designation": split.upper(),
            "render_family": f"{split}-positive-rf-{i % (3 if split == 'development' else 2)}",
            "provenance": f"candidate-v8-fresh-generator:{split}:{seed}:{i}",
        }
        case["surface_sha256"] = canonical_surface_hash(case)
        cases.append(case)
    for i in range(negative_count):
        cid = f"CV8-{split.upper()}-N-{i:03d}"
        q, text = render_negative(i, split)
        memories = [memory(cid+"-x", text)] + benign_noise(cid)
        random.Random(seed + 10000 + i).shuffle(memories)
        case = {
            "id": cid,
            "query": q,
            "memories": memories,
            "relevant_memory_ids": [],
            "designation": split.upper(),
            "render_family": f"{split}-negative-rf-{i % len(NEGATIVE_MODES)}",
            "provenance": f"candidate-v8-fresh-generator:{split}:{seed}:negative:{i}",
        }
        case["surface_sha256"] = canonical_surface_hash(case)
        cases.append(case)
    return {
        "schema_version": "candidate-v8-benchmark-v1",
        "name": f"candidate-v8-{split}-v1",
        "designation": split.upper(),
        "seed": seed,
        "namespace": f"CV8-{split.upper()}-",
        "case_count": len(cases),
        "answerable_count": answerable_count,
        "no_evidence_count": negative_count,
        "generator_family": "fresh-semantic-spec-render-v1",
        "render_family_namespace": f"{split}-heldout-family",
        "cases": cases,
    }

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("split", choices=sorted(SEEDS))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = generate(args.split)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({
        "split": args.split,
        "case_count": payload["case_count"],
        "answerable_count": payload["answerable_count"],
        "no_evidence_count": payload["no_evidence_count"],
        "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
    }, indent=2))

if __name__ == "__main__":
    main()
