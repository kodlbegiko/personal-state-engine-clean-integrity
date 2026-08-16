from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

STAGES = {
    "development": {"seed": 11021, "answerable": 360, "negative": 240, "families": ("L", "M", "N", "O")},
    "protected": {"seed": 22027, "answerable": 260, "negative": 160, "families": ("P", "Q")},
    "confirmatory": {"seed": 33037, "answerable": 300, "negative": 180, "families": ("R", "S", "T")},
    "final": {"seed": 44041, "answerable": 360, "negative": 240, "families": ("U", "V", "W", "X")},
}

DOMAINS = (
    {"relation": "work_role", "label": "work role", "values": ("systems analyst", "lab coordinator", "field engineer", "archive specialist", "quality planner")},
    {"relation": "software_tool", "label": "software tool", "values": ("ForgeEdit", "SlatePad", "VectorDesk", "CodeHarbor", "DraftPilot")},
    {"relation": "volunteering", "label": "volunteering", "values": ("food-bank sorting", "trail maintenance", "library shelving", "river cleanup", "meal delivery")},
    {"relation": "accommodation", "label": "accommodation", "values": ("North Garden Hotel", "Cedar House Hostel", "East Quay Lodge", "Maple Court Inn", "Harbor Guesthouse")},
    {"relation": "appointment", "label": "appointment", "values": ("dental checkup", "vision screening", "passport interview", "clinic review", "physio visit")},
    {"relation": "subscription", "label": "subscription", "values": ("Research tier", "Studio tier", "Standard tier", "Archive tier", "Team tier")},
    {"relation": "sports_team", "label": "sports team", "values": ("Valley Comets", "Harbor Falcons", "Metro Lynx", "Cedar Owls", "River Foxes")},
    {"relation": "dietary_restriction", "label": "dietary restriction", "values": ("nut-free", "sesame-free", "gluten-free", "dairy-free", "vegetarian")},
    {"relation": "language", "label": "language", "values": ("Finnish", "Catalan", "Estonian", "Malay", "Czech")},
    {"relation": "transport", "label": "commute transport", "values": ("metro", "tram", "bus", "train", "bicycle")},
    {"relation": "routine", "label": "routine", "values": ("morning journaling", "evening walk", "weekly planning", "lunch reading", "sunrise stretching")},
    {"relation": "certification", "label": "certification", "values": ("Atlas Safety Credential", "Orion Data Certificate", "Harbor First Aid License", "Cedar Lab Qualification", "Northstar Audit Credential")},
)

FIRST = (
    "Alden", "Bianca", "Corin", "Dalia", "Emil", "Farah", "Galen", "Hana", "Ivo", "Jessa",
    "Kian", "Liora", "Marek", "Nadia", "Orin", "Petra", "Quin", "Rhea", "Silas", "Tova",
    "Uma", "Vera", "Wren", "Xara", "Yuri", "Zella",
)
LAST = (
    "Voss", "Merin", "Calder", "Dorne", "Ellis", "Farrow", "Grove", "Hollis", "Ivers", "Jorin",
    "Kest", "Lorne", "Morrow", "Neris", "Oakes", "Perrin", "Quill", "Rosen", "Sayer", "Trell",
    "Ulmer", "Vale", "Wells", "Yarrow", "Zorin",
)

QUERY_TEMPLATES: dict[str, str] = {
    # Development: wh-fronting, possessive nominalization, cleft, contrastive discourse.
    "L": "For {name}, which {field} does the profile record?",
    "M": "What is the recorded {field} of {name}?",
    "N": "Which {field} is it that the record associates with {name}?",
    "O": "Regarding {name}, identify the {field} in the active profile rather than an older note.",
    # Protected: record lookup and prepositional framing.
    "P": "Profile lookup for {name}: what value is listed under {field}?",
    "Q": "With respect to {name}, what does the entry give for {field}?",
    # Confirmatory: slot-filling, appositive subject frame, yes-form reformulated request.
    "R": "Which value fills {name}'s {field} slot in the record?",
    "S": "For {field}, what recorded value belongs to {name}, the profile subject?",
    "T": "Can the profile state the {field} recorded for {name}?",
    # Final: relative/descriptive record forms and discourse-fronted retrieval.
    "U": "Reading the entry for {name}, what is specified as the {field}?",
    "V": "For the {field} associated with {name}, which value does the profile give?",
    "W": "From {name}'s entry, retrieve the recorded {field} value.",
    "X": "For {name}, what value does the profile give under {field}?",
}

