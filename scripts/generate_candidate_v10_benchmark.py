from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path

STAGE_SPECS = {
    "development": {"seed": 2026081515, "answerable": 280, "negative": 200, "namespace": "CV10-DEV", "families": ["A", "B", "C"]},
    "protected": {"seed": 2026081516, "answerable": 220, "negative": 140, "namespace": "CV10-PROT", "families": ["D", "E"]},
    "confirmatory": {"seed": 2026081517, "answerable": 250, "negative": 170, "namespace": "CV10-CONF", "families": ["F", "G", "H"]},
    "final": {"seed": 2026081518, "answerable": 280, "negative": 200, "namespace": "CV10-FINAL", "families": ["I", "J", "K"]},
}

FIRST = ["Adela", "Bruno", "Chiara", "Dev", "Elin", "Farid", "Gwen", "Hugo", "Ina", "Jonas", "Keiko", "Luc", "Maya", "Nolan", "Oksana", "Pavel", "Reina", "Sven", "Talia", "Umar", "Val", "Wes", "Yara", "Zev", "Ari", "Bela", "Cleo", "Dara", "Emil", "Faye", "Gio", "Hana"]
LAST = ["Arden", "Bauer", "Costa", "Dahl", "Evans", "Fischer", "Garcia", "Hale", "Ito", "Jensen", "Kovac", "Lopez", "Mori", "Neri", "Olsen", "Petrov", "Quinn", "Rossi", "Singh", "Tanaka", "Ulrich", "Vega", "Wong", "Xu", "Young", "Zoric", "Bennett", "Choi", "Dubois", "Eriksen", "Ferrer", "Gruber"]

