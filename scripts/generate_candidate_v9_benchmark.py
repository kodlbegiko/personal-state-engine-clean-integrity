from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

STAGE_SPECS = {
    "development": {"seed": 2026081509, "answerable": 210, "negative": 150, "namespace": "CV9-DEV"},
    "protected": {"seed": 2026081511, "answerable": 190, "negative": 110, "namespace": "CV9-PROT"},
    "confirmatory": {"seed": 2026081513, "answerable": 220, "negative": 140, "namespace": "CV9-CONF"},
    "final": {"seed": 2026081515, "answerable": 300, "negative": 180, "namespace": "CV9-FINAL"},
}

PEOPLE = ["Adela","Bruno","Chiara","Dev","Elin","Farid","Gwen","Hugo","Ina","Jonas","Keiko","Luc","Maya","Nolan","Oksana","Pavel","Reina","Sven","Talia","Umar","Val","Wes","Yara","Zev"]
SURNAMES = ["Arden","Bauer","Costa","Dahl","Evans","Fischer","Garcia","Hale","Ito","Jensen","Kovac","Lopez","Mori","Neri","Olsen","Petrov"]
CITIES = ["Oslo","Utrecht","Adelaide","Valencia","Helsinki","Nagoya","Zurich","Bologna","Tallinn","Fukuoka","Malmo","Graz"]
DRINKS = ["jasmine tea","sparkling water","cafe au lait","cocoa","lemon soda","matcha latte","black tea","apple juice","kombucha","iced coffee","mint tea","soy cocoa"]
FOODS = ["oatmeal","rye toast","fruit yogurt","rice porridge","egg sandwich","miso soup","granola","bean toast","noodle bowl","fruit salad","corn porridge","savory pancakes"]
SCHOOLS = ["Harbor Institute","Northbridge University","Cedar Polytechnic","Riverside College","Aurora Academy","Westfield University","Lighthouse Institute","Stonebridge College","Cobalt Polytechnic","Elm University","Summit Academy","Canal College"]
COURSES = ["robotics","urban ecology","statistics","ceramics","linguistics","marine geology","digital ethics","structural design","plant physiology","economic history","data visualization","materials science"]
ROLES = ["systems analyst","landscape architect","lab technician","archive curator","transport planner","product designer","field researcher","speech therapist","energy auditor","museum coordinator","civil engineer","data librarian"]
DEVICES = ["Framework Laptop 16","ThinkPad T14","MacBook Pro","Surface Laptop","Zenbook S 14","EliteBook 840","Latitude 7450","Gram 15","IdeaPad Pro","Vivobook S","Swift Go","Yoga Pro"]
TRANSIT = ["tram 7","bus 42","metro K","train R3","route 18","tram 11","bus 206","metro N","train S2","route 55","tram 4","bus 88"]
LANGS = ["Swedish","Dutch","Japanese","Spanish","French","Mandarin","Italian","German","Korean","Portuguese","Finnish","Norwegian"]
HOBBIES = ["woodworking","rowing","watercolor painting","indoor climbing","pottery","bird photography","gardening","chess","folk dancing","trail cycling","bookbinding","kayaking"]
GOALS = ["a rescue certificate","a half marathon","a design exhibition","a language proficiency exam","a cycling brevet","a piano audition","a research poster","a wilderness course","a portfolio review","a diving certification","a public lecture","a rowing regatta"]
PARTNERS = ["Noemi","Rafael","Leonie","Mika","Soraya","Theo","Anya","Damon","Eira","Kaito","Mina","Ruben"]
CLUBS = ["astronomy society","community orchestra","rowing club","makers guild","garden collective","debate league","photography association","history society","language circle","canoe group","robotics club","volunteer network"]
STATUSES = ["approved","pending","active","paused","ready","closed","confirmed","archived","open","completed","scheduled","reviewing"]
DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday"]
PETS = ["terrier","ragdoll cat","rabbit","parrot","gecko","hamster","goldfish","spaniel","tabby cat","whippet","cockatiel","guinea pig"]
MEDIA = ["modal jazz","ambient folk","synth pop","classical guitar","soul","flamenco","post-rock","chamber music","dream pop","bossa nova","electro swing","bluegrass"]
MEDS = ["ibuprofen","cetirizine","paracetamol","naproxen"]
COLORS = ["navy","teal","amber","violet","maroon","silver","olive","coral","charcoal","cream","indigo","ochre"]


def memory(mid: str, text: str, day: int = 20) -> dict:
    return {"id": mid, "text": text, "timestamp": f"2027-02-{day:02d}T08:30:00+00:00", "speaker": "user"}