RELEVANT_TEMPLATES: dict[str, str] = {
    "L": "The profile states that {name}'s {field} is {value}.",
    "M": "{name}'s {field} is {value}.",
    "N": "For {name}, the {field} is recorded as {value}.",
    "O": "The active profile shows that {name}'s {field} is {value}.",
    "P": "Under {field}, {name} is recorded as {value}.",
    "Q": "The {field} assigned to {name} is {value}.",
    "R": "In the record, {name}'s {field} is {value}.",
    "S": "The value recorded for {name}'s {field} is {value}.",
    "T": "The profile states that {name}'s {field} is {value}.",
    "U": "The entry states that {name}'s {field} is {value}.",
    "V": "{name} is listed with {field}: {value}.",
    "W": "Recorded for {name}: the {field} is {value}.",
    "X": "For {name}, the record shows that the {field} is {value}.",
}

ELIGIBLE_DISTRACTOR_TEMPLATES: dict[str, str] = {
    "L": "Earlier profile snapshot — {name}'s {field}: {value}.",
    "M": "Last year, the entry for {name} gave {field}: {value}.",
    "N": "Before the newer entry, {name}'s {field}: {value}.",
    "O": "Historically, the profile for {name} noted {field}: {value}.",
    "P": "Reference note about {name}'s {field}: {value}.",
    "Q": "A discussion note about {name}'s {field}: {value}.",
    "R": "Narrative note about {name}'s {field}: {value}.",
    "S": "Earlier entry for {name} — {field}: {value}.",
    "T": "Last month, the profile for {name} gave {field}: {value}.",
    "U": "Prior profile snapshot for {name} — {field}: {value}.",
    "V": "Profile note about {name}'s {field}: {value}.",
    "W": "Before the active entry, {name}'s {field}: {value}.",
    "X": "Historical note about {name}'s {field}: {value}.",
}

STRUCTURAL_MECHANISM = {
    "L": "wh_fronted_profile_record",
    "M": "nominalized_of_possessive",
    "N": "cleft_association_question",
    "O": "contrastive_discourse_request",
    "P": "record_lookup_colon_frame",
    "Q": "prepositional_entry_frame",
    "R": "slot_filling_possessive",
    "S": "appositive_subject_frame",
    "T": "reformulated_can_profile_state",
    "U": "entry_participial_fronting",
    "V": "relative_association_frame",
    "W": "imperative_possessive_retrieval",
    "X": "discourse_fronted_under_field",
}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")


def person(stage: str, index: int) -> str:
    stage_tag = {"development": "D", "protected": "P", "confirmatory": "C", "final": "F"}[stage]
    return f"{FIRST[index % len(FIRST)]} {LAST[(index * 7 + 3) % len(LAST)]}{stage_tag}{index:03d}"


def other_person(stage: str, index: int) -> str:
    return person(stage, index + 10000)


def choose_values(domain: dict[str, Any], index: int) -> tuple[str, str, str]:
    values = domain["values"]
    return (
        values[index % len(values)],
        values[(index + 1) % len(values)],
        values[(index + 2) % len(values)],
    )


def timestamp(day_offset: int) -> str:
    # Fixed synthetic time axis; no wall-clock dependency.
    return f"2028-04-{10 + day_offset:02d}T09:00:00+00:00"


def answerable_case(stage: str, family: str, index: int, rng: random.Random) -> dict[str, Any]:
    domain = DOMAINS[(index * 5 + rng.randrange(len(DOMAINS))) % len(DOMAINS)]
    wrong_domain = DOMAINS[(DOMAINS.index(domain) + 1 + (index % (len(DOMAINS) - 1))) % len(DOMAINS)]
    name = person(stage, index)
    wrong_name = other_person(stage, index)
    value, old_value, uncertain_value = choose_values(domain, index)
    query = QUERY_TEMPLATES[family].format(name=name, field=domain["label"])
    relevant = RELEVANT_TEMPLATES[family].format(name=name, field=domain["label"], value=value)
    eligible_distractor = ELIGIBLE_DISTRACTOR_TEMPLATES[family].format(
        name=name, field=domain["label"], value=old_value
    )
    wrong_relation_value = wrong_domain["values"][(index + 2) % len(wrong_domain["values"])]

    memories = [
        {
            "id": f"CV11-{stage[:3].upper()}-A-{index:03d}-rel",
            "speaker": "user",
            "text": relevant,
            "timestamp": timestamp(1),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-A-{index:03d}-eligible-decoy",
            "speaker": "user",
            "text": eligible_distractor,
            # Deliberately newer to pressure Candidate-v2 lexical/recency ordering.
            "timestamp": timestamp(3),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-A-{index:03d}-uncertain",
            "speaker": "user",
            "text": f"{name}'s {domain['label']} is perhaps {uncertain_value}.",
            "timestamp": timestamp(4),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-A-{index:03d}-wrong-subject",
            "speaker": "user",
            "text": f"{wrong_name}'s {domain['label']} is {old_value}.",
            "timestamp": timestamp(4),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-A-{index:03d}-wrong-relation",
            "speaker": "user",
            "text": f"{name}'s {wrong_domain['label']} is {wrong_relation_value}.",
            "timestamp": timestamp(4),
        },
    ]
    rng.shuffle(memories)
    relevant_id = next(m["id"] for m in memories if m["text"] == relevant)
    return {
        "id": f"CV11-{stage.upper()}-A-{index:03d}",
        "designation": stage.upper(),
        "query": query,
        "memories": memories,
        "relevant_memory_ids": [relevant_id],
        "generator_metadata": {
            "query_grammar_family": family,
            "evidence_grammar_family": family,
            "structural_mechanism": STRUCTURAL_MECHANISM[family],
            "semantic_domain": domain["relation"],
            "template_provenance": f"candidate-v11:{stage}:{family}:answerable:v1",
            "polarity": "answerable",
        },
        "provenance": f"candidate-v11-fresh-generator:{stage}:answerable:{index}",
    }