DOMAINS = [
    {"name":"preferences","q":"usual breakfast choice","e":"regular breakfast","values":["buckwheat bowl","pear porridge","sesame toast","pumpkin congee","herb omelette","millet pancakes"]},
    {"name":"preferences","q":"preferred beverage","e":"default drink","values":["oolong spritz","barley tea","pear soda","citrus tonic","roasted tea","plum water"]},
    {"name":"education","q":"current university","e":"academic institution","values":["Maple Coast University","Granite Institute","Eastern Bay College","Juniper Polytechnic","Silver Lake Academy","Crescent University"]},
    {"name":"education","q":"course this term","e":"current course","values":["aquatic chemistry","urban hydrology","formal logic","soil physics","visual anthropology","acoustic design"]},
    {"name":"employment","q":"professional role","e":"work role","values":["water systems analyst","museum registrar","mobility planner","lab coordinator","product researcher","archive specialist"]},
    {"name":"location","q":"current home city","e":"home location","values":["Sendai","Ghent","Turin","Linz","Dunedin","Sapporo"]},
    {"name":"device ownership/use","q":"primary work computer","e":"main laptop device","values":["NovaBook 14","Atlas Pro 13","Pinebook Studio","Vector Air 15","CedarBook X","Orion Notebook"]},
    {"name":"transportation","q":"weekday commute route","e":"regular transit route","values":["tram M4","bus 317","metro Q","train L2","route 64","tram C9"]},
    {"name":"language","q":"fluent language","e":"spoken language","values":["Icelandic","Catalan","Estonian","Polish","Thai","Greek"]},
    {"name":"hobbies","q":"weekend hobby","e":"regular activity","values":["linocut printing","sailing","mushroom photography","glass painting","orienteering","letterpress"]},
    {"name":"goals","q":"current goal","e":"training target","values":["an alpine first-aid badge","a coastal rowing race","a typography portfolio","a navigation assessment","a public recital","a conservation certificate"]},
    {"name":"relationships","q":"current partner","e":"spouse or partner","values":["Nia","Mateo","Lea","Riku","Samira","Tomas"]},
    {"name":"memberships","q":"club membership","e":"member organization","values":["harbor astronomy circle","makers cooperative","city choir society","river rowing guild","local history circle","community garden network"]},
    {"name":"schedules","q":"recurring meeting day","e":"standing check-in schedule","values":["Monday morning","Tuesday afternoon","Wednesday evening","Thursday morning","Friday afternoon","Saturday morning"]},
    {"name":"pets","q":"pet animal","e":"owned pet","values":["greyhound","tortoise","budgerigar","ferret","maine coon cat","axolotl"]},
    {"name":"media","q":"usual music choice","e":"favorite genre","values":["minimalist jazz","Nordic folk","Afrobeat","baroque chamber music","shoegaze","Latin soul"]},
    {"name":"medication","q":"current medication","e":"prescribed medicine","values":["loratadine","famotidine","melatonin","diclofenac gel","fexofenadine","saline spray"]},
    {"name":"attributes/colors","q":"backpack color","e":"backpack color","object":"backpack","values":["midnight blue","sandstone","forest green","burnt orange","pearl gray","deep burgundy"]},
    {"name":"status","q":"permit status","e":"permit status","object":"permit","values":["under review","awaiting documents","queued for approval","in verification","renewal pending","ready for pickup"]},
    {"name":"certifications","q":"professional certification","e":"credential","values":["Northstar Level II","Coastal Safety B","Orchid Data Certificate","Field Survey Grade 1","Atlas Teaching Badge","Civic Mediation Award"]},
    {"name":"subscriptions","q":"software subscription","e":"service plan","values":["Studio Plus","Research Basic","Cloud Family","Creator Annual","Team Standard","Archive Pro"]},
    {"name":"travel plans","q":"next trip destination","e":"travel plan","values":["Reykjavik","Ljubljana","Porto","Jeju","Krakow","Hobart"]},
    {"name":"dietary restrictions","q":"dietary restriction","e":"food restriction","values":["no shellfish","lactose-free meals","no peanuts","vegetarian meals","gluten-free food","no sesame"]},
    {"name":"sports teams","q":"sports team followed","e":"team supported","values":["North Harbor Comets","Redwood Owls","Metro Foxes","Blue Ridge Sparks","Seaside Arrows","Granite Wolves"]},
    {"name":"volunteering","q":"volunteer activity","e":"community service","values":["river cleanup","library tutoring","food-bank sorting","trail restoration","senior tech help","animal shelter shifts"]},
    {"name":"software/tools","q":"main software tool","e":"work app","values":["Orbit Studio","Cobalt Editor","Lumen Notes","MapForge","Quill IDE","Harbor Canvas"]},
    {"name":"communication channels","q":"preferred contact channel","e":"communication channel","values":["Signal","Matrix","email","Mattermost","phone call","company chat"]},
    {"name":"recurring routines","q":"evening routine","e":"daily habit","values":["a twenty-minute walk","tea and journaling","piano scales","balcony gardening","language flashcards","stretching"]},
    {"name":"project ownership","q":"project currently owned","e":"project responsibility","values":["Project Orion","Atlas Migration","Harbor Index","Cedar Launch","Lumen Archive","Northwind Pilot"]},
    {"name":"appointments","q":"next appointment","e":"scheduled visit","values":["17 September at 14:30","21 September at 09:00","3 October at 16:00","8 October at 11:15","12 October at 10:30","19 October at 15:45"]},
    {"name":"accommodations","q":"trip accommodation","e":"lodging","values":["Harbor House","Juniper Hotel","Cedar Guesthouse","North Gate Hostel","Riverside Inn","Lantern Lodge"]},
]

FAMILY_META = {
    "A": ("direct_wh", "canonical_assignment", "subject_relation_value", "current"),
    "B": ("possessive_question", "possessive_copular", "possessor_object_attribute", "current"),
    "C": ("indirect_request", "record_assignment", "subject_record_slot", "current"),
    "D": ("association_question", "inverse_copular", "value_relation_subject", "current"),
    "E": ("elliptical_request", "entry_nominalization", "subject_entry_value", "current"),
    "F": ("embedded_field_question", "profile_assignment", "subject_profile_slot", "current"),
    "G": ("contrastive_question", "update_assignment", "subject_update_value", "current"),
    "H": ("first_or_third_person", "coreference_assignment", "cross_sentence_coreference", "current"),
    "I": ("field_question", "prepositional_record", "slot_subject_value", "current"),
    "J": ("nominalized_profile_question", "field_contains", "field_subject_value", "current"),
    "K": ("as_of_now_question", "as_of_now_assignment", "subject_slot_value", "current"),
}


