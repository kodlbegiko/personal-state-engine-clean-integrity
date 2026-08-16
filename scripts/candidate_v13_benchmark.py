from __future__ import annotations

"""Candidate-v13 preregistered benchmark generator.

The module contains generator logic only. It never reads historical formal
payloads. Development may be materialized after the preregistration lock.
Formal stages require explicit formal authorization from the frozen runner.
"""

import argparse
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STAGES = {
    "development": {
        "seed": 13013, "total": 900, "answerable": 540, "no_evidence": 360,
        "prefix": "D", "designation": "DEVELOPMENT",
        "grammar": ("V13-DG1","V13-DG2","V13-DG3","V13-DG4","V13-DG5","V13-DG6"),
        "discourse": ("V13-DD1","V13-DD2","V13-DD3","V13-DD4","V13-DD5","V13-DD6"),
    },
    "protected": {
        "seed": 26039, "total": 720, "answerable": 450, "no_evidence": 270,
        "prefix": "P", "designation": "PROTECTED",
        "grammar": ("V13-PG1","V13-PG2","V13-PG3","V13-PG4","V13-PG5"),
        "discourse": ("V13-PD1","V13-PD2","V13-PD3","V13-PD4","V13-PD5"),
    },
    "confirmatory": {
        "seed": 39019, "total": 720, "answerable": 450, "no_evidence": 270,
        "prefix": "C", "designation": "CONFIRMATORY",
        "grammar": ("V13-CG1","V13-CG2","V13-CG3","V13-CG4","V13-CG5"),
        "discourse": ("V13-CD1","V13-CD2","V13-CD3","V13-CD4","V13-CD5"),
    },
    "final": {
        "seed": 52027, "total": 900, "answerable": 558, "no_evidence": 342,
        "prefix": "F", "designation": "FINAL",
        "grammar": ("V13-FG1","V13-FG2","V13-FG3","V13-FG4","V13-FG5","V13-FG6"),
        "discourse": ("V13-FD1","V13-FD2","V13-FD3","V13-FD4","V13-FD5","V13-FD6"),
    },
}

RELATIONS = (
    "language", "work_role", "subscription", "software_tool",
    "volunteering", "membership", "status", "appointment", "routine",
    "travel_plan", "communication_channel", "project_ownership",
)
RELATION_TEXT = {
    "language": "language", "work_role": "work role", "subscription": "subscription",
    "software_tool": "software tool", "volunteering": "volunteering",
    "membership": "membership", "status": "status", "appointment": "appointment",
    "routine": "routine", "travel_plan": "travel plan",
    "communication_channel": "communication channel",
    "project_ownership": "project ownership",
}
VALUE_PREFIX = {
    "language": "Lingua", "work_role": "Role", "subscription": "Plan",
    "software_tool": "Tool", "volunteering": "Civic", "membership": "Guild",
    "status": "State", "appointment": "Visit", "routine": "Ritual",
    "travel_plan": "Way", "communication_channel": "Channel",
    "project_ownership": "Project",
}
STRUCTURAL = ("S1","S2","S3","S4","S5","S6","S7")
NEGATIVE_STRUCTURAL = ("S1","S2","S3","S4","S5","S6")
FIRST = (
    "Aren","Belen","Cairn","Dessa","Eron","Falen","Garin","Hessa",
    "Iven","Jalen","Korin","Lessa","Maren","Neris","Oren","Pella",
    "Quin","Ressa","Soren","Tarin","Ulen","Vessa","Wren","Yara",
)
LAST = (
    "Aster","Borel","Cerin","Davor","Eris","Faron","Galen","Horel",
    "Ivor","Jorin","Karel","Lorin","Meris","Navor","Orin","Parel",
    "Quarel","Rovin","Sarel","Toren","Uvar","Vorel","Warin","Yorin",
)


