from __future__ import annotations

"""Generate Candidate-v12 preregistered Development-only benchmark.

This generator is independent of Candidate-v11 Protected payload text. It never
reads historical Protected files. Entities, values, IDs, grammar templates and
discourse constructions are fresh and synthetic.
"""

import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/benchmarks/candidate-v12-development-v1.json"
SEED = 12031
ANSWERABLE_COUNT = 432
NO_EVIDENCE_COUNT = 288

RELATIONS = (
    "language",
    "work role",
    "subscription",
    "software tool",
    "volunteering",
    "membership",
    "status",
    "appointment",
    "routine",
    "travel plan",
    "communication channel",
    "project ownership",
)

FIRST = (
    "Neris", "Velan", "Soria", "Tavian", "Elira", "Coren", "Maelis", "Joren",
    "Liora", "Perris", "Zevan", "Aveline", "Roven", "Selka", "Toren", "Ilyra",
    "Darian", "Vessa", "Kaelen", "Miren", "Orel", "Talise", "Brenna", "Cyren",
)
LAST = (
    "Varin", "Kelor", "Saren", "Norel", "Tavin", "Leris", "Maren", "Dovin",
    "Ceris", "Faren", "Ralis", "Voren", "Kiren", "Selin", "Parel", "Javis",
    "Naven", "Toris", "Valen", "Coris", "Merin", "Solvar", "Darel", "Yorin",
)

GRAMMAR_FAMILIES = ("DA", "DB", "DC", "DD", "DE", "DF")
DISCOURSE_FAMILIES = ("D0", "D1", "D2", "D3", "D4", "D5")


def _entity(i: int) -> str:
    # Synthetic identity namespace is unique to Candidate-v12 Development.
    return f"{FIRST[i % len(FIRST)]} {LAST[(i * 7 + 3) % len(LAST)]}D{i:04d}"


def _value(relation: str, i: int, variant: str) -> str:
    prefix = {
        "language": "Lingua",
        "work role": "Rolecraft",
        "subscription": "Planform",
        "software tool": "Toolset",
        "volunteering": "Civicwork",
        "membership": "Guildmark",
        "status": "Stateflag",
        "appointment": "Visitmark",
        "routine": "Ritualmark",
        "travel plan": "Waymark",
        "communication channel": "Channelmark",
        "project ownership": "Projectmark",
    }[relation]
    return f"{prefix}-{variant}-{i:04d}"


def _query(name: str, relation: str, family: str) -> str:
    templates = {
        "DA": "Which {relation} is stated for {name}?",
        "DB": "Reference material concerns {name}. What is the stated {relation}?",
        "DC": "For this task, the subject is {name}; identify the supported {relation}.",
        "DD": "Background material is supplied first. The person in scope is {name}. Which {relation} is stated?",
        "DE": "Ignore surrounding context; {name} is the target individual. State the supported {relation}.",
        "DF": "A factual request about {name} asks which {relation} is supported.",
    }
    return templates[family].format(name=name, relation=relation)


def _memory(mid: str, text: str, day: int) -> dict:
    return {
        "id": mid,
        "speaker": "user",
        "text": text,
        "timestamp": f"2032-02-{day:02d}T09:00:00+00:00",
    }


def _answerable_case(i: int, family: str, discourse: str, relation: str) -> dict:
    name = _entity(i)
    wrong_name = _entity(i + 10000)
    other_relation = RELATIONS[(RELATIONS.index(relation) + 5) % len(RELATIONS)]
    gold_value = _value(relation, i, "G")
    alt_value = _value(relation, i, "U")
    wrong_rel_value = _value(other_relation, i, "R")
    case_id = f"CV12-DEV-A-{i:04d}"
    gold_id = f"CV12-DEV-A-{i:04d}-gold"
    memories = [
        _memory(gold_id, f"{name}'s {relation} is {gold_value}.", 10),
        _memory(f"{case_id}-uncertain", f"{name}'s {relation} is perhaps {alt_value}.", 14),
        _memory(f"{case_id}-wrong-subject", f"{wrong_name}'s {relation} is {alt_value}.", 15),
        _memory(f"{case_id}-wrong-relation", f"{name}'s {other_relation} is {wrong_rel_value}.", 15),
        _memory(f"{case_id}-novalue", f"No verified value is available for {name}'s {relation}.", 15),
    ]
    return {
        "id": case_id,
        "designation": "DEVELOPMENT",
        "query": _query(name, relation, family),
        "memories": memories,
        "relevant_memory_ids": [gold_id],
        "generator_metadata": {
            "grammar_family": family,
            "discourse_family": discourse,
            "template_provenance": f"candidate-v12:development:{family}:{discourse}:answerable:v1",
            "gold_frame": {
                "subject_entity": name,
                "relation_frame": relation.replace(" ", "_"),
                "temporal_scope": "CURRENT",
                "answer_type": "RELATION_VALUE",
            },
        },
    }