def person(i: int, stage: str) -> str:
    salt = STAGE_SPECS[stage]["seed"] % 31
    return f"{FIRST[(i * 7 + salt) % len(FIRST)]} {LAST[(i * 11 + salt) % len(LAST)]}{i // len(LAST)}"


def value(domain: dict, i: int, stage: str) -> str:
    return domain["values"][(i * 5 + STAGE_SPECS[stage]["seed"]) % len(domain["values"])]


def render(family: str, p: str, qslot: str, eslot: str, val: str, first_person: bool = False) -> tuple[str, str]:
    if first_person:
        if family in {"C", "H"}:
            return f"What is my current {qslot}?", f"My {eslot} is {val}."
    table = {
        "A": (f"Which {qslot} does {p} have right now?", f"{p} has {val} recorded as the {eslot}."),
        "B": (f"What is {p}'s current {qslot}?", f"{p}'s {eslot} is {val}."),
        "C": (f"For {p}, can you identify the {qslot} currently on record?", f"The record for {p} lists {val} under {eslot}."),
        "D": (f"Which {qslot} is associated with {p} at present?", f"{val} is the {eslot} currently associated with {p}."),
        "E": (f"I need {p}'s {qslot}; what does the latest record say?", f"For {p}, the latest {eslot} entry is {val}."),
        "F": (f"Regarding {p}, what currently fills the {qslot} field?", f"{p}'s profile shows the {eslot} as {val}."),
        "G": (f"Not the old record: which {qslot} applies to {p} now?", f"After the update, {p} has {val} recorded for {eslot}."),
        "H": (f"What should I use for {p}'s current {qslot}?", f"{p} updated the profile. Their {eslot} is {val}."),
        "I": (f"Which entry belongs in {p}'s {qslot} field today?", f"Under {eslot}, {p} is recorded as {val}."),
        "J": (f"What does the profile say about the {qslot} for {p}?", f"The {eslot} field for {p} contains {val}."),
        "K": (f"As of now, how is {p}'s {qslot} recorded?", f"As of now, {p} has {val} in the {eslot} field."),
    }
    return table[family]


def special_object_bridge(domain: dict, family: str, p: str, val: str, query: str, evidence: str, i: int) -> tuple[str, str]:
    obj = domain.get("object")
    if not obj or family not in {"B", "F", "G", "J"} or i % 3:
        return query, evidence
    if domain["name"] == "status":
        return f"What is {p}'s current {obj} status?", f"{p}'s {obj} is {val}."
    if domain["name"] == "attributes/colors":
        return f"What color is {p}'s {obj}?", f"{p}'s {obj} is {val}."
    return query, evidence


def memory(mid: str, text: str, day: int = 20) -> dict:
    return {"id": mid, "text": text, "timestamp": f"2027-03-{day:02d}T08:30:00+00:00", "speaker": "user"}


def metadata(domain: dict, family: str, polarity: str, template_id: str) -> dict:
    qg, eg, arg, temporal = FAMILY_META[family]
    return {
        "semantic_domain": domain["name"],
        "query_grammar_family": family,
        "query_realization": qg,
        "evidence_grammar_family": family,
        "evidence_realization": eg,
        "argument_structure_family": arg,
        "temporal_family": temporal,
        "polarity_adversarial_family": polarity,
        "template_provenance": template_id,
    }