def _entity(stage_prefix: str, i: int, offset: int = 0) -> str:
    j = i + offset
    return f"{FIRST[j % len(FIRST)]} {LAST[(j * 7 + 5) % len(LAST)]} V13{stage_prefix}{j:05d}"


def _value(stage_prefix: str, relation: str, i: int, variant: str) -> str:
    return f"{VALUE_PREFIX[relation]}-{stage_prefix}-{variant}-{i:05d}"


def _memory(mid: str, text: str, day: int) -> dict:
    return {"id": mid, "speaker": "user", "text": text,
            "timestamp": f"2037-03-{day:02d}T09:00:00+00:00"}


def _query(stage: str, family: str, name: str, distractor: str,
           relation: str, other_relation: str) -> str:
    r = RELATION_TEXT[relation]
    o = RELATION_TEXT[other_relation]
    templates = {
        "V13-DG1": "Which {r} is stated for {name}?",
        "V13-DG2": "{name}'s recorded {r}: what value is supported?",
        "V13-DG3": "Review the context. What {r} is documented for {name}?",
        "V13-DG4": "For {name} (the record subject), which {r} is supported?",
        "V13-DG5": "Currently, which {r} is stated for {name}?",
        "V13-DG6": "Contrast {distractor} with {name}; for {name}, which {r} is supported?",
        "V13-PG1": "For {name}, what {r} is recorded by the evidence?",
        "V13-PG2": "Among records concerning {name}, identify the subject whose {r} is requested.",
        "V13-PG3": "As of now, for {name}, identify the {r} on record.",
        "V13-PG4": "Can you determine, from the record for {name}, what their {r} is?",
        "V13-PG5": "A separate {o} detail also appears; for {name}, which {r} is supported?",
        "V13-CG1": "It is {name} whose {r} is being asked about; what value is supported?",
        "V13-CG2": "This record concerns {name}. For them, which {r} is supported?",
        "V13-CG3": "{name} is the subject. And their {r}?",
        "V13-CG4": "Do not use the {o} detail. For {name}, which {r} is supported?",
        "V13-CG5": "Although a tentative note exists, identify {name}'s current {r}.",
        "V13-FG1": "A narrative note introduces several facts. Within it, what {r} is supported for {name}?",
        "V13-FG2": "The file introduces {name}. For that person, which {r} is currently supported?",
        "V13-FG3": "Concerning {name}, the requested relation is their {r}; identify its supported value.",
        "V13-FG4": "CURRENT {r} :: {name} :: which value is supported?",
        "V13-FG5": "Compare {distractor}, {name}, and another record subject; only for {name}, which {r} is supported?",
        "V13-FG6": "Conflicting context exists around the file. Which {r} is directly supported for {name}?",
    }
    return templates[family].format(name=name, distractor=distractor, r=r, o=o)


def _gold_text(name: str, relation: str, value: str, structural: str) -> str:
    r = RELATION_TEXT[relation]
    if structural == "S3":
        return f"Currently, {name}'s {r} is recorded as {value}."
    if structural == "S7":
        return f"{name}'s {r} is recorded as {value}."
    return f"{name}'s {r} is {value}."