def negative_case(stage: str, family: str, index: int, rng: random.Random) -> dict[str, Any]:
    domain = DOMAINS[(index * 7 + rng.randrange(len(DOMAINS))) % len(DOMAINS)]
    wrong_domain = DOMAINS[(DOMAINS.index(domain) + 3 + (index % (len(DOMAINS) - 1))) % len(DOMAINS)]
    name = person(stage, 5000 + index)
    wrong_name = other_person(stage, 5000 + index)
    value, alt_value, _ = choose_values(domain, index + 2)
    query = QUERY_TEMPLATES[family].format(name=name, field=domain["label"])
    wrong_relation_value = wrong_domain["values"][(index + 1) % len(wrong_domain["values"])]
    memories = [
        {
            "id": f"CV11-{stage[:3].upper()}-N-{index:03d}-novalue",
            "speaker": "user",
            "text": f"No verified value is available for {name}'s {domain['label']}.",
            "timestamp": timestamp(4),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-N-{index:03d}-uncertain",
            "speaker": "user",
            "text": f"{name}'s {domain['label']} is perhaps {value}.",
            "timestamp": timestamp(4),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-N-{index:03d}-wrong-subject",
            "speaker": "user",
            "text": f"{wrong_name}'s {domain['label']} is {alt_value}.",
            "timestamp": timestamp(4),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-N-{index:03d}-agenda",
            "speaker": "user",
            "text": f"Agenda item: discuss {name}'s {domain['label']} at a later meeting.",
            "timestamp": timestamp(4),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-N-{index:03d}-wrong-relation",
            "speaker": "user",
            "text": f"{name}'s {wrong_domain['label']} is {wrong_relation_value}.",
            "timestamp": timestamp(4),
        },
    ]
    rng.shuffle(memories)
    return {
        "id": f"CV11-{stage.upper()}-N-{index:03d}",
        "designation": stage.upper(),
        "query": query,
        "memories": memories,
        "relevant_memory_ids": [],
        "generator_metadata": {
            "query_grammar_family": family,
            "evidence_grammar_family": family,
            "structural_mechanism": STRUCTURAL_MECHANISM[family],
            "semantic_domain": domain["relation"],
            "template_provenance": f"candidate-v11:{stage}:{family}:negative:v1",
            "polarity": "no_evidence_adversarial",
        },
        "provenance": f"candidate-v11-fresh-generator:{stage}:negative:{index}",
    }


def generate(stage: str) -> dict[str, Any]:
    config = STAGES[stage]
    rng = random.Random(config["seed"])
    families = config["families"]
    answerable = [
        answerable_case(stage, families[i % len(families)], i, rng)
        for i in range(config["answerable"])
    ]
    negatives = [
        negative_case(stage, families[i % len(families)], i, rng)
        for i in range(config["negative"])
    ]
    cases = answerable + negatives
    rng.shuffle(cases)
    return {
        "schema_version": "candidate-v11-benchmark-v1",
        "name": f"candidate-v11-{stage}-v1",
        "stage": stage,
        "seed": config["seed"],
        "case_count": len(cases),
        "answerable_count": len(answerable),
        "no_evidence_count": len(negatives),
        "grammar_families": list(families),
        "generator_design": "stage-separated structural grammar mechanisms with semantic competition and adversarial no-evidence cases",
        "cases": cases,
        "monetary_cost_usd": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=tuple(STAGES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = generate(args.stage)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    args.output.write_text(encoded)
    print(json.dumps({
        "stage": args.stage,
        "seed": payload["seed"],
        "case_count": payload["case_count"],
        "answerable_count": payload["answerable_count"],
        "no_evidence_count": payload["no_evidence_count"],
        "families": payload["grammar_families"],
        "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
    }, indent=2))


if __name__ == "__main__":
    main()