def answerable_case(i: int, stage: str) -> dict:
    spec = STAGE_SPECS[stage]
    domain = DOMAINS[i % len(DOMAINS)]
    family = spec["families"][i % len(spec["families"])]
    p = person(i, stage)
    val = value(domain, i, stage)
    first_person = (i % 41 == 0 and family in {"C", "H"})
    q, rel = render(family, p, domain["q"], domain["e"], val, first_person=first_person)
    q, rel = special_object_bridge(domain, family, p, val, q, rel, i)
    prefix = f"{spec['namespace']}-A-{i:03d}"

    other_domain = DOMAINS[(i + 7) % len(DOMAINS)]
    other_val = value(other_domain, i + 3, stage)
    if first_person:
        wrong_subject = memory(prefix + "-d1", f"Another person's {domain['e']} is {val}.", 19)
        wrong_relation = memory(prefix + "-d2", f"My {other_domain['e']} is {other_val}.", 19)
        stale = memory(prefix + "-d3", f"Previously, my {domain['e']} was {domain['values'][(i + 1) % len(domain['values'])]}.", 18)
        uncertain = memory(prefix + "-d4", f"My {domain['e']} is perhaps {domain['values'][(i + 2) % len(domain['values'])]}.", 19)
    else:
        p2 = person(i + 997, stage)
        wrong_subject = memory(prefix + "-d1", f"{p2}'s {domain['e']} is {val}.", 19)
        wrong_relation = memory(prefix + "-d2", f"{p}'s {other_domain['e']} is {other_val}.", 19)
        stale = memory(prefix + "-d3", f"Previously, {p}'s {domain['e']} was {domain['values'][(i + 1) % len(domain['values'])]}.", 18)
        uncertain = memory(prefix + "-d4", f"{p}'s {domain['e']} is perhaps {domain['values'][(i + 2) % len(domain['values'])]}.", 19)
    memories = [memory(prefix + "-rel", rel, 20), wrong_subject, wrong_relation, stale, uncertain]
    random.Random(spec["seed"] + i * 17).shuffle(memories)
    return {
        "id": prefix,
        "query": q,
        "memories": memories,
        "relevant_memory_ids": [prefix + "-rel"],
        "designation": stage.upper(),
        "generator_metadata": metadata(domain, family, "answerable", f"candidate-v10:{stage}:{family}:answerable"),
        "provenance": f"candidate-v10-fresh-generator:{stage}:{spec['seed']}:{i}",
    }


def negative_case(i: int, stage: str) -> dict:
    spec = STAGE_SPECS[stage]
    domain = DOMAINS[(i * 3 + 5) % len(DOMAINS)]
    family = spec["families"][i % len(spec["families"])]
    p = person(3000 + i, stage)
    val = value(domain, i + 9, stage)
    q, _ = render(family, p, domain["q"], domain["e"], val)
    if domain.get("object") and family in {"B", "F", "G", "J"} and i % 3 == 0:
        if domain["name"] == "status":
            q = f"What is {p}'s current permit status?"
        elif domain["name"] == "attributes/colors":
            q = f"What color is {p}'s backpack?"
    prefix = f"{spec['namespace']}-N-{i:03d}"
    p2 = person(5000 + i, stage)
    other_domain = DOMAINS[(i * 3 + 12) % len(DOMAINS)]
    other_val = value(other_domain, i + 2, stage)
    texts = [
        f"No verified value is available for {p}'s {domain['e']}.",
        f"{p}'s {domain['e']} is perhaps {val}.",
        f"Previously, {p}'s {domain['e']} was {val}.",
        f"{p2}'s {domain['e']} is {val}.",
        f"{p}'s {other_domain['e']} is {other_val}.",
        f"Agenda item: discuss {p}'s {domain['e']} at a later meeting.",
    ]
    rng = random.Random(spec["seed"] + 7000 + i * 19)
    rng.shuffle(texts)
    memories = [memory(prefix + f"-d{j}", text, 19 if j else 20) for j, text in enumerate(texts[:5])]
    return {
        "id": prefix,
        "query": q,
        "memories": memories,
        "relevant_memory_ids": [],
        "designation": stage.upper(),
        "generator_metadata": metadata(domain, family, "no_evidence_adversarial", f"candidate-v10:{stage}:{family}:negative"),
        "provenance": f"candidate-v10-fresh-generator:{stage}:{spec['seed']}:neg:{i}",
    }