def _answerable(stage: str, i: int, family: str, discourse: str, structural: str) -> dict:
    cfg = STAGES[stage]
    p = cfg["prefix"]
    relation = RELATIONS[(i * 7 + 2) % len(RELATIONS)]
    other_relation = RELATIONS[(RELATIONS.index(relation) + 5) % len(RELATIONS)]
    name = _entity(p, i)
    wrong_name = _entity(p, i, 40000)
    third_name = _entity(p, i, 50000)
    gold_value = _value(p, relation, i, "G")
    alt_value = _value(p, relation, i, "A")
    wrong_rel_value = _value(p, other_relation, i, "R")
    case_id = f"CV13-{p}-A-{i:05d}"
    gold_id = f"{case_id}-gold"
    memories = [
        _memory(gold_id, _gold_text(name, relation, gold_value, structural), 20),
        _memory(f"{case_id}-uncertain", f"{name}'s {RELATION_TEXT[relation]} is perhaps {alt_value}.", 22),
        _memory(f"{case_id}-wrong-subject", f"{wrong_name}'s {RELATION_TEXT[relation]} is {alt_value}.", 23),
        _memory(f"{case_id}-wrong-relation", f"{name}'s {RELATION_TEXT[other_relation]} is {wrong_rel_value}.", 23),
        _memory(f"{case_id}-contradiction", f"{name}'s {RELATION_TEXT[relation]} is not {alt_value}.", 24),
        _memory(f"{case_id}-novalue", f"No verified value is available for {name}'s {RELATION_TEXT[relation]}.", 24),
    ]
    relevant = [gold_id]
    preferred = gold_id
    if structural == "S3":
        memories.append(_memory(f"{case_id}-historical",
            f"Previously, {name}'s {RELATION_TEXT[relation]} was {alt_value}.", 5))
    if structural == "S7":
        secondary_id = f"{case_id}-secondary"
        memories.append(_memory(secondary_id,
            f"{name}'s {RELATION_TEXT[relation]} is {alt_value}.", 19))
        relevant.append(secondary_id)
    query = _query(stage, family, name, wrong_name, relation, other_relation)
    return {
        "id": case_id, "designation": cfg["designation"], "query": query,
        "memories": memories, "relevant_memory_ids": relevant,
        "preferred_memory_id": preferred,
        "generator_metadata": {
            "grammar_family": family, "discourse_family": discourse,
            "structural_family": structural,
            "template_provenance": f"candidate-v13:{stage}:{family}:{discourse}:{structural}:answerable:v1",
            "gold_frame": {"subject_entity": name, "relation_frame": relation,
                           "temporal_scope": "CURRENT", "answer_type": "RELATION_VALUE"},
            "third_entity": third_name,
        },
    }


def _negative(stage: str, i: int, family: str, discourse: str, structural: str) -> dict:
    cfg = STAGES[stage]
    p = cfg["prefix"]
    relation = RELATIONS[(i * 5 + 1) % len(RELATIONS)]
    other_relation = RELATIONS[(RELATIONS.index(relation) + 7) % len(RELATIONS)]
    name = _entity(p, i, 20000)
    wrong_name = _entity(p, i, 60000)
    uncertain = _value(p, relation, i + 20000, "N")
    wrong_rel_value = _value(p, other_relation, i + 20000, "W")
    case_id = f"CV13-{p}-N-{i:05d}"
    memories = [
        _memory(f"{case_id}-uncertain", f"{name}'s {RELATION_TEXT[relation]} is perhaps {uncertain}.", 22),
        _memory(f"{case_id}-agenda", f"Agenda item: discuss {name}'s {RELATION_TEXT[relation]} during a later review.", 22),
        _memory(f"{case_id}-wrong-subject", f"{wrong_name}'s {RELATION_TEXT[relation]} is {uncertain}.", 23),
        _memory(f"{case_id}-wrong-relation", f"{name}'s {RELATION_TEXT[other_relation]} is {wrong_rel_value}.", 23),
        _memory(f"{case_id}-contradiction", f"{name}'s {RELATION_TEXT[relation]} is not {uncertain}.", 24),
        _memory(f"{case_id}-novalue", f"No verified value is available for {name}'s {RELATION_TEXT[relation]}.", 24),
    ]
    if structural == "S3":
        memories.append(_memory(f"{case_id}-historical",
            f"Previously, {name}'s {RELATION_TEXT[relation]} was {uncertain}.", 4))
    query = _query(stage, family, name, wrong_name, relation, other_relation)
    return {
        "id": case_id, "designation": cfg["designation"], "query": query,
        "memories": memories, "relevant_memory_ids": [], "preferred_memory_id": None,
        "generator_metadata": {
            "grammar_family": family, "discourse_family": discourse,
            "structural_family": structural,
            "template_provenance": f"candidate-v13:{stage}:{family}:{discourse}:{structural}:negative:v1",
            "gold_frame": {"subject_entity": name, "relation_frame": relation,
                           "temporal_scope": "CURRENT", "answer_type": "RELATION_VALUE"},
        },
    }