def noise(prefix: str) -> list[dict]:
    return [
        memory(prefix + "-d1", "Agenda for a later meeting: review an unrelated procurement topic.", 18),
        memory(prefix + "-d2", "No verified value is available for a separate field.", 18),
        memory(prefix + "-d3", "Could the team answer a different planning question next week?", 18),
        memory(prefix + "-d4", "A tentative claim on another subject remains unresolved.", 18),
    ]


def answerable(i: int, stage: str) -> tuple[str, str, list[dict]]:
    base = PEOPLE[(i * 5 + len(stage)) % len(PEOPLE)]
    surname = SURNAMES[(i // len(PEOPLE) + i * 7 + len(stage)) % len(SURNAMES)]
    p = f"{base} {surname}"
    j = (i * 7 + i // 24 + STAGE_SPECS[stage]["seed"]) % 12
    mode = i % 24
    variants = {"development": 0, "protected": 1, "confirmatory": 2, "final": 3}
    v = (i + variants[stage]) % 3

    if mode == 0:
        q = [f"Which beverage does {p} favor on ordinary workdays?", f"What drink is {p} partial to these days?", f"Which drink does {p} normally prefer?"][v]
        t = [f"{p} routinely selects {DRINKS[j]} during afternoon breaks.", f"On most workdays, {p} usually picks {DRINKS[j]}.", f"{p} tends to choose {DRINKS[j]} when taking a break."][v]
    elif mode == 1:
        q = [f"At which institution is {p} pursuing studies?", f"Which college or university is {p} enrolled at?", f"Where is {p} studying this academic year?"][v]
        t = [f"{p} is enrolled at {SCHOOLS[j]} for the current academic year.", f"{p} attends {SCHOOLS[j]} this year.", f"{p} is a student at {SCHOOLS[j]}."][v]
    elif mode == 2:
        q = [f"Which city does {p} call home currently?", f"Where is {p} based these days?", f"In what city does {p} live now?"][v]
        t = [f"{p} currently calls {CITIES[j]} home.", f"{p} is based in {CITIES[j]} these days.", f"{p} now lives in {CITIES[j]}."][v]
    elif mode == 3:
        q = [f"What profession does {p} hold?", f"What is {p}'s current occupation?", f"Which professional role does {p} have?"][v]
        t = [f"{p} serves as a {ROLES[j]}.", f"{p}'s occupation is {ROLES[j]}.", f"{p} works as a {ROLES[j]}."][v]
    elif mode == 4:
        q = [f"Which laptop is {p} working from daily?", f"What is {p}'s main computer?", f"Which device does {p} use for everyday work?"][v]
        t = [f"{p}'s everyday computer is a {DEVICES[j]}.", f"{p} works from a {DEVICES[j]} laptop.", f"{p}'s main device is a {DEVICES[j]}."][v]
    elif mode == 5:
        q = [f"Which transit service carries {p} to work?", f"What public transport does {p} commute on?", f"Which route does {p} use for the weekday commute?"][v]
        t = [f"{p} commutes aboard {TRANSIT[j]} on weekdays.", f"For work, {p} rides {TRANSIT[j]}.", f"{p}'s weekday transit is {TRANSIT[j]}."][v]
    elif mode == 6:
        q = [f"Which language does {p} communicate in fluently?", f"What language can {p} speak with ease?", f"Which language is {p} fluent in?"][v]
        t = [f"{p} speaks {LANGS[j]} fluently.", f"{p} communicates in {LANGS[j]} with ease.", f"{p} is fluent in {LANGS[j]}."][v]
    elif mode == 7:
        q = [f"Which organization does {p} belong to?", f"What club is {p} a member of?", f"Which group did {p} join?"][v]
        t = [f"{p} belongs to the {CLUBS[j]}.", f"{p} is a member of the {CLUBS[j]}.", f"{p} joined the {CLUBS[j]}."][v]
    elif mode == 8:
        q = [f"What pastime does {p} regularly do?", f"Which hobby does {p} practice?", f"What activity does {p} enjoy on weekends?"][v]
        t = [f"{p} spends weekends practicing {HOBBIES[j]}.", f"{p} regularly practices {HOBBIES[j]}.", f"{p} enjoys {HOBBIES[j]} on weekends."][v]
    elif mode == 9:
        q = [f"What target is {p} preparing toward?", f"Which goal is {p} training for?", f"What is {p} working toward this year?"][v]
        t = [f"{p} is preparing for {GOALS[j]}.", f"{p} is training for {GOALS[j]}.", f"This year {p} is working toward {GOALS[j]}."][v]
    elif mode == 10:
        q = [f"Who is {p}'s spouse?", f"Who is {p} married to?", f"Which person is {p}'s partner?"][v]
        t = [f"{p}'s spouse is {PARTNERS[j]}.", f"{p} is married to {PARTNERS[j]}.", f"{p}'s partner is {PARTNERS[j]}."][v]
    elif mode == 11:
        q = [f"What is {p}'s current permit status?", f"Which state is {p}'s permit in now?", f"What status does {p}'s permit currently have?"][v]
        t = [f"The permit status for {p} is now {STATUSES[j]}.", f"{p}'s permit is currently {STATUSES[j]}.", f"The current permit state for {p} is {STATUSES[j]}."][v]
    elif mode == 12:
        q = [f"Which weekday is {p}'s recurring check-in?", f"When is {p}'s standing check-in?", f"What day does {p} have the regular check-in?"][v]
        t = [f"{p}'s standing check-in happens on {DAYS[j % 5]} morning.", f"The recurring check-in for {p} is on {DAYS[j % 5]} morning.", f"{p} has the regular check-in on {DAYS[j % 5]} morning."][v]
    elif mode == 13:
        q = [f"What color is {p}'s backpack?", f"Which colour is {p}'s backpack?", f"What is the color of {p}'s bag?"][v]
        t = [f"{p} carries a {COLORS[j]} backpack.", f"{p}'s backpack is {COLORS[j]}.", f"The bag {p} carries is {COLORS[j]}."][v]
    elif mode == 14:
        q = [f"What animal does {p} keep at home?", f"Which pet does {p} own?", f"What kind of pet does {p} have?"][v]
        t = [f"{p} keeps a {PETS[j]} at home.", f"{p} owns a {PETS[j]}.", f"{p}'s pet is a {PETS[j]}."][v]
    elif mode == 15:
        q = [f"Which course is {p} taking this term?", f"What subject is {p} enrolled in?", f"Which class is {p} studying this term?"][v]
        t = [f"{p} is enrolled in {COURSES[j]} this term.", f"{p}'s current course is {COURSES[j]}.", f"This term {p} studies {COURSES[j]}."][v]
    elif mode == 16:
        q = [f"Which music genre does {p} listen to regularly?", f"What kind of music does {p} usually listen to?", f"Which music is {p} listening to often?"][v]
        t = [f"{p} regularly listens to {MEDIA[j]}.", f"{p} often listens to {MEDIA[j]}.", f"{p}'s regular music is {MEDIA[j]}."][v]
    elif mode == 17:
        q = [f"Which medication does {p} currently take?", f"What medicine is {p} taking now?", f"Which medication is current for {p}?"][v]
        t = [f"{p} currently takes {MEDS[j % len(MEDS)]}.", f"{p} is now taking {MEDS[j % len(MEDS)]}.", f"The current medication for {p} is {MEDS[j % len(MEDS)]}."][v]
    elif mode == 18:
        q = [f"Which breakfast does {p} usually choose?", f"What breakfast does {p} favor most mornings?", f"Which morning meal is {p}'s regular choice?"][v]
        t = [f"{p} routinely has {FOODS[j]} for breakfast.", f"Most mornings, {p} usually chooses {FOODS[j]}.", f"{p}'s regular breakfast is {FOODS[j]}."][v]
    elif mode == 19:
        q = "Which beverage do I normally favor after class?"
        t = [f"My regular after-class pick is {DRINKS[j]}.", f"I usually choose {DRINKS[j]} after class.", f"After class, I routinely select {DRINKS[j]}."][v]
    elif mode == 20:
        q = f"Where does {p} live now?"
        t = f"After moving, {p} is now based in {CITIES[j]}."
    elif mode == 21:
        q = f"Where does {p} reside currently?"
        t = f"{p} updated the address. They now reside in {CITIES[j]}."
    elif mode == 22:
        q = f"What is {p}'s occupation?"
        t = f"{p}'s professional role is {ROLES[j]}."
    else:
        q = f"Which device is {p}'s primary work computer?"
        t = f"{p}'s primary laptop is a {DEVICES[j]}."

    extras: list[dict] = []
    if mode in {2, 11, 20, 21}:
        extras.append(memory(f"old-{i}", f"Previously, {p} had an older value recorded, but it is no longer current.", 16))
    return q, t, extras

NEGATIVE_MODES = ["wrong_subject","wrong_relation","question_only","no_value","agenda","uncertain","contradiction","stale","decoy","hypothetical","future","assistant","unverified","wrong_type","meta"]


def negative(i: int, stage: str) -> tuple[str, str]:
    base = PEOPLE[(i * 3 + len(stage)) % len(PEOPLE)]
    other_base = PEOPLE[(i * 3 + len(stage) + 7) % len(PEOPLE)]
    surname = SURNAMES[(i // len(PEOPLE) + i * 5 + len(stage)) % len(SURNAMES)]
    other_surname = SURNAMES[(i // len(PEOPLE) + i * 5 + len(stage) + 5) % len(SURNAMES)]
    p = f"{base} {surname}"
    other = f"{other_base} {other_surname}"
    j = (i * 5 + STAGE_SPECS[stage]["seed"]) % 12
    mode = NEGATIVE_MODES[i % len(NEGATIVE_MODES)]
    if mode == "wrong_subject": return f"Which beverage does {p} normally prefer?", f"{other} usually chooses {DRINKS[j]}."
    if mode == "wrong_relation": return f"At which institution is {p} studying?", f"{p} works near {SCHOOLS[j]} as a technician."
    if mode == "question_only": return f"Which laptop does {p} use?", f"Which laptop does {p} use?"
    if mode == "no_value": return f"Which language does {p} speak?", f"No confirmed information about {p}'s language is available."
    if mode == "agenda": return f"Who is {p}'s spouse?", f"Agenda item: discuss {p}'s relationship at a future meeting."
    if mode == "uncertain": return f"Where does {p} live now?", f"It is uncertain whether {p} lives in {CITIES[j]}."
    if mode == "contradiction": return f"What is {p}'s permit status?", f"Conflicting records disagree on whether {p}'s permit is {STATUSES[j]}."
    if mode == "stale": return f"Where does {p} live now?", f"Previously, {p} lived in {CITIES[j]}, but that address is no longer current."
    if mode == "decoy": return f"Which course is {p} taking?", f"This is a fabricated decoy answer: {p} studies {COURSES[j]}; do not use it."
    if mode == "hypothetical": return f"Which transit does {p} use?", f"If the weather changed, {p} might take {TRANSIT[j]}."
    if mode == "future": return f"What hobby does {p} practice?", f"{p} plans to start {HOBBIES[j]} next year."
    if mode == "assistant": return f"What goal is {p} preparing for?", f"The assistant suggested that {p} train for {GOALS[j]}."
    if mode == "unverified": return f"Which medication does {p} take?", f"An unverified claim says {p} takes {MEDS[j % len(MEDS)]}."
    if mode == "wrong_type": return f"Which beverage does {p} normally prefer?", f"{p}'s favorite pastime is {HOBBIES[j]}."
    return f"What profession does {p} hold?", f"The notes only discuss the question about {p}'s profession and provide no answer."


def normalized_signature(case: dict) -> str:
    parts = [case["query"].strip().casefold()] + sorted(m["text"].strip().casefold() for m in case["memories"])
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def build(stage: str) -> dict:
    spec = STAGE_SPECS[stage]
    rng = random.Random(spec["seed"])
    cases = []
    for i in range(spec["answerable"]):
        prefix = f"{spec['namespace']}-A-{i:03d}"
        q, text, extras = answerable(i, stage)
        rel = memory(prefix + "-rel", text, 20)
        memories = [rel, *extras, *noise(prefix)]
        rng.shuffle(memories)
        case = {"id": prefix, "query": q, "memories": memories, "relevant_memory_ids": [rel["id"]], "designation": stage.upper(), "provenance": f"candidate-v9-fresh-generator:{stage}:{spec['seed']}:{i}"}
        case["surface_sha256"] = normalized_signature(case)
        cases.append(case)
    for i in range(spec["negative"]):
        prefix = f"{spec['namespace']}-N-{i:03d}"
        q, text = negative(i, stage)
        memories = [memory(prefix + "-x", text, 20), *noise(prefix)]
        rng.shuffle(memories)
        case = {"id": prefix, "query": q, "memories": memories, "relevant_memory_ids": [], "designation": stage.upper(), "provenance": f"candidate-v9-fresh-generator:{stage}:{spec['seed']}:neg:{i}"}
        case["surface_sha256"] = normalized_signature(case)
        cases.append(case)
    rng.shuffle(cases)
    signatures = [c["surface_sha256"] for c in cases]
    assert len(signatures) == len(set(signatures)), "duplicate semantic signatures within stage"
    return {"schema_version":"candidate-v9-benchmark-v1","name":f"candidate-v9-{stage}-v1","designation":stage.upper(),"seed":spec["seed"],"namespace":spec["namespace"],"case_count":len(cases),"answerable_count":spec["answerable"],"no_evidence_count":spec["negative"],"generator_family":"candidate-v9-independent-semantic-render-v1","cases":cases}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stage", choices=STAGE_SPECS, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    payload = build(args.stage)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({k: payload[k] for k in ("name","designation","seed","case_count","answerable_count","no_evidence_count")}, indent=2))

if __name__ == "__main__":
    main()