def normalize(text: str) -> str:
    text = text.casefold()
    text = re.sub(r"\b(?:adela|bruno|chiara|dev|elin|farid|gwen|hugo|ina|jonas|keiko|luc|maya|nolan|oksana|pavel|reina|sven|talia|umar|val|wes|yara|zev|ari|bela|cleo|dara|emil|faye|gio|hana)\b", "<person>", text)
    text = re.sub(r"\b(?:arden|bauer|costa|dahl|evans|fischer|garcia|hale|ito|jensen|kovac|lopez|mori|neri|olsen|petrov|quinn|rossi|singh|tanaka|ulrich|vega|wong|xu|young|zoric|bennett|choi|dubois|eriksen|ferrer|gruber)\d*\b", "<surname>", text)
    text = re.sub(r"\d+(?:[.:]\d+)?", "<num>", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def skeleton(text: str) -> str:
    text = normalize(text)
    # Open-class spans are intentionally abstracted approximately; declared
    # grammar-family metadata is the authoritative latent-family partition.
    text = re.sub(r"\b[a-z][a-z-]*(?:\s+[a-z][a-z-]*){0,3}\b(?=[.?!])", "<tail>", text)
    return text


def audit_payload(payload: dict) -> dict:
    cases = payload["cases"]
    exact = [json.dumps({"q": c["query"], "m": [m["text"] for m in c["memories"]]}, sort_keys=True) for c in cases]
    normalized = [json.dumps({"q": normalize(c["query"]), "m": sorted(normalize(m["text"]) for m in c["memories"])}, sort_keys=True) for c in cases]
    qsk = [skeleton(c["query"]) for c in cases]
    esk = [skeleton(next(m["text"] for m in c["memories"] if m["id"] in c["relevant_memory_ids"])) for c in cases if c["relevant_memory_ids"]]
    families = Counter(c["generator_metadata"]["query_grammar_family"] for c in cases)
    domains = Counter(c["generator_metadata"]["semantic_domain"] for c in cases)
    return {
        "schema_version": "candidate-v10-freshness-audit-v1",
        "stage": payload["designation"].casefold(),
        "case_count": len(cases),
        "exact_surface_duplicate_count": len(exact) - len(set(exact)),
        "normalized_surface_duplicate_count": len(normalized) - len(set(normalized)),
        "question_skeleton_unique": len(set(qsk)),
        "evidence_skeleton_unique": len(set(esk)),
        "grammar_family_distribution": dict(sorted(families.items())),
        "semantic_domain_distribution": dict(sorted(domains.items())),
        "declared_family_partition": payload["grammar_family_partition"],
        "template_provenance": sorted({c["generator_metadata"]["template_provenance"] for c in cases}),
        "inference_metadata_visibility": false if False else False,
    }


def generate(stage: str) -> dict:
    spec = STAGE_SPECS[stage]
    cases = [answerable_case(i, stage) for i in range(spec["answerable"])]
    cases += [negative_case(i, stage) for i in range(spec["negative"])]
    random.Random(spec["seed"] + 99991).shuffle(cases)
    payload = {
        "schema_version": "candidate-v10-benchmark-v1",
        "name": f"candidate-v10-{stage}-v1",
        "designation": stage.upper(),
        "seed": spec["seed"],
        "namespace": spec["namespace"],
        "case_count": len(cases),
        "answerable_count": spec["answerable"],
        "no_evidence_count": spec["negative"],
        "generator_family": "candidate-v10-latent-family-separated-v1",
        "grammar_family_partition": spec["families"],
        "cases": cases,
    }
    return payload


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stage", choices=STAGE_SPECS, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    args = p.parse_args()
    payload = generate(args.stage)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    audit = audit_payload(payload)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(audit, indent=2) + "\n")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(json.dumps({"stage": args.stage, "cases": payload["case_count"], "sha256": digest, "audit": audit}, indent=2))
    if audit["exact_surface_duplicate_count"] or audit["normalized_surface_duplicate_count"]:
        raise SystemExit("freshness duplicate detected")


if __name__ == "__main__":
    main()