def materialize(stage: str, output: Path | None = None, formal_authorized: bool = False) -> Path:
    if stage not in STAGES:
        raise ValueError(f"unknown stage: {stage}")
    if stage != "development" and not formal_authorized:
        raise RuntimeError("formal stage materialization requires frozen-runner authorization")
    cfg = STAGES[stage]
    rng = random.Random(cfg["seed"])
    cases: list[dict] = []
    for i in range(1, cfg["answerable"] + 1):
        family = cfg["grammar"][(i - 1) % len(cfg["grammar"])]
        discourse = cfg["discourse"][(i * 3 + 1) % len(cfg["discourse"])]
        structural = STRUCTURAL[(i - 1) % len(STRUCTURAL)]
        cases.append(_answerable(stage, i, family, discourse, structural))
    for i in range(1, cfg["no_evidence"] + 1):
        family = cfg["grammar"][(i + 2) % len(cfg["grammar"])]
        discourse = cfg["discourse"][(i * 2 + 3) % len(cfg["discourse"])]
        structural = NEGATIVE_STRUCTURAL[(i - 1) % len(NEGATIVE_STRUCTURAL)]
        cases.append(_negative(stage, i, family, discourse, structural))
    rng.shuffle(cases)
    assert len(cases) == cfg["total"]
    assert sum(bool(c["relevant_memory_ids"]) for c in cases) == cfg["answerable"]
    assert sum(not c["relevant_memory_ids"] for c in cases) == cfg["no_evidence"]
    assert len({c["id"] for c in cases}) == len(cases)
    assert len({c["query"] for c in cases}) == len(cases)
    structural_counts = {s: sum(c["generator_metadata"]["structural_family"] == s for c in cases)
                         for s in STRUCTURAL}
    if stage != "development":
        assert all(count / len(cases) >= 0.08 for count in structural_counts.values())
    queries = [c["query"] for c in cases]
    memories = [m["text"] for c in cases for m in c["memories"]]
    entities = [c["generator_metadata"]["gold_frame"]["subject_entity"] for c in cases]
    payload = {
        "schema_version": "candidate-v13-benchmark-v1", "candidate": "v13",
        "stage": stage, "designation": cfg["designation"], "seed": cfg["seed"],
        "case_count": len(cases), "answerable_count": cfg["answerable"],
        "no_evidence_count": cfg["no_evidence"], "grammar_families": list(cfg["grammar"]),
        "discourse_families": list(cfg["discourse"]),
        "structural_family_counts": structural_counts,
        "fresh_generation_policy": {
            "reads_historical_formal_payloads": False,
            "historical_formal_strings_used": False,
            "historical_formal_entities_used": False,
            "historical_formal_values_used": False,
            "synthetic_stage_identity_namespace": True,
            "synthetic_stage_value_namespace": True,
        },
        "integrity_digest": {
            "query_sha256": hashlib.sha256("\n".join(sorted(queries)).encode()).hexdigest(),
            "memory_text_sha256": hashlib.sha256("\n".join(sorted(memories)).encode()).hexdigest(),
            "entity_sha256": hashlib.sha256("\n".join(sorted(entities)).encode()).hexdigest(),
        },
        "cases": cases,
    }
    if output is None:
        output = ROOT / "experiments/benchmarks" / f"candidate-v13-{stage}-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=tuple(STAGES), required=True)
    parser.add_argument("--formal-authorized", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    materialize(args.stage, args.output, args.formal_authorized)


if __name__ == "__main__":
    main()