def _negative_case(i: int, family: str, discourse: str, relation: str) -> dict:
    name = _entity(i + 20000)
    wrong_name = _entity(i + 30000)
    other_relation = RELATIONS[(RELATIONS.index(relation) + 7) % len(RELATIONS)]
    uncertain = _value(relation, i + 20000, "N")
    wrong_rel_value = _value(other_relation, i + 20000, "W")
    case_id = f"CV12-DEV-N-{i:04d}"
    memories = [
        _memory(f"{case_id}-uncertain", f"{name}'s {relation} is perhaps {uncertain}.", 14),
        _memory(f"{case_id}-agenda", f"Agenda item: discuss {name}'s {relation} during a later review.", 14),
        _memory(f"{case_id}-wrong-subject", f"{wrong_name}'s {relation} is {uncertain}.", 15),
        _memory(f"{case_id}-wrong-relation", f"{name}'s {other_relation} is {wrong_rel_value}.", 15),
        _memory(f"{case_id}-novalue", f"No verified value is available for {name}'s {relation}.", 15),
    ]
    return {
        "id": case_id,
        "designation": "DEVELOPMENT",
        "query": _query(name, relation, family),
        "memories": memories,
        "relevant_memory_ids": [],
        "generator_metadata": {
            "grammar_family": family,
            "discourse_family": discourse,
            "template_provenance": f"candidate-v12:development:{family}:{discourse}:negative:v1",
            "gold_frame": {
                "subject_entity": name,
                "relation_frame": relation.replace(" ", "_"),
                "temporal_scope": "CURRENT",
                "answer_type": "RELATION_VALUE",
            },
        },
    }


def main() -> None:
    rng = random.Random(SEED)
    cases = []
    for i in range(1, ANSWERABLE_COUNT + 1):
        family = GRAMMAR_FAMILIES[(i - 1) % len(GRAMMAR_FAMILIES)]
        discourse = DISCOURSE_FAMILIES[(i * 5 + 1) % len(DISCOURSE_FAMILIES)]
        relation = RELATIONS[(i * 7 + 2) % len(RELATIONS)]
        cases.append(_answerable_case(i, family, discourse, relation))
    for i in range(1, NO_EVIDENCE_COUNT + 1):
        family = GRAMMAR_FAMILIES[(i + 2) % len(GRAMMAR_FAMILIES)]
        discourse = DISCOURSE_FAMILIES[(i * 3 + 4) % len(DISCOURSE_FAMILIES)]
        relation = RELATIONS[(i * 5 + 1) % len(RELATIONS)]
        cases.append(_negative_case(i, family, discourse, relation))

    rng.shuffle(cases)
    queries = [c["query"] for c in cases]
    memory_texts = [m["text"] for c in cases for m in c["memories"]]
    entity_names = [c["generator_metadata"]["gold_frame"]["subject_entity"] for c in cases]

    assert len(cases) == 720
    assert len(set(queries)) == len(queries)
    assert len(set(entity_names)) == len(entity_names)
    assert all("P" not in c["generator_metadata"]["grammar_family"] for c in cases)

    payload = {
        "schema_version": "candidate-v12-development-benchmark-v1",
        "candidate": "v12",
        "designation": "DEVELOPMENT",
        "seed": SEED,
        "case_count": len(cases),
        "answerable_count": ANSWERABLE_COUNT,
        "no_evidence_count": NO_EVIDENCE_COUNT,
        "grammar_families": list(GRAMMAR_FAMILIES),
        "discourse_families": list(DISCOURSE_FAMILIES),
        "fresh_generation_policy": {
            "reads_candidate_v11_protected": False,
            "historical_protected_strings_used": False,
            "historical_protected_entities_used": False,
            "historical_protected_values_used": False,
            "synthetic_identity_namespace": True,
            "synthetic_value_namespace": True,
        },
        "integrity_digest": {
            "query_sha256": hashlib.sha256("\n".join(sorted(queries)).encode()).hexdigest(),
            "memory_text_sha256": hashlib.sha256("\n".join(sorted(memory_texts)).encode()).hexdigest(),
        },
        "cases": cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
